# APM e descoberta automática AWS

O Zabbix 8.0.0rc3 recebe os três sinais reais das aplicações `orders-api` e `orders-worker`:

- Traces: SDK HTTP OTLP → collector EKS → Tempo e collector privado do Zabbix.
- Métricas: SDK OTLP exporta contagem e histograma de duração por operação, tipo de span e resultado a cada 60 segundos. As chamadas sintéticas permanecem em 300 segundos. URLs completas, payloads e identificadores de pedidos não são dimensões.
- Logs: Alloy coleta somente os containers das aplicações para o ramo APM e mantém a coleta existente no Loki. O JSON original é preservado; serviço, namespace, pod, severidade e trace/span IDs são normalizados para OTLP.

O collector do Zabbix grava traces, métricas e logs no mesmo schema ClickHouse oficial da versão, com retenção de três dias. Filtrar por `orders-api` ou `orders-worker` e janela recente em **APM → Metrics/Logs**. A validação usa `apmmetric.get` e `apmlog.get`, os serviços nativos que alimentam a interface. A coleta não retroage aos períodos anteriores à ativação. Dados antigos eventualmente relidos pelo Alloy não alteram a retenção nem a janela de aceitação do Loki.

## Descoberta e monitoramento

O host `cosmotech-aws-discovery-us-east-1` usa o template oficial **AWS by HTTP**. A descoberta EC2 roda a cada cinco minutos; ELB, Lambda, S3, RDS, ECS e Backup a cada quinze minutos. Recursos ausentes não geram hosts fictícios. Os hosts descobertos recebem templates nativos com itens, triggers, descobertas dependentes de volumes/jobs/targets e dashboards dos templates. Recursos AWS ficam no grupo **CosmoTech / AWS Resources**.

A região configurada é `us-east-1`; ampliar regiões exige ajustar filtros e IAM juntos. As seis EC2 existentes incluem os três nós EKS. Os três servidores Ubuntu das ferramentas mantêm adicionalmente agentes TLS PSK para CPU, memória, filesystem e estado dos serviços. Nós gerenciados do EKS usam monitoramento AWS e Kubernetes; não se instala um pacote Ubuntu nesses nós.

A autenticação usa IMDSv2 e `AssumeRole` para `cosmotech-zabbix-aws-monitoring`, com permissões de leitura de inventário e CloudWatch. Não há chaves permanentes em macros. O hop limit de IMDSv2 é 2 exclusivamente na EC2 Zabbix para o container servidor obter as credenciais do perfil. A role assumida não lê dados de objetos S3, payloads, filas ou segredos. As identidades dos agentes continuam no Secrets Manager.

O documento SSM `CosmoTech-Configure-Zabbix-Discovery` reconcilia configuração e dashboards a cada 30 minutos via State Manager. Não exclui recursos AWS nem reinicia aplicações. A implantação do código de cada aplicação continua no respectivo repositório, com promoção automática para GitOps.

## Compatibilidade da pré-release

O reconciliador aplica correções limitadas aos templates nativos instalados desta versão:

1. Prototypes AWS HTTP herdam a ausência de interface do controlador, evitando tratar IDs de instâncias/buckets como IPs de agente.
2. Nomes visíveis EC2 incluem o Instance ID, evitando colisão entre nós com o mesmo Name tag.
3. Scripts de Backup recebem `metadata_auth` e o argumento `/` ausente na chamada STS de seis argumentos.
4. Campos opcionais de vault sem Vault Lock/air gap são descartados quando ausentes. O item e trigger independentes de erro da API são preservados.

Reavaliar essas correções antes de atualizar os templates oficiais. O script é idempotente e as substituições de código são exatas.

## Dashboards e alertas

- **CosmoTech | APM - Traces Metrics Logs**: volume dos três sinais e logs de erro por aplicação.
- **CosmoTech | AWS - Descoberta e infraestrutura**: EC2 descobertas, problemas, CPU/status checks e erros Lambda/ALB.
- **CosmoTech | EC2 - Sistema operacional e discos**: uma página por servidor, CPU, memória, uptime, filesystem e serviços reais `zabbix-agent2`, `docker` ou `k3s`.
- O dashboard anterior de AWS/EKS/EC2/APM continua disponível.

Alertas incluem ausência de sinais APM em 15 minutos, logs de erro, agente/serviço inativo, CPU/disco e falhas AWS dos templates. As métricas guardam sete dias de histórico e trinta dias de tendências conforme o configurador; templates AWS mantêm suas políticas próprias. CloudWatch GetMetricData e coletas adicionais têm custo variável por uso.

## Operação e recuperação

As versões dos charts Alloy 1.15.0 e OpenTelemetry Collector 0.178.2 são preservadas. Aplicar os valores versionados em `ops/helm/values/` com `--reuse-values --server-side=false` e revisar o manifesto antes da atualização. Confirmar também os valores persistidos no release, não apenas a ConfigMap. Para recuperar o fluxo anterior, reverter o commit e os valores do Helm; não apagar os volumes Postgres/ClickHouse. O erro de ingestão do proxy APM nativo desta pré-release continua contornado pelo collector, preservando o schema e o frontend nativos.

## Alerta operacional encontrado na implantação

A descoberta encontrou um alerta real no NLB do Istio: o target group HTTPS `k8s-istiosys-istioing-281ec43271` aponta para a NodePort 31146, mapeada ao targetPort 8443 do gateway, sem targets saudáveis. Os três alvos retornaram `Target.FailedHealthChecks` no ELB. Esse listener é distinto das rotas públicas das aplicações atendidas pelo ALB, que continuam HTTP 200. O alerta foi preservado no Zabbix; nenhuma porta/listener foi removida para ocultá-lo. A correção do listener TLS exige alinhar o gateway/terminação TLS ao uso pretendido desse NLB.
