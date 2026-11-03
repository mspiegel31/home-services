# Strata: Qwen3.8-Flash-Next lanes on NVIDIA GPUs (https://github.com/Niko1221/Strata).
#
# A thin layer over upstream's published image: the Terminal (bundled CPython
# 3.12, strata CLI at /opt/strata/terminal/bin/strata, wrapper at
# /usr/local/bin/strata) plus one engine package under
# /opt/strata/components/engine/<version>-linux-x86_64-cuda-cuda13/ (engine,
# strata-vision encoder, libstrata_kq.so, bundled libcudart/cublas) and the
# seed llama.cpp gguf-py under /opt/strata/seed/third_party/llama.cpp/.
#
# The digest is the tag's manifest: a re-pull of the same tag keeps this
# image byte-identical until the pin is bumped deliberately. Upstream
# publishes since 0.2.1 as ghcr.io/niko1221/strata:<ver>-<flavor>.
#
# 0.2.9-cuda13's BUILD.json (read from the image): archs 75/86/89/120 +
# compute_120 PTX, vision cuda13.0, portable=true — the STRATA_PORTABLE=ON
# AVX2 baseline our self-compiled builds passed, so the Ryzen 5700X box
# (AVX2, no AVX-512) is covered by the published engine, not by a local
# compile. sm_120 covers the RTX PRO 5000 Blackwell card.
FROM ghcr.io/niko1221/strata:0.2.9-cuda13@sha256:83e37db8625c67b61c579fd7c0f9068f2d831037a937f139c569502b54290998

# The lane run configs (hand-authored, and the setup.py-era configs already on
# the model-more PVC) name paths from the 0.1.x layout that this image does
# not have: /opt/strata/engine/strata and .../strata-vision, and
# /opt/strata/data/expert-profile.bin. Both are stable symlinks, so a config
# keeps working without a rewrite across engine-version bumps (the digest pin
# changes with them; the symlink target is resolved at build time).
RUN set -e; \
    set -- /opt/strata/components/engine/*/; \
    [ $# -eq 1 ] || { echo "expected exactly one engine package, got $#"; exit 1; }; \
    pkg="$1"; [ -x "$pkg/strata" ] || { echo "no engine entrypoint in $pkg"; exit 1; }; \
    ln -sfn "$pkg" /opt/strata/engine; \
    [ -f /opt/strata/terminal/data/expert-profile.bin ]; \
    ln -sfn /opt/strata/terminal/data /opt/strata/data

COPY merge_args.py /opt/strata-exporter/merge_args.py
COPY entrypoint.sh /opt/strata-exporter/entrypoint.sh
RUN chmod 0755 /opt/strata-exporter/entrypoint.sh

VOLUME ["/data"]
EXPOSE 8080

ENTRYPOINT ["/opt/strata-exporter/entrypoint.sh"]
