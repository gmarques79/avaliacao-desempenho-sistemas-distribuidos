"""
Orquestrador Automatizado de Experimentos de Desempenho.

Executa de forma controlada, reprodutível e sistemática as matrizes de testes para:
1. Cliente-Servidor Sequencial
2. Cliente-Servidor Concorrente
3. Cliente-Servidor com Thread Pool (N configurável)
4. Rede P2P

Grava cada medição individual em arquivo CSV com informações de timestamp, arquitetura,
tamanho do payload, quantidade de clientes, identificador do cliente, tempo e throughput.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime
import os
from pathlib import Path
import threading
import time
from typing import List, Optional

from src.client.client import TCPClient, TransferResult
from src.common.file_utils import SIZES_MAP, ensure_test_files
from src.p2p.p2p_network import run_p2p_session
from src.servers.concurrent_server import ConcurrentServer
from src.servers.pool_server import PoolServer
from src.servers.sequential_server import SequentialServer

DEFAULT_RESULTS_DIR = Path("experiments") / "results"
DEFAULT_CSV_PATH = DEFAULT_RESULTS_DIR / "raw_experiments_results.csv"

CSV_HEADERS = [
    "timestamp",
    "architecture",
    "file_size_label",
    "file_size_mb",
    "clients",
    "pool_size",
    "repetition",
    "client_id",
    "time_seconds",
    "bytes_received",
    "throughput_mb_s",
    "success",
]


def init_csv(csv_path: Path) -> None:
    """Inicializa o arquivo CSV com cabeçalho caso ainda não exista."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not csv_path.exists():
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


def record_result(
    csv_path: Path,
    architecture: str,
    file_size_label: str,
    file_size_mb: float,
    clients: int,
    pool_size: Optional[int],
    repetition: int,
    client_id: int,
    result: TransferResult,
) -> None:
    """Registra uma linha de resultado atômico no CSV."""
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            architecture,
            file_size_label,
            f"{file_size_mb:.2f}",
            clients,
            pool_size if pool_size is not None else "N/A",
            repetition,
            client_id,
            f"{result.elapsed_seconds:.6f}",
            result.bytes_received,
            f"{result.throughput_mb_s:.4f}",
            result.success,
        ])


def run_cs_iteration(
    architecture: str,
    file_name: str,
    data_dir: Path,
    num_clients: int,
    pool_size: int = 4,
) -> List[TransferResult]:
    """Inicia o servidor correspondente e dispara `num_clients` simultâneos sincronizados."""
    server = None
    if architecture == "sequential":
        server = SequentialServer(host="127.0.0.1", port=0, data_dir=data_dir)
    elif architecture == "concurrent":
        server = ConcurrentServer(host="127.0.0.1", port=0, data_dir=data_dir)
    elif architecture == "pool":
        server = PoolServer(host="127.0.0.1", port=0, data_dir=data_dir, pool_size=pool_size)
    else:
        raise ValueError(f"Arquitetura cliente-servidor desconhecida: {architecture}")

    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(0.15)  # Aguarda o socket bind
    port = server.bound_port

    results: List[TransferResult] = [None] * num_clients  # type: ignore
    barrier = threading.Barrier(num_clients)

    def worker_client(client_idx: int) -> None:
        client = TCPClient(host="127.0.0.1", port=port)
        # Sincroniza todos os clientes para dispararem no mesmo instante exato
        barrier.wait()
        res = client.download_file(file_name)
        results[client_idx] = res

    threads = [
        threading.Thread(target=worker_client, args=(i,))
        for i in range(num_clients)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=300.0)

    server.stop()
    server_thread.join(timeout=1.0)
    return results


def run_single_experiment(
    architecture: str,
    file_size_label: str,
    file_path: Path,
    num_clients: int,
    repetitions: int,
    pool_size: Optional[int] = 4,
    csv_path: Path = DEFAULT_CSV_PATH,
) -> None:
    """Executa um cenário de testes com o número de repetições configurado."""
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    print(
        f"\n>>> Executando: Arq={architecture} | Tam={file_size_label} ({file_size_mb:.1f} MB) | "
        f"Clientes={num_clients} | Repetições={repetitions}"
        + (f" | Pool={pool_size}" if architecture == "pool" else "")
    )

    for rep in range(1, repetitions + 1):
        if architecture == "p2p":
            results = run_p2p_session(
                file_path=file_path,
                num_leechers=num_clients,
            )
        else:
            results = run_cs_iteration(
                architecture=architecture,
                file_name=file_path.name,
                data_dir=file_path.parent,
                num_clients=num_clients,
                pool_size=pool_size or 4,
            )

        times = [r.elapsed_seconds for r in results if r.success]
        avg_time = sum(times) / len(times) if times else 0.0
        print(f"  Repetição {rep}/{repetitions}: Média={avg_time:.4f}s (Min={min(times):.4f}s, Max={max(times):.4f}s)")

        for c_idx, res in enumerate(results, start=1):
            record_result(
                csv_path=csv_path,
                architecture=architecture,
                file_size_label=file_size_label,
                file_size_mb=file_size_mb,
                clients=num_clients,
                pool_size=pool_size if architecture == "pool" else None,
                repetition=rep,
                client_id=c_idx,
                result=res,
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automação de Experimentos de Desempenho em Sistemas Distribuídos."
    )
    parser.add_argument(
        "--architectures",
        nargs="+",
        default=["sequential", "concurrent", "pool", "p2p"],
        choices=["sequential", "concurrent", "pool", "p2p", "all"],
        help="Arquitetura(s) a avaliar.",
    )
    parser.add_argument(
        "--sizes",
        nargs="+",
        default=["5MB", "50MB", "500MB"],
        help="Tamanho(s) dos arquivos a testar.",
    )
    parser.add_argument(
        "--clients",
        nargs="+",
        type=int,
        default=[1, 2, 4, 8],
        help="Quantidades de clientes concorrentes a testar.",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=5,
        help="Número de repetições de cada cenário (padrão: 5).",
    )
    parser.add_argument(
        "--pool-sizes",
        nargs="+",
        type=int,
        default=[2, 4, 8],
        help="Valores de N para o Thread Pool (quando aplicável). Padrão: 2 4 8.",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Diretório dos arquivos de dados de teste.",
    )
    parser.add_argument(
        "--output-csv",
        default=str(DEFAULT_CSV_PATH),
        help="Caminho do arquivo CSV de saída para os resultados brutos.",
    )

    args = parser.parse_args()

    archs = args.architectures
    if "all" in archs:
        archs = ["sequential", "concurrent", "pool", "p2p"]

    csv_path = Path(args.output_csv)
    init_csv(csv_path)

    # 1. Garante existência dos arquivos de teste solicitados
    print(f"Garantindo arquivos de teste em '{args.data_dir}' para tamanhos: {args.sizes}...")
    size_dict = {s: SIZES_MAP[s] for s in args.sizes if s in SIZES_MAP}
    generated_files = ensure_test_files(base_dir=args.data_dir, sizes=size_dict)
    print("Arquivos prontos.")

    # 2. Executa a matriz de experimentos
    total_start = time.perf_counter()
    for size_label in args.sizes:
        file_path = generated_files[size_label]
        for num_clients in args.clients:
            for arch in archs:
                if arch == "pool":
                    for p_size in args.pool_sizes:
                        run_single_experiment(
                            architecture=arch,
                            file_size_label=size_label,
                            file_path=file_path,
                            num_clients=num_clients,
                            repetitions=args.repetitions,
                            pool_size=p_size,
                            csv_path=csv_path,
                        )
                else:
                    run_single_experiment(
                        architecture=arch,
                        file_size_label=size_label,
                        file_path=file_path,
                        num_clients=num_clients,
                        repetitions=args.repetitions,
                        pool_size=None,
                        csv_path=csv_path,
                    )

    total_elapsed = time.perf_counter() - total_start
    print(f"\n[CONCLUÍDO] Todos os experimentos foram executados em {total_elapsed:.2f} segundos!")
    print(f"Resultados brutos armazenados em: {csv_path.resolve()}")


if __name__ == "__main__":
    main()
