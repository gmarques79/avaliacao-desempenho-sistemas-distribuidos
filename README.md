# Avaliação de Desempenho na Transferência de Arquivos em Sistemas Distribuídos

Projeto prático de avaliação de desempenho na transferência de arquivos sob diferentes arquiteturas distribuídas, desenvolvido para a disciplina de **Sistemas Distribuídos** da **Universidade Federal de Sergipe (UFS)**.

* **Repositório GitHub:** [https://github.com/gmarques79/avaliacao-desempenho-sistemas-distribuidos](https://github.com/gmarques79/avaliacao-desempenho-sistemas-distribuidos)
* **Autor:** Gustavo Marques (UFS)
* **Relatório:** https://docs.google.com/document/d/1M21r2vP2vG1t1O6oQ4b8mpjbqeX0UI3s/edit?usp=sharing&ouid=108975621930995309183&rtpof=true&sd=true

---

## 1. Contexto da Atividade

A transferência eficiente de dados em sistemas distribuídos depende criticamente da arquitetura de software, das estratégias de concorrência no servidor e da topologia de rede adotada. O projeto investiga quantitativamente como diferentes soluções se comportam quando submetidas a variações de carga e volume de dados.

O estudo avalia quatro modelos arquiteturais:
1. **Cliente-Servidor Sequencial:** O servidor atende rigorosamente uma conexão por vez; as demais aguardam no backlog TCP do sistema operacional.
2. **Cliente-Servidor Concorrente:** O servidor instancia uma nova thread para cada cliente conectado, atendendo requisições em paralelo.
3. **Cliente-Servidor com Limite de Concorrência (Thread Pool):** O servidor limita o atendimento simultâneo a $N$ threads operárias (*workers*), com $N \in \{2, 4, 8\}$ configurável.
4. **Peer-to-Peer (P2P em Enxame por Chunks):** Rede descentralizada onde clientes consumidores (*leechers*) também atuam como servidores (*seeders*), fragmentando o arquivo em blocos e compartilhando-os entre si para desafogar o nó inicial.

---

## 2. Objetivo

Desenvolver uma solução completa, estruturada e 100% reproduzível que permita:
* Executar as quatro arquiteturas sob condições controladas;
* Configurar o tamanho do arquivo (5 MB, 50 MB e 500 MB);
* Configurar a quantidade de clientes concorrentes (1, 2, 4 e 8);
* Configurar o limite $N$ do Thread Pool ($N=2, 4, 8$);
* Executar múltiplas repetições com sincronização de disparo;
* Medir tempos com precisão de nanossegundos via `time.perf_counter()`;
* Descartar os dados recebidos sem gravação em disco para isolar o tempo de rede;
* Calcular automaticamente o tempo Mínimo, Médio, Máximo e Desvio Padrão;
* Salvar os resultados em arquivos CSV;
* Gerar automaticamente gráficos comparativos em alta resolução;
* Fornecer base sólida para elaboração do relatório acadêmico.

---

## 3. Arquiteturas Implementadas

Para detalhes completos de fluxogramas e protocolos, consulte [docs/architectures.md](docs/architectures.md).

* **Sequencial:** `src/servers/sequential_server.py`
* **Concorrente:** `src/servers/concurrent_server.py`
* **Thread Pool:** `src/servers/pool_server.py`
* **P2P Swarm:** `src/p2p/tracker.py`, `src/p2p/node.py` e `src/p2p/p2p_network.py`

---

## 4. Tecnologias Utilizadas

* **Linguagem:** Python 3.13.13 (compatível com Python 3.10+)
* **Comunicação de Baixo Nível:** Módulo nativo `socket` (TCP com opção `TCP_NODELAY`)
* **Concorrência e Sincronização:** `threading`, `threading.Barrier`, `concurrent.futures.ThreadPoolExecutor`
* **Medição de Alta Resolução:** `time.perf_counter()`
* **Processamento de Dados e Visualização:** `pandas`, `tabulate` e `matplotlib`
* **Testes Automatizados:** `pytest`

---

## 5. Estrutura do Repositório

```text
avaliacao-desempenho-sistemas-distribuidos/
│
├── README.md                 # Documentação principal com instruções completas
├── .gitignore                # Regras de exclusão do Git (ignora dados brutos e temporários)
├── requirements.txt          # Dependências do projeto (matplotlib, pandas, pytest, tabulate)
│
├── src/                      # Código-fonte principal
│   ├── client/               # Cliente TCP de teste com medição estrita de transferência
│   │   └── client.py
│   ├── servers/              # Implementações dos servidores TCP
│   │   ├── base_server.py    # Lógica de streaming e despacho de sockets
│   │   ├── sequential_server.py
│   │   ├── concurrent_server.py
│   │   └── pool_server.py
│   ├── common/               # Protocolo binário e geração determinística de payloads
│   │   ├── protocol.py
│   │   └── file_utils.py
│   └── p2p/                  # Arquitetura P2P em enxame cooperativo
│       ├── tracker.py        # Coordenador de enxame (Swarm Tracker)
│       ├── node.py           # Nó P2P (Seeder e Leecher com servidor embutido)
│       └── p2p_network.py    # Orquestrador de sessões P2P
│
├── experiments/              # Scripts de execução e análise experimental
│   ├── run_experiments.py    # Orquestrador da matriz experimental completa
│   ├── calculate_metrics.py  # Agregador estatístico (mínimo, média, máximo, desvio)
│   ├── generate_charts.py    # Gerador dos 5 gráficos comparativos exigidos
│   └── results/              # Dados brutos coletados e figuras salvas
│       ├── raw_experiments_results.csv  # 1.350 medições individuais
│       ├── summary_metrics.csv          # Métricas consolidadas por cenário
│       └── charts/                      # Figuras PNG em alta resolução
│           ├── chart1_mean_time_vs_clients.png
│           ├── chart2_mean_time_vs_file_size.png
│           ├── chart3_min_mean_max_by_architecture.png
│           ├── chart4_threadpool_variation.png
│           └── chart5_clientserver_vs_p2p.png
│
├── tests/                    # 14 testes unitários e de integração automatizados
│   ├── test_protocol.py
│   ├── test_servers.py
│   ├── test_p2p.py
│   └── test_metrics.py
│
├── docs/                     # Documentação técnica aprofundada
│   ├── architectures.md      # Detalhamento de cada arquitetura
│   ├── methodology.md        # Rigor metodológico e variáveis de controle
│   └── experiments.md        # Passo a passo para reprodução
│
└── report/                   # Relatório acadêmico completo
    ├── README.md
    └── relatorio.md          # Documento acadêmico com as 14 seções e respostas
```

---

## 6. Requisitos e Instalação

### Pré-requisitos
* Python 3.10 ou superior instalado.
* Git.

### Instalação

```bash
git clone https://github.com/gmarques79/avaliacao-desempenho-sistemas-distribuidos.git
cd avaliacao-desempenho-sistemas-distribuidos
pip install -r requirements.txt
```

Para validar a integridade de todas as implementações:

```bash
pytest -v
```

---

## 7. Geração dos Arquivos de Teste

Os arquivos de carga (5 MB, 50 MB e 500 MB) são gerados em streaming de blocos de 1 MB, garantindo conteúdo determinístico e evitando consumo excessivo de memória RAM.

Para gerá-los no diretório `data/`:

```bash
python -c "from src.common.file_utils import ensure_test_files; ensure_test_files('data')"
```

> **Nota:** Arquivos de dados pesados (`.dat`) estão devidamente incluídos no `.gitignore` e não são versionados no repositório.

---

## 8. Execução Individual dos Servidores e Clientes

### Servidor Sequencial
```bash
python -m src.servers.sequential_server --port 5001 --data-dir data
```

### Servidor Concorrente (Thread por Cliente)
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

## 9. Execução Automatizada dos Experimentos

O orquestrador `experiments/run_experiments.py` automatiza toda a matriz de testes:

```bash
python -m experiments.run_experiments \
  --architectures sequential concurrent pool p2p \
  --sizes 5MB 50MB 500MB \
  --clients 1 2 4 8 \
  --repetitions 5 \
  --pool-sizes 2 4 8
```

Os resultados individuais são registrados em tempo real no arquivo:
`experiments/results/raw_experiments_results.csv`

---

## 10. Coleta dos Resultados e Cálculo das Métricas

Para agregar as 1.350 medições individuais em métricas consolidadas (Mínimo, Média, Máximo, Desvio Padrão e Throughput):

```bash
python -m experiments.calculate_metrics \
  --input-csv experiments/results/raw_experiments_results.csv \
  --output-csv experiments/results/summary_metrics.csv
```

---

## 11. Geração dos Gráficos

Para gerar o conjunto completo de figuras comparativas:

```bash
python -m experiments.generate_charts \
  --summary-csv experiments/results/summary_metrics.csv \
  --output-dir experiments/results/charts
```

Gráficos gerados:
1. `chart1_mean_time_vs_clients.png`: Tempo Médio × Número de Clientes.
2. `chart2_mean_time_vs_file_size.png`: Tempo Médio × Tamanho do Arquivo (escala log).
3. `chart3_min_mean_max_by_architecture.png`: Dispersão Mínimo, Médio e Máximo.
4. `chart4_threadpool_variation.png`: Variação de $N$ no Thread Pool ($N=2, 4, 8$).
5. `chart5_clientserver_vs_p2p.png`: Comparação Cliente-Servidor vs P2P.

---

## 12. Metodologia

* **Medição Estrita:** O tempo de transferência é cronometrado exclusivamente entre o envio da requisição e a recepção do último byte pelo cliente via `time.perf_counter()`.
* **Zero I/O no Cliente:** Os dados recebidos são imediatamente descartados em memória sem gravação em disco.
* **Sincronização:** Barreira de execução (`threading.Barrier`) para disparar todos os clientes simultaneamente.
* **Repetições:** 5 repetições para cada cenário experimental.

Consulte [docs/methodology.md](docs/methodology.md) para a descrição formal das equações e controles.

---

## 13. Resumo dos Resultados Reais

Abaixo destacam-se os dados consolidados coletados no ambiente de testes para o cenário sob maior carga (**Payload de 500 MB**):

| Arquitetura | Clientes | Parâmetro $N$ | Mínimo (s) | Média (s) | Máximo (s) | Desvio Padrão (s) | Throughput (MB/s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Sequencial | 8 | — | **0.4946** | 2.8468 | **7.0473** | 1.6968 | 293.63 |
| Concorrente | 8 | — | 2.7286 | 3.0159 | 3.3027 | **0.2052** | 166.52 |
| Thread Pool | 8 | $N=2$ | 0.7119 | **2.6639** | 6.8777 | 1.7637 | 286.75 |
| Thread Pool | 8 | $N=4$ | 2.2573 | 3.7895 | 5.5781 | 1.2622 | 148.06 |
| Thread Pool | 8 | $N=8$ | 3.8055 | 4.8965 | 6.2365 | 0.7760 | 104.60 |
| P2P | 8 | — | 20.3546 | 21.7447 | 24.2437 | 1.2861 | 23.07 |

### Principais Conclusões:
1. **Bloqueio de Início de Fila no Sequencial:** Enquanto o primeiro cliente conclui em apenas 0,49 s, o último cliente é forçado a esperar 7,05 s.
2. **Equidade no Concorrente:** Todos os clientes concluem em aproximadamente 3,0 s com desvio padrão de apenas 0,20 s.
3. **Ponto Ótimo no Thread Pool ($N=2$):** Ao limitar a concorrência a 2 workers, o servidor preservou a vazão sequencial do disco e obteve o menor tempo médio geral (2,66 s), superando $N=8$ (4,90 s), que sofreu degradação por concorrência excessiva de I/O e context switching.
4. **Cooperatividade P2P:** Leechers compartilharam blocos ativamente entre si, retirando a sobrecarga exclusiva do nó inicial.

A análise completa detalhada respondendo a todas as 12 questões da disciplina encontra-se em [report/relatorio.md](report/relatorio.md).

---

## 14. Limitações

* Testes conduzidos em loopback local (`127.0.0.1`), onde a latência de rede é desprezível e todos os processos compartilham a mesma CPU e barramento de memória.

---

## 15. Integrante

* **Gustavo Marques**  
  Departamento de Computação  
  Universidade Federal de Sergipe (UFS)
