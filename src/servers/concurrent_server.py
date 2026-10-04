"""
Servidor Cliente-Servidor Concorrente (Thread por Cliente).

Características arquiteturais:
- Para cada nova conexão aceita no socket de escuta, o servidor instancia e dispara
  um novo thread dedicado (threading.Thread).
- Todos os clientes conectados são atendidos simultaneamente, dividindo a largura de banda
  e ciclos de processamento de forma concorrente.
- A thread é encerrada automaticamente assim que a transferência do arquivo é finalizada.
- Permite comparar a sobrecarga de criação de threads e o paralelismo em relação aos
  modelos sequencial e com pool fixo.
"""

import argparse
from pathlib import Path
import socket
import sys
import threading
from typing import List

from src.common.protocol import (
    DEFAULT_BUFFER_SIZE,
    DEFAULT_HOST,
    DEFAULT_PORT,
)
from src.servers.base_server import handle_file_request


class ConcurrentServer:
    """Servidor TCP concorrente que cria uma thread para cada cliente conectado."""

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
        self._threads: List[threading.Thread] = []
        self._lock = threading.Lock()

    @property
    def bound_port(self) -> int:
        """Retorna a porta real em que o servidor está escutando."""
        return self._bound_port

    def start(self) -> None:
        """Inicia o servidor e atende clientes criando uma nova thread para cada conexão."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self._bound_port = self.server_socket.getsockname()[1]
        self.server_socket.listen(self.backlog)
        self.server_socket.settimeout(0.5)

        self._running.set()
        print(f"[CONCURRENT SERVER] Escutando em {self.host}:{self._bound_port} (Thread-per-client)")

        try:
            while self._running.is_set():
                try:
                    conn, addr = self.server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                # Cria e despacha uma nova thread para o cliente
                thread = threading.Thread(
                    target=handle_file_request,
                    args=(conn, self.data_dir, self.buffer_size),
                    daemon=True,
                    name=f"ClientWorker-{addr[0]}:{addr[1]}",
                )
                thread.start()

                with self._lock:
                    # Limpa referências a threads já concluídas
                    self._threads = [t for t in self._threads if t.is_alive()]
                    self._threads.append(thread)

        finally:
            self.stop()

    def stop(self) -> None:
        """Interrompe o servidor e aguarda a finalização das threads ativas."""
        self._running.clear()
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None

        with self._lock:
            active_threads = list(self._threads)

        for thread in active_threads:
            thread.join(timeout=1.0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor TCP Concorrente (1 thread por cliente).")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Endereço de bind.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Porta de escuta.")
    parser.add_argument("--data-dir", default="data", help="Diretório de arquivos a servir.")
    parser.add_argument("--buffer-size", type=int, default=DEFAULT_BUFFER_SIZE, help="Tamanho do buffer de transmissão.")
    args = parser.parse_args()

    server = ConcurrentServer(
        host=args.host,
        port=args.port,
        data_dir=args.data_dir,
        buffer_size=args.buffer_size,
    )

    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[CONCURRENT SERVER] Encerrando por sinal do usuário...")
        server.stop()


if __name__ == "__main__":
    main()
