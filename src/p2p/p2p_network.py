"""
Orquestrador de sessão de rede P2P para experimentos automatizados.

Gerencia o ciclo de vida completo:
1. Inicia o SwarmTracker;
2. Configura e conecta o nó Seeder inicial;
3. Instancia N nós Leechers simultâneos em threads separadas;
4. Dispara a transferência P2P distribuída e coleta as medições individuais;
5. Finaliza todos os nós e libera recursos com segurança.
"""

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import threading
import time
from typing import List

from src.client.client import TransferResult
from src.p2p.node import P2PNode
from src.p2p.tracker import SwarmTracker


def run_p2p_session(
    file_path: Path | str,
    num_leechers: int,
    chunk_size: int | None = None,
) -> List[TransferResult]:
    """
    Executa um experimento P2P completo com 1 Seeder inicial e `num_leechers` Leechers.
    Retorna a lista de TransferResult de cada nó consumidor.
    """
    path = Path(file_path)
    file_size = os.path.getsize(path)

    # Dimensionamento adaptativo do chunk para manter total de blocos equilibrado
    if chunk_size is None:
        if file_size <= 10 * 1024 * 1024:
            chunk_size = 256 * 1024       # 256 KB para 5MB (~20 chunks)
        elif file_size <= 100 * 1024 * 1024:
            chunk_size = 1024 * 1024      # 1 MB para 50MB (~50 chunks)
        else:
            chunk_size = 4 * 1024 * 1024  # 4 MB para 500MB (~125 chunks)

    tracker = SwarmTracker(host="127.0.0.1", port=0)
    tracker.set_file_info(
        file_name=path.name,
        file_size=file_size,
        chunk_size=chunk_size,
    )
    tracker_thread = threading.Thread(target=tracker.start, daemon=True)
    tracker_thread.start()
    time.sleep(0.1)

    tracker_port = tracker.bound_port

    seeder = P2PNode(
        peer_id="seeder-0",
        tracker_host="127.0.0.1",
        tracker_port=tracker_port,
        host="127.0.0.1",
        port=0,
        source_file=path,
        is_seeder=True,
    )
    seeder.start_server()
    seeder.register_in_tracker()

    leechers: List[P2PNode] = []
    for i in range(num_leechers):
        leecher = P2PNode(
            peer_id=f"leecher-{i+1}",
            tracker_host="127.0.0.1",
            tracker_port=tracker_port,
            host="127.0.0.1",
            port=0,
            source_file=None,
            is_seeder=False,
        )
        leecher.start_server()
        leecher.register_in_tracker()
        leechers.append(leecher)

    results: List[TransferResult] = []
    with ThreadPoolExecutor(max_workers=max(num_leechers, 1)) as executor:
        futures = [executor.submit(node.download_file_p2p) for node in leechers]
        for f in futures:
            results.append(f.result())

    for leecher in leechers:
        leecher.stop()
    seeder.stop()
    tracker.stop()
    tracker_thread.join(timeout=1.0)

    return results
