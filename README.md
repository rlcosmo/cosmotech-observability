# CosmoTech — Observabilidade e recuperação

Repositório oficial de configurações de observabilidade, valores de charts, rotinas de backup e orientações de recuperação do laboratório.

## O que consultar

- [Logs, conexões e Zabbix](docs/synthetic-traffic-and-zabbix.md): dashboards, agentes EC2, APM e consultas no Loki.
- [APM e descoberta AWS](docs/zabbix-apm-signals-and-discovery.md): operação, monitoramento, sinais de telemetria e recuperação.
- [Command Center e acesso EC2](docs/command-center-and-ec2-access.md): dashboards, acesso e documentação da arquitetura.

## Procedimento recomendado

1. Identifique o componente afetado (métricas, logs, traces, dashboard ou agente).
2. Consulte o guia correspondente e valide a configuração versionada antes de alterá-la.
3. Revise o impacto da mudança e aplique-a somente no ambiente autorizado.
4. Confirme o recebimento de sinais e o funcionamento dos dashboards e alertas.
5. Em caso de falha, siga o procedimento documentado de recuperação.

## Segurança e pendências

- Preserve a senha atual do Grafana; não a substitua sem planejamento.
- A restauração do snapshot mais recente do **Tempo** ainda consta como pendente de validação.
- **Backups, senhas, tokens e chaves não devem ser adicionados ao Git.**

## Origem

Extraído de [aws-serverless-lab](https://github.com/rlcosmo/aws-serverless-lab) no commit `6f3e67f9e93d626393b23b6884b031767a63fea0`, preservando o histórico. A extração não recriou infraestrutura.
