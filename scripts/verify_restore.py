"""Restore a consistent snapshot into a disposable database; verify every table."""

import os, subprocess, uuid
from pathlib import Path
import psycopg
from psycopg import sql

root = Path(os.environ.get("TASK_PG_ROOT", "/workspace/postgres-local"))
runtime = Path(os.environ.get("TASK_PG_RUNTIME", "/workspace/care-navigator-runtime"))
bin_dir = root / "usr/lib/postgresql/17/bin"
env = {
    **os.environ,
    "LD_LIBRARY_PATH": str(root / "usr/lib/x86_64-linux-gnu"),
    "PGHOST": os.environ.get("PGHOST", str(runtime)),
}
database = os.environ.get("PGDATABASE", "care_navigator")
restore = "care_restore_" + uuid.uuid4().hex[:12]
backup = runtime / f"{restore}.dump"
# Keep source unchanged, with a stable snapshot while computing comparisons.
with psycopg.connect(
    dbname=database, host=env["PGHOST"], user=os.environ.get("PGUSER", "agent")
) as source:
    source.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
    snapshot = source.execute("SELECT pg_export_snapshot()").fetchone()[0]
    subprocess.run(
        [
            str(bin_dir / "pg_dump"),
            "-Fc",
            f"--snapshot={snapshot}",
            "-f",
            str(backup),
            database,
        ],
        env=env,
        check=True,
    )
    backup.chmod(0o600)
    subprocess.run([str(bin_dir / "createdb"), restore], env=env, check=True)
    try:
        subprocess.run(
            [
                str(bin_dir / "pg_restore"),
                "--exit-on-error",
                "--no-owner",
                "-d",
                restore,
                str(backup),
            ],
            env=env,
            check=True,
        )
        with psycopg.connect(
            dbname=restore, host=env["PGHOST"], user=os.environ.get("PGUSER", "agent")
        ) as restored:
            tables = [
                r[0]
                for r in source.execute(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
                )
            ]
            actual = [
                r[0]
                for r in restored.execute(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"
                )
            ]
            assert tables == actual, "Schema table mismatch"
            total = 0
            for table in tables:
                # Compare all row content in canonical order; never print patient content or credentials.
                query = sql.SQL(
                    "SELECT row_to_json(t)::text FROM {} t ORDER BY row_to_json(t)::text"
                ).format(sql.Identifier(table))
                expected = source.execute(query).fetchall()
                assert expected == restored.execute(query).fetchall(), (
                    f"Restore mismatch: {table}"
                )
                total += len(expected)
            print(
                f"Backup and restoration verified: {len(tables)} tables, {total} rows, all row content matches consistent source snapshot."
            )
            print(f"Private synthetic backup retained at {backup}")
    finally:
        subprocess.run([str(bin_dir / "dropdb"), restore], env=env, check=True)
