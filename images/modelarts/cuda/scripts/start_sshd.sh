#!/usr/bin/env bash
set -euo pipefail

MY_SSHD_PORT="${MY_SSHD_PORT:-38888}"
MA_HOME="${MA_HOME:-/home/ma-user}"

mkdir -p "${MA_HOME}/etc" "${MA_HOME}/var/run" "${MA_HOME}/.ssh" /run/sshd

if [ ! -f "${MA_HOME}/etc/ssh_host_rsa_key0" ]; then
    ssh-keygen -f "${MA_HOME}/etc/ssh_host_rsa_key0" -N '' -t rsa > /dev/null
fi

chmod 700 "${MA_HOME}/.ssh" || true
chmod 600 "${MA_HOME}/.ssh/authorized_keys" 2>/dev/null || true
chmod 600 "${MA_HOME}/.ssh/id_rsa" 2>/dev/null || true
chmod 644 "${MA_HOME}/.ssh/id_rsa.pub" 2>/dev/null || true

cat > "${MA_HOME}/.ssh/config" <<SSHCONFIG
Host *
  StrictHostKeyChecking no
  UserKnownHostsFile /dev/null
  ServerAliveInterval 30
  ServerAliveCountMax 3
SSHCONFIG

chmod 600 "${MA_HOME}/.ssh/config" || true

exec /usr/sbin/sshd \
    -D \
    -p "${MY_SSHD_PORT}" \
    -h "${MA_HOME}/etc/ssh_host_rsa_key0" \
    -o AuthorizedKeysFile="${MA_HOME}/.ssh/authorized_keys" \
    -o PidFile="${MA_HOME}/var/run/sshd.pid" \
    -o StrictModes=no \
    -o UsePAM=no \
    -o PermitRootLogin=no \
    -o PasswordAuthentication=no \
    -o PubkeyAuthentication=yes