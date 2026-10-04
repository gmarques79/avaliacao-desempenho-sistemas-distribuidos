# Avaliação de Desempenho na Transferência de Arquivos em Sistemas Distribuídos

Projeto de avaliação de desempenho na transferência de arquivos utilizando diferentes arquiteturas distribuídas, desenvolvido para a disciplina de **Sistemas Distribuídos** da **Universidade Federal de Sergipe (UFS)**.

---

## 1. Contexto da Atividade

A avaliação de desempenho de sistemas distribuídos sob diferentes padrões arquiteturais permite compreender o impacto da concorrência, do escalonamento de recursos e da topologia de rede no throughput e na latência de transferência de dados.

O projeto avalia quatro variações arquiteturais:

1. **Cliente-Servidor Sequencial:** O servidor atende estritamente uma conexão por vez. Demais conexões aguardam na fila do sistema operacional (backlog TCP).
2. **Cliente-Servidor Concorrente:** O servidor cria uma thread dedicada para cada cliente conectado, atendendo requisições simultaneamente.
3. **Cliente-Servidor com Limite de Concorrência (Thread Pool):** O servidor limita o atendimento simultâneo a um número máximo configurável $N$ de threads operárias (*workers*), enfileirando requisições excedentes.
4. **Peer-to-Peer (P2P):** Rede descentralizada onde nós atuam concorrentemente como consumidores (*leechers*) e fornecedores (*seeders*), fragmentando o arquivo em blocos (*chunks*) para distribuir a carga de transmissão entre múltiplos participantes.

Os experimentos avaliam variações sistemáticas de:
* **Tamanho do arquivo:** 5 MB, 50 MB e 500 MB.
* **Quantidade de clientes/nós simultâneos:** 1, 2, 4 e 8.
* **Tamanho do Thread Pool ($N$):** 2, 4 e 8.
* **Métricas coletadas por cliente:** Tempo mínimo, médio, máximo e desvio padrão.

---

## 2. Tecnologias

* **Linguagem Principal:** Python 3.13+
* **Comunicação em Rede:** Módulo `socket` nativo (TCP/IP com enquadramento binário)
* **Concorrência e Paralelismo:** Módulos `threading` e `concurrent.futures.ThreadPoolExecutor`
* **Medição de Alta Resolução:** `time.perf_counter()`
* **Tratamento de Dados e Visualização:** `pandas` e `matplotlib`
* **Testes Automatizados:** `pytest`

---

## 3. Estrutura do Repositório

```text
avaliacao-desempenho-sistemas-distribuidos/
│
├── README.md                 # Documentação principal do projeto
├── .gitignore                # Regras de exclusão do Git (ignora dados pesados e temporários)
├── requirements.txt          # Dependências do projeto
│
├── src/                      # Código-fonte da aplicação
│   ├── client/               # Implementação do cliente de transferência TCP
│   │   └── client.py
│   ├── servers/              # Implementações dos servidores
│   │   ├── sequential_server.py
│   │   ├── concurrent_server.py
│   │   └── pool_server.py
│   ├── common/               # Protocolo binário, geração de payloads e utilitários
│   │   ├── protocol.py
│   │   └── file_utils.py
│   └── p2p/                  # Arquitetura Peer-to-Peer em swarm por blocos
│       ├── tracker.py
│       ├── node.py
│       └── p2p_network.py
│
├── experiments/              # Automação e processamento experimental
│   ├── run_experiments.py    # Orquestrador automatizado dos cenários
│   ├── calculate_metrics.py  # Agregação estatística (mínimo, média, máximo, desvio)
│   ├── generate_charts.py    # Geração dos gráficos comparativos
│   └── results/              # Dados brutos (CSV) e figuras geradas (PNG)
│
├── tests/                    # Suíte de testes unitários e de integração
│   ├── test_protocol.py
│   ├── test_servers.py
│   └── test_p2p.py
│
├── docs/                     # Documentação detalhada
│   ├── architectures.md      # Detalhamento de cada arquitetura
│   ├── methodology.md        # Metodologia experimental e controles
│   └── experiments.md        # Guia passo a passo de reprodução
│
└── report/                   # Base para geração do relatório acadêmico final
    └── README.md
```

---

## 4. Requisitos e Instalação

### Pré-requisitos
* Python 3.10 ou superior instalado.
* Git.

### Instalação das dependências

```bash
git clone https://github.com/gmarques79/avaliacao-desempenho-sistemas-distribuidos.git
cd avaliacao-desempenho-sistemas-distribuidos
pip install -r requirements.txt
```

---

## 5. Integrante

* **Gustavo Marques** — Departamento de Computação — Universidade Federal de Sergipe (UFS)
