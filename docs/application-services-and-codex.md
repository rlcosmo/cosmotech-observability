# Serviços EC2, discos, Codex e APM

## Painéis

- [Observabilidade](https://grafana.cosmotechsolutions.com.br/d/observability-tools-lab): aplicações Zabbix, Argo CD, Kestra e GLPI, suas dependências de aplicação e filesystems persistentes das três EC2. Nodes EKS continuam nos painéis Kubernetes.
- [AWS e custos](https://grafana.cosmotechsolutions.com.br/d/aws-account-costs-lab): percentual disponível nas duas janelas do Codex, horário real de renovação no fuso do navegador e idade da coleta.
- [Zabbix](https://zabbix.cosmotechsolutions.com.br/): nome correto com dois b. Zabbix 8.0.0rc3 em EC2 privada dedicada `i-02878f35eed1572d0`, 4 vCPU, 16 GiB RAM e 120 GiB gp3 criptografado. Esta capacidade gera cobrança AWS.

## Como interpretar e recuperar

O timer `cosmotech-monitoring.timer` no host ITSM coleta a cada minuto usando seu instance profile. O documento SSM sem parâmetros `CosmoTech-Read-Application-Health` consulta somente processos de aplicação, disponibilidade de réplicas Argo e uso dos discos; não retorna ambiente ou credenciais. O IAM permite a execução apenas nas três EC2 da plataforma.

UP significa container ativo/saudável ou réplicas prontas; DOWN identifica o nome do serviço parado, ausente ou não saudável. DESCONHECIDO significa falha de sondagem ou leitura vencida, nunca aproveitamento de UP antigo. A tabela mostra host, aplicação, serviço e comando de recuperação sugerido para a infra avaliar. Nenhum serviço é reiniciado pelo painel. Antes de recuperar, consultar logs locais e espaço livre. Dados de filesystem incluem total, usado e disponível por montagem; a cor fica laranja em 80% e vermelha em 90%.

A coleta fica sem validade depois de 180 segundos. A tabela de idade e o estado do coletor permitem diferenciar indisponibilidade da aplicação e falha de monitoramento. O Prometheus mantém o histórico conforme a retenção existente de 24 horas. Snapshots locais mantêm somente nomes e estados para reportar UNKNOWN durante falhas; não contêm segredos.

## Cota Codex

`scripts/publish_codex_usage.py` consulta `account/rateLimits/read` do `codex app-server` autenticado na estação. Somente percentuais, duração das janelas e timestamps de reset são publicados no parâmetro String `/cosmotech/monitoring/codex-usage`, assumindo por STS o papel `cosmotech-codex-usage-publisher`. Esse papel só grava esse parâmetro. A role do coletor só lê esse parâmetro. Credenciais OpenAI, email, conversas e conteúdo de autenticação ficam na estação.

O daemon `python3 scripts/publish_codex_usage.py --daemon` publica a cada cinco minutos, com lock para impedir duplicação. Está ativo na estação atual. Sua execução depende da estação e da sessão autenticada disponíveis; ao fechar a estação, o painel deixa de mostrar a cota após quinze minutos. Reiniciar o daemon ao iniciar outra sessão de trabalho. Logs em `~/.cache/cosmotech-codex-usage/publisher.log` contêm somente sucesso/falha e timestamp. Não se estima um saldo em tokens: a interface oficial fornece percentual disponível e renovação, não esse saldo absoluto. Fonte: https://learn.chatgpt.com/docs/app-server .

## APM e retenção

O collector EKS mantém a entrega ao Tempo e também envia traces por OTLP/gRPC ao host Zabbix em `10.20.11.207:4317`. Apenas o security group EKS pode acessar essa porta; a interface web 8088 aceita apenas o ALB TLS existente. PostgreSQL e ClickHouse não publicam portas. Não há IP público ou SSH nessa EC2.

O proxy nativo do pré-release tem um defeito conhecido ao serializar DateTime64 no ClickHouse, aceitando dados que podem não ser gravados: https://support.zabbix.com/browse/ZBX-28212 . Foi adotado o contorno descrito no chamado: um collector contrib com exporter ClickHouse grava diretamente o schema compatível, com confirmação síncrona e retries limitados. O proxy permanece registrado, seu listener de diagnóstico está restrito ao loopback 14317. O pipeline ativo passa pelo collector `telemetry`, incluído na sondagem de serviços. Remover o contorno somente após validar uma versão do proxy que grave o trace completo.

As tabelas foram geradas dos scripts oficiais de `8.0.0rc3`, com hashes em `ops/zabbix/telemetry-schema-source.json`. A retenção de telemetria é três dias (TTL de 259200 segundos). O cadastro global de datasource foi configurado via API, com senha lida exclusivamente no host. A senha de Admin foi alterada, Guests desativado e credenciais guardadas em SSM SecureString `/cosmotech/zabbix/credentials`. Não colocar credenciais em dashboards, Git ou Terraform.

Backup lógico diário do PostgreSQL às 03:17, retenção de sete dias; a seleção AWS Backup inclui a EC2/EBS para recuperação consistente em crash. Restaurar primeiro os volumes em ambiente isolado, subir bancos e schema, iniciar os serviços e confirmar uma nova ingestão antes de trocar o destino público. Não apagar volumes durante reinstalação. Logs Docker têm limite de três arquivos de 10 MB por serviço.

## Evidências em 2026-11-05

Grafana confirmou os dashboards atualizados via API: observabilidade com 34 painéis e AWS com 27. Todas as expressões PromQL foram aceitas; 16 serviços UP, nenhum DOWN/desconhecido e nove montagens das três EC2 chegaram ao Prometheus. Testes verificam DOWN com nome do serviço, falha de sondagem sem falso UP, isolamento de credenciais na publicação e rejeição de cota inválida.

O trace sintético `2f21ad81a92c0035378cac8ff6de13f7` foi enviado no EKS pelo pipeline real, encontrado em `zabbix.otel_traces` no ClickHouse e contado como um registro. Isso valida ingestão fim a fim sem criar pedido de negócio. APM exibirá traces reais das aplicações quando as operações instrumentadas receberem tráfego.
