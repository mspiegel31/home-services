#!/usr/bin/env python3
"""Why this exists: the lane config json is written once by setup.py and never
refreshed — the engine's multi-session cache flags, the batch-slot count and
the forced vision wiring are not in setup.py's env contract, and hand-edits are
lost on a reinstall. The entrypoint runs this on every start, after any setup
pass and before setup.py serves. Flags already in the config (a lane's own
override) are left alone.

Vision is the second symptom: setup.py gates images per-model (UD-Q4_K_XL
inherits the unsloth family's "vision": False), so a lane that CAN serve images
can't ask for them. STRATA_VISION_MMPROJ forces the wiring; see enable_vision.

The symptom it fixes: with the engine's default 6 prompt-cache checkpoints, one
90k-token chat session holds all of them, so two interleaved sessions evict
each other's chains and every context switch re-prefills the whole prompt at
~4.4k tok/s (20 s at 90k). Measured on the IQ4_XS lane: 86.3% prompt reuse,
9 of 80 requests at 0 reused.
"""
import json
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


def merge(path, parallel=None, vision_mmproj=None):
    with open(path) as f:
        cfg = json.load(f)
    args = cfg.setdefault("args", [])
    have = set(args)
    added = []
    for flag, value in zip(STANDARD_ARGS[::2], STANDARD_ARGS[1::2]):
        if flag not in have:
            args += [flag, value]
            added.append(f"{flag} {value}")
    if vision_mmproj:
        added += enable_vision(cfg, vision_mmproj)
    if parallel:
        # the lane yaml's PARALLEL env is the declarative source for the batch
        # slots; an empty value leaves whatever the volume already has (the
        # engine's own default is one request at a time).
        n = int(parallel) if parallel.isdigit() else 0
        if not PARALLEL_MIN <= n <= PARALLEL_MAX:
            print(f"[strata] PARALLEL={parallel} is not {PARALLEL_MIN}..{PARALLEL_MAX}: "
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
        # insert before the cache flags so the engine's own arg order is kept
        at = args.index("--prompt-cache") if "--prompt-cache" in args else len(args)
        args[at:at] = ["--vision", "--vram-reserve-mib", VISION_RESERVE_MIB]
        added.append(f"--vision --vram-reserve-mib {VISION_RESERVE_MIB}")
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
    merge(*sys.argv[1:4])
