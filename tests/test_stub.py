import pytest

from compressor import CompressionError, NodePreempted, compress, stub


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(stub, "SECONDS_PER_STEP", 0)
    monkeypatch.delenv("COMPRESSOR_PREEMPT_AT_STEP", raising=False)


@pytest.fixture
def model(tmp_path):
    path = tmp_path / "model.bin"
    path.write_text("weights")
    return path


def test_writes_a_compressed_file_and_reports_the_result(model, tmp_path):
    result = compress(model, tmp_path / "out", target_ratio=0.5)
    assert result.output_path.exists()
    assert result.steps_run == stub.TOTAL_STEPS
    assert result.compressor_version == stub.COMPRESSOR_VERSION


def test_the_same_model_at_the_same_ratio_reports_the_same_loss(model, tmp_path):
    first = compress(model, tmp_path / "a", target_ratio=0.5)
    second = compress(model, tmp_path / "b", target_ratio=0.5)
    assert first.accuracy_loss_pct == second.accuracy_loss_pct


def test_a_higher_ratio_loses_more_accuracy(model, tmp_path):
    gentle = compress(model, tmp_path / "a", target_ratio=0.5)
    aggressive = compress(model, tmp_path / "b", target_ratio=0.85)
    assert gentle.accuracy_loss_pct < 3 < aggressive.accuracy_loss_pct


def test_carries_on_from_the_checkpoint_after_a_preemption(model, tmp_path):
    checkpoints = tmp_path / "checkpoints"
    with pytest.raises(NodePreempted):
        compress(model, tmp_path / "out", checkpoint_dir=checkpoints, preempt_at_step=8)
    result = compress(model, tmp_path / "out", checkpoint_dir=checkpoints)
    assert result.steps_run == stub.TOTAL_STEPS - 7


def test_starts_over_without_a_checkpoint_directory(model, tmp_path):
    with pytest.raises(NodePreempted):
        compress(model, tmp_path / "out", preempt_at_step=8)
    assert compress(model, tmp_path / "out").steps_run == stub.TOTAL_STEPS


def test_refuses_a_missing_model(tmp_path):
    with pytest.raises(CompressionError):
        compress(tmp_path / "absent.bin", tmp_path / "out")


def test_refuses_an_invalid_ratio(model, tmp_path):
    with pytest.raises(CompressionError):
        compress(model, tmp_path / "out", target_ratio=1.5)
