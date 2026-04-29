from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CheckpointInfo:
    path: Path
    best_metric: float
    global_step: int
    best_model_checkpoint: Optional[str]


def _load_trainer_state(path: Path) -> Dict:
    trainer_state_path = path / "trainer_state.json"
    if not trainer_state_path.exists():
        return {}

    with trainer_state_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def discover_checkpoints(workspace: Path) -> List[CheckpointInfo]:
    checkpoints: List[CheckpointInfo] = []

    for path in sorted(workspace.glob("checkpoint-*")):
        if not path.is_dir():
            continue

        state = _load_trainer_state(path)
        checkpoints.append(
            CheckpointInfo(
                path=path,
                best_metric=float(state.get("best_metric", float("-inf"))),
                global_step=int(state.get("global_step", -1)),
                best_model_checkpoint=state.get("best_model_checkpoint"),
            )
        )

    return checkpoints


def resolve_best_checkpoint(workspace: Path) -> Path:
    checkpoints = discover_checkpoints(workspace)
    if not checkpoints:
        raise FileNotFoundError(
            f"No checkpoint-* directories found in workspace: {workspace}"
        )

    referenced_scores: Dict[Path, tuple[float, int]] = {}

    for info in checkpoints:
        if not info.best_model_checkpoint:
            continue

        local_ref = workspace / Path(info.best_model_checkpoint).name
        if not local_ref.exists():
            continue

        score = (info.best_metric, info.global_step)
        if local_ref not in referenced_scores or score > referenced_scores[local_ref]:
            referenced_scores[local_ref] = score

    if referenced_scores:
        return max(
            referenced_scores.items(),
            key=lambda item: (item[1][0], item[1][1], item[0].name),
        )[0]

    return max(
        checkpoints,
        key=lambda info: (info.best_metric, info.global_step, info.path.name),
    ).path
