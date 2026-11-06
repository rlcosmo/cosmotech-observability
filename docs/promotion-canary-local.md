# RCL e Canary — evidência integrada06/11/2026

PodMonitor atualizado para propagar cosmotech.io/gmud-id em métricas. Dashboard uid orders-worker-canary instalado no Grafana por API e lido de volta:12 painéis pt-BR, legenda RCL/versão/canal. Credenciais existentes só em memória, sem logs. Scripts/install_worker_canary_dashboard.py reutiliza Secret existente e preserva backup privado de dashboard anterior.

RCL000001/GLPI5 foi abortado por métricas iniciais insuficientes e drenou a candidata, mantendo stable. RCL000003/GLPI7 aprovou automaticamente, passou1→2 consumidores e promoveu Worker1.0.2, drenando candidata a0. Observação12h aberta até22:04:27Z06/11. API RCL000002/GLPI6 aguarda humano. Gate lê SQS/CW diretamente; painéis do exporter SQS ainda podem estar SEM DADOS e não foram declarados integrados.

800 pedidos sintéticos aceitos; três amostras consultadas pela API estavam COMPLETED. Pagamento SIMULATED_CAPTURED é simulação da aplicação, sem provedor externo real. CI/SQS/DynamoDB/métricas/efeitos GitOps são reais. Evidência consolidada: showcase10/14 e assets/rcl-live-evidence.json do laboratório.

## Registro anterior preservado

# Observabilidade Worker — estado vigente06/11/2026

PodMonitor worker-canary aplicado. A nova imagem instrumentada ainda aguarda revisão humana da GMUD4; não há candidata ou dados versionados integrados validados. Dashboard12 painéis preparado localmente, não importado. Coletor SQS tem testes com cliente mockado; não enviou dados nem foi ativado como serviço.

Gate Kestra/GMUD3 e4, portal/SNS e assinatura Argo ativos até aprovação; Bedrock opcional/desabilitado. Nova evidência real: endpoints oficiais do plano de controle EKS conectados pela IaC, quatro targets up e alertas resolvidos, sem supressão. Canary/rollback e janela real12h permanecem pendentes. Não apresentar JSON de dashboard ou teste local como captura/validação integrada.

## Histórico preservado (anterior ao gate atual)

<details><summary>Registro anterior</summary>

# Métricas e painel do Worker Canary

Preparados localmente: ops/kubernetes/worker-canary-podmonitor.yaml, ops/grafana/dashboards/orders-worker-canary.json e src/sqs_canary_metrics.py. Não foram aplicados/importados no ambiente.

O PodMonitor seleciona somente pods Orders Worker com label cosmotech.io/component, scrape privado /metrics a cada15s. O dashboard tem12 painéis: mensagens por resultado/versão, P95, retries, falhas DynamoDB, inflight/drain, backlog, idade, DLQ, freshness, amostras e disponibilidade. Usa variável de datasource Prometheus. JSON válido não comprova painel instalado ou query com dados reais.

O coletor SQS aceita um cliente get_metric_statistics injetado, consulta somente métricas AWS/SQS e retorna texto Prometheus. Deve ser conectado ao coletor/timer/exporter existente após aprovação, com queue/source e DLQ EKS corretas e permissão cloudwatch:GetMetricStatistics. Não recebe nem envia mensagens, não lê itens DynamoDB. Ausência de datapoints, atraso maior180s ou valores inválidos emitam collection_success0 e omitem gauges; falhas SDK propagadas devem marcar coleta inválida no chamador, sem manter um falso freshness atual.

O adaptador do Canary ainda precisa traduzir queries Prometheus em observação completa: digest/channel corretos, janela iniciada na etapa atual, samples de negócio (não sintéticos), Argo Synced/Healthy na revisão esperada e fontes de fila atuais. Não gerar dados zero para vetor vazio. Lease180s requer renovação coordenada e monitorada; a projeção ConfigMap tem atraso e a implementação futura precisa demonstrar seu orçamento de tempo.

Após deploy autorizado: executar queries de cada painel, conferir labels/histogramas, datasource, scrape, freshness e comparação entre versões antes de capturar Grafana. A exposição anônima preexistente continua risco conhecido, sem correção neste escopo. Não compartilhar URL operacional nem finanças pessoais em capturas.


## Revisão Bedrock / publisher

Modelo regional Nova Micro escolhido no adaptador Converse, sem chamada paga. Publisher GPG, portal WSGI autenticado, SNS existente e adaptadores de solicitação/execução foram preparados. CIs locais só solicitam; permissões/workflows remotos não foram alterados. A avaliação `.disabled` não é o fluxo principal completo. Coletor confiável, bindings de staging/reconciliação e ativação continuam pendentes; não habilitar enforcement_verified sem prova independente. Relatório consolidado em `/opt/aws-serverless-lab/docs/linkedin-showcase/10-action-plan.md`.

</details>
