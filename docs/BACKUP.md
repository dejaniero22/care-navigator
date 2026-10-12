# Backup and restoration

Backups may contain every database record and authentication hash. In this prototype they contain synthetic data only. Keep them outside Git in private storage, apply retention/access controls, and never treat a successful local restore as a production recovery program.

The cloud PostgreSQL binaries are in `/workspace/postgres-local/usr/lib/postgresql/17/bin`; add that directory to PATH and its libraries through `LD_LIBRARY_PATH` for manual administration. The socket directory is `/workspace/care-navigator-runtime`.

## Tested restore check

```bash
cd /workspace/care-navigator
.venv/bin/python scripts/verify_restore.py
```

This exports a repeatable-read PostgreSQL snapshot, makes a custom-format dump outside the checkout with mode 600, creates a uniquely named disposable database, restores with exit-on-error, verifies table names and all canonical row content against that exact source snapshot, then drops only the disposable database it created. It prints counts, never row content or credentials. Existing source records are untouched. It requires database creation privileges and the local PostgreSQL binaries. Snapshots taken while browser demos run are still consistent because the exported snapshot is shared by the comparison and dump.

## Manual backup and restore to a new database

```bash
export PATH=/workspace/postgres-local/usr/lib/postgresql/17/bin:$PATH
export LD_LIBRARY_PATH=/workspace/postgres-local/usr/lib/x86_64-linux-gnu
export PGHOST=/workspace/care-navigator-runtime
umask 077
pg_dump -Fc -f /workspace/care-navigator-runtime/synthetic-backup.dump care_navigator
createdb care_navigator_recovered
pg_restore --exit-on-error --no-owner -d care_navigator_recovered /workspace/care-navigator-runtime/synthetic-backup.dump
```

Do not overwrite or drop the original database. Set `PGDATABASE=care_navigator_recovered` in a separate application instance and verify consent, grant revocation, referral history and reports before deciding to switch. Formal recovery objectives, encryption, offsite retention, role/credential recovery and incident rehearsals need review before live use.
