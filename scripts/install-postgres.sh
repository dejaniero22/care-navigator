#!/usr/bin/env bash
set -euo pipefail
# Optional user-owned PostgreSQL for the Debian 13 cloud image. No sudo or root writes.
if [ -x /workspace/postgres-local/usr/lib/postgresql/17/bin/postgres ]; then exit 0; fi
if ! rg -q '^VERSION_CODENAME=trixie$' /etc/os-release; then
  echo 'This bootstrap requires Debian 13. Supply PostgreSQL 17 through PGHOST/PGUSER/PGDATABASE instead.' >&2; exit 1
fi
mkdir -p /workspace/postgres-packages/lists/partial /workspace/postgres-packages/cache/archives/partial /workspace/postgres-local
cat > /workspace/postgres-packages/sources.list <<'SOURCES'
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main
SOURCES
TASK_APT_ARGS=(-o Dir::Etc::sourcelist=/workspace/postgres-packages/sources.list -o Dir::Etc::sourceparts=- -o Dir::State::lists=/workspace/postgres-packages/lists -o Dir::Cache=/workspace/postgres-packages/cache)
/usr/bin/apt-get "${TASK_APT_ARGS[@]}" update
cd /workspace/postgres-packages
/usr/bin/apt-get "${TASK_APT_ARGS[@]}" download postgresql-17 postgresql-client-17 libpq5 libllvm19 liburing2
for archive in ./*.deb; do dpkg-deb -x "$archive" /workspace/postgres-local; done
LD_LIBRARY_PATH=/workspace/postgres-local/usr/lib/x86_64-linux-gnu /workspace/postgres-local/usr/lib/postgresql/17/bin/postgres --version
