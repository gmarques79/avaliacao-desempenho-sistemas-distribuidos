"""
Tracker / Coordenador de Swarm para a arquitetura P2P.

Funções do Tracker:
1. Registra os nós participantes da rede (IP, porta, papel: seeder ou leecher);
2. Mantém o mapeamento dos blocos (chunks) disponíveis em cada nó;
3. Responde a consultas dos leechers sobre quais nós possuem determinado bloco;
4. Notifica novos nós disponíveis para troca direta (P2P mesh).
"""

import json
import socket
import threading
from typing import Dict, List, Set, Tuple


class SwarmTracker:
    """Tracker centralizado em memória para coordenação do swarm P2P."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self.host = host
        self.port = port
        self.server_socket: socket.socket | None = None
        self._bound_port = port
        self._running = threading.Event()
        self._lock = threading.Lock()

        self.file_name: str = ""
        self.file_size: int = 0
        self.chunk_size: int = 0
        self.total_chunks: int = 0

        # Mapeamento do enxame: peer_id -> {"host": str, "port": int, "chunks": Set[int]}
        self.peers: Dict[str, Dict] = {}

    @property
    def bound_port(self) -> int:
        return self._bound_port

    def set_file_info(self, file_name: str, file_size: int, chunk_size: int) -> None:
        """Configura os metadados do arquivo a ser distribuído no swarm."""
        with self._lock:
            self.file_name = file_name
            self.file_size = file_size
            self.chunk_size = chunk_size
            self.total_chunks = (file_size + chunk_size - 1) // chunk_size

    def start(self) -> None:
        """Inicia o serviço do Tracker."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self._bound_port = self.server_socket.getsockname()[1]
        self.server_socket.listen(128)
        self.server_socket.settimeout(0.5)

        self._running.set()

        try:
            while self._running.is_set():
                try:
                    conn, _ = self.server_socket.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                handler = threading.Thread(
                    target=self._handle_client,
                    args=(conn,),
                    daemon=True,
                )
                handler.start()
        finally:
            self.stop()

    def _handle_client(self, conn: socket.socket) -> None:
        """Processa requisições JSON enviadas por peers."""
        try:
            data = conn.recv(64 * 1024).decode("utf-8").strip()
            if not data:
                return

            req = json.loads(data)
            action = req.get("action")
            response = {}

            with self._lock:
                if action == "REGISTER":
                    peer_id = req["peer_id"]
                    is_seeder = req.get("is_seeder", False)
                    p_host = req["host"]
                    p_port = req["port"]

                    initial_chunks: Set[int] = (
                        set(range(self.total_chunks)) if is_seeder else set()
                    )

                    self.peers[peer_id] = {
                        "host": p_host,
                        "port": p_port,
                        "chunks": initial_chunks,
                        "is_seeder": is_seeder,
                    }

                    response = {
                        "status": "OK",
                        "total_chunks": self.total_chunks,
                        "chunk_size": self.chunk_size,
                        "file_size": self.file_size,
                    }

                elif action == "HAVE":
                    peer_id = req["peer_id"]
                    chunk_idx = req["chunk_idx"]
                    if peer_id in self.peers:
                        self.peers[peer_id]["chunks"].add(chunk_idx)
                    response = {"status": "OK"}

                elif action == "GET_PEERS_FOR_CHUNK":
                    chunk_idx = req["chunk_idx"]
                    requesting_peer = req.get("peer_id")
                    candidate_peers = []

                    for pid, pdata in self.peers.items():
                        if pid != requesting_peer and chunk_idx in pdata["chunks"]:
                            candidate_peers.append({
                                "peer_id": pid,
                                "host": pdata["host"],
                                "port": pdata["port"],
                                "is_seeder": pdata["is_seeder"],
                            })

                    response = {"status": "OK", "peers": candidate_peers}

                elif action == "GET_SWARM_STATE":
                    response = {
                        "status": "OK",
                        "total_chunks": self.total_chunks,
                        "peers": {
                            pid: {
                                "host": pdata["host"],
                                "port": pdata["port"],
                                "chunk_count": len(pdata["chunks"]),
                                "is_seeder": pdata["is_seeder"],
                            }
                            for pid, pdata in self.peers.items()
                        },
                    }

                else:
                    response = {"status": "ERROR", "message": f"Ação desconhecida: {action}"}

            payload = json.dumps(response).encode("utf-8")
            conn.sendall(payload)

        except Exception as exc:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def stop(self) -> None:
        """Para o tracker e libera a porta."""
        self._running.clear()
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None
