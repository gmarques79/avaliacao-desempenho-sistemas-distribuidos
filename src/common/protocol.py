"""
Módulo de protocolo de comunicação binária TCP para transferência de arquivos.

O protocolo define:
- Enquadramento da requisição: String textual codificada em UTF-8 terminada por '\\n'
  Formato: "GET <filename>\\n"
- Enquadramento da resposta:
  - Cabeçalho: 8 bytes (inteiro unsigned long long em big-endian - '!Q') com o tamanho total do arquivo em bytes.
    Se o tamanho for 0, o arquivo não foi encontrado ou está inacessível.
  - Carga útil (Payload): Fluxo de bytes brutos exatamente do tamanho especificado no cabeçalho.
"""

import socket
import struct
from typing import Optional

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5001
DEFAULT_BUFFER_SIZE = 64 * 1024
HEADER_FORMAT = "!Q"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


def send_exact(sock: socket.socket, data: bytes) -> None:
    """
    Garante o envio de exatamente todos os bytes contidos em `data`.
    Lança socket.error caso a conexão seja encerrada antes da conclusão.
    """
    sock.sendall(data)


def recv_exact(sock: socket.socket, n_bytes: int) -> bytes:
    """
    Recebe exatamente `n_bytes` do socket especificado.
    Lança ConnectionError ou EOFError se a conexão for encerrada antes de ler a quantidade esperada.
    """
    received = bytearray()
    while len(received) < n_bytes:
        chunk = sock.recv(n_bytes - len(received))
        if not chunk:
            raise ConnectionError(
                f"Conexão encerrada inesperadamente após ler {len(received)} de {n_bytes} bytes esperados."
            )
        received.extend(chunk)
    return bytes(received)


def encode_request(filename: str) -> bytes:
    """Codifica a requisição de arquivo no formato 'GET <filename>\\n'."""
    clean_filename = filename.strip()
    return f"GET {clean_filename}\n".encode("utf-8")


def decode_request(sock: socket.socket) -> Optional[str]:
    """
    Lê a linha de comando enviada pelo cliente até o caractere '\\n'.
    Retorna o nome do arquivo requisitado ou None se a conexão foi fechada.
    """
    buffer = bytearray()
    while True:
        chunk = sock.recv(1)
        if not chunk:
            return None
        if chunk == b"\n":
            break
        buffer.extend(chunk)
        if len(buffer) > 1024:  # Proteção contra requisições maliciosas ou desmedidas
            raise ValueError("Nome do arquivo na requisição excedeu o limite máximo (1024 bytes).")

    line = buffer.decode("utf-8").strip()
    if line.startswith("GET "):
        return line[4:].strip()
    return line


def encode_header(file_size_bytes: int) -> bytes:
    """Empacota o tamanho do arquivo em 8 bytes big-endian."""
    return struct.pack(HEADER_FORMAT, file_size_bytes)


def decode_header(header_bytes: bytes) -> int:
    """Desempacota os 8 bytes do cabeçalho retornando o tamanho do arquivo."""
    return struct.unpack(HEADER_FORMAT, header_bytes)[0]
