"""
Cálculo de Métricas Estatísticas dos Experimentos.

Consolida os resultados brutos em métricas resumidas por cenário:
- Tempo Mínimo (s)
- Tempo Médio (s)
- Tempo Máximo (s)
- Desvio Padrão do Tempo (s)
- Taxa de Transferência Média (MB/s)

Salva o resultado em CSV consolidado e imprime tabelas legíveis em formato Markdown
para incorporação direta no relatório acadêmico.
"""

import argparse
import math
from pathlib import Path
from typing import Dict, List

import pandas as pd

DEFAULT_RAW_CSV = Path("experiments") / "results" / "raw_experiments_results.csv"
DEFAULT_SUMMARY_CSV = Path("experiments") / "results" / "summary_metrics.csv"


def calculate_statistics(values: List[float]) -> Dict[str, float]:
    """Calcula estatísticas descritivas básicas de forma determinística."""
    if not values:
        return {"min": 0.0, "mean": 0.0, "max": 0.0, "std": 0.0, "count": 0}

    n = len(values)
    min_val = min(values)
    max_val = max(values)
    mean_val = sum(values) / n

    if n > 1:
        variance = sum((x - mean_val) ** 2 for x in values) / (n - 1)
        std_val = math.sqrt(variance)
    else:
        std_val = 0.0

    return {
        "count": n,
        "min": min_val,
        "mean": mean_val,
        "max": max_val,
        "std": std_val,
    }


def aggregate_experiments(
    raw_csv_path: Path | str,
    output_summary_csv: Path | str = DEFAULT_SUMMARY_CSV,
) -> pd.DataFrame:
    """Carrega o CSV de dados brutos e gera o DataFrame com as métricas consolidadas."""
    raw_path = Path(raw_csv_path)
    if not raw_path.exists():
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {raw_path}")

    df = pd.read_csv(raw_path)

    if "success" in df.columns:
        df = df[df["success"] == True]

    group_cols = ["architecture", "file_size_label", "file_size_mb", "clients", "pool_size"]

    summary_records = []
    grouped = df.groupby(group_cols, dropna=False)

    for keys, group in grouped:
        times = group["time_seconds"].astype(float).tolist()
        throughputs = group["throughput_mb_s"].astype(float).tolist()

        t_stats = calculate_statistics(times)
        tp_stats = calculate_statistics(throughputs)

        record = {
            "architecture": keys[0],
            "file_size_label": keys[1],
            "file_size_mb": float(keys[2]),
            "clients": int(keys[3]),
            "pool_size": keys[4],
            "samples_count": t_stats["count"],
            "min_time_s": round(t_stats["min"], 6),
            "mean_time_s": round(t_stats["mean"], 6),
            "max_time_s": round(t_stats["max"], 6),
            "std_time_s": round(t_stats["std"], 6),
            "mean_throughput_mb_s": round(tp_stats["mean"], 4),
            "min_throughput_mb_s": round(tp_stats["min"], 4),
            "max_throughput_mb_s": round(tp_stats["max"], 4),
        }
        summary_records.append(record)

    summary_df = pd.DataFrame(summary_records)
    summary_df = summary_df.sort_values(
        by=["file_size_mb", "clients", "architecture", "pool_size"]
    ).reset_index(drop=True)

    out_path = Path(output_summary_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(out_path, index=False)

    return summary_df


def format_markdown_table(summary_df: pd.DataFrame) -> str:
    """Gera uma visualização tabular elegante em Markdown para o relatório."""
    display_df = summary_df.copy()
    display_df = display_df.rename(
        columns={
            "architecture": "Arquitetura",
            "file_size_label": "Tamanho",
            "clients": "Clientes",
            "pool_size": "N (Pool)",
            "min_time_s": "T. Mín (s)",
            "mean_time_s": "T. Méd (s)",
            "max_time_s": "T. Máx (s)",
            "std_time_s": "Desvio (s)",
            "mean_throughput_mb_s": "Throughput (MB/s)",
        }
    )
    cols = [
        "Arquitetura",
        "Tamanho",
        "Clientes",
        "N (Pool)",
        "T. Mín (s)",
        "T. Méd (s)",
        "T. Máx (s)",
        "Desvio (s)",
        "Throughput (MB/s)",
    ]
    return display_df[cols].to_markdown(index=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agregação e cálculo de métricas estatísticas dos experimentos."
    )
    parser.add_argument(
        "--input-csv",
        default=str(DEFAULT_RAW_CSV),
        help="Caminho do CSV bruto de entrada.",
    )
    parser.add_argument(
        "--output-csv",
        default=str(DEFAULT_SUMMARY_CSV),
        help="Caminho do CSV consolidado de saída.",
    )
    args = parser.parse_args()

    try:
        summary_df = aggregate_experiments(args.input_csv, args.output_csv)
        print(f"\n[SUCESSO] Métricas consolidadas salvas em: {Path(args.output_csv).resolve()}")
        print("\n=== RESUMO DAS MÉTRICAS COLETADAS ===\n")
        print(format_markdown_table(summary_df))
    except Exception as exc:
        print(f"[ERRO] Falha ao processar métricas: {exc}")


if __name__ == "__main__":
    main()
