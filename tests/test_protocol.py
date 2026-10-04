"""
Testes unitários para o protocolo e utilitários de arquivo.
"""

import io
import socket
import tempfile
from pathlib import Path

import pytest

from src.common.protocol import (
    decode_header,
    decode_request,
    encode_header,
    encode_request,
    recv_exact,
    send_exact,
)
from src.common.file_utils import generate_test_file


def test_request_encoding_decoding():
    filename = "payload_5MB.dat"
    encoded = encode_request(filename)
    assert encoded == b"GET payload_5MB.dat\n"

    # Simula socket com stream de bytes
    server_sock, client_sock = socket.socketpair()
    try:
        client_sock.sendall(encoded)
        decoded = decode_request(server_sock)
        assert decoded == filename
    finally:
        server_sock.close()
        client_sock.close()


def test_header_encoding_decoding():
    file_size = 524288000  # 500 MB
    header = encode_header(file_size)
    assert len(header) == 8
    decoded_size = decode_header(header)
    assert decoded_size == file_size


def test_send_and_recv_exact():
    server_sock, client_sock = socket.socketpair()
    data = b"Hello, Distributed Systems!" * 50
    try:
        client_sock.sendall(data)
        received = recv_exact(server_sock, len(data))
        assert received == data
    finally:
        server_sock.close()
        client_sock.close()


def test_generate_test_file():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "test_dummy.dat"
        target_size = 1024 * 1024  # 1 MB
        generate_test_file(test_file, target_size, block_size=64 * 1024)

        assert test_file.exists()
        assert test_file.stat().st_size == target_size
