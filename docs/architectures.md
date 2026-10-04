# Arquiteturas Distribuídas Implementadas

Este documento descreve a organização interna, o funcionamento dos fluxos de conexão e os princípios de concorrência das quatro arquiteturas avaliadas.

---

## 1. Cliente-Servidor Sequencial

### Princípio de Funcionamento
O servidor sequencial opera sob um laço mono-thread. Ao aceitar uma conexão (`accept()`), ele bloqueia o fluxo principal para atender exclusivamente àquele cliente até a transmissão do último byte do arquivo.

```text
       Cliente 1 ───► [ Conexão Ativa ] ───► Transmissão de Dados
       Cliente 2 ───► [ Fila TCP (Backlog) ] ───► Aguardando...
       Cliente 3 ───► [ Fila TCP (Backlog) ] ───► Aguardando...
```

### Características Técnicas
* **Concorrência:** Nenhuma no nível da aplicação.
* **Comportamento sob Carga:** Fenômeno de *Head-of-Line Blocking* (bloqueio de início de fila). Se o Cliente 1 leva 5 segundos para baixar o arquivo, o Cliente 2 experimentará uma latência mínima percebida de 5 segundos antes de sequer iniciar a transmissão de seus dados, totalizando aproximadamente 10 segundos para sua conclusão.
* **Consumo de Recursos:** Mínimo consumo de CPU e memória, sem sobrecarga de *context switching*.

---

## 2. Cliente-Servidor Concorrente (Thread por Cliente)

### Princípio de Funcionamento
Para cada conexão aceita pelo laço principal, o servidor instancia uma nova thread do sistema operacional (`threading.Thread`) dedicada a atender aquele cliente específico.

```text
                      ┌───► Thread Worker 1 ───► Cliente 1 (Transmissão Simultânea)
  [ Accept Loop ] ────┼───► Thread Worker 2 ───► Cliente 2 (Transmissão Simultânea)
                      └───► Thread Worker 3 ───► Cliente 3 (Transmissão Simultânea)
```

### Características Técnicas
* **Concorrência:** Dinâmica e sem teto explícito de threads.
* **Comportamento sob Carga:** Todos os clientes recebem fatias do tempo de CPU e da largura de banda da placa de rede simultaneamente. Não há bloqueio sequencial.
* **Sobrecarga (Overhead):** A criação contínua de threads introduz custo de alocação de pilhas de memória e custos de chaveamento de contexto no escalonador do sistema operacional.

---

## 3. Cliente-Servidor com Limite de Concorrência (Thread Pool)

### Princípio de Funcionamento
Utiliza um conjunto pré-alocado e fixo de $N$ threads de trabalho através da classe `concurrent.futures.ThreadPoolExecutor`. Quando chegam conexões adicionais além de $N$, as requisições aguardam na fila interna do pool.

```text
  [ Conexões Clientes ] ──► [ Fila de Tarefas do Pool ]
                                   │
               ┌───────────────────┼───────────────────┐
               ▼                   ▼                   ▼
        [ Worker Thread 1 ] [ Worker Thread 2 ] ... [ Worker Thread N ]
               │                   │                   │
               ▼                   ▼                   ▼
           Cliente 1           Cliente 2           Cliente N
```

### Características Técnicas
* **Concorrência:** Limitada estritamente ao parâmetro $N$ configurado (avaliado com $N=2$, $N=4$ e $N=8$).
* **Comportamento sob Carga:** Protege o servidor contra exaustão de descritores de arquivo e sobrecarga excessiva de chaveamento de contexto. O throughput permanece previsível e estável.
* **Trade-off:** Se $C > N$, os clientes além do limite $N$ sofrem enfileiramento parcial até que os primeiros liberem os workers.

---

## 4. Peer-to-Peer (P2P em Enxame por Chunks)

### Princípio de Funcionamento
A arquitetura P2P descentraliza a entrega de dados. O arquivo original é dividido em $M$ blocos (*chunks*) indexados de tamanho fixo (256 KB).

1. **Tracker Central (Swarm Coordinator):** Mantém a tabela de quais nós possuem quais blocos e gerencia o registro do enxame.
2. **Nó Seeder Inicial:** Possui todos os blocos $\{0, 1, \dots, M-1\}$ e atua como a fonte primária.
3. **Nós Leechers (Consumidores e Distribuidores Simultâneos):**
   * Cada leecher abre um servidor TCP local em porta própria para fornecer blocos já baixados.
   * Concorrentemente, consulta os outros nós e busca blocos ausentes.
   * Ao receber um bloco $k$, o leecher avisa ao Tracker (`HAVE k`) e passa a servir esse bloco para qualquer outro leecher.
   * A seleção de provedores prioriza outros leechers em vez do seeder inicial, desafogando o nó raiz.

```text
                           [ Tracker / Swarm ]
                             ▲      ▲      ▲
                             │      │      │
                      ┌──────┴──────┼──────┴──────┐
                      ▼             ▼             ▼
                 [ Seeder 0 ] ◄──────────► [ Leecher 1 ]
                      ▲                           ▲
                      │                           │
                      ▼                           ▼
                 [ Leecher 2 ] ◄──────────► [ Leecher 3 ]
```

### Características Técnicas
* **Concorrência:** Totalmente distribuída e cooperativa.
* **Capacidade de Rede:** A largura de banda total de upload do sistema cresce proporcionalmente à quantidade de leechers conectados à rede, pois cada novo cliente adiciona capacidade de serviço aos demais.
