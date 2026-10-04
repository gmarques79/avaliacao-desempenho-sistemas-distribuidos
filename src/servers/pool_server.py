"""
Servidor Cliente-Servidor com Limite de Concorrência (Thread Pool).

Características arquiteturais:
- Utiliza a abstração de alto nível `concurrent.futures.ThreadPoolExecutor`.
- Mantém um conjunto fixo e configurável de N threads trabalhadoras (workers).
- As requisições de clientes aceitas são submetidas ao pool como tarefas assíncronas.
- Caso existam mais de N conexões simultâneas, as excedentes aguardam na fila do pool
  até que um worker termine a transferência corrente e fique livre.
- Permite avaliar experimentalmente o controle de sobrecarga de recursos (CPU e descritores),
  testando valores típicos como N=2, N=4 e N=8.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
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


class PoolServer:
    """Servidor TCP com concorrência limitada via ThreadPoolExecutor."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        data_dir: Path | str = "data",
        pool_size: int = 4,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
        backlog: int = 128,
    ) -> None:
        if pool_size < 1:
            raise ValueError("O tamanho do Thread Pool (N) deve ser de pelo menos 1.")

        self.host = host
        self.port = port
        self.data_dir = Path(data_dir)
        self.pool_size = pool_size
        self.buffer_size = buffer_size
        self.backlog = backlog
        self.server_socket: socket.socket | None = None
        self._executor: ThreadPoolExecutor | None = None
        self._running = threading.Event()
        self._bound_port = port

    @property
    def bound_port(self) -> int:
        """Retorna a porta real em que o servidor está escutando."""
        return self._bound_port

    def start(self) -> None:
        """Inicia o executor e o loop de aceitação de conexões."""
        self._executor = ThreadPoolExecutor(
            max_workers=self.pool_size,
            thread_name_prefix="ThreadPoolWorker",
        )
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self._bound_port = self.server_socket.getsockname()[1]
        self.server_socket.listen(self.backlog)
        self.server_socket.settimeout(0.5)

        self._running.set()
        print(
            f"[POOL SERVER] Escutando em {self.host}:{self._bound_port} "
            f"(Thread Pool N={self.pool_size} workers)"
        )

        try:
            while self._running.is_set():
                try:
                    conn, addr = self.server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                # Submete o atendimento ao pool de threads configurado
                if self._executor and not self._executor._shutdown:
                    self._executor.submit(
                        handle_file_request,
                        conn,
                        self.data_dir,
                        self.buffer_size,
                    )
                else:
                    try:
                        conn.close()
                    except OSError:
                        pass

        finally:
            self.stop()

    def stop(self) -> None:
        """Encerra o loop e finaliza o pool de threads com segurança."""
        self._running.clear()
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None

        if self._executor:
            try:
                self._executor.shutdown(wait=True, cancel_futures=True)
            except Exception:
                pass
            self._executor = None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Servidor TCP com Limite de Concorrência (ThreadPoolExecutor)."
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Endereço de bind.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Porta de escuta.")
    parser.add_argument("--data-dir", default="data", help="Diretório de arquivos a servir.")
    parser.add_argument(
        "--pool-size",
        "-N",
        type=int,
        default=4,
        help="Quantidade máxima de threads operárias simultâneas (N). Padrão: 4.",
    )
    parser.add_argument(
        "--buffer-size",
        type=int,
        default=DEFAULT_BUFFER_SIZE,
        help="Tamanho do buffer de transmissão.",
    )
    args = parser.parse_args()

    server = PoolServer(
        host=args.host,
        port=args.port,
        data_dir=args.data_dir,
        pool_size=args.pool_size,
        buffer_size=args.buffer_size,
    )

    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[POOL SERVER] Encerrando por sinal do usuário...")
        server.stop()


if __name__ == "__main__":
    main()
