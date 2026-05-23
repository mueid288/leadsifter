"""
Local development entry point.

Usage:
    python main.py                  # starts uvicorn with hot reload
    docker compose up               # runs the full stack (recommended)

For production, run:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
import subprocess
import sys


def main() -> None:
    subprocess.run(
        [
            "uvicorn", "app.main:app",
            "--reload",
            "--host", "0.0.0.0",
            "--port", "8000",
        ],
        check=True,
    )


if __name__ == "__main__":
    sys.exit(main())
