#!/usr/bin/env python3
"""Why this exists: the lane config json is written once by setup.py and never
refreshed — the engine's multi-session cache flags and the batch-slot count
are not in setup.py's env contract, and hand-edits are lost on a reinstall.
The entrypoint runs this on every start, after any setup pass and before
setup.py serves. Flags already in the config (a lane's own override) are left
alone.

The symptom it fixes: with the engine's default 6 prompt-cache checkpoints, one
90k-token chat session holds all of them, so two interleaved sessions evict
each other's chains and every context switch re-prefills the whole prompt at
~4.4k tok/s (20 s at 90k). Measured on the IQ4_XS lane: 86.3% prompt reuse,
9 of 80 requests at 0 reused.
"""
import json
import sys

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


def merge(path, parallel=None):
    with open(path) as f:
        cfg = json.load(f)
    args = cfg.setdefault("args", [])
    have = set(args)
    added = []
    for flag, value in zip(STANDARD_ARGS[::2], STANDARD_ARGS[1::2]):
        if flag not in have:
            args += [flag, value]
            added.append(f"{flag} {value}")
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


if __name__ == "__main__":
    merge(*sys.argv[1:3])
