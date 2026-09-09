#!/bin/sh
set -eu

if [ "$(id -u)" -eq 0 ]; then
    chown -R signal:signal /data
    exec gosu signal:signal "$0" "$@"
fi

: "${SIGNAL_ACCOUNT:?Set SIGNAL_ACCOUNT to the linked account in E.164 format}"
SIGNAL_DEVICE_NAME="${SIGNAL_DEVICE_NAME:-Hermes Agent}"

accounts="$(signal-cli --config /data listAccounts)"
if printf '%s\n' "$accounts" | grep -Fqx "Number: $SIGNAL_ACCOUNT"; then
    exec signal-cli --config /data --account "$SIGNAL_ACCOUNT" daemon --http 0.0.0.0:8080
fi

if [ -n "$accounts" ]; then
    printf '%s\n' "signal-cli state contains a different account; refusing to link or start" >&2
    exit 1
fi

printf '%s\n' "No linked signal-cli account found. Scan the QR code or URI below from Signal > Linked devices."
signal-cli --config /data link --name "$SIGNAL_DEVICE_NAME"

accounts="$(signal-cli --config /data listAccounts)"
if ! printf '%s\n' "$accounts" | grep -Fqx "Number: $SIGNAL_ACCOUNT"; then
    printf '%s\n' "Linked account does not match SIGNAL_ACCOUNT; refusing to start" >&2
    exit 1
fi

exec signal-cli --config /data --account "$SIGNAL_ACCOUNT" daemon --http 0.0.0.0:8080
