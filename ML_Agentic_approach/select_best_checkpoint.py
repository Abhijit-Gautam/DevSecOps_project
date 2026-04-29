from __future__ import annotations

import argparse
import json
from pathlib import Path

from checkpoint_utils import discover_checkpoints, resolve_best_checkpoint


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect checkpoint-* folders and print the selected best checkpoint."
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("."),
        help="Workspace path containing checkpoint-* directories.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print checkpoint summary as JSON.",
    )
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    checkpoints = discover_checkpoints(workspace)
    if not checkpoints:
        print(f"No checkpoint-* directories found in: {workspace}")
        return 1

    best = resolve_best_checkpoint(workspace)

    if args.json:
        payload = {
            "workspace": str(workspace),
            "selected": str(best),
            "checkpoints": [
                {
                    "path": str(info.path),
                    "best_metric": info.best_metric,
                    "global_step": info.global_step,
                    "best_model_checkpoint": info.best_model_checkpoint,
                }
                for info in checkpoints
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(f"Workspace: {workspace}")
    print("Discovered checkpoints:")
    for info in checkpoints:
        print(
            f"- {info.path.name}: best_metric={info.best_metric}, "
            f"global_step={info.global_step}, "
            f"best_model_checkpoint={info.best_model_checkpoint}"
        )

    print(f"Selected best checkpoint: {best}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
