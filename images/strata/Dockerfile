# Strata: Qwen3.8-Flash-Next on NVIDIA GPUs (https://github.com/Niko1221/Strata).
#
# Upstream's Dockerfile, fetched at a pinned commit instead of COPY'd: the
# engine and image-encoder build steps below are byte-for-byte upstream's, so a
# revision bump means re-copying them from the same file at the new SHA.
#
# Two stages: the devel flavor compiles the engine, the runtime flavor ships it.
# A locally built engine has BUILD.json source=local, so setup.py has it load the
# toolkit's libcudart/libcublas rather than pip wheels, and the runtime flavor
# carries exactly those. find_nvcc and get_llama_cpp (the zip unpack) are only
# reached when setup.py has to compile, which the pinned sources make impossible:
# a source change needs a new image, not --build (no nvcc and no git here).
#
# build-images.yml pins this image to amd64 and caches the layers below to a
# :buildcache tag in ghcr: they are GBs, and the repo-wide GHA cache is 10 GB.
# Upstream's CMakeLists FORCEs GGML_NATIVE ON unless STRATA_PORTABLE (the AVX2
# release build) or STRATA_ISA_FLOOR is given, so the engine otherwise inherits
# the build host's ISA via -march=native. The ubuntu-latest pool mixes AVX-512
# and AVX2 hosts, and a binary built on an AVX-512 host SIGILLs in
# ggml_cpu_init on an AVX2-only PC: 6f32ec0.1 (built 2026-10-05) does exactly
# that on this box's Ryzen 5700X, EVEX-encoded ymm16-19 in the ggml_cpu_init
# prologue. Both builds below pass STRATA_PORTABLE=ON.
#
# llama-swap spawns this with the upstream env contract (FAMILY, MODEL, CONTEXT,
# VISION, GPU/GPUS, LOW_RAM, HOST, PORT, API_KEY). :8080 is the engine, :8000 is
# metrics_exporter.py, which Alloy's vllm_backends scrape reads because the
# engine's own /metrics is JSON.
ARG CUDA_TAG=13.0.1-devel-ubuntu24.04@sha256:7d2f6a8c2071d911524f95061a0db363e24d27aa51ec831fcccf9e76eb72bc92
ARG CUDA_RUNTIME_TAG=13.0.1-runtime-ubuntu24.04@sha256:c3fde347d52d578c84fd644bc177bc7ec333feaf11550d990da4084d7612e4c7

FROM nvidia/cuda:${CUDA_TAG} AS builder

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 LANG=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential ca-certificates curl git libatomic1 libgomp1 \
        python3 python3-pip python3-venv unzip \
    && rm -rf /var/lib/apt/lists/*

ARG STRATA_REF=6f32ec070f23ced9f50e704d854d775da52591ab

WORKDIR /opt/strata
RUN git init -q . \
    && git remote add origin https://github.com/Niko1221/Strata.git \
    && git fetch -q --depth 1 origin "${STRATA_REF}" \
    && git checkout -q FETCH_HEAD \
    && rm -rf .git

# RTX 50 (120) only: the runtime picks the cubin matching the card, and a set
# with one arch is the fastest build. A non-Blackwell card needs its own arch
# here (RTX 30 = 86, RTX 40 = 89, A-series = 80).
ARG CUDA_ARCHITECTURES=120
ARG BUILD_VISION=1
# setup.cmake_build sizes ninja at max(2, cpu_count // 2), so the 4-vCPU runner
# compiles with -j 2: 25 of the 27 min this image takes uncached. Single-arch
# nvcc at -j 4 stays inside the runner's 16 GB. The default is sized for that
# runner, not for a local build: this box's 8 cores / 96 GB take
# --build-arg BUILD_JOBS=8 (nvcc is the RAM sink, ~2 GB per job at one arch).
ARG BUILD_JOBS=4

RUN python3 -m venv .venv \
    && .venv/bin/pip install --no-cache-dir --upgrade pip \
    && .venv/bin/pip install --no-cache-dir -r requirements.txt \
    && chmod +x setup.sh docker-entrypoint.sh

# llama.cpp at the pinned commit, then the engine and the image encoder, built
# exactly the way setup.py builds them. BUILD.json is what setup.py reads to
# decide whether an engine is current: source=local with a matching src hash
# means the first start reuses it instead of recompiling.
RUN .venv/bin/python - <<'PYEOF'
import json, os, pathlib, shutil
import setup

jobs = int(os.environ.get("BUILD_JOBS") or 0)
if jobs:
    # cmake_build's -j is max(2, cpu_count // 2) and ninja takes no env var
    os.cpu_count = lambda: 2 * jobs

llama = setup.get_llama_cpp()
nvcc, _ = setup.find_nvcc()
arch = os.environ.get("CUDA_ARCHITECTURES", "75;80;86;89;120").strip().strip('"').replace(",", ";")
vision = "gpu" if os.environ.get("BUILD_VISION", "1") == "1" else "none"

setup.cmake_build(setup.ROOT, setup.ROOT / "build", "strata",
    ["-DSTRATA_ENABLE_CUDA=ON", "-DSTRATA_BUILD_TESTS=OFF", "-DSTRATA_PORTABLE=ON",
     f"-DCMAKE_CUDA_ARCHITECTURES={arch}", f"-DCMAKE_CUDA_COMPILER={nvcc}",
     f"-DSTRATA_GGML_DIR={llama}"], None, "build-strata.bat")
if vision != "none":
    setup.cmake_build(setup.ROOT / "tools" / "vision", setup.ROOT / "build-vision", "strata-vision",
        [f"-DLLAMA_DIR={llama}", "-DSTRATA_VISION_CUDA=ON", "-DSTRATA_PORTABLE=ON",
         f"-DCMAKE_CUDA_ARCHITECTURES={arch}", f"-DCMAKE_CUDA_COMPILER={nvcc}"], None, "build-vision.bat")

eng = setup.ROOT / "engine"
eng.mkdir(exist_ok=True)
shutil.copy2(setup.ROOT / "build" / setup.EXE, eng / setup.EXE)
if vision != "none":
    shutil.copy2(setup.ROOT / "build-vision" / "bin" / setup.VEXE, eng / setup.VEXE)
bindir = pathlib.Path(nvcc).parent
meta = {"source": "local", "version": setup.source_version(),
        "archs": [int(a.split("-")[0]) for a in arch.split(";") if a.split("-")[0].isdigit()], "vision": vision,
        "cuda_dirs": [str(d) for d in (bindir, bindir / "x64", bindir.parent / "lib64") if d.is_dir()],
        "src": setup.source_hash(setup.ENGINE_SOURCES),
        "vision_src": setup.source_hash(setup.VISION_SOURCES) if vision != "none" else None}
(eng / "BUILD.json").write_text(json.dumps(meta, indent=1))
PYEOF

# the cmake trees are build-time only; the engine itself is what the container needs
RUN rm -rf build build-vision

FROM nvidia/cuda:${CUDA_RUNTIME_TAG}

# STRATA_EXECV=1: setup.py replaces itself with the server, so the server is PID 1
# and docker stop's SIGTERM reaches it (see setup.start).
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 LANG=C.UTF-8 STRATA_EXECV=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl libatomic1 libgomp1 python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/strata
COPY --from=builder /opt/strata /opt/strata

COPY metrics_exporter.py /opt/strata-exporter/metrics_exporter.py
COPY entrypoint.sh /opt/strata-exporter/entrypoint.sh
COPY merge_args.py /opt/strata-exporter/merge_args.py
COPY strata-entrypoint.sh /opt/strata/docker-entrypoint.sh
RUN chmod +x /opt/strata-exporter/entrypoint.sh /opt/strata/docker-entrypoint.sh

VOLUME ["/data"]
EXPOSE 8080 8000

ENTRYPOINT ["/opt/strata-exporter/entrypoint.sh"]
