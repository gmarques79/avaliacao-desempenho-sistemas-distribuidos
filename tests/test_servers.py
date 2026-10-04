"""
Testes de integração para os servidores cliente-servidor.
"""

from pathlib import Path
import tempfile
import threading
import time

import pytest

from src.client.client import TCPClient
from src.common.file_utils import generate_test_file
from src.servers.concurrent_server import ConcurrentServer
from src.servers.sequential_server import SequentialServer


@pytest.fixture
def temp_environment():
    """Cria um diretório temporário com arquivo de teste de 1MB."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        dir_path = Path(tmp_dir)
        test_file = dir_path / "payload_1MB.dat"
        file_size = 1024 * 1024
        generate_test_file(test_file, file_size)
        yield dir_path, "payload_1MB.dat", file_size


def test_sequential_server_single_client(temp_environment):
    dir_path, filename, expected_size = temp_environment

    server = SequentialServer(host="127.0.0.1", port=0, data_dir=dir_path)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    # Aguarda o socket fazer bind
    time.sleep(0.2)
    port = server.bound_port

    try:
        client = TCPClient(host="127.0.0.1", port=port)
        result = client.download_file(filename)

        assert result.success is True
        assert result.bytes_received == expected_size
        assert result.elapsed_seconds > 0.0
        assert result.throughput_mb_s > 0.0
    finally:
        server.stop()
        server_thread.join(timeout=1.0)


def test_sequential_server_multiple_clients(temp_environment):
    dir_path, filename, expected_size = temp_environment

    server = SequentialServer(host="127.0.0.1", port=0, data_dir=dir_path)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    time.sleep(0.2)
    port = server.bound_port

    results = []
    num_clients = 3

    def run_client():
        client = TCPClient(host="127.0.0.1", port=port)
        res = client.download_file(filename)
        results.append(res)

    threads = [threading.Thread(target=run_client) for _ in range(num_clients)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    try:
        assert len(results) == num_clients
        for res in results:
            assert res.success is True
            assert res.bytes_received == expected_size
    finally:
        server.stop()
        server_thread.join(timeout=1.0)


def test_concurrent_server_multiple_clients(temp_environment):
    dir_path, filename, expected_size = temp_environment

    server = ConcurrentServer(host="127.0.0.1", port=0, data_dir=dir_path)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    time.sleep(0.2)
    port = server.bound_port

    results = []
    num_clients = 4

    def run_client():
        client = TCPClient(host="127.0.0.1", port=port)
        res = client.download_file(filename)
        results.append(res)

    threads = [threading.Thread(target=run_client) for _ in range(num_clients)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    try:
        assert len(results) == num_clients
        for res in results:
            assert res.success is True
            assert res.bytes_received == expected_size
    finally:
        server.stop()
        server_thread.join(timeout=1.0)

