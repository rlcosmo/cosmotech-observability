"""Render the versioned architecture roadmap using the system Cairo library; no secrets or network."""

from __future__ import annotations

import ctypes as C
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "docs/architecture-roadmap.json").read_text())
W, H = 595.28, 841.89
NAVY, TEAL, INK, GRAY, LIGHT = "#10233f", "#009e9b", "#25364b", "#52657a", "#f0f4f8"
lib = C.CDLL("libcairo.so.2")
P, D, I, S = C.c_void_p, C.c_double, C.c_int, C.c_char_p


def fn(name, result, args):
    value = getattr(lib, name)
    value.restype = result
    value.argtypes = args
    return value


pdf_surface = fn("cairo_pdf_surface_create", P, [S, D, D])
image_surface = fn("cairo_image_surface_create", P, [I, I, I])
create = fn("cairo_create", P, [P])
destroy = fn("cairo_destroy", None, [P])
finish = fn("cairo_surface_finish", None, [P])
surface_destroy = fn("cairo_surface_destroy", None, [P])
show_page = fn("cairo_show_page", None, [P])
set_source = fn("cairo_set_source_rgb", None, [P, D, D, D])
rectangle = fn("cairo_rectangle", None, [P, D, D, D, D])
fill = fn("cairo_fill", None, [P])
move = fn("cairo_move_to", None, [P, D, D])
line_to = fn("cairo_line_to", None, [P, D, D])
stroke = fn("cairo_stroke", None, [P])
line_width = fn("cairo_set_line_width", None, [P, D])
font = fn("cairo_select_font_face", None, [P, S, I, I])
font_size = fn("cairo_set_font_size", None, [P, D])
show_text = fn("cairo_show_text", None, [P, S])
scale = fn("cairo_scale", None, [P, D, D])
write_png = fn("cairo_surface_write_to_png", I, [P, S])
status = fn("cairo_status", I, [P])
metadata = fn("cairo_pdf_surface_set_metadata", None, [P, I, S])


tag_begin = fn("cairo_tag_begin", None, [P, S, S])
tag_end = fn("cairo_tag_end", None, [P, S])


class Extents(C.Structure):
    _fields_ = [
        (n, D)
        for n in ["x_bearing", "y_bearing", "width", "height", "x_advance", "y_advance"]
    ]


extents = fn("cairo_text_extents", None, [P, S, C.POINTER(Extents)])


class Canvas:
    def __init__(self, context, pdf=False):
        self.c = context
        self.pdf = pdf

    def color(self, value):
        set_source(self.c, *(int(value[i : i + 2], 16) / 255 for i in (1, 3, 5)))

    def rect(self, x, y, w, h, color):
        self.color(color)
        rectangle(self.c, x, y, w, h)
        fill(self.c)

    def line(self, x, y, x2, y2, color=TEAL, width=1):
        self.color(color)
        line_width(self.c, width)
        move(self.c, x, y)
        line_to(self.c, x2, y2)
        stroke(self.c)

    def text(self, text, x, y, size=10, color=INK, bold=False, mono=False):
        self.color(color)
        font(self.c, b"DejaVu Sans Mono" if mono else b"DejaVu Sans", 0, int(bold))
        font_size(self.c, size)
        move(self.c, x, y)
        show_text(self.c, str(text).encode())

    def width(self, text, size=10, bold=False, mono=False):
        font(self.c, b"DejaVu Sans Mono" if mono else b"DejaVu Sans", 0, int(bold))
        font_size(self.c, size)
        out = Extents()
        extents(self.c, str(text).encode(), C.byref(out))
        return out.x_advance

    def wrap(self, text, width, size=10, bold=False, mono=False):
        lines = []
        for paragraph in text.split("\n"):
            current = ""
            for word in paragraph.split():
                if self.width(word, size, bold, mono) > width:
                    if current:
                        lines.append(current)
                        current = ""
                    part = ""
                    for ch in word:
                        if self.width(part + ch, size, bold, mono) > width:
                            lines.append(part)
                            part = ""
                        part += ch
                    current = part
                elif (
                    self.width((current + " " + word).strip(), size, bold, mono) > width
                ):
                    lines.append(current)
                    current = word
                else:
                    current = (current + " " + word).strip()
            lines.append(current)
        return lines

    def paragraph(
        self,
        text,
        x,
        y,
        width=515,
        size=10,
        leading=15,
        color=INK,
        bold=False,
        mono=False,
    ):
        for row in self.wrap(text, width, size, bold, mono):
            self.text(row, x, y, size, color, bold, mono)
            y += leading
        assert y < 792, f"Content overflow: {y} {text[:50]}"
        return y

    def header(self, title, subtitle, page):
        self.rect(0, 0, W, 40, NAVY)
        self.text("COSMOTECH  /  ARQUITETURA E OPERAÇÃO", 40, 25, 9, "#ffffff", True)
        self.text(title, 40, 81, 23, NAVY, True)
        self.paragraph(subtitle, 40, 103, 515, 9.2, 13, GRAY)
        self.line(40, 797, 555, 797, "#d9e1eb")
        self.text(
            "USO INTERNO  •  " + DATA["snapshot_date"] + "  •  " + DATA["region"],
            40,
            819,
            8,
            GRAY,
        )
        self.text(f"{page} / 8", 518, 819, 8, GRAY)

    def table(self, rows, y=134, widths=(140, 375), size=9.5, heads=None):
        if heads:
            self.rect(40, y - 13, sum(widths), 25, NAVY)
            x = 46
            for head, width in zip(heads, widths):
                self.text(head, x, y + 3, 8.5, "#ffffff", True)
                x += width
            y += 26
        for n, row in enumerate(rows):
            wrapped = [
                self.wrap(str(t), w - 14, size, index == 0)
                for index, (t, w) in enumerate(zip(row, widths))
            ]
            height = max(len(x) for x in wrapped) * 13 + 13
            self.rect(
                40, y - 10, sum(widths), height, LIGHT if n % 2 == 0 else "#ffffff"
            )
            x = 47
            for index, (lines, w) in enumerate(zip(wrapped, widths)):
                linked = self.pdf and str(row[index]).startswith("https://")
                if linked:
                    tag_begin(self.c, b"Link", ("uri='" + row[index] + "'").encode())
                for k, t in enumerate(lines):
                    self.text(
                        t, x, y + k * 13, size, NAVY if index == 0 else INK, index == 0
                    )
                if linked:
                    tag_end(self.c, b"Link")
                x += w
            y += height
        assert y < 789, f"Table overflow {y}"
        return y

    def box(self, title, body, x, y, w, h, color=LIGHT):
        self.rect(x, y, w, h, color)
        self.rect(x, y, 3, h, TEAL)
        self.text(title, x + 12, y + 21, 10, NAVY, True)
        self.paragraph(body, x + 12, y + 39, w - 24, 8.8, 13, INK)


def architecture(c):
    c.header(
        "Arquitetura e Roadmap",
        "Inventário verificado na AWS, nos clusters e nas EC2. Ferramentas instaladas e próximos passos separados.",
        1,
    )
    for x, value, label in [
        (40, "6", "EC2 privadas"),
        (214, "2", "clusters"),
        (388, "3 sinais", "traces · métricas · logs"),
    ]:
        c.rect(x, 133, 167, 63, LIGHT)
        c.text(value, x + 12, 160, 21, TEAL, True)
        c.text(label, x + 12, 180, 9, INK)
    c.box(
        "ENTRADA HTTPS",
        "DNS público → ACM + WAF → ALB compartilhado → hosts das aplicações e ferramentas.",
        40,
        216,
        515,
        66,
    )
    c.line(190, 282, 190, 307)
    c.line(465, 282, 465, 307)
    c.box(
        "CLUSTER EKS · APLICAÇÕES",
        "aws-eks-istio-lab-dev  •  Kubernetes 1.37\n3 nós Spot / duas AZs\n\nOrders API → SQS → Orders Worker → DynamoDB\nHPA em ambas as apps; hosts HTTPS próprios.\n\nIstio, Kyverno, Autoscaler, EBS CSI,\nPod Identity e Load Balancer Controller.",
        40,
        307,
        320,
        181,
    )
    c.box(
        "EC2 DE GESTÃO",
        "K3s + Argo CD + Redis\nGitOps para os clusters.",
        380,
        307,
        175,
        75,
    )
    c.box("EC2 ITSM", "GLPI + MariaDB\nKestra + PostgreSQL", 380, 397, 175, 75)
    c.box(
        "EC2 ZABBIX / APM",
        "Zabbix + PostgreSQL + ClickHouse\nCollector OTLP + Agent 2",
        380,
        487,
        175,
        88,
    )
    c.line(190, 488, 190, 510)
    c.box(
        "OBSERVABILIDADE NO EKS",
        "Métricas: Prometheus → Grafana / Alertmanager\nLogs: Alloy → Loki + APM Zabbix\nTraces: OpenTelemetry → Tempo + APM Zabbix",
        40,
        510,
        320,
        99,
    )
    c.line(360, 548, 380, 548)
    c.box(
        "ENTREGA CONTÍNUA",
        "GitHub Actions → ECR + GitOps → Argo CD → EKS\nKestra apresenta evidências reais das etapas por cluster. Fluxo atual automático.",
        40,
        631,
        515,
        75,
    )
    c.paragraph(
        "Pontos de atenção: ferramentas em EC2 individuais não equivalem a alta disponibilidade. O HTTPS do NLB Istio tem alerta ativo; os hosts das aplicações pelo ALB respondem normalmente.",
        40,
        736,
        515,
        9.5,
        14,
        GRAY,
    )


def catalog(c, title, subtitle, key, page):
    c.header(title, subtitle, page)
    c.table(DATA[key], 136)


def pipeline(c):
    c.header(
        "Como a entrega acontece",
        "Configuração da aplicação acompanha seu repositório individual; o GitOps recebe o estado promovido.",
        5,
    )
    steps = [
        (
            "1  PUSH NA APP",
            "Código e manifests de deploy são alterados no repositório da API ou do worker.",
        ),
        (
            "2  VALIDAR E PUBLICAR",
            "GitHub Actions executa testes e verificações; Trivy verifica a imagem, publicada no ECR.",
        ),
        (
            "3  PROMOVER E ENTREGAR",
            "O SHA e os manifests são promovidos para GitOps. Argo CD sincroniza e verifica a saúde no cluster.",
        ),
        (
            "4  OBSERVAR",
            "Kestra recebe os eventos de execução e organiza as esteiras por cluster; logs e APM confirmam o resultado.",
        ),
    ]
    y = 139
    for name, text in steps:
        c.box(name, text, 40, y, 515, 66)
        y += 77
    c.text("REPOSITÓRIOS CANÔNICOS", 40, y + 4, 11, TEAL, True)
    y = c.table(DATA["repos"], y + 29, (210, 305), 8.8)
    c.paragraph(
        "Terraform define a infraestrutura e entrega documentos SSM. Dashboards e coletores são versionados em observabilidade. Aprovações de produção são uma evolução futura, não uma etapa habilitada neste fluxo.",
        40,
        y + 18,
        515,
        9.5,
        14,
        GRAY,
    )


def access(c):
    c.header(
        "Acesso às EC2",
        "As seis instâncias são privadas e não possuem KeyName. Os três servidores Ubuntu estão Online no SSM.",
        6,
    )
    y = c.table(
        DATA["hosts"],
        140,
        (117, 82, 169, 147),
        8.1,
        ["Servidor", "IP privado", "Instance ID", "Acesso atual"],
    )
    c.text("PELO NAVEGADOR", 40, y + 24, 11, TEAL, True)
    y = c.paragraph(
        "Entre na conta AWS com sua identidade IAM/SSO autorizada → região us-east-1 → EC2 → Instâncias → selecione o servidor → Conectar → Session Manager → Conectar. Também é possível iniciar a sessão no console Systems Manager.",
        40,
        y + 44,
        515,
        10,
        15,
    )
    c.text("PELO TERMINAL", 40, y + 20, 11, TEAL, True)
    y += 42
    c.paragraph(
        "Com AWS CLI autenticada, permissão ssm:StartSession e plugin Session Manager no computador:",
        40,
        y,
        515,
        9.5,
        14,
    )
    y += 32
    for iid in ["i-0def4e806c49cf60e", "i-0b33fdd51332e04e5", "i-02878f35eed1572d0"]:
        c.rect(40, y - 13, 515, 25, LIGHT)
        c.text(
            "aws ssm start-session --region us-east-1 --target " + iid,
            47,
            y + 3,
            8.4,
            INK,
            False,
            True,
        )
        y += 31
    y = c.paragraph(
        "A conta Linux ubuntu existe nesses servidores. A sessão SSM é autorizada por IAM; não usa a senha do Grafana, GLPI ou Zabbix. Quando a política permitir, sudo -i abre um shell administrativo. Não há senha Linux compartilhada configurada para esse acesso.",
        40,
        y + 10,
        515,
        9.5,
        14,
    )
    y = c.paragraph(
        "SSH por chave exige uma chave pública autorizada no Linux, sshd ativo e conectividade privada/VPN ou túnel adequado. Hoje a porta 22 não está liberada e o serviço SSH está inativo nos três servidores. A PEM do GitHub App autentica o GitHub, não é uma chave SSH dessas EC2.",
        40,
        y + 12,
        515,
        9.5,
        14,
    )
    c.paragraph(
        "Os nós EKS não aparecem como managed nodes SSM. A operação cotidiana deve usar kubectl, logs e os mecanismos do EKS. Habilitar acesso direto aos nós seria uma configuração adicional.",
        40,
        y + 12,
        515,
        9.5,
        14,
        GRAY,
    )


def roadmap(c):
    c.header(
        "Roadmap de evolução",
        "Horizontes propostos a partir deste inventário; não são mudanças já executadas nem compromissos de prazo.",
        7,
    )
    y = 141
    for stage in DATA["roadmap"]:
        c.rect(40, y - 15, 515, 30, NAVY if stage["state"] == "INSTALADO" else LIGHT)
        c.text(
            stage["phase"],
            49,
            y + 3,
            10,
            "#ffffff" if stage["state"] == "INSTALADO" else NAVY,
            True,
        )
        y += 35
        c.text(stage["state"] + "  •  " + stage["owner"], 49, y, 8.5, TEAL, True)
        y += 19
        for item in stage["items"]:
            c.text("•", 49, y, 10, TEAL)
            y = c.paragraph(item, 63, y, 480, 9.2, 13) + 3
        y += 10
    assert y < 790, y


def operations(c):
    c.header(
        "Portais e operação",
        "Documentação sem senhas, tokens ou chaves privadas. Valores protegidos permanecem no AWS Secrets Manager.",
        8,
    )
    y = c.table(DATA["links"], 140, (180, 335), 8.2, ["Ferramenta", "Endereço"])
    c.text("RETENÇÃO E RECUPERAÇÃO", 40, y + 26, 11, TEAL, True)
    y = c.paragraph(
        "Prometheus: 24 horas. Telemetria APM no ClickHouse: três dias. Backup lógico PostgreSQL do Zabbix: sete dias. Logs da Lambda de teste: sete dias. PVCs de observabilidade são persistentes; há rotinas e volumes de testes de recuperação. Validar RPO/RTO com restauração medida.",
        40,
        y + 46,
        515,
        9.5,
        14,
    )
    c.text("O QUE O COMMAND CENTER MOSTRA", 40, y + 23, 11, TEAL, True)
    y = c.paragraph(
        "Fonte: problemas abertos do Zabbix. Disaster (5) e High (4) ficam acima; Warning (2) e Average (3) abaixo. Problemas reconhecidos continuam visíveis. Eventos resolvidos, suprimidos e triggers desabilitadas são excluídos. Coleta inválida ou vencida exibe SEM COLETA; nunca zero saudável por falta de dados.",
        40,
        y + 43,
        515,
        9.5,
        14,
    )
    c.text("LIMITES CONHECIDOS E FONTES", 40, y + 23, 11, TEAL, True)
    y = c.paragraph(
        "No recorte consultado, não foram encontradas hosted zones Route 53 nem trails CloudTrail configurados. O DNS público existe; a zona não está gerenciada nesta conta consultada. Um trail persistente e a gravação de sessões SSM devem ser formalizados no roadmap.",
        40,
        y + 43,
        515,
        9.2,
        13,
    )
    y = c.paragraph(
        "Evidências: inventário AWS/EC2/SSM, Helm, workloads e PVCs do EKS, K3s/Argo e processos Docker das EC2. Versões confirmadas incluem EKS 1.37, K3s 1.37.1, Argo CD 3.6.1, Istio 1.31.3, Grafana 13.3 e Zabbix 8.0.0rc3. As imagens dos bancos e ferramentas são fixadas por digest.",
        40,
        y + 12,
        515,
        9.2,
        13,
    )
    c.paragraph(
        "Referências operacionais: docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html · zabbix.com/documentation/8.0/en/manual/api/reference/problem/get",
        40,
        y + 12,
        515,
        8.2,
        12,
        GRAY,
    )


PAGES = [
    architecture,
    lambda c: catalog(
        c,
        "Plataforma e aplicações",
        "Função resumida dos componentes instalados nos clusters.",
        "platform",
        2,
    ),
    lambda c: catalog(
        c,
        "Observabilidade e monitoria",
        "Métricas, logs, traces e gestão de incidentes se complementam.",
        "observability",
        3,
    ),
    lambda c: catalog(
        c,
        "Gestão, dados e serviços AWS",
        "Ferramentas instaladas e serviços que sustentam a arquitetura.",
        "services",
        4,
    ),
    pipeline,
    access,
    roadmap,
    operations,
]


def main():
    output = ROOT / "docs/artifacts/cosmotech-arquitetura-roadmap.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    surface = pdf_surface(str(output).encode(), W, H)
    metadata(surface, 0, b"CosmoTech | Arquitetura, acesso EC2 e roadmap")
    metadata(surface, 1, b"CosmoTech Solutions")
    context = create(surface)
    for page in PAGES:
        page(Canvas(context, pdf=True))
        assert status(context) == 0
        show_page(context)
    destroy(context)
    finish(surface)
    surface_destroy(surface)
    previews = Path("/tmp/cosmotech-architecture-previews")
    previews.mkdir(parents=True, exist_ok=True)
    for index, page in enumerate(PAGES, 1):
        surface = image_surface(0, int(W * 2), int(H * 2))
        context = create(surface)
        scale(context, 2, 2)
        c = Canvas(context)
        c.rect(0, 0, W, H, "#ffffff")
        page(c)
        assert write_png(surface, str(previews / f"page-{index}.png").encode()) == 0
        destroy(context)
        surface_destroy(surface)
    print(
        json.dumps(
            {
                "pdf": str(output),
                "pages": len(PAGES),
                "bytes": output.stat().st_size,
                "previews": str(previews),
            }
        )
    )


if __name__ == "__main__":
    main()
