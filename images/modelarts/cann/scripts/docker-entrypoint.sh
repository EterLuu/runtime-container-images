#!/usr/bin/env bash
set -euo pipefail

/usr/local/bin/start_sshd.sh &
sleep 2

exec "$@"