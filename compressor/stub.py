"""A stand-in for the compressor.

It has the same call as the real tool and behaves the same way from the outside,
but it finishes in seconds and writes a placeholder file. Treat it as a black box.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

COMPRESSOR_VERSION = "0.9.3-stub"
TOTAL_STEPS = 20
SECONDS_PER_STEP = float(os.environ.get("COMPRESSOR_SECONDS_PER_STEP", "0.25"))
_CHECKPOINT_FILE = "checkpoint.json"


class CompressionError(Exception):
    """The input cannot be compressed. Retrying will not help."""


class NodePreempted(Exception):
    """The machine running the job was taken away before the job finished."""


@dataclass(frozen=True)
class CompressionResult:
    output_path: Path
    source_sha256: str
    target_ratio: float
    accuracy_loss_pct: float
    compressor_version: str
    steps_run: int


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _accuracy_loss(source_sha256: str, target_ratio: float) -> float:
    # Deterministic: the same model at the same ratio always reports the same loss.
    jitter = int(source_sha256[:4], 16) / 0xFFFF * 0.5
    return round(target_ratio * 4 + jitter, 2)


def _read_checkpoint(directory: Path, source_sha256: str, target_ratio: float) -> int:
    path = directory / _CHECKPOINT_FILE
    if not path.exists():
        return 0
    saved = json.loads(path.read_text())
    same_job = (
        saved.get("source_sha256") == source_sha256
        and saved.get("target_ratio") == target_ratio
    )
    return int(saved.get("step", 0)) if same_job else 0


def _write_checkpoint(
    directory: Path, source_sha256: str, target_ratio: float, step: int
) -> None:
    payload = {"source_sha256": source_sha256, "target_ratio": target_ratio, "step": step}
    (directory / _CHECKPOINT_FILE).write_text(json.dumps(payload))


def compress(
    model_path: str | Path,
    output_dir: str | Path,
    target_ratio: float = 0.5,
    checkpoint_dir: str | Path | None = None,
    on_progress: Callable[[int, int], None] | None = None,
    preempt_at_step: int | None = None,
) -> CompressionResult:
    """Compress one model.

    Args:
        model_path: The model file to compress.
        output_dir: Where the compressed model is written.
        target_ratio: The share of the model's size to remove, above 0 and below 1.
        checkpoint_dir: Where progress is saved. Passing the same directory for the
            same model and ratio carries on from the last saved step. Without it,
            every call starts from the beginning.
        on_progress: Called after each step with (step, total_steps).
        preempt_at_step: Raises NodePreempted on reaching this step, so you can try
            out what happens when a machine is taken away. The environment variable
            COMPRESSOR_PREEMPT_AT_STEP does the same.

    Raises:
        CompressionError: The model file is missing or empty, or the ratio is invalid.
        NodePreempted: The machine was taken away.
    """
    source = Path(model_path)
    if not source.is_file() or source.stat().st_size == 0:
        raise CompressionError(f"no usable model at {source}")
    if not 0 < target_ratio < 1:
        raise CompressionError(f"target_ratio must be between 0 and 1, got {target_ratio}")

    source_sha256 = _sha256(source)
    checkpoints = Path(checkpoint_dir) if checkpoint_dir is not None else None
    start = 0
    if checkpoints is not None:
        checkpoints.mkdir(parents=True, exist_ok=True)
        start = _read_checkpoint(checkpoints, source_sha256, target_ratio)

    if preempt_at_step is None and os.environ.get("COMPRESSOR_PREEMPT_AT_STEP"):
        preempt_at_step = int(os.environ["COMPRESSOR_PREEMPT_AT_STEP"])

    for step in range(start + 1, TOTAL_STEPS + 1):
        if step == preempt_at_step:
            raise NodePreempted(f"node taken back at step {step} of {TOTAL_STEPS}")
        time.sleep(SECONDS_PER_STEP)
        if checkpoints is not None:
            _write_checkpoint(checkpoints, source_sha256, target_ratio, step)
        if on_progress is not None:
            on_progress(step, TOTAL_STEPS)

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    output_path = destination / f"{source.stem}.compressed{source.suffix}"
    output_path.write_text(
        f"placeholder for {source.name}, {target_ratio:.0%} smaller, {source_sha256}\n"
    )

    return CompressionResult(
        output_path=output_path,
        source_sha256=source_sha256,
        target_ratio=target_ratio,
        accuracy_loss_pct=_accuracy_loss(source_sha256, target_ratio),
        compressor_version=COMPRESSOR_VERSION,
        steps_run=TOTAL_STEPS - start,
    )
