"""
Utilitários para geração e manipulação de arquivos de dados de teste.
Garante criação determinística, rápida e sem estouro de memória para arquivos de 5MB, 50MB e 500MB.
"""

import os
from pathlib import Path
from typing import Dict

# Tamanhos canônicos especificados na atividade
SIZES_MAP: Dict[str, int] = {
    "5MB": 5 * 1024 * 1024,
    "50MB": 50 * 1024 * 1024,
    "500MB": 500 * 1024 * 1024,
}


def generate_test_file(filepath: Path | str, size_bytes: int, block_size: int = 1024 * 1024) -> Path:
    """
    Gera um arquivo binário com exatamente `size_bytes`, escrevendo blocos de tamanho `block_size`.
    Se o arquivo já existir com o tamanho exato, a geração é ignorada para evitar redundância.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.is_file() and path.stat().st_size == size_bytes:
        return path

    # Padrão cíclico determinístico de bytes
    base_pattern = bytes([i % 256 for i in range(min(block_size, 4096))])
    block = (base_pattern * ((block_size // len(base_pattern)) + 1))[:block_size]

    bytes_written = 0
    with open(path, "wb") as f:
        while bytes_written < size_bytes:
            remaining = size_bytes - bytes_written
            to_write = min(block_size, remaining)
            f.write(block[:to_write])
            bytes_written += to_write

    return path


def ensure_test_files(base_dir: Path | str = "data", sizes: Dict[str, int] = SIZES_MAP) -> Dict[str, Path]:
    """
    Garante que os arquivos de teste especificados existam no diretório base.
    Retorna um dicionário mapeando o rótulo do tamanho (ex: '5MB') para o caminho do arquivo.
    """
    target_dir = Path(base_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    generated = {}

    for label, size in sizes.items():
        filename = f"payload_{label}.dat"
        file_path = target_dir / filename
        generate_test_file(file_path, size)
        generated[label] = file_path

    return generated
