"""
Testes de integração para a arquitetura P2P.
"""

from pathlib import Path
import tempfile

import pytest

from src.common.file_utils import generate_test_file
from src.p2p.p2p_network import run_p2p_session


@pytest.fixture
def temp_test_file():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "p2p_payload.dat"
        file_size = 1024 * 1024  # 1 MB
        generate_test_file(test_file, file_size)
        yield test_file, file_size


def test_p2p_single_leecher(temp_test_file):
    test_file, expected_size = temp_test_file
    results = run_p2p_session(
        file_path=test_file,
        num_leechers=1,
        chunk_size=128 * 1024,
    )

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].bytes_received == expected_size
    assert results[0].elapsed_seconds > 0.0


def test_p2p_multiple_leechers(temp_test_file):
    test_file, expected_size = temp_test_file
    num_leechers = 3
    results = run_p2p_session(
        file_path=test_file,
        num_leechers=num_leechers,
        chunk_size=128 * 1024,
    )

    assert len(results) == num_leechers
    for r in results:
        assert r.success is True
        assert r.bytes_received == expected_size
        assert r.elapsed_seconds > 0.0
