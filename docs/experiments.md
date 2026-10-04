# Guia de Reprodução dos Experimentos

Este guia detalha os procedimentos necessários para reproduzir integralmente os experimentos, recalcular as métricas estatísticas e regenerar os gráficos.

---

## 1. Preparação do Ambiente

Clone o repositório e certifique-se de possuir Python 3.10+ instalado:

```bash
git clone https://github.com/gmarques79/avaliacao-desempenho-sistemas-distribuidos.git
cd avaliacao-desempenho-sistemas-distribuidos
pip install -r requirements.txt
```

---

## 2. Geração dos Arquivos de Carga (Payloads)

Os arquivos de teste de 5 MB, 50 MB e 500 MB são gerados de forma determinística e não são versionados no Git para não poluir o repositório.

Para gerá-los manualmente:

```bash
python -c "from src.common.file_utils import ensure_test_files; ensure_test_files('data')"
```

Caso você execute o orquestrador `run_experiments.py`, os arquivos ausentes serão gerados automaticamente antes da bateria de testes.

---

## 3. Execução Individual dos Módulos

### Servidor Sequencial
```bash
python -m src.servers.sequential_server --port 5001 --data-dir data
```

### Servidor Concorrente
```bash
python -m src.servers.concurrent_server --port 5001 --data-dir data
```

### Servidor com Thread Pool (N configurável)
```bash
python -m src.servers.pool_server --port 5001 --data-dir data --pool-size 4
```

### Cliente TCP Individual
```bash
python -m src.client.client --host 127.0.0.1 --port 5001 --file payload_50MB.dat
```

---

## 4. Execução Automatizada da Matriz Experimental

O script `experiments/run_experiments.py` permite parametrizar:
* `--architectures`: `sequential`, `concurrent`, `pool`, `p2p`, ou `all`.
* `--sizes`: `5MB`, `50MB`, `500MB`.
* `--clients`: lista de clientes simultâneos (ex: `1 2 4 8`).
* `--repetitions`: número de repetições por cenário (padrão: `5`).
* `--pool-sizes`: valores de $N$ para o pool (ex: `2 4 8`).

### Exemplo: Bateria Completa dos Experimentos
```bash
python -m experiments.run_experiments \
  --architectures sequential concurrent pool p2p \
  --sizes 5MB 50MB 500MB \
  --clients 1 2 4 8 \
  --repetitions 5 \
  --pool-sizes 2 4 8
```

Os dados brutos coletados por cada cliente em cada repetição serão salvos em:
`experiments/results/raw_experiments_results.csv`

---

## 5. Cálculo das Métricas e Sumarização

Para agregar os dados e calcular o Tempo Mínimo, Tempo Médio, Tempo Máximo e Desvio Padrão:

```bash
python -m experiments.calculate_metrics \
  --input-csv experiments/results/raw_experiments_results.csv \
  --output-csv experiments/results/summary_metrics.csv
```

---

## 6. Geração dos Gráficos Comparativos

Para gerar as figuras em PNG a partir do CSV consolidado:

```bash
python -m experiments.generate_charts \
  --summary-csv experiments/results/summary_metrics.csv \
  --output-dir experiments/results/charts
```

As imagens geradas incluirão:
1. `chart1_mean_time_vs_clients.png`
2. `chart2_mean_time_vs_file_size.png`
3. `chart3_min_mean_max_by_architecture.png`
4. `chart4_threadpool_variation.png`
5. `chart5_clientserver_vs_p2p.png`
