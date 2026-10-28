from scripts.load_smoke import percentile


def test_percentile_is_deterministic() -> None:
    values = [100.0, 20.0, 50.0, 10.0, 80.0]
    assert percentile(values, 0.50) == 50.0
    assert percentile(values, 0.95) == 100.0
    assert percentile([], 0.95) == 0.0
