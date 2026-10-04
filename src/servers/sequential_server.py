"""
Servidor Cliente-Servidor Sequencial.

Características arquiteturais:
- O servidor atende estritamente 1 cliente por vez no thread principal.
- Novas requisições enquanto o servidor estiver ocupado permanecem enfileiradas no
  backlog TCP do sistema operacional.
- O próximo cliente só é atendido após o término completo da transferência anterior.
- Permite observar experimentalmente o fenômeno de serialização e head-of-line blocking.
"""

import argparse
from pathlib import Path
import socket
import sys
import threading

from src.common.protocol import (
    DEFAULT_BUFFER_SIZE,
    DEFAULT_HOST,
    DEFAULT_PORT,
)
from src.servers.base_server import handle_file_request


class SequentialServer:
    """Servidor TCP sequencial monothread."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        data_dir: Path | str = "data",
        buffer_size: int = DEFAULT_BUFFER_SIZE,
        backlog: int = 128,
    ) -> None:
        self.host = host
        self.port = port
        self.data_dir = Path(data_dir)
        self.buffer_size = buffer_size
        self.backlog = backlog
        self.server_socket: socket.socket | None = None
        self._running = threading.Event()
        self._bound_port = port

    @property
    def bound_port(self) -> int:
        """Retorna a porta real em que o servidor está escutando (útil quando port=0)."""
        return self._bound_port

    def start(self) -> None:
        """Inicia o servidor e entra no loop sequencial de atendimento."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self._bound_port = self.server_socket.getsockname()[1]
        self.server_socket.listen(self.backlog)
        # Timeout para permitir checagem periódica do flag de interrupção
        self.server_socket.settimeout(0.5)

        self._running.set()
        print(f"[SEQUENTIAL SERVER] Escutando em {self.host}:{self._bound_port} (Diretório: {self.data_dir})")

        try:
            while self._running.is_set():
                try:
                    conn, addr = self.server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                # Atendimento estritamente sequencial e bloqueante no mesmo thread
                handle_file_request(conn, self.data_dir, self.buffer_size)

        finally:
            self.stop()

    def stop(self) -> None:
        """Para o loop do servidor e fecha o socket."""
        self._running.clear()
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor TCP Sequencial (1 cliente por vez).")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Endereço de bind.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Porta de escuta.")
    parser.add_argument("--data-dir", default="data", help="Diretório de arquivos a servir.")
    parser.add_argument("--buffer-size", type=int, default=DEFAULT_BUFFER_SIZE, help="Tamanho do buffer de transmissão.")
    args = parser.parse_args()

    server = SequentialServer(
        host=args.host,
        port=args.port,
        data_dir=args.data_dir,
        buffer_size=args.buffer_size,
    )

    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[SEQUENTIAL SERVER] Encerrando por sinal do usuário...")
        server.stop()


if __name__ == "__main__":
    main()
