# V2-002 — SQS e Workers

Implementação preparada no repositório canônico, sem alterações nos Workers: eles já expõem contadores e histogramas reais. O coletor existente passa a consultar oito métricas CloudWatch: backlog, in-flight, atrasadas, idade, DLQ e somas de mensagens enviadas/recebidas/deletadas por janela de 60s. Throughput processado é o contador de sucessos do Worker; recebimento/deleção SQS pode incluir duplicatas e não equivale a pedidos únicos.

Gauges ausentes, inválidos ou com atraso superior a 180s invalidam a coleta. Contadores esparsos em fila ociosa emitem disponibilidade=0 e omitem a taxa, preservando gauges válidos. Não substituir falta de dados por zero. Consultas usam namespace AWS/SQS e nomes EKS presentes na IaC canônica; confirmar as dimensões reais antes do aceite. Configuração opcional: LAB_SQS_QUEUE_NAME/LAB_SQS_DLQ_NAME.

Dashboard `cosmotech-v2-sqs-workers`: backlog, in-flight, throughput, retries, falhas/ACK, P50/P95/P99, idade, DLQ, freshness e saúde de scrape. Percentis são de processamento (inclusive tentativas com falha), não de latência ponta a ponta; sem amostras não há percentil válido. Agregação separa stable/canary. Histograma atual limita resolução da cauda a 180s.

Oito alertas incluem coleta ausente/stale, backlog >100 por 10m, idade >180s por 5m, DLQ >0 por 2m, erros, retries, P95 >30s com pelo menos 20 amostras e scrape ausente. Limiares são iniciais de laboratório, não SLO contratado. Alertas SQS exigem freshness; o alerta de evidência cobre a ausência. Roteamento reutiliza o Alertmanager/SNS existente após revisão. Não foram enviados alertas de teste reais.

Entrega declarativa: ConfigMap de dashboard e PrometheusRule em ops/kubernetes. Confirmar label selector do Prometheus e sidecar Grafana existente. Importação deve ocorrer pelo proprietário GitOps/Helm, sem chamada manual à API Grafana. Esses manifests ainda não estão sincronizados pelo Argo CD.

Para DLQ: investigar logs e correlação, preservar mensagens, corrigir causa via PR/pipeline e planejar replay idempotente aprovado. Não consumir/purgar/redrive automático. Para backlog: distinguir ausência de consumidores, dependência lenta e taxa de entrada; não escalar fora da IaC. Para coleta ausente: verificar role CloudWatch, dimensões, horário e endpoint privado /lab-metrics.

Testes locais: 26 testes pytest aprovados, incluindo collector integrado, permissões negadas, dados inválidos/stale e contadores esparsos; bash e compilação Python aprovados. PromQL e testes de firing/recovery executados no CI com promtool. Importação/queries reais, scrape e entrega de notificações seguem pendentes até execução autorizada com role e pipeline. Não declarar operação real a partir de JSON válido.

Custos novos provisionados: nenhum. Após ativação, são oito chamadas GetMetricStatistics por minuto, além das séries no Prometheus e uso de CI; estimar pela tarifa/quota vigente. Não são oito chamadas gratuitas garantidas.

## Evidência CI e preparação DR

CI aprovado no commit babf8c3: https://github.com/rlcosmo/cosmotech-observability/actions/runs/42367303704. Promtool confirmou oito regras e os cenários de DLQ/freshness/ausência/falhas. O teste detectou uma duplicação de alertas por labels; corrigida por agregação antes do aceite.

Dashboard adicional `cosmotech-v2-dr-readiness` preparado com disponibilidade por região, RTO, RPO e indisponibilidade em andamento. Depende de probes/exportador ainda não implantados. Não usar este dashboard como evidência de DR operacional.
