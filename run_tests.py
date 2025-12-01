#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    cmd = [sys.executable, "-m", "pytest"]
    env = os.environ.copy()
    src_path = str(repo_root / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.call(cmd, cwd=repo_root, env=env)


if __name__ == "__main__":
    sys.exit(main())
