"""
Implementação do Cliente TCP para avaliação de desempenho de transferências de arquivos.

O cliente:
1. Conecta-se ao servidor TCP de destino;
2. Inicia o cronômetro de alta precisão (time.perf_counter());
3. Envia a requisição do arquivo ("GET <filename>\\n");
4. Lê o cabeçalho com o tamanho esperado em bytes;
5. Recebe o fluxo de dados em blocos, descartando-os imediatamente em memória (sem persistência em disco);
6. Finaliza a contagem do tempo de transferência;
7. Retorna métricas detalhadas (tempo decorrido, total transferido, throughput em MB/s).
"""

import argparse
from dataclasses import dataclass
import socket
import sys
import time
from typing import Optional

from src.common.protocol import (
    DEFAULT_BUFFER_SIZE,
    DEFAULT_HOST,
    DEFAULT_PORT,
    HEADER_SIZE,
    decode_header,
    encode_request,
    recv_exact,
)


@dataclass
class TransferResult:
    """Resultado com métricas da transferência realizada pelo cliente."""
    success: bool
    elapsed_seconds: float
    bytes_received: int
    expected_bytes: int
    throughput_mb_s: float
    error_message: Optional[str] = None

    def __str__(self) -> str:
        if not self.success:
            return f"[FALHA] Erro: {self.error_message}"
        return (
            f"[SUCESSO] Recebidos: {self.bytes_received / (1024 * 1024):.2f} MB | "
            f"Tempo: {self.elapsed_seconds:.4f} s | "
            f"Taxa: {self.throughput_mb_s:.2f} MB/s"
        )


class TCPClient:
    """Cliente TCP otimizado para medição de transferências de dados sem persistência em disco."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        buffer_size: int = DEFAULT_BUFFER_SIZE,
        timeout: float = 300.0,
    ) -> None:
        self.host = host
        self.port = port
        self.buffer_size = buffer_size
        self.timeout = timeout

    def download_file(self, filename: str) -> TransferResult:
        """
        Executa a conexão, envio da requisição e recebimento do arquivo.
        A medição com time.perf_counter() engloba estritamente o ciclo de requisição e recebimento.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        # Desabilita o algoritmo de Nagle para evitar latências artificiais em pequenos pacotes
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        bytes_received = 0
        expected_bytes = 0

        try:
            # 1. Estabelece a conexão física TCP
            sock.connect((self.host, self.port))

            # =========================================================================
            # INÍCIO FORMAL DA MEDIÇÃO DA TRANSFERÊNCIA
            # =========================================================================
            start_time = time.perf_counter()

            # 2. Envia a requisição do arquivo solicitado
            request_payload = encode_request(filename)
            sock.sendall(request_payload)

            # 3. Lê o cabeçalho binário (8 bytes com o tamanho do arquivo)
            header_bytes = recv_exact(sock, HEADER_SIZE)
            expected_bytes = decode_header(header_bytes)

            if expected_bytes == 0:
                end_time = time.perf_counter()
                elapsed = end_time - start_time
                return TransferResult(
                    success=False,
                    elapsed_seconds=elapsed,
                    bytes_received=0,
                    expected_bytes=0,
                    throughput_mb_s=0.0,
                    error_message=f"Arquivo '{filename}' não encontrado ou vazio no servidor.",
                )

            # 4. Recebe o fluxo de dados em chunks, descartando-os sem salvar em disco
            while bytes_received < expected_bytes:
                to_read = min(self.buffer_size, expected_bytes - bytes_received)
                chunk = sock.recv(to_read)
                if not chunk:
                    raise ConnectionError(
                        f"Conexão encerrada prematuramente. Recebidos {bytes_received} de {expected_bytes} bytes."
                    )
                bytes_received += len(chunk)
                # O chunk é descartado pelo coletor do Python sem escrita em disco

            # =========================================================================
            # FIM FORMAL DA MEDIÇÃO DA TRANSFERÊNCIA
            # =========================================================================
            end_time = time.perf_counter()
            elapsed_time = end_time - start_time

            throughput = (
                (bytes_received / (1024 * 1024)) / elapsed_time
                if elapsed_time > 0
                else 0.0
            )

            return TransferResult(
                success=True,
                elapsed_seconds=elapsed_time,
                bytes_received=bytes_received,
                expected_bytes=expected_bytes,
                throughput_mb_s=throughput,
            )

        except Exception as exc:
            return TransferResult(
                success=False,
                elapsed_seconds=0.0,
                bytes_received=bytes_received,
                expected_bytes=expected_bytes,
                throughput_mb_s=0.0,
                error_message=str(exc),
            )
        finally:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Cliente TCP para teste de transferência de arquivos.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Endereço IP ou hostname do servidor.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Porta TCP do servidor.")
    parser.add_argument("--file", required=True, help="Nome do arquivo a ser requisitado.")
    parser.add_argument("--buffer-size", type=int, default=DEFAULT_BUFFER_SIZE, help="Tamanho do buffer de leitura (bytes).")
    args = parser.parse_args()

    client = TCPClient(host=args.host, port=args.port, buffer_size=args.buffer_size)
    print(f"Requisitando '{args.file}' de {args.host}:{args.port}...")
    result = client.download_file(args.file)
    print(result)
    if not result.success:
        sys.exit(1)


if __name__ == "__main__":
    main()
