# Project Maya: GLM-5.3-Flash (321B MoE) on NVIDIA GPUs (https://github.com/mw00/project-maya).
#
# Same four-stage shape as images/strata: src checks the pinned revision out, vision builds the
# image encoder against llama.cpp, builder compiles the engine, runtime ships both. The engine
# compile is maya.py's compile_engine command line and the encoder is compile_vision's, kept in
# separate stages because the encoder links all of llama.cpp (~16 of the ~20 min cold compile) and
# depends on setup.py's llama pin, not on MAYA_REF: a bump that leaves tools/vision alone replays
# the encoder from :buildcache. LLAMA_CPP_COMMIT must equal setup.py's pin; builder asserts it.
#
# STRATA_PORTABLE=ON on both compiles, a deviation from upstream's command lines (compile_engine
# omits it: it assumes it builds on the machine it will run on). Upstream's CMakeLists FORCEs
# GGML_NATIVE ON without it, the GHA pool mixes AVX-512 and AVX2 hosts, and a native-built binary
# SIGILLs in ggml_cpu_init on AVX2-only CPUs — images/strata's 6f32ec0.1 incident, same trap here
# (this fleet's Ryzen 5700X).
#
# The runtime flavor carries cuda-nvcc + g++ although nothing compiles at run time: the first
# boot's `maya.py --setup` pass runs check_pc, which hard-fails without them. The steady-state
# path execs serve/server.py directly and never reaches check_pc (see maya-entrypoint.sh).
#
# build-images.yml pins this image to amd64 and caches the compile layers to a :buildcache tag in
# ghcr (the repo-wide GHA cache is 10 GB and these layers are GBs).
ARG CUDA_TAG=13.0.1-devel-ubuntu24.04@sha256:7d2f6a8c2071d911524f95061a0db363e24d27aa51ec831fcccf9e76eb72bc92
ARG CUDA_RUNTIME_TAG=13.0.1-runtime-ubuntu24.04@sha256:c3fde347d52d578c84fd644bc177bc7ec333feaf11550d990da4084d7612e4c7

FROM nvidia/cuda:${CUDA_TAG} AS src

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates git \
    && rm -rf /var/lib/apt/lists/*

# v1.1.0: --parallel, DFlash2 drafting, EXL3 quants — the first release the Maya-M lane ships with.
ARG MAYA_REF=7b1b33fc93a4cc4dadf2ed3006622142fad264ca

WORKDIR /opt/maya
RUN git init -q . \
    && git remote add origin https://github.com/mw00/project-maya.git \
    && git fetch -q --depth 1 origin "${MAYA_REF}" \
    && git checkout -q FETCH_HEAD \
    && rm -rf .git

# The image encoder, configured and built the way maya.py's compile_vision builds it: the pinned
# llama.cpp with GLM-5.3-Flash's vision tower patched in (glm5next_patch.py, idempotent, stdlib
# only), then tools/vision/CMakeLists.txt doing the rest. The retry is cmake_steps' own: CUDA
# 13.0's ptxas intermittently fails to parse a PTX file it just wrote (Strata issue #45).
FROM nvidia/cuda:${CUDA_TAG} AS vision

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential ca-certificates curl python3 python3-venv unzip \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/tc \
    && /opt/tc/bin/pip install --no-cache-dir cmake==4.4.3 ninja==1.13.2

# setup.py's llama.cpp pin. Keep identical to builder's: both are cache keys, and the whole point
# is that a Maya bump that leaves tools/vision alone replays this stage.
ARG LLAMA_CPP_COMMIT=3cf03257f219afbe7334045ff7c6a06ac68c627d
ARG CUDA_ARCHITECTURES=120
ARG BUILD_JOBS=4

RUN curl -fsSL "https://github.com/ggml-org/llama.cpp/archive/${LLAMA_CPP_COMMIT}.zip" -o /llama.zip \
    && unzip -q /llama.zip -d /opt \
    && mv /opt/llama.cpp-* /opt/llama.cpp \
    && rm -rf /llama.zip /opt/llama.cpp/tools/ui

COPY --from=src /opt/maya/tools/vision /opt/vision

RUN python3 /opt/vision/glm5next_patch.py /opt/llama.cpp \
    && /opt/tc/bin/cmake -G Ninja -DCMAKE_MAKE_PROGRAM=/opt/tc/bin/ninja \
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

WORKDIR /opt/maya
COPY --from=src /opt/maya/ /opt/maya/

# RTX 50 (120) only, as images/strata: one arch is the fastest build and the runtime picks the
# matching cubin. BUILD_JOBS=4 keeps the 4-vCPU runner inside its 16 GB (nvcc ~2-4 GB per job);
# keep identical to the :buildcache values so local builds reuse CI's layers.
ARG CUDA_ARCHITECTURES=120
ARG BUILD_JOBS=4
ARG LLAMA_CPP_COMMIT=3cf03257f219afbe7334045ff7c6a06ac68c627d

# .venv holds exactly setup.py's PY_PACKAGES plus pip_install's stamp file, so the container's
# first tools_step finds nothing to install and never touches PyPI.
RUN python3 -m venv .venv \
    && .venv/bin/pip install --no-cache-dir --upgrade pip \
    && .venv/bin/python -c "import setup; print(*setup.PY_PACKAGES)" \
           | xargs .venv/bin/pip install --no-cache-dir \
    && .venv/bin/python -c "import json, setup; open('.venv/.strata-pip.json', 'w').write(json.dumps(sorted(set(setup.PY_PACKAGES)), indent=0))"

# llama.cpp at the pinned commit, unpacked where tools_step looks (third_party/llama.cpp: its
# llama_ok check is ggml/CMakeLists.txt + gguf-py/), then the engine. The tree stays in the image:
# the pack builder imports gguf-py from it on the first boot. Unpatched, as on a fresh install —
# compile_engine runs before compile_vision patches, and the patch only touches mtmd.
#
# build/MAYA-BUILD.json is what build_step and refresh_engine compare against; a mismatch would
# make the container try to recompile at run time (no nvcc on the steady-state path's side of the
# entrypoint, and a slow boot regardless), so its fields are written from the same helpers maya.py
# uses.
RUN curl -fsSL "https://github.com/ggml-org/llama.cpp/archive/${LLAMA_CPP_COMMIT}.zip" -o /llama.zip \
    && unzip -q /llama.zip -d /opt/maya/third_party \
    && mv /opt/maya/third_party/llama.cpp-* /opt/maya/third_party/llama.cpp \
    && rm -rf /llama.zip

RUN .venv/bin/python - <<'PYEOF'
import json, os, subprocess, time
import setup as S
import maya as M

assert S.LLAMA_CPP_COMMIT == os.environ["LLAMA_CPP_COMMIT"], (
    f"ARG LLAMA_CPP_COMMIT {os.environ['LLAMA_CPP_COMMIT']} is not this checkout's pin "
    f"{S.LLAMA_CPP_COMMIT} (setup.py): bump both together")

nvcc = "/usr/local/cuda/bin/nvcc"
llama = S.ROOT / "third_party" / "llama.cpp"
arch = os.environ.get("CUDA_ARCHITECTURES", "120")
jobs = os.environ.get("BUILD_JOBS", "4")
cmake, ninja = str(S.ROOT / ".venv" / "bin" / "cmake"), str(S.ROOT / ".venv" / "bin" / "ninja")

conf = [cmake, "-G", "Ninja", f"-DCMAKE_MAKE_PROGRAM={ninja}",
        "-S", str(S.ROOT), "-B", str(S.ROOT / "build"), "-DCMAKE_BUILD_TYPE=Release",
        "-DSTRATA_ENABLE_CUDA=ON", f"-DCMAKE_CUDA_ARCHITECTURES={arch}",
        "-DSTRATA_NATIVE_EXPERTS=ON", "-DSTRATA_BUILD_TESTS=OFF", "-DSTRATA_PORTABLE=ON",
        f"-DCMAKE_CUDA_COMPILER={nvcc}", f"-DSTRATA_GGML_DIR={llama}"]
subprocess.run(conf, check=True)
subprocess.run([cmake, "--build", str(S.ROOT / "build"), "--target", "strata", "-j", jobs], check=True)

M.STAMP.write_text(json.dumps({
    "src": S.source_hash(S.ENGINE_SOURCES),
    "archs": [int(a) for a in arch.split(";") if a.split("-")[0].isdigit()],
    "gpu_ids": [0], "nvcc": nvcc, "host_compiler": None, "llama": str(llama),
    "lib_dirs": M.cuda_lib_dirs(nvcc), "date": time.strftime("%Y-%m-%d %H:%M")}, indent=1))
PYEOF

COPY --from=vision /opt/build-vision/bin/strata-vision /opt/maya/build-vision/bin/strata-vision

RUN .venv/bin/python - <<'PYEOF'
import json, os, time
import setup as S
import maya as M

M.VSTAMP.write_text(json.dumps({
    "src": S.source_hash(("tools/vision",)),
    "archs": [int(a) for a in os.environ.get("CUDA_ARCHITECTURES", "120").split(";")
              if a.split("-")[0].isdigit()],
    "llama": str(S.ROOT / "third_party" / "llama.cpp"),
    "date": time.strftime("%Y-%m-%d %H:%M")}, indent=1))
PYEOF

# the cmake trees are build-time only; Maya's EXE lives in build/ itself (no engine/ folder)
RUN rm -rf /opt/maya/build/CMakeFiles /opt/maya/build/_deps

FROM nvidia/cuda:${CUDA_RUNTIME_TAG}

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 LANG=C.UTF-8 \
    MAYA_UPDATE_CHECK=0

# cuda-nvcc-13-0 + cuda-cudart-dev-13-0 + g++ exist for check_pc's benefit alone (first-boot setup
# pass; nothing compiles at run time — the engine and encoder ship prebuilt). MAYA_UPDATE_CHECK=0:
# the dashboard's About > Update would git-pull into a container that has no git.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl g++ libatomic1 libgomp1 python3 python3-venv \
        cuda-nvcc-13-0 cuda-cudart-dev-13-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/maya
COPY --from=builder /opt/maya /opt/maya

COPY maya-entrypoint.sh /opt/maya/docker-entrypoint.sh
RUN chmod +x /opt/maya/docker-entrypoint.sh

VOLUME ["/data"]
EXPOSE 8080

ENTRYPOINT ["/opt/maya/docker-entrypoint.sh"]
