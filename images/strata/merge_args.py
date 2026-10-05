#!/usr/bin/env python3
"""Why this exists: the lane config json is written once by setup.py and never
refreshed — the engine's multi-session cache flags, the batch-slot count, the
VRAM reserve and the PLE mode are not in setup.py's env contract, and hand-edits
are lost on a reinstall. The entrypoint runs this on every start, after any
setup pass and before setup.py serves. The lane yaml's `cmd` env is the single
source of truth and wins over the config on every run:

    PARALLEL                    -> cfg["parallel"] (batch slots, 2..8)
    STRATA_VRAM_RESERVE_MIB     -> --vram-reserve-mib (256..16384)
    STRATA_PLE_IO               -> --ple-io (direct|mmap|ram)
    STRATA_VISION_MMPROJ        -> --vision + the config's vision block

Standard cache args are still left alone if the config already carries them.

The reserve and the slot cap exist because of an engine VRAM leak (verified on
the live box 2026-10-05, engine 0.1.39): Verifier::capture_batch /
capture_commit_batch in src/core/verify.cpp keep one CUDA graph pair per
distinct set of busy batch slots in std::map<uint64_t, cudaGraphExec_t>
exec_bm_, commit_bm_, keyed by batch_key(rows, S, hbase). Entries are destroyed
only in ~Verifier(), so nothing evicts them: VRAM use grows with every new slot
combination until cudaGraphInstantiate fails with
`verify: batch instantiate: out of memory` and the engine restarts.
Cost: ~9 MiB per graph pair (linear fit 8.86 MiB/pair against nvidia-smi).
Possible combinations: 2^N - 1 for N slots — 255 at parallel 8, 63 at parallel 6.
Sizing rule: the post-load free VRAM (log line `strata serve: N MiB of VRAM
free with everything loaded`) must be >= (2^PARALLEL - 1) * 9 MiB * 1.5, i.e.
>= 850 MiB at 6 slots. Distinct from upstream #776 (handled by
STRATA_VERIFY_ALL_RESIDENT=0); upstream has no issue for this one yet.

Vision: setup.py gates images per-model (UD-Q4_K_XL inherits the unsloth
family's "vision": False), so a lane that CAN serve images can't ask for them.
STRATA_VISION_MMPROJ forces the wiring; see enable_vision.

The symptom the standard args fix: with the engine's default 6 prompt-cache
checkpoints, one 90k-token chat session holds all of them, so two interleaved
sessions evict each other's chains and every context switch re-prefills the
whole prompt at ~4.4k tok/s (20 s at 90k). Measured on the IQ4_XS lane: 86.3%
prompt reuse, 9 of 80 requests at 0 reused.
"""
import json
import os
import sys

# The image encoder's fixed home in the image; the engine binary is built with
# CUDA vision (BUILD_VISION=1), so every lane can serve images once its config
# carries the two halves the engine and server.py each read.
VISION_EXE = "/opt/strata/engine/strata-vision"
VISION_RESERVE_MIB = "700"
VISION_MAX_TOKENS = 1024

STANDARD_ARGS = [
    # engine flag docs: --prompt-cache N keeps N conversation checkpoints
    # between requests, ~118 MB RAM each; 32 holds several 50-90k sessions.
    "--prompt-cache", "32",
    # --conversation-cache-mib parks idle conversations' KV in RAM so
    # returning to a chat never re-prefills. The lanes are RAM-tight (experts
    # + PLE table), hence the 8 GiB slots and the min-free floor that stops
    # parking when physical RAM runs low.
    "--conversation-cache-mib", "16384",
    "--conversation-cache-slots", "8",
    "--conversation-cache-min-free-mib", "8192",
]

# server.py's own range for cfg["parallel"]; outside it the server ignores the
# value with a warning, so refuse it here instead of writing a broken config.
PARALLEL_MIN, PARALLEL_MAX = 2, 8

# sanity bounds for STRATA_VRAM_RESERVE_MIB; the engine accepts any int but a
# typo'd reserve either starves the graph cache (see docstring) or the model.
RESERVE_MIN, RESERVE_MAX = 256, 16384

# the engine's own choices, from generate.cpp's `--ple-io direct|mmap|ram` help
PLE_IO_MODES = ("direct", "mmap", "ram")


def set_arg(args, flag, value):
    """Set `flag value` in args, inserting before --prompt-cache (or at the
    end) when the flag is absent, so the engine's own arg order is kept.
    Returns True only if args actually changed."""
    if flag in args:
        at = args.index(flag) + 1
        if at < len(args) and args[at] == value:
            return False
        if at < len(args):
            args[at] = value
        else:
            args.append(value)
        return True
    at = args.index("--prompt-cache") if "--prompt-cache" in args else len(args)
    args[at:at] = [flag, value]
    return True


def merge(path, env):
    with open(path) as f:
        cfg = json.load(f)
    args = cfg.setdefault("args", [])
    have = set(args)
    added = []
    for flag, value in zip(STANDARD_ARGS[::2], STANDARD_ARGS[1::2]):
        if flag not in have:
            args += [flag, value]
            added.append(f"{flag} {value}")
    if env.get("STRATA_VISION_MMPROJ"):
        added += enable_vision(cfg, env["STRATA_VISION_MMPROJ"])
    # after enable_vision, which inserts its own 700: the lane's env must win
    reserve = env.get("STRATA_VRAM_RESERVE_MIB", "")
    if reserve:
        if not reserve.isdigit() or not RESERVE_MIN <= int(reserve) <= RESERVE_MAX:
            print(f"[strata] STRATA_VRAM_RESERVE_MIB={reserve} is not "
                  f"{RESERVE_MIN}..{RESERVE_MAX}: leaving the config's own value",
                  flush=True)
        elif set_arg(args, "--vram-reserve-mib", str(int(reserve))):
            added.append(f"--vram-reserve-mib {int(reserve)}")
    ple = env.get("STRATA_PLE_IO", "")
    if ple:
        if ple not in PLE_IO_MODES:
            print(f"[strata] STRATA_PLE_IO={ple} is not "
                  f"{'|'.join(PLE_IO_MODES)}: leaving the config's own value",
                  flush=True)
        elif set_arg(args, "--ple-io", ple):
            added.append(f"--ple-io {ple}")
    if env.get("PARALLEL"):
        # the lane yaml's PARALLEL env is the declarative source for the batch
        # slots; an empty value leaves whatever the volume already has (the
        # engine's own default is one request at a time).
        n = int(env["PARALLEL"]) if env["PARALLEL"].isdigit() else 0
        if not PARALLEL_MIN <= n <= PARALLEL_MAX:
            print(f"[strata] PARALLEL={env['PARALLEL']} is not {PARALLEL_MIN}..{PARALLEL_MAX}: "
                  f"leaving the config's own value", flush=True)
        elif cfg.get("parallel") != n:
            cfg["parallel"] = n
            added.append(f"parallel {n}")
    if added:
        with open(path, "w") as f:
            json.dump(cfg, f, indent=1)
        print(f"[strata] standard args added to {path}: {'; '.join(added)}", flush=True)
    else:
        print(f"[strata] standard args already present in {path}", flush=True)


def enable_vision(cfg, mmproj):
    """Wire images into a lane whose setup.py refuses to (Strata gates
    UD-Q4_K_XL's vision off per-model: setup.py's MODELS entry inherits the
    unsloth family's "vision": False, so --vision yes is dropped with a warning
    and the config's vision block stays null).

    Two halves, both required: the engine binary reads --vision from args
    (without it every image request dies with "this engine was started without
    --vision"), and server.py reads the config's vision block to warm the
    encoder and route image parts. The block mirrors what setup.py writes for a
    lane it does enable (verified against the IQ4_XS and Swift lanes).

    The pack layout is not an obstacle: the unsloth family packs both quants
    with --compat-bf16, and the mmproj is the same BF16 encoder file for every
    quant of the base model.
    """
    args = cfg.setdefault("args", [])
    added = []
    if "--vision" not in args:
        at = args.index("--prompt-cache") if "--prompt-cache" in args else len(args)
        args[at:at] = ["--vision"]
        added.append("--vision")
    if set_arg(args, "--vram-reserve-mib", VISION_RESERVE_MIB):
        added.append(f"--vram-reserve-mib {VISION_RESERVE_MIB}")
    vis = cfg.get("vision")
    if not isinstance(vis, dict) or vis.get("mmproj") != mmproj:
        native = args[args.index("--native") + 1] if "--native" in args else None
        if native is None:
            print(f"[strata] {mmproj}: no --native in args, leaving vision off", flush=True)
            return added
        cfg["vision"] = {"exe": VISION_EXE, "mmproj": mmproj, "model": native,
                         "gpu": True, "max_tokens": VISION_MAX_TOKENS}
        added.append(f"vision {mmproj}")
    return added


if __name__ == "__main__":
    merge(sys.argv[1], os.environ)
