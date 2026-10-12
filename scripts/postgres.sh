#!/usr/bin/env bash
set -euo pipefail
# User-owned cloud runtime, outside source control. Uses signed Debian packages.
TASK_PG_ROOT=${TASK_PG_ROOT:-/workspace/postgres-local}
TASK_PG_RUNTIME=${TASK_PG_RUNTIME:-/workspace/care-navigator-runtime}
export LD_LIBRARY_PATH="$TASK_PG_ROOT/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
TASK_PG_BIN="$TASK_PG_ROOT/usr/lib/postgresql/17/bin"
mkdir -p "$TASK_PG_RUNTIME"
chmod 700 "$TASK_PG_RUNTIME"
if [ ! -f "$TASK_PG_RUNTIME/data/PG_VERSION" ]; then
  "$TASK_PG_BIN/initdb" -D "$TASK_PG_RUNTIME/data" --auth-local=trust --auth-host=scram-sha-256 --encoding=UTF8 --locale=C.UTF-8 > "$TASK_PG_RUNTIME/init.log"
fi
if ! "$TASK_PG_BIN/pg_isready" -h "$TASK_PG_RUNTIME" >/dev/null 2>&1; then
  "$TASK_PG_BIN/pg_ctl" -D "$TASK_PG_RUNTIME/data" -l "$TASK_PG_RUNTIME/postgres.log" -o "-k $TASK_PG_RUNTIME -c listen_addresses=''" start
fi
if ! "$TASK_PG_BIN/psql" -h "$TASK_PG_RUNTIME" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='care_navigator'" | rg -q 1; then
  "$TASK_PG_BIN/createdb" -h "$TASK_PG_RUNTIME" care_navigator
fi
"$TASK_PG_BIN/pg_isready" -h "$TASK_PG_RUNTIME"
