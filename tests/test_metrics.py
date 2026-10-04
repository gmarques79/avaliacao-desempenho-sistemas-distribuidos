"""
Testes unitários para cálculo de métricas estatísticas.
"""

import math
from pathlib import Path
import tempfile
import pandas as pd
import pytest

from experiments.calculate_metrics import (
    aggregate_experiments,
    calculate_statistics,
)


def test_calculate_statistics_basic():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    stats = calculate_statistics(values)

    assert stats["count"] == 5
    assert stats["min"] == 1.0
    assert stats["max"] == 5.0
    assert stats["mean"] == 3.0
    # Amostral: s = sqrt( (4 + 1 + 0 + 1 + 4) / 4 ) = sqrt(2.5) ≈ 1.5811
    assert math.isclose(stats["std"], math.sqrt(2.5), rel_tol=1e-4)


def test_calculate_statistics_single_value():
    values = [42.0]
    stats = calculate_statistics(values)
    assert stats["count"] == 1
    assert stats["min"] == 42.0
    assert stats["max"] == 42.0
    assert stats["mean"] == 42.0
    assert stats["std"] == 0.0


def test_aggregate_experiments_csv():
    with tempfile.TemporaryDirectory() as tmp_dir:
        raw_csv = Path(tmp_dir) / "raw.csv"
        out_csv = Path(tmp_dir) / "summary.csv"

        df_raw = pd.DataFrame([
            {
                "timestamp": "2026-10-04T12:00:00",
                "architecture": "sequential",
                "file_size_label": "5MB",
                "file_size_mb": 5.0,
                "clients": 2,
                "pool_size": "N/A",
                "repetition": 1,
                "client_id": 1,
                "time_seconds": 1.0,
                "bytes_received": 5242880,
                "throughput_mb_s": 5.0,
                "success": True,
            },
            {
                "timestamp": "2026-10-04T12:00:01",
                "architecture": "sequential",
                "file_size_label": "5MB",
                "file_size_mb": 5.0,
                "clients": 2,
                "pool_size": "N/A",
                "repetition": 1,
                "client_id": 2,
                "time_seconds": 2.0,
                "bytes_received": 5242880,
                "throughput_mb_s": 2.5,
                "success": True,
            },
        ])
        df_raw.to_csv(raw_csv, index=False)

        summary_df = aggregate_experiments(raw_csv, out_csv)
        assert len(summary_df) == 1
        row = summary_df.iloc[0]
        assert row["architecture"] == "sequential"
        assert row["clients"] == 2
        assert row["min_time_s"] == 1.0
        assert row["max_time_s"] == 2.0
        assert row["mean_time_s"] == 1.5
        assert out_csv.exists()
