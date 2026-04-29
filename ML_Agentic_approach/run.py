"""
Dev server entry point.

Run from the project root:
    python run.py
    python run.py --port 8000
"""
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app import main

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="DevSecOps Report Evaluator API")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 5000)))
    parser.add_argument("--no-debug", action="store_true")
    args = parser.parse_args()

    os.environ["PORT"] = str(args.port)
    if args.no_debug:
        os.environ["DEBUG"] = "false"

    main()
