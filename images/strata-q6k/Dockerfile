# Strata Q6K variant: identical to images/strata at the same STRATA_REF, with
# the two opt-in engine build flags Unsloth's UD-Q6_K_XL needs —
# -DSTRATA_Q6K_EXPERTS=ON (the Q6_K gate/up grouped-kernel instances) and
# -DSTRATA_MMQ_KQUANTS=ON (Q6_K in the MMQ prompt kernels). Upstream gates
# Q6_K behind these flags (docs/UNSLOTH_Q6.md: "every grouped-kernel instance
# is loaded at start and would cost other models expert slots"), so the stock
# images/strata engine refuses a Q6_K_XL pack. This image is the Q6 lane's
# engine only; keep it byte-identical to images/strata everywhere else
# (strata-entrypoint.sh is literally the same file in both), and bump
# STRATA_REF / LLAMA_CPP_COMMIT here and there together.
#
# Strata: Qwen3.8-Flash-Next on NVIDIA GPUs (https://github.com/Niko1221/Strata).
#
# Upstream's Dockerfile, fetched at a pinned commit instead of COPY'd: the
# engine build below is byte-for-byte upstream's, so a revision bump means
# re-copying it from the same file at the new SHA. The image-encoder build is
# not: upstream builds both engines in one step, which couples the encoder's
# ~16 min llama.cpp compile to every Strata bump; the vision stage decouples
# them.
#
# Four stages: src checks the pinned revision out, vision builds the image
# encoder against llama.cpp, builder compiles the engine, and the runtime
# flavor ships both. A locally built engine has BUILD.json source=local, so
# setup.py has it load the toolkit's libcudart/libcublas rather than pip
# wheels, and the runtime flavor carries exactly those. find_nvcc and
# get_llama_cpp (the zip unpack) are only reached when setup.py has to
# compile, which the pinned sources make impossible: a source change needs a
# new image, not --build (no nvcc and no git here).
#
# build-images.yml pins this image to amd64 and caches the layers below to a
# :buildcache tag in ghcr: they are GBs, and the repo-wide GHA cache is 10 GB.
# Upstream's CMakeLists FORCEs GGML_NATIVE ON unless STRATA_PORTABLE (the AVX2
# release build) or STRATA_ISA_FLOOR is given, so the engine otherwise inherits
# the build host's ISA via -march=native. The ubuntu-latest pool mixes AVX-512
# and AVX2 hosts, and a binary built on an AVX-512 host SIGILLs in
# ggml_cpu_init on an AVX2-only PC: 6f32ec0.1 (built 2026-10-05) does exactly
# that on this box's Ryzen 5700X, EVEX-encoded ymm16-19 in the ggml_cpu_init
# prologue. Both compiles below pass STRATA_PORTABLE=ON.
#
# The cache decoupling: the encoder links all of llama.cpp, and ggml-cuda's
# template instances are ~16 of the ~20 min cold compile. Those objects depend
# on setup.py's llama pin, not on STRATA_REF, so the encoder compiles in its
# own stage and takes the encoder's sources as a content-keyed COPY: a bump
# that leaves tools/vision alone replays the encoder from :buildcache, and the
# build costs the engine's ~5 min alone. LLAMA_CPP_COMMIT must equal setup.py's
# pin; builder asserts it after the checkout.
ARG CUDA_TAG=13.0.1-devel-ubuntu24.04@sha256:7d2f6a8c2071d911524f95061a0db363e24d27aa51ec831fcccf9e76eb72bc92
ARG CUDA_RUNTIME_TAG=13.0.1-runtime-ubuntu24.04@sha256:c3fde347d52d578c84fd644bc177bc7ec333feaf11550d990da4084d7612e4c7

# The pinned revision, checked out once for both compile stages. Downstream
# stages take it as a COPY, not a checkout RUN: a COPY's cache key follows the
# copied files' content, so a bump that changes nothing under tools/vision
# leaves the encoder's compile layer keyed the same.
FROM nvidia/cuda:${CUDA_TAG} AS src

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

ARG STRATA_REF=61b3fb5dd3f1e8ec09cf7e4e05208bc6d3c46406

WORKDIR /opt/strata
RUN git init -q . \
    && git remote add origin https://github.com/Niko1221/Strata.git \
    && git fetch -q --depth 1 origin "${STRATA_REF}" \
    && git checkout -q FETCH_HEAD \
    && rm -rf .git

# The image encoder, configured and built the way setup.py builds it:
# setup.cmake_build's command line with the vision call's definitions, and
# tools/vision/CMakeLists.txt doing the rest (it FORCEs the llama build's cache
# vars and links strata-vision against mtmd and llama).
FROM nvidia/cuda:${CUDA_TAG} AS vision

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential ca-certificates curl python3 python3-venv unzip \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/tc \
    && /opt/tc/bin/pip install --no-cache-dir cmake==4.4.3 ninja==1.13.2

# setup.py's llama.cpp pin: the zip get_llama_cpp unpacks, minus the web UI
# upstream strips too. Bump it here and in builder together; builder asserts
# both against its checkout's setup.py.
ARG LLAMA_CPP_COMMIT=3cf03257f219afbe7334045ff7c6a06ac68c627d
# Keep these two identical to builder's: they are part of this stage's cache
# key, and the whole point is that a Strata bump replays it.
ARG CUDA_ARCHITECTURES=120
ARG BUILD_JOBS=4

RUN curl -fsSL "https://github.com/ggml-org/llama.cpp/archive/${LLAMA_CPP_COMMIT}.zip" -o /llama.zip \
    && unzip -q /llama.zip -d /opt \
    && mv /opt/llama.cpp-* /opt/llama.cpp \
    && rm -rf /llama.zip /opt/llama.cpp/tools/ui

COPY --from=src /opt/strata/tools/vision /opt/vision

# The retry is setup.cmake_build's: CUDA 13.0's ptxas intermittently fails to
# parse a PTX file it just wrote (Strata issue #45), and the same command then
# gets past it.
RUN /opt/tc/bin/cmake -G Ninja -DCMAKE_MAKE_PROGRAM=/opt/tc/bin/ninja \
        -S /opt/vision -B /opt/build-vision -DCMAKE_BUILD_TYPE=Release \
        -DLLAMA_DIR=/opt/llama.cpp -DSTRATA_VISION_CUDA=ON -DSTRATA_PORTABLE=ON \
        -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCHITECTURES}" \
        -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc \
    && (/opt/tc/bin/cmake --build /opt/build-vision --target strata-vision -j "${BUILD_JOBS}" \
        || { echo "  (the build stopped - trying it once more)"; \
             /opt/tc/bin/cmake --build /opt/build-vision --target strata-vision -j "${BUILD_JOBS}"; })

FROM nvidia/cuda:${CUDA_TAG} AS builder

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 LANG=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential ca-certificates curl libatomic1 libgomp1 \
        python3 python3-pip python3-venv unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/strata
COPY --from=src /opt/strata/ /opt/strata/

# RTX 50 (120) only: the runtime picks the cubin matching the card, and a set
# with one arch is the fastest build. A non-Blackwell card needs its own arch
# here (RTX 30 = 86, RTX 40 = 89, A-series = 80).
ARG CUDA_ARCHITECTURES=120
# setup.cmake_build sizes ninja at max(2, cpu_count // 2), so the 4-vCPU runner
# would compile with -j 2. BUILD_JOBS=4 gives the runner -j 4; single-arch nvcc
# stays inside its 16 GB.
#
# Keep these values identical wherever the cache is shared. They are part of
# both compile layers' keys, so a local build reuses CI's :buildcache layers
# only at the CI values:
#   docker build --cache-from type=registry,ref=ghcr.io/mspiegel31/strata:buildcache .
# A one-off cold compile can pass higher ones instead (this box's 8 cores /
# 96 GB take -j 8, nvcc being the RAM sink at ~2 GB per job) and accept the
# registry layers going unused.
ARG BUILD_JOBS=4
ARG LLAMA_CPP_COMMIT=3cf03257f219afbe7334045ff7c6a06ac68c627d

RUN python3 -m venv .venv \
    && .venv/bin/pip install --no-cache-dir --upgrade pip \
    && .venv/bin/pip install --no-cache-dir -r requirements.txt \
    && chmod +x setup.sh docker-entrypoint.sh

# llama.cpp at the pinned commit, then the engine, built exactly the way
# setup.py builds it. BUILD.json is what setup.py reads to decide whether an
# engine is current: source=local with a matching src hash means the first
# start reuses it instead of recompiling. The encoder is the vision stage's;
# its llama pin has to be this checkout's, or the two engines would link
# different ggml trees.
RUN .venv/bin/python - <<'PYEOF'
import json, os, pathlib, shutil
import setup

# the encoder in engine/ came from the vision stage; both engines have to link
# the same llama.cpp tree, so the stage's pin has to be this checkout's
assert setup.LLAMA_CPP_COMMIT == os.environ["LLAMA_CPP_COMMIT"], (
    f"ARG LLAMA_CPP_COMMIT {os.environ['LLAMA_CPP_COMMIT']} is not this "
    f"checkout's pin {setup.LLAMA_CPP_COMMIT} (setup.py): bump both together")

jobs = int(os.environ.get("BUILD_JOBS") or 0)
if jobs:
    # cmake_build's -j is max(2, cpu_count // 2) and ninja takes no env var
    os.cpu_count = lambda: 2 * jobs

llama = setup.get_llama_cpp()
nvcc, _ = setup.find_nvcc()
arch = os.environ.get("CUDA_ARCHITECTURES", "75;80;86;89;120").strip().strip('"').replace(",", ";")

setup.cmake_build(setup.ROOT, setup.ROOT / "build", "strata",
    ["-DSTRATA_ENABLE_CUDA=ON", "-DSTRATA_BUILD_TESTS=OFF", "-DSTRATA_PORTABLE=ON",
     "-DSTRATA_Q6K_EXPERTS=ON", "-DSTRATA_MMQ_KQUANTS=ON",
     f"-DCMAKE_CUDA_ARCHITECTURES={arch}", f"-DCMAKE_CUDA_COMPILER={nvcc}",
     *setup.toolkit_root_defs(nvcc), f"-DSTRATA_GGML_DIR={llama}"], None, "build-strata.bat")

eng = setup.ROOT / "engine"
eng.mkdir(exist_ok=True)
shutil.copy2(setup.ROOT / "build" / setup.EXE, eng / setup.EXE)
bindir = pathlib.Path(nvcc).parent
meta = {"source": "local", "version": setup.source_version(),
        "archs": [int(a.split("-")[0]) for a in arch.split(";") if a.split("-")[0].isdigit()], "vision": "gpu",
        "cuda_dirs": [str(d) for d in (bindir, bindir / "x64", bindir.parent / "lib64") if d.is_dir()],
        "src": setup.source_hash(setup.ENGINE_SOURCES),
        "vision_src": setup.source_hash(setup.VISION_SOURCES)}
(eng / "BUILD.json").write_text(json.dumps(meta, indent=1))
PYEOF

COPY --from=vision /opt/build-vision/bin/strata-vision /opt/strata/engine/strata-vision

# the cmake tree is build-time only; the engine itself is what the container needs
RUN rm -rf build

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
