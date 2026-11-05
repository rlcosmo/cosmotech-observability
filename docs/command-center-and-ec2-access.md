# Command Center e acesso às EC2

Dashboard: https://grafana.cosmotechsolutions.com.br/d/command-center

O topo agrupa Disaster (5) e High (4). A faixa inferior agrupa Warning (2) e Average (3), conforme solicitado. Cada severidade apresenta quantidade e lista com host, problema, duração, reconhecimento e evento. Os links superiores também levam aos painéis de serviços/discos, AWS/custos e logs/conexões.

## Origem, validade e acesso de serviço

O coletor existente na EC2 ITSM lê os problemas do Zabbix por HTTPS com `svc_grafana_command_center`. A conta pertence a um grupo com leitura dos grupos CosmoTech e só pode chamar `problem.get` e `trigger.get`. Não possui permissão de alteração/reconhecimento de eventos. A negação de uma chamada fora dessa lista foi validada na API real.

Usuário, senha, token e vencimento ficam exclusivamente em `cosmotech/grafana/command-center`, no AWS Secrets Manager. O perfil ITSM lê somente esse segredo; o perfil Zabbix pode publicá-lo para provisionamento/rotação. Nenhum valor fica nos manifests, Terraform/state, dashboards ou cache de métricas. A credencial nasce com 180 dias e um painel mostra os dias restantes. Reexecutar `CosmoTech-Provision-Command-Center` a menos de 30 dias do vencimento renova o token; sincronizar essa operação ao procedimento de rotação.

O timer coleta em aproximadamente um minuto e o Grafana atualiza a cada 30 segundos. O cache mantém o último snapshot em uma falha, mas o dashboard só o utiliza quando a coleta está OK e tem menos de 180 segundos. Os contadores usam -1 como sinal interno, mapeado para **SEM COLETA**, quando não há fonte válida; nunca transformam falha de coleta em zero saudável. Reconhecidos continuam visíveis; resolvidos, suprimidos e triggers/hosts desabilitados ficam fora da visão. A visão atual é de problemas do Zabbix, sem conversão de severidades de Alertmanager.

`CosmoTech-Install-Command-Center` entrega o coletor versionado no servidor ITSM, preservando os serviços/timers existentes. A ConfigMap Grafana recebe apenas os JSONs de dashboards; o sidecar os importa. Não são necessários novos plugins ou portas de rede.

## Acesso atual às EC2

Todas as seis EC2 consultadas não têm IP público nem KeyName. Os três servidores Ubuntu estão Online no SSM, com SSH inativo e sem porta 22 liberada:

| Servidor | Instance ID | IP privado |
|---|---|---|
| ITSM / GLPI / Kestra | i-0def4e806c49cf60e | 10.20.11.150 |
| Argo CD / K3s | i-0b33fdd51332e04e5 | 10.20.11.199 |
| Zabbix / APM | i-02878f35eed1572d0 | 10.20.11.207 |

No navegador: entrar na conta AWS com identidade autorizada, selecionar us-east-1, EC2 → Instâncias → servidor → Conectar → Session Manager. Também se pode usar Systems Manager → Session Manager → Start session.

No computador, com AWS CLI autenticada e Session Manager plugin:

```bash
aws ssm start-session --region us-east-1 --target i-0def4e806c49cf60e
aws ssm start-session --region us-east-1 --target i-0b33fdd51332e04e5
aws ssm start-session --region us-east-1 --target i-02878f35eed1572d0
```

A identidade IAM precisa de autorização para iniciar a sessão e seus canais. Quando a política da sessão permitir, `sudo -i` abre shell administrativo. A senha das ferramentas não autentica no Linux. A chave PEM do GitHub App é de assinatura do aplicativo GitHub, não uma chave SSH de EC2.

Para SSH por chave, seria preciso instalar/habilitar sshd, autorizar uma chave pública no usuário Linux e fornecer conectividade privada/VPN ou túnel e regra de rede específica. Isso não foi habilitado por esta entrega. Login SSH por senha também não é o mecanismo configurado. Não publicar a porta 22 para viabilizar uma explicação de acesso.

Os três nós EKS são Amazon Linux 2023 Spot e não estão registrados como managed nodes SSM. Usar kubectl, logs e ferramentas EKS na operação normal. Acesso direto por Session Manager aos nós exigiria configuração adicional.

## PDF e reprodução

[Arquitetura, acesso e roadmap em PDF](artifacts/cosmotech-arquitetura-roadmap.pdf) — oito páginas, inventário datado, catálogo das ferramentas, fluxos CI/CD, seis hosts e próximos passos claramente identificados como propostas.

Fonte editorial: `docs/architecture-roadmap.json`; gerador: `scripts/build_architecture_pdf.py`. Usa a biblioteca Cairo já disponível no sistema, sem instalar ferramentas. Regerar com `python3 scripts/build_architecture_pdf.py`; os previews ficam em `/tmp/cosmotech-architecture-previews`. As imagens foram revisadas e o PDF validado com oito páginas e links para os portais. O documento não contém senhas ou chaves.

Validações: casos de eventos reconhecidos, resolvidos, suprimidos, duplicados e triggers desabilitadas; falha de API sem falso zero; métodos de escrita bloqueados; consultas PromQL reais; dashboard importado por API Grafana. O alerta HTTPS do NLB Istio permanece visível e foi incluído no roadmap.

Referências: [Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html), [problem.get](https://www.zabbix.com/documentation/8.0/en/manual/api/reference/problem/get).
