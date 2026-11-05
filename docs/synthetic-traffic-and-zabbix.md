# Logs, tráfego sintético e monitoração Zabbix

## Aplicações e conexões

As configurações oficiais ficam em `deploy/dev` dos repositórios `cosmotech-orders-api` e `cosmotech-orders-worker`. As respectivas Actions testam, constroem, verificam a imagem e promovem automaticamente o conjunto completo ao espelho GitOps. Não há aprovação humana nesta fase. O merge automático agora refaz a validação se outra aplicação avançar main simultaneamente, com cinco tentativas limitadas.

Cada pod emite `synthetic_heartbeat` a cada 300 segundos e executa dois GETs: ao `/diagnostics/ping` do serviço par dentro do cluster e ao site HTTPS `example.com`. Os logs JSON contêm serviço, direção, status, duração e trace ID. Clientes propagam W3C traceparent; os servidores registram `synthetic_inbound`. Endpoints de diagnóstico são somente leitura e não geram pedidos, pagamentos, inventário ou mensagens SQS.

O worker publica somente três caminhos Exact: `/health/live`, `/health/ready` e `/diagnostics/ping`. A política do validador GitOps foi atualizada para permitir esse diagnóstico sem permitir rotas de negócio ou Prefix amplo. Startup probes e readiness gates do ALB continuam habilitadas.

A Lambda `cosmotech-external-http-probe` roda fora da VPC, chamada pelo EventBridge Scheduler `cosmotech-observability/external-app-http`, com `rate(5 minutes)` e flexible window OFF. Ela usa os hosts HTTPS públicos das duas aplicações e propaga traceparent. Timeout de cinco segundos por chamada, execução de vinte segundos, concorrência reservada um e zero retries assíncronos evitam sobreposição prolongada. Falhas vão ao SNS existente e ao alarme CloudWatch. A sonda é somente leitura; a próxima execução renova o teste sem necessidade de replay de dados de negócio.

## Onde consultar

- [Logs e conexões no Grafana](https://grafana.cosmotechsolutions.com.br/d/applications-connectivity-lab).
- [Zabbix: AWS, EKS, EC2 e APM](https://zabbix.cosmotechsolutions.com.br/zabbix.php?action=dashboard.view&dashboardid=439).
- Grafana Explore/Loki: `{namespace=~"orders-api|orders-worker",container=~"orders-api|orders-worker"} | json | event=~"synthetic_.*"`.
- CloudWatch Logs: `/aws/lambda/cosmotech-external-http-probe`, eventos `synthetic_external_inbound`.
- Tempo e menu APM do Zabbix: localizar pelo trace ID registrado no log. Os spans contêm cliente/servidor e chamadas externas, sem corpo de pedido, resposta ou autenticação.

O Alloy coleta somente pods do próprio node (`HOSTNAME` já fornecido pelo chart como `spec.nodeName`), evitando coleta duplicada pelos três DaemonSets. Relabeling adiciona namespace, pod, container, node, app e service_name. Trace IDs permanecem no conteúdo JSON e não viram labels persistentes do Loki. `ops/helm/values/alloy-log-labels.json` contém o override a preservar nos próximos upgrades Helm; o ConfigMap vivo foi atualizado e recarregado.

## EC2 e agentes

Agente nativo Zabbix Agent 2 `8.0.0rc3` instalado nos três hosts Ubuntu 24.04:

| Host | IP privado | Monitoração |
|---|---|---|
| cosmotech-zabbix-dev | 10.20.11.207 | Linux ativo, serviço do agente e saúde dos componentes habilitados do servidor Zabbix |
| cosmotech-itsm-dev | 10.20.11.150 | Linux ativo, CPU, memória, disco, rede e serviço do agente |
| cosmotech-argocd-dev | 10.20.11.199 | Linux ativo, CPU, memória, disco, rede e serviço do agente |

O host padrão `Zabbix server` foi reaproveitado como `cosmotech-zabbix-dev`, mantendo seu ID. Sua interface passou de 127.0.0.1 ao IP privado e o template passivo foi substituído por `Linux by Zabbix agent active`. O problema anterior do agente foi resolvido pela recepção real de dados ativos. O listener passivo de cada agente fica restrito ao loopback; a monitoração ocorre por conexão ativa TLS-PSK ao servidor privado `10.20.11.207:10051`. SGs permitem essa porta somente a partir dos três hosts. Não há porta de agente pública.

Cada host tem sua própria chave em `cosmotech/zabbix/agents/<hostname>`, no Secrets Manager. O instance profile lê apenas sua identidade; o host Zabbix lê as três para cadastro. Os valores nunca entram no Terraform ou Git. `/etc/zabbix/cosmotech-agent2.psk` usa root:zabbix, modo 0640. O pacote oficial é fixado por versão e SHA256; o documento `CosmoTech-Install-Zabbix-Agent2` e três associações SSM diárias mantêm instalação e serviço. Rotação de PSK deve coordenar o cadastro no servidor e a configuração do agente.

Os checks opcionais de saúde do servidor para recursos não habilitados (IPMI, Java, VMware, SNMP trapper, connectors e relatórios) seguem as opções do Compose e são desativados somente nesse host quando o recurso não está implantado. A configuração não desabilita métricas Linux, ingestão APM ou outros recursos ativos. Ao habilitar um recurso opcional no Compose, executar novamente `CosmoTech-Configure-Zabbix-Monitoring` para reativar seus checks.

## AWS, EKS e APM

- `cosmotech-aws-account`: inventário por serviço, custos, estado dos alarmes CloudWatch e disponibilidade dos serviços EC2, usando o coletor existente em porta privada. Serviços ausentes aparecem com contagem zero; não é feita uma afirmação de saúde detalhada para cada recurso AWS apenas por existir no inventário.
- `cosmotech-eks-cluster`: nodes Ready/total, pods Running/Pending/Failed, réplicas indisponíveis, API/worker prontos, CPU média e maior uso de disco dos nodes, através das métricas existentes no Prometheus. Não são criados tokens Kubernetes permanentes.
- `cosmotech-apm-orders-api` e `cosmotech-apm-orders-worker`: quantidade de spans, erros, percentual de erro e p95 da janela de quinze minutos no ClickHouse usado pelo APM. Há triggers para ausência de spans, erro sustentado, latência e indisponibilidade da consulta.
- `cosmotech-platform-web`: nove cenários HTTPS para aplicações e ferramentas, com intervalos de cinco minutos.

O tráfego de traces mantém a entrega ao Tempo e ao ClickHouse pelo collector compatível com Zabbix 8.0rc3. O contorno do defeito upstream do proxy nativo continua em uso. Não foi removida a monitoração por causa do defeito; a gravação foi validada no armazenamento final. Credenciais do ClickHouse vêm do arquivo root existente e são usadas somente na configuração autenticada do Zabbix.

## Retenção e recuperação

CloudWatch da sonda externa retém sete dias. A retenção Loki existente permanece; traces ClickHouse continuam com TTL de três dias. Backups e retenções dos bancos seguem a configuração anterior. Credenciais PSK têm recuperação de trinta dias no Secrets Manager. Lambda, Scheduler, chamadas HTTP, novos segredos e coletas adicionam uso faturável na AWS.

Para parar o tráfego sintético, alterar a configuração das aplicações pelo repositório e desabilitar o schedule na IaC. Para corrigir falha de conexão, verificar os campos direction/target/status_code/trace_id antes de alterar rede ou probes. No agente, verificar `systemctl status zabbix-agent2`, journal e disponibilidade ativa do host; nunca imprimir a PSK para diagnosticar. Reexecutar os documentos SSM após corrigir a causa. Os snapshots operacionais em infrastructure-iac devem acompanhar a origem em observability para uma reinstalação reproduzir os ajustes já validados.

## Evidência de 2026-11-05

Os três agentes ficaram com `active_available=1`, usando os IPs privados corretos. O Zabbix recebeu 3/3 nodes EKS Ready, zero pods Pending/Failed e zero réplicas de Deployment indisponíveis. Ambos os serviços têm spans e p95 medidos, sem item APM não suportado, e `problem.get` não apresentou problema ativo nessa validação. Logs das aplicações mostraram ciclos separados por 300 segundos e respostas internas/externas 200. A sonda pública foi validada manualmente e em execuções agendadas com 200 para ambos os hosts. Todas as consultas do novo dashboard Grafana foram aceitas no Loki e retornaram dados.
