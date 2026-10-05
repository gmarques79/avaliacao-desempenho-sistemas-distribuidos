"""
Nó P2P (Peer-to-Peer) com suporte a papéis de Seeder e Leecher.

Arquitetura:
- Cada nó possui um servidor TCP embutido para responder a requisições de blocos (chunks).
- O nó Seeder lê os blocos sob demanda diretamente do arquivo em disco (eficiência de memória).
- Os nós Leechers requisitam blocos ausentes a outros peers (incluindo outros Leechers),
  armazenam os blocos obtidos e passam a servi-los imediatamente ao enxame.
- Utiliza seleção balanceada de peers (priorizando outros leechers quando disponíveis)
  para maximizar a distribuição de carga fora do nó inicial.
"""

import json
from pathlib import Path
import random
import socket
import struct
import threading
import time
from typing import Dict, List, Optional, Set

from src.client.client import TransferResult
from src.common.protocol import recv_exact


class P2PNode:
    """Representa um participante do enxame P2P (Seeder ou Leecher)."""

    def __init__(
        self,
        peer_id: str,
        tracker_host: str,
        tracker_port: int,
        host: str = "127.0.0.1",
        port: int = 0,
        source_file: Optional[Path | str] = None,
        is_seeder: bool = False,
    ) -> None:
        self.peer_id = peer_id
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port
        self.host = host
        self.port = port
        self.source_file = Path(source_file) if source_file else None
        self.is_seeder = is_seeder

        self.server_socket: socket.socket | None = None
        self._bound_port = port
        self._running = threading.Event()
        self._server_thread: threading.Thread | None = None

        # Dados do arquivo obtidos do Tracker
        self.total_chunks: int = 0
        self.chunk_size: int = 0
        self.file_size: int = 0

        # Armazenamento em memória de blocos obtidos por leechers
        self.downloaded_chunks: Dict[int, bytes] = {}
        self._chunks_lock = threading.Lock()

        # Métricas de transferência
        self.transfer_result: Optional[TransferResult] = None

    @property
    def bound_port(self) -> int:
        return self._bound_port

    def start_server(self) -> None:
        """Inicia o servidor de upload do nó para responder a requisições de blocos."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self._bound_port = self.server_socket.getsockname()[1]
        self.server_socket.listen(128)
        self.server_socket.settimeout(0.5)

        self._running.set()
        self._server_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._server_thread.start()

    def _accept_loop(self) -> None:
        """Loop que aceita conexões de outros peers querendo baixar blocos."""
        while self._running.is_set():
            try:
                conn, _ = self.server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            worker = threading.Thread(
                target=self._handle_peer_upload,
                args=(conn,),
                daemon=True,
            )
            worker.start()

    def _handle_peer_upload(self, conn: socket.socket) -> None:
        """Envia o bloco requisitado pelo peer."""
        try:
            line = bytearray()
            while True:
                ch = conn.recv(1)
                if not ch or ch == b"\n":
                    break
                line.extend(ch)

            cmd = line.decode("utf-8").strip()
            if not cmd.startswith("GET_CHUNK "):
                return

            chunk_idx = int(cmd.split()[1])
            chunk_data: Optional[bytes] = None

            if self.is_seeder and self.source_file:
                # Seeder lê diretamente do disco
                offset = chunk_idx * self.chunk_size
                with open(self.source_file, "rb") as f:
                    f.seek(offset)
                    chunk_data = f.read(self.chunk_size)
            else:
                # Leecher lê do seu cache em memória
                with self._chunks_lock:
                    chunk_data = self.downloaded_chunks.get(chunk_idx)

            if chunk_data is not None:
                # Cabeçalho do chunk: 4 bytes índice (unsigned int) + 4 bytes tamanho
                header = struct.pack("!II", chunk_idx, len(chunk_data))
                conn.sendall(header + chunk_data)
            else:
                conn.sendall(struct.pack("!II", chunk_idx, 0))

        except Exception:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def register_in_tracker(self) -> None:
        """Registra o nó no Tracker central."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((self.tracker_host, self.tracker_port))
            req = {
                "action": "REGISTER",
                "peer_id": self.peer_id,
                "is_seeder": self.is_seeder,
                "host": self.host,
                "port": self._bound_port,
            }
            sock.sendall(json.dumps(req).encode("utf-8"))
            resp = json.loads(sock.recv(64 * 1024).decode("utf-8"))

            if resp.get("status") == "OK":
                self.total_chunks = resp["total_chunks"]
                self.chunk_size = resp["chunk_size"]
                self.file_size = resp["file_size"]
            else:
                raise RuntimeError(f"Erro ao registrar no tracker: {resp}")

    def notify_have_chunk(self, chunk_idx: int) -> None:
        """Informa ao Tracker que o nó obteve o bloco chunk_idx."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.tracker_host, self.tracker_port))
                req = {
                    "action": "HAVE",
                    "peer_id": self.peer_id,
                    "chunk_idx": chunk_idx,
                }
                sock.sendall(json.dumps(req).encode("utf-8"))
                sock.recv(1024)
        except Exception:
            pass

    def get_peers_for_chunk(self, chunk_idx: int) -> List[Dict]:
        """Consulta o Tracker sobre quais peers possuem determinado bloco."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.tracker_host, self.tracker_port))
                req = {
                    "action": "GET_PEERS_FOR_CHUNK",
                    "peer_id": self.peer_id,
                    "chunk_idx": chunk_idx,
                }
                sock.sendall(json.dumps(req).encode("utf-8"))
                resp = json.loads(sock.recv(64 * 1024).decode("utf-8"))
                if resp.get("status") == "OK":
                    return resp.get("peers", [])
        except Exception:
            pass
        return []

    def download_file_p2p(self) -> TransferResult:
        """
        Executa a transferência completa no modelo P2P:
        1. Consulta peers que detêm blocos ausentes;
        2. Baixa blocos de forma distribuída (priorizando outros leechers para desafogar o seeder);
        3. Disponibiliza cada bloco baixado imediatamente para outros nós;
        4. Mede o tempo com precisão de perf_counter().
        """
        if self.is_seeder:
            raise RuntimeError("Nó configurado como Seeder não realiza download.")

        # Início da medição de transferência P2P
        start_time = time.perf_counter()

        missing_chunks = list(range(self.total_chunks))
        # Embaralha a ordem para que diferentes leechers solicitem blocos distintos primeiro
        random.shuffle(missing_chunks)

        total_bytes_downloaded = 0

        while missing_chunks and self._running.is_set():
            chunk_idx = missing_chunks.pop(0)

            peers = self.get_peers_for_chunk(chunk_idx)
            if not peers:
                # Bloco ainda não foi propagado: recoloca na fila com breve espera
                missing_chunks.append(chunk_idx)
                time.sleep(0.01)
                continue

            # Priorização P2P: prefere baixar de outros leechers para descentralizar
            non_seeders = [p for p in peers if not p.get("is_seeder", False)]
            chosen_peer = random.choice(non_seeders) if non_seeders else random.choice(peers)

            success = False
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as p_sock:
                    p_sock.settimeout(5.0)
                    p_sock.connect((chosen_peer["host"], chosen_peer["port"]))
                    p_sock.sendall(f"GET_CHUNK {chunk_idx}\n".encode("utf-8"))

                    # Cabeçalho do chunk: 4 bytes índice + 4 bytes tamanho
                    header = recv_exact(p_sock, 8)
                    ret_idx, chunk_len = struct.unpack("!II", header)

                    if chunk_len > 0:
                        chunk_data = recv_exact(p_sock, chunk_len)
                        with self._chunks_lock:
                            self.downloaded_chunks[chunk_idx] = chunk_data
                        total_bytes_downloaded += chunk_len
                        success = True
                        # Anuncia imediatamente a disponibilidade do bloco ao enxame
                        self.notify_have_chunk(chunk_idx)

            except Exception:
                success = False

            if not success:
                # Em caso de falha de conexão com o peer selecionado, recoloca na fila
                missing_chunks.append(chunk_idx)
                time.sleep(0.01)

        # Fim da medição de transferência P2P
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time

        throughput = (
            (total_bytes_downloaded / (1024 * 1024)) / elapsed_time
            if elapsed_time > 0
            else 0.0
        )

        res = TransferResult(
            success=(len(self.downloaded_chunks) == self.total_chunks),
            elapsed_seconds=elapsed_time,
            bytes_received=total_bytes_downloaded,
            expected_bytes=self.file_size,
            throughput_mb_s=throughput,
        )
        self.transfer_result = res
        return res

    def stop(self) -> None:
        """Encerra o servidor do nó e limpa os blocos em memória."""
        self._running.clear()
        if self.server_socket:
            try:
                self.server_socket.close()
            except OSError:
                pass
            self.server_socket = None

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=1.0)

        with self._chunks_lock:
            self.downloaded_chunks.clear()
