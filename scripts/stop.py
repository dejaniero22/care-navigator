"""Stop only project processes recorded by scripts/start.sh; leave PostgreSQL running."""

import os, signal, subprocess
from pathlib import Path

root = Path(__file__).resolve().parent.parent
runtime = Path(os.environ.get("TASK_LOG_DIR", "/workspace/care-navigator-runtime"))


def children(pid):
    output = subprocess.check_output(["ps", "-eo", "pid=,ppid="], text=True)
    return [
        int(row.split()[0]) for row in output.splitlines() if int(row.split()[1]) == pid
    ]


def terminate(pid):
    for child in children(pid):
        terminate(child)
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


for service, marker in [
    ("backend", str(root / "backend/manage.py")),
    ("frontend", str(root / "frontend/node_modules/vite/bin/vite.js")),
]:
    saved = runtime / f"{service}.pid"
    if not saved.exists():
        continue
    pid = int(saved.read_text())
    info = subprocess.run(
        ["ps", "-p", str(pid), "-o", "args="], capture_output=True, text=True
    )
    if info.returncode:
        saved.unlink()
        continue
    command = info.stdout
    if marker not in command:
        raise SystemExit(
            f"Refusing to terminate mismatched {service} PID. Inspect it manually."
        )
    terminate(pid)
    saved.unlink()
    print(f"Stopped project {service}.")
