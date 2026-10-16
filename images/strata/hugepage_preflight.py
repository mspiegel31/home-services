#!/usr/bin/env python3
"""Keep a reserved hugetlb pool from starving an ordinary-RAM fallback."""
import os
from pathlib import Path
import sys


def require_hugepages(required, meminfo):
    fields = {}
    for line in meminfo.splitlines():
        key, _, value = line.partition(":")
        if key in ("HugePages_Free", "HugePages_Rsvd", "Hugepagesize"):
            fields[key] = value.split()
    free = int(fields["HugePages_Free"][0])
    reserved = int(fields["HugePages_Rsvd"][0])
    if fields["Hugepagesize"] != ["2048", "kB"]:
        raise ValueError("the expert arena requires 2 MiB hugepages")
    if required <= 0 or min(free, reserved) < 0:
        raise ValueError("hugepage counts must be nonnegative and the requirement positive")
    available = free - reserved
    if available < required:
        raise ValueError(
            f"need {required} uncommitted 2 MiB hugepages, have {available} "
            f"(HugePages_Free={free}, HugePages_Rsvd={reserved}). "
            "Release competing allocations or provision the host pool before retrying; "
            "ordinary-RAM fallback can starve the host while hugepages remain reserved"
        )


def main():
    required = os.environ.get("STRATA_REQUIRED_HUGEPAGES")
    if required is None:
        return 0
    try:
        count = int(required)
        if count <= 0:
            raise ValueError("STRATA_REQUIRED_HUGEPAGES must be a positive page count")
        require_hugepages(count, Path("/proc/meminfo").read_text())
    except (OSError, ValueError, KeyError, IndexError) as error:
        print(f"[strata] refusing to start: hugepage preflight failed: {error}", file=sys.stderr, flush=True)
        return 1
    print(f"[strata] hugepage preflight passed: {count} uncommitted 2 MiB pages available", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
