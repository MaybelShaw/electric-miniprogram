import os
import socket
import sys
import time


host = os.environ.get("POSTGRES_HOST", "db")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
timeout = int(os.environ.get("WAIT_FOR_DB_TIMEOUT", "90"))
deadline = time.monotonic() + timeout
last_error = None

while time.monotonic() < deadline:
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"Database TCP endpoint is reachable: {host}:{port}", flush=True)
            sys.exit(0)
    except OSError as exc:
        last_error = exc
        print(f"Waiting for database TCP endpoint {host}:{port}: {exc}", flush=True)
        time.sleep(2)

print(f"Database TCP endpoint did not become reachable: {host}:{port}: {last_error}", file=sys.stderr, flush=True)
sys.exit(1)
