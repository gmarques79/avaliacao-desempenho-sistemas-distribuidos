# Metodologia Experimental de Avaliação de Desempenho

Este documento estabelece as diretrizes científicas, variáveis de controle, procedimentos de amostragem e rigor metodológico empregados na avaliação comparativa de transferência de arquivos em diferentes arquiteturas de Sistemas Distribuídos.

---

## 1. Objetivos da Avaliação

Investigar o comportamento temporal e a escalabilidade de quatro modelos arquiteturais sob cargas crescentes de concorrência e volume de dados:
1. **Cliente-Servidor Sequencial (Monothread):** Baseline com serialização estrita.
2. **Cliente-Servidor Concorrente (Thread-per-client):** Concorrência dinâmica sem teto rígido.
3. **Cliente-Servidor com Limite de Concorrência (Thread Pool):** Concorrência controlada com $N \in \{2, 4, 8\}$ threads operárias.
4. **Peer-to-Peer (P2P Mesh por Chunks):** Distribuição descentralizada com compartilhamento de blocos entre consumidores (*leechers*).

---

## 2. Variáveis Experimentais

### 2.1 Variáveis Independentes

* **Arquitetura de Comunicação:**
  * `sequential`
  * `concurrent`
  * `pool` (com parâmetros $N=2$, $N=4$, $N=8$)
  * `p2p` (com fragmentação em blocos e retransmissão cruzada)
* **Tamanho do Arquivo (Payload):**
  * $5\text{ MB} = 5 \times 1024 \times 1024\text{ bytes} = 5.242.880\text{ bytes}$
  * $50\text{ MB} = 50 \times 1024 \times 1024\text{ bytes} = 52.428.800\text{ bytes}$
  * $500\text{ MB} = 500 \times 1024 \times 1024\text{ bytes} = 524.288.000\text{ bytes}$
* **Concorrência (Clientes / Nós Consumidores):**
  * $C \in \{1, 2, 4, 8\}$ clientes simultâneos.
* **Repetições:**
  * $R = 5$ repetições independentes para cada tupla $\langle \text{Arquitetura}, \text{Tamanho}, \text{Clientes} \rangle$.

### 2.2 Variáveis Dependentes (Métricas Coletadas)

Para cada execução de cliente individual, é registrado o tempo decorrido $t_i$. Para cada conjunto de $n$ amostras de um cenário ($n = C \times R$), calculam-se:

* **Tempo Mínimo ($T_{\min}$):**
  $$T_{\min} = \min(t_1, t_2, \dots, t_n)$$
* **Tempo Médio ($\bar{T}$):**
  $$\bar{T} = \frac{1}{n} \sum_{i=1}^n t_i$$
* **Tempo Máximo ($T_{\max}$):**
  $$T_{\max} = \max(t_1, t_2, \dots, t_n)$$
* **Desvio Padrão Amostral ($s$):**
  $$s = \sqrt{\frac{1}{n - 1} \sum_{i=1}^n (t_i - \bar{T})^2}$$
* **Taxa Média de Transferência (Throughput em MB/s):**
  $$\text{Throughput} = \frac{\text{Bytes Recebidos} / (1024 \times 1024)}{t_i}$$

---

## 3. Protocolo de Medição e Isolamento

Para garantir que a medição reflita **exclusivamente a transferência de rede** e a eficiência da arquitetura distribuída:

1. **Janela de Medição Estrita:**
   O cronômetro de alta resolução `time.perf_counter()` é acionado imediatamente antes do envio do primeiro byte da requisição pelo cliente e interrompido no exato instante em que o último byte esperado do arquivo é recebido do socket.
2. **Eliminação de Gargalo de I/O em Disco no Cliente:**
   Conforme especificado no enunciado, **o cliente descarta os bytes recebidos diretamente em memória**. Nenhum arquivo é gravado em disco pelo cliente receptor, eliminando distorções causadas por latência de escrita em disco, cache de filesystem ou saturação de gravação.
3. **Sincronização de Disparo Concorrente:**
   Todos os $C$ clientes de cada iteração são conectados e sincronizados por meio de uma barreira de execução (`threading.Barrier(C)`). Isso assegura que todos os clientes iniciem suas requisições no mesmo milissegundo, provocando a concorrência e o enfileiramento real no servidor.
4. **Desabilitação do Algoritmo de Nagle:**
   O socket dos clientes e servidores utiliza a opção `TCP_NODELAY`, impedindo que pequenos pacotes de controle sofram atrasos artificiais de coalescência.
5. **Leitura em Streaming no Servidor:**
   O servidor lê os arquivos do disco em blocos fixos de 64 KB (`sendall`), evitando alocar a totalidade do payload (ex: 500 MB) na memória RAM de uma única vez para cada cliente, garantindo estabilidade e escalabilidade.

---

## 4. Controle do Ambiente Experimental

Todas as baterias de testes devem ser executadas com o registro das características da plataforma:

* **Sistema Operacional:** Microsoft Windows 11 Pro 64-bit
* **Interpretador:** Python 3.13.13
* **Interface de Rede:** Loopback TCP/IP (`127.0.0.1`), garantindo repetibilidade e isolamento de interferências de tráfego externo de Internet.
* **Tamanho de Buffer:** 64 KB (padrão otimizado para TCP socket em SO moderno).
* **Backlog de Conexões:** 128 conexões na fila do socket de escuta.
