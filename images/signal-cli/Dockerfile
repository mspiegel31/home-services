FROM debian:13.4-slim@sha256:486b1c3d3a6a836d2518d5ac1a7b522050a034ae83b47c063fd45d550b2b9dbf

ARG SIGNAL_CLI_VERSION=0.14.7
ARG SIGNAL_CLI_SHA256=0fe065294adcf35df4c249b635d0ce57de7765d4fec660bffaa2e7f0549d4e5f

RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates curl gosu zlib1g \
    && rm -rf /var/lib/apt/lists/*

RUN curl --fail --location --show-error --silent \
      "https://github.com/AsamK/signal-cli/releases/download/v${SIGNAL_CLI_VERSION}/signal-cli-${SIGNAL_CLI_VERSION}-Linux-native.tar.gz" \
      --output /tmp/signal-cli.tar.gz \
    && printf '%s  %s\n' "${SIGNAL_CLI_SHA256}" /tmp/signal-cli.tar.gz | sha256sum --check --strict \
    && tar --extract --gzip --file /tmp/signal-cli.tar.gz --directory /usr/local/bin \
    && chmod 0755 /usr/local/bin/signal-cli \
    && rm /tmp/signal-cli.tar.gz

RUN groupadd --gid 10000 signal \
    && useradd --uid 10000 --gid signal --create-home --home-dir /home/signal signal \
    && install --directory --owner signal --group signal --mode 0700 /data

COPY --chmod=0755 entrypoint.sh /usr/local/bin/signal-cli-entrypoint

USER root
ENV XDG_DATA_HOME=/data
VOLUME ["/data"]
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD gosu signal:signal curl --fail --silent --show-error http://127.0.0.1:8080/api/v1/check >/dev/null || exit 1

ENTRYPOINT ["/usr/local/bin/signal-cli-entrypoint"]
