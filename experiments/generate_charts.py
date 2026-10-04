"""
Geração Automatizada de Gráficos a partir dos Dados Experimentais.

Gera os 5 gráficos exigidos na especificação da atividade acadêmica:
1. Tempo médio × Número de clientes (para diferentes tamanhos)
2. Tempo médio × Tamanho do arquivo
3. Mínimo, médio e máximo por arquitetura
4. Comportamento do Thread Pool conforme N varia (N=2, N=4, N=8)
5. Comparação direta entre Cliente-Servidor e P2P
(Bônus: Comparação de Throughput em MB/s)
"""

import argparse
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DEFAULT_SUMMARY_CSV = Path("experiments") / "results" / "summary_metrics.csv"
DEFAULT_CHARTS_DIR = Path("experiments") / "results" / "charts"

# Configuração de estilo visual acadêmico limpo e profissional
plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.titlesize": 14,
    "grid.alpha": 0.4,
    "grid.linestyle": "--",
})

ARCH_COLORS = {
    "sequential": "#d95f02",
    "concurrent": "#1b9e77",
    "pool (N=2)": "#7570b3",
    "pool (N=4)": "#e7298a",
    "pool (N=8)": "#66a61e",
    "pool": "#e7298a",
    "p2p": "#386cb0",
}

ARCH_LABELS = {
    "sequential": "C-S Sequencial",
    "concurrent": "C-S Concorrente",
    "pool (N=2)": "Thread Pool (N=2)",
    "pool (N=4)": "Thread Pool (N=4)",
    "pool (N=8)": "Thread Pool (N=8)",
    "pool": "Thread Pool",
    "p2p": "P2P (Swarm Chunks)",
}


def load_data(summary_csv_path: Path) -> pd.DataFrame:
    if not summary_csv_path.exists():
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {summary_csv_path}")

    df = pd.read_csv(summary_csv_path)

    # Cria rótulo composto para diferenciar pools
    def get_arch_label(row):
        arch = row["architecture"]
        pool = str(row["pool_size"])
        if arch == "pool" and pool != "N/A" and pool != "nan":
            return f"pool (N={int(float(pool))})"
        return arch

    df["arch_variant"] = df.apply(get_arch_label, axis=1)
    return df


def plot_mean_time_vs_clients(df: pd.DataFrame, output_dir: Path) -> None:
    """Gráfico 1: Tempo Médio × Número de Clientes para cada tamanho de arquivo."""
    sizes = sorted(df["file_size_mb"].unique())
    fig, axes = plt.subplots(1, len(sizes), figsize=(6 * len(sizes), 5), sharey=False)
    if len(sizes) == 1:
        axes = [axes]

    for ax, sz in zip(axes, sizes):
        sub_df = df[df["file_size_mb"] == sz]
        sz_label = sub_df["file_size_label"].iloc[0]

        for variant in sorted(sub_df["arch_variant"].unique()):
            v_df = sub_df[sub_df["arch_variant"] == variant].sort_values("clients")
            color = ARCH_COLORS.get(variant, "#333333")
            label = ARCH_LABELS.get(variant, variant)
            ax.plot(
                v_df["clients"],
                v_df["mean_time_s"],
                marker="o",
                linewidth=2,
                markersize=6,
                label=label,
                color=color,
            )

        ax.set_title(f"Payload: {sz_label}")
        ax.set_xlabel("Número de Clientes")
        ax.set_ylabel("Tempo Médio (s)")
        ax.set_xticks(sorted(sub_df["clients"].unique()))
        ax.grid(True)
        ax.legend()

    plt.suptitle("Gráfico 1: Tempo Médio de Transferência × Número de Clientes", y=1.02)
    plt.tight_layout()
    out_file = output_dir / "chart1_mean_time_vs_clients.png"
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Salvo: {out_file.name}")


def plot_mean_time_vs_file_size(df: pd.DataFrame, output_dir: Path) -> None:
    """Gráfico 2: Tempo Médio × Tamanho do Arquivo (escala logarítmica)."""
    # Avalia para o cenário com número intermediário/máximo de clientes
    target_clients = df["clients"].max()
    sub_df = df[df["clients"] == target_clients]

    if sub_df.empty:
        return

    plt.figure(figsize=(8, 5))
    for variant in sorted(sub_df["arch_variant"].unique()):
        v_df = sub_df[sub_df["arch_variant"] == variant].sort_values("file_size_mb")
        color = ARCH_COLORS.get(variant, "#333333")
        label = ARCH_LABELS.get(variant, variant)
        plt.plot(
            v_df["file_size_mb"],
            v_df["mean_time_s"],
            marker="s",
            linewidth=2,
            markersize=7,
            label=label,
            color=color,
        )

    plt.title(f"Gráfico 2: Tempo Médio × Tamanho do Arquivo ({target_clients} clientes simultâneos)")
    plt.xlabel("Tamanho do Arquivo (MB)")
    plt.ylabel("Tempo Médio (s) - Escala Log")
    plt.yscale("log")
    plt.grid(True, which="both")
    plt.legend()
    plt.tight_layout()
    out_file = output_dir / "chart2_mean_time_vs_file_size.png"
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Salvo: {out_file.name}")


def plot_min_mean_max(df: pd.DataFrame, output_dir: Path) -> None:
    """Gráfico 3: Mínimo, Médio e Máximo por Arquitetura em cenário sob carga."""
    # Seleciona tamanho intermediário (ex: 50MB ou o maior disponível) e máximo de clientes
    sz = df["file_size_mb"].median() if len(df["file_size_mb"].unique()) > 1 else df["file_size_mb"].iloc[0]
    target_clients = df["clients"].max()

    sub_df = df[(df["file_size_mb"] == sz) & (df["clients"] == target_clients)]
    if sub_df.empty:
        sub_df = df[df["clients"] == target_clients]

    variants = sorted(sub_df["arch_variant"].unique())
    means = [sub_df[sub_df["arch_variant"] == v]["mean_time_s"].iloc[0] for v in variants]
    mins = [sub_df[sub_df["arch_variant"] == v]["min_time_s"].iloc[0] for v in variants]
    maxs = [sub_df[sub_df["arch_variant"] == v]["max_time_s"].iloc[0] for v in variants]

    # Barras de erro: [mean - min, max - mean]
    err_lower = np.array(means) - np.array(mins)
    err_upper = np.array(maxs) - np.array(means)
    errors = [err_lower, err_upper]

    labels = [ARCH_LABELS.get(v, v) for v in variants]
    colors = [ARCH_COLORS.get(v, "#555555") for v in variants]

    plt.figure(figsize=(9, 5))
    bars = plt.bar(labels, means, yerr=errors, capsize=6, color=colors, alpha=0.85, edgecolor="black")

    # Rótulo de valores acima das barras
    for bar, m, mi, ma in zip(bars, means, mins, maxs):
        y_pos = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            ma + (ma * 0.03),
            f"M={m:.2f}s\n[{mi:.2f}, {ma:.2f}]",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    plt.title(f"Gráfico 3: Tempo Mínimo, Médio e Máximo por Arquitetura ({target_clients} clientes)")
    plt.ylabel("Tempo (segundos)")
    plt.xticks(rotation=20, ha="right")
    plt.grid(axis="y")
    plt.tight_layout()
    out_file = output_dir / "chart3_min_mean_max_by_architecture.png"
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Salvo: {out_file.name}")


def plot_threadpool_variation(df: pd.DataFrame, output_dir: Path) -> None:
    """Gráfico 4: Comportamento do Thread Pool conforme N varia."""
    pool_df = df[df["architecture"] == "pool"].copy()
    if pool_df.empty:
        return

    pool_sizes = sorted([int(float(p)) for p in pool_df["pool_size"].unique() if p != "N/A"])
    if not pool_sizes:
        return

    plt.figure(figsize=(8, 5))
    sizes = sorted(pool_df["file_size_mb"].unique())
    target_size = sizes[1] if len(sizes) > 1 else sizes[0]
    p_sub = pool_df[pool_df["file_size_mb"] == target_size]

    for n in pool_sizes:
        n_df = p_sub[p_sub["pool_size"].astype(str).str.startswith(str(n))].sort_values("clients")
        if not n_df.empty:
            plt.plot(
                n_df["clients"],
                n_df["mean_time_s"],
                marker="^",
                linewidth=2,
                markersize=7,
                label=f"Pool Worker N={n}",
            )

    plt.title(f"Gráfico 4: Impacto da Variação de N no Thread Pool (Payload: {p_sub['file_size_label'].iloc[0]})")
    plt.xlabel("Número de Clientes Simultâneos")
    plt.ylabel("Tempo Médio (s)")
    plt.xticks(sorted(p_sub["clients"].unique()))
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    out_file = output_dir / "chart4_threadpool_variation.png"
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Salvo: {out_file.name}")


def plot_clientserver_vs_p2p(df: pd.DataFrame, output_dir: Path) -> None:
    """Gráfico 5: Comparação direta entre Cliente-Servidor (Concorrente / Pool) e P2P."""
    # Seleciona comparativo para o maior payload disponível
    sizes = sorted(df["file_size_mb"].unique())
    target_size = sizes[-1]
    sub_df = df[df["file_size_mb"] == target_size]

    selected_variants = ["concurrent", "pool (N=4)", "sequential", "p2p"]
    plt.figure(figsize=(8, 5))

    for variant in selected_variants:
        v_df = sub_df[sub_df["arch_variant"] == variant].sort_values("clients")
        if not v_df.empty:
            color = ARCH_COLORS.get(variant, "#333333")
            label = ARCH_LABELS.get(variant, variant)
            plt.plot(
                v_df["clients"],
                v_df["mean_time_s"],
                marker="D",
                linewidth=2.5,
                markersize=7,
                label=label,
                color=color,
            )

    plt.title(f"Gráfico 5: Comparativo Cliente-Servidor vs P2P (Payload: {sub_df['file_size_label'].iloc[0]})")
    plt.xlabel("Quantidade de Clientes / Leechers")
    plt.ylabel("Tempo Médio de Conclusão (s)")
    plt.xticks(sorted(sub_df["clients"].unique()))
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    out_file = output_dir / "chart5_clientserver_vs_p2p.png"
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Salvo: {out_file.name}")


def generate_all_charts(
    summary_csv_path: Path | str = DEFAULT_SUMMARY_CSV,
    output_dir: Path | str = DEFAULT_CHARTS_DIR,
) -> None:
    """Gera o conjunto completo de gráficos a partir do CSV de resumo."""
    in_path = Path(summary_csv_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = load_data(in_path)
    print(f"Carregados {len(df)} registros agregados de {in_path.name}.")

    plot_mean_time_vs_clients(df, out_dir)
    plot_mean_time_vs_file_size(df, out_dir)
    plot_min_mean_max(df, out_dir)
    plot_threadpool_variation(df, out_dir)
    plot_clientserver_vs_p2p(df, out_dir)

    print(f"\n[SUCESSO] Todos os gráficos foram gerados em: {out_dir.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Geração de gráficos comparativos a partir de métricas consolidadas."
    )
    parser.add_argument(
        "--summary-csv",
        default=str(DEFAULT_SUMMARY_CSV),
        help="Caminho do CSV com as métricas consolidadas.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_CHARTS_DIR),
        help="Diretório onde as imagens PNG serão salvas.",
    )
    args = parser.parse_args()

    try:
        generate_all_charts(args.summary_csv, args.output_dir)
    except Exception as exc:
        print(f"[ERRO] Falha ao gerar gráficos: {exc}")


if __name__ == "__main__":
    main()
