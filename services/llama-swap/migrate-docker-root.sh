#!/usr/bin/env bash
set -euo pipefail

source_root=/var/lib/docker
target_root=/mnt/models/docker
daemon_config=/etc/docker/daemon.json
backup_config=/etc/docker/daemon.json.before-data-root

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this script with sudo." >&2
  exit 1
fi

if [[ "$(findmnt -n -o TARGET --target /mnt/models)" != "/mnt/models" ]]; then
  echo "/mnt/models is not a mounted filesystem; refusing migration." >&2
  exit 1
fi

systemctl stop docker.service docker.socket
systemctl stop containerd.service

install -d -m 0711 "${target_root}"
rsync -aHAX --numeric-ids --delete "${source_root}/" "${target_root}/"

cp -a "${daemon_config}" "${backup_config}"
tmp_config=$(mktemp)
jq '. + {"data-root": "/mnt/models/docker"}' "${daemon_config}" > "${tmp_config}"
install -o root -g root -m 0644 "${tmp_config}" "${daemon_config}"
rm -f "${tmp_config}"

systemctl start containerd.service
systemctl start docker.service

if [[ "$(docker info --format '{{.DockerRootDir}}')" != "${target_root}" ]]; then
  echo "Docker did not adopt ${target_root}; preserving ${source_root} for recovery." >&2
  exit 1
fi

docker ps >/dev/null
rm -rf "${source_root}"

echo "Docker data root migrated to ${target_root}."
df -h / "${target_root}"
