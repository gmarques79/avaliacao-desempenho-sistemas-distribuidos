"""
Módulo base para servidores de arquivos TCP.
Centraliza utilitários de transmissão de arquivos e ciclo de vida do socket servidor.
"""

import os
from pathlib import Path
import socket
from typing import Optional

from src.common.protocol import (
    DEFAULT_BUFFER_SIZE,
    DEFAULT_HOST,
    DEFAULT_PORT,
    decode_request,
    encode_header,
)


def handle_file_request(
    conn: socket.socket,
    data_dir: Path,
    buffer_size: int = DEFAULT_BUFFER_SIZE,
) -> None:
    """
    Atende à requisição de um cliente conectado:
    1. Lê a requisição ("GET <filename>\\n");
    2. Localiza o arquivo no diretório especificado;
    3. Envia o cabeçalho de 8 bytes com o tamanho;
    4. Transmite o arquivo em blocos de tamanho `buffer_size`;
    5. Encerra a conexão.
    """
    try:
        filename = decode_request(conn)
        if not filename:
            return

        file_path = data_dir / filename

        if not file_path.is_file():
            conn.sendall(encode_header(0))
            return

        file_size = os.path.getsize(file_path)
        conn.sendall(encode_header(file_size))

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(buffer_size)
                if not chunk:
                    break
                conn.sendall(chunk)

    except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
        # Cliente encerrou ou desconectou prematuramente
        pass
    except Exception as exc:
        print(f"[ERRO] Falha ao atender requisição: {exc}")
    finally:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conn.close()
