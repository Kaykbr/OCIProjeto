"""Gera os 4 curriculos ficticios de exemplo em PDF (data/curriculos/).

Todos os dados sao INVENTADOS: nomes, e-mails, telefones e empresas nao
correspondem a pessoas ou organizacoes reais (ver nota de LGPD no README).

Uso:
    python scripts/gerar_curriculos_exemplo.py
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import CURRICULOS_DIR  # noqa: E402

# ---------------------------------------------------------------------------
# Dados dos curriculos ficticios
# ---------------------------------------------------------------------------

CURRICULOS: list[dict] = [
    {
        "nome": "Carlos Andrade",
        "cargo": "Desenvolvedor Backend Pleno",
        "dados_pessoais": {
            "E-mail": "carlos.andrade@exemplo.com.br",
            "Telefone": "(11) 90000-0001",
            "Cidade": "Sao Paulo - SP (remoto ou hibrido)",
            "LinkedIn": "linkedin.com/in/carlos-andrade-exemplo",
            "GitHub": "github.com/carlos-andrade-exemplo",
        },
        "resumo": (
            "Desenvolvedor backend com 3 anos de experiencia em Python, com foco em "
            "APIs REST e sistemas transacionais usando Django e Django REST Framework. "
            "Forte em modelagem de dados relacionais, otimizacao de consultas SQL e "
            "escrita de testes automatizados. Atua bem em times ageis com code review "
            "e integracao continua. Nunca trabalhou com provedores de nuvem: todos os "
            "deploys que acompanhou foram feitos por um time de infraestrutura separado, "
            "em servidores on-premise. Busca evoluir para uma posicao senior e assumir "
            "responsabilidade sobre a infraestrutura das aplicacoes que constroi."
        ),
        "experiencias": [
            {
                "cargo": "Desenvolvedor Backend Pleno",
                "empresa": "Fintech Meridiano (empresa ficticia)",
                "periodo": "mar/2023 - atual",
                "atividades": [
                    "Desenvolvimento e manutencao de APIs REST em Django REST Framework para o modulo de cobrancas, atendendo cerca de 40 mil requisicoes por dia.",
                    "Modelagem de dados e escrita de migrations em PostgreSQL; reduziu em 60% o tempo de uma rotina de fechamento mensal reescrevendo consultas com select_related e indices compostos.",
                    "Implementacao de tarefas assincronas com Celery e Redis para conciliacao de pagamentos.",
                    "Cobertura de testes automatizados com pytest, mantendo o modulo acima de 80% de cobertura.",
                    "Participacao em code reviews diarios e nas cerimonias de Scrum do time (7 pessoas).",
                ],
            },
            {
                "cargo": "Desenvolvedor Backend Junior",
                "empresa": "Softlar Sistemas (empresa ficticia)",
                "periodo": "jan/2022 - fev/2023",
                "atividades": [
                    "Manutencao de um ERP legado em Python 2.7 e migracao gradual de modulos para Python 3.10.",
                    "Criacao de relatorios financeiros com consultas SQL complexas em MySQL.",
                    "Automacao de rotinas internas com scripts Python e cron.",
                ],
            },
            {
                "cargo": "Estagiario de Desenvolvimento",
                "empresa": "Softlar Sistemas (empresa ficticia)",
                "periodo": "jul/2021 - dez/2021",
                "atividades": [
                    "Correcao de bugs de baixa complexidade e escrita de documentacao tecnica interna.",
                ],
            },
        ],
        "formacao": [
            "Bacharelado em Ciencia da Computacao - Universidade Exemplo de Sao Paulo - concluido em 2021.",
            "Curso livre: Django REST Framework na pratica - Alura - 2022.",
            "Curso livre: SQL e modelagem de dados - Alura - 2023.",
        ],
        "habilidades": {
            "Linguagens": "Python (avancado), SQL (avancado), JavaScript (basico)",
            "Frameworks e bibliotecas": "Django, Django REST Framework, Celery, pytest, Pandas (basico)",
            "Bancos de dados": "PostgreSQL, MySQL, Redis",
            "Ferramentas": "Git, GitHub Actions (uso basico), Linux, Postman",
            "Cloud e infraestrutura": "Sem experiencia pratica. Nunca provisionou recursos em AWS, Azure, GCP ou OCI e nao tem experiencia com Docker em producao.",
            "Metodologias": "Scrum, code review, TDD parcial",
        },
        "idiomas": [
            "Portugues - nativo",
            "Ingles - intermediario (le documentacao tecnica com fluencia, conversacao limitada)",
            "Espanhol - basico",
        ],
    },
    {
        "nome": "Fernanda Lima",
        "cargo": "Analista de Dados",
        "dados_pessoais": {
            "E-mail": "fernanda.lima@exemplo.com.br",
            "Telefone": "(31) 90000-0002",
            "Cidade": "Belo Horizonte - MG (hibrido)",
            "LinkedIn": "linkedin.com/in/fernanda-lima-exemplo",
        },
        "resumo": (
            "Analista de dados com 4 anos de experiencia em construcao de indicadores e "
            "dashboards corporativos. Dominio de SQL analitico e Power BI, com historico "
            "de substituir planilhas manuais por paineis automatizados usados pela "
            "diretoria. Esta em transicao para Ciencia de Dados: cursa uma pos-graduacao "
            "na area e estuda Python aplicado a analise de dados, ainda em nivel basico - "
            "usa Pandas para exploracoes simples, mas nunca colocou um modelo de machine "
            "learning em producao. Objetivo de carreira: atuar como Cientista de Dados Junior."
        ),
        "experiencias": [
            {
                "cargo": "Analista de Dados Pleno",
                "empresa": "Rede Varejo Colina (empresa ficticia)",
                "periodo": "ago/2022 - atual",
                "atividades": [
                    "Construcao e manutencao de 12 dashboards em Power BI para as areas comercial, logistica e financeira.",
                    "Escrita de consultas SQL analiticas em SQL Server (CTEs, window functions) sobre um data warehouse de 2 TB.",
                    "Modelagem dimensional (star schema) das areas de vendas e estoque junto ao time de engenharia de dados.",
                    "Analise exploratoria de dados de vendas em Python com Pandas para identificar sazonalidade por regiao.",
                    "Treinamento de usuarios de negocio no autoatendimento dos paineis.",
                ],
            },
            {
                "cargo": "Analista de Dados Junior",
                "empresa": "Consultoria Prisma Analytics (empresa ficticia)",
                "periodo": "fev/2021 - jul/2022",
                "atividades": [
                    "Extracao e tratamento de dados de multiplas fontes (Excel, CSV, APIs) para relatorios de clientes.",
                    "Automacao de relatorios recorrentes que antes eram montados manualmente em planilhas.",
                    "Apresentacao de resultados para clientes nao tecnicos.",
                ],
            },
        ],
        "formacao": [
            "Bacharelado em Estatistica - Universidade Exemplo de Minas Gerais - concluido em 2020.",
            "Pos-graduacao (MBA) em Ciencia de Dados - Instituto Exemplo - em andamento, previsao de conclusao em 2026.",
            "Curso livre: Python para Data Science - Alura - 2024.",
        ],
        "habilidades": {
            "Linguagens": "SQL (avancado), Python (basico), DAX (intermediario), R (nocoes)",
            "Visualizacao": "Power BI (avancado), Excel avancado, Looker Studio (basico)",
            "Bancos de dados": "SQL Server, PostgreSQL, BigQuery (nocoes)",
            "Bibliotecas Python": "Pandas (basico), Matplotlib (basico). Sem experiencia com scikit-learn.",
            "Estatistica": "Estatistica descritiva, testes de hipotese, regressao linear (base academica)",
            "Cloud e engenharia": "Sem experiencia com pipelines em nuvem, Airflow, Spark ou versionamento de modelos.",
        },
        "idiomas": [
            "Portugues - nativo",
            "Ingles - avancado (leitura, escrita e reunioes)",
        ],
    },
    {
        "nome": "Pedro Souza",
        "cargo": "Desenvolvedor Frontend",
        "dados_pessoais": {
            "E-mail": "pedro.souza@exemplo.com.br",
            "Telefone": "(51) 90000-0003",
            "Cidade": "Porto Alegre - RS (remoto)",
            "LinkedIn": "linkedin.com/in/pedro-souza-exemplo",
            "GitHub": "github.com/pedro-souza-exemplo",
        },
        "resumo": (
            "Desenvolvedor frontend com 2 anos de experiencia construindo interfaces em "
            "React e TypeScript. Cuida bem de acessibilidade, responsividade e performance "
            "de renderizacao, e tem pratica em consumir APIs REST de terceiros. Nao tem "
            "experiencia profissional com backend: nunca escreveu endpoints, nao modelou "
            "banco de dados e conhece Node.js apenas como ferramenta de build (npm, Vite). "
            "Quer se tornar desenvolvedor full stack e assumir tambem a camada de servidor."
        ),
        "experiencias": [
            {
                "cargo": "Desenvolvedor Frontend Junior",
                "empresa": "Agencia Pixel Sul (empresa ficticia)",
                "periodo": "mai/2024 - atual",
                "atividades": [
                    "Desenvolvimento de SPAs em React 18 com TypeScript, React Router e React Query.",
                    "Implementacao de design system compartilhado com Styled Components e Storybook.",
                    "Melhoria de metricas de Core Web Vitals de um e-commerce (LCP de 4,1s para 1,8s) com code splitting e lazy loading.",
                    "Testes de componentes com Jest e Testing Library.",
                    "Consumo de APIs REST fornecidas pelo time de backend; participacao nas definicoes de contrato, sem implementa-las.",
                ],
            },
            {
                "cargo": "Desenvolvedor Frontend Trainee",
                "empresa": "Startup Vitrine Digital (empresa ficticia)",
                "periodo": "jun/2023 - abr/2024",
                "atividades": [
                    "Manutencao de paginas em HTML, CSS e JavaScript puro e migracao gradual para React.",
                    "Ajustes de responsividade e correcao de bugs de layout em multiplos navegadores.",
                ],
            },
        ],
        "formacao": [
            "Tecnologo em Analise e Desenvolvimento de Sistemas - Faculdade Exemplo do Sul - concluido em 2023.",
            "Curso livre: React com TypeScript - Alura - 2024.",
            "Curso livre: Acessibilidade web (WCAG) - Alura - 2025.",
        ],
        "habilidades": {
            "Linguagens": "JavaScript (avancado), TypeScript (intermediario), HTML5 e CSS3 (avancado)",
            "Frameworks e bibliotecas": "React, React Query, React Router, Styled Components, Vite, Jest, Testing Library",
            "Design e UX": "Figma (leitura de layouts), design system, acessibilidade WCAG 2.1 nivel AA",
            "Backend": "Sem experiencia profissional. Conhece Node.js apenas como runtime de build; nunca usou Express, NestJS ou ORM.",
            "Bancos de dados": "Nocoes teoricas de SQL, sem uso profissional.",
            "Ferramentas": "Git, GitHub, npm, Chrome DevTools, Figma",
        },
        "idiomas": [
            "Portugues - nativo",
            "Ingles - intermediario (leitura tecnica boa, conversacao em desenvolvimento)",
        ],
    },
    {
        "nome": "Ana Beatriz",
        "cargo": "Analista de QA / Testes",
        "dados_pessoais": {
            "E-mail": "ana.beatriz@exemplo.com.br",
            "Telefone": "(81) 90000-0004",
            "Cidade": "Recife - PE (hibrido)",
            "LinkedIn": "linkedin.com/in/ana-beatriz-exemplo",
        },
        "resumo": (
            "Analista de QA com 5 anos de experiencia, sendo os 3 primeiros em testes "
            "manuais e exploratorios e os ultimos 2 em automacao de testes de interface "
            "com Selenium WebDriver. Escreve bons casos de teste, documenta defeitos com "
            "clareza e conhece bem o processo de qualidade de ponta a ponta. Programa em "
            "Java no nivel necessario para escrever scripts de teste, mas nao domina "
            "estruturas de dados nem desenvolvimento de aplicacoes. Nao tem experiencia "
            "com testes de API automatizados, testes de performance ou pipelines de CI/CD. "
            "Objetivo de carreira declarado: evoluir para SDET (Software Development Engineer in Test)."
        ),
        "experiencias": [
            {
                "cargo": "Analista de QA Pleno",
                "empresa": "Health Sistemas Nordeste (empresa ficticia)",
                "periodo": "set/2023 - atual",
                "atividades": [
                    "Automacao de aproximadamente 180 casos de teste de regressao de UI com Selenium WebDriver, Java e TestNG, usando o padrao Page Objects.",
                    "Execucao e manutencao da suite de regressao a cada release quinzenal, com analise dos falsos positivos.",
                    "Escrita de cenarios em Gherkin/Cucumber junto com o time de produto.",
                    "Registro e triagem de defeitos no Jira/Xray; interlocucao direta com desenvolvedores na correcao.",
                ],
            },
            {
                "cargo": "Analista de Testes Junior",
                "empresa": "Health Sistemas Nordeste (empresa ficticia)",
                "periodo": "out/2020 - ago/2023",
                "atividades": [
                    "Testes manuais funcionais, exploratorios e de regressao em sistema web hospitalar.",
                    "Elaboracao de planos e casos de teste a partir de historias de usuario.",
                    "Testes de aceitacao acompanhando usuarios finais em ambiente de homologacao.",
                ],
            },
        ],
        "formacao": [
            "Bacharelado em Sistemas de Informacao - Universidade Exemplo de Pernambuco - concluido em 2020.",
            "Certificacao CTFL (ISTQB Foundation Level) - 2022.",
            "Curso livre: Selenium WebDriver com Java - Alura - 2023.",
        ],
        "habilidades": {
            "Automacao de testes": "Selenium WebDriver (intermediario/avancado), TestNG, Cucumber/Gherkin, Page Objects",
            "Linguagens": "Java (intermediario, voltado a scripts de teste), SQL (basico, consultas de validacao)",
            "Testes manuais": "Planos e casos de teste, testes exploratorios, regressao, aceitacao, ISTQB CTFL",
            "Ferramentas": "Jira, Xray, Postman (uso manual), Git (comandos basicos), Maven",
            "Lacunas conhecidas": "Sem experiencia com testes automatizados de API (RestAssured), testes de performance (JMeter/k6), Docker, CI/CD (Jenkins/GitHub Actions) ou testes de contrato.",
        },
        "idiomas": [
            "Portugues - nativo",
            "Ingles - intermediario (leitura tecnica)",
            "Libras - basico",
        ],
    },
]


# ---------------------------------------------------------------------------
# Renderizacao do PDF
# ---------------------------------------------------------------------------

# As fontes core do PDF (Helvetica) usam latin-1: trocamos os caracteres
# tipograficos que ficam fora dessa tabela.
_SUBSTITUICOES = {
    "–": "-", "—": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "•": "-", "…": "...",
    " ": " ",
}


def _latin1(texto: str) -> str:
    for origem, destino in _SUBSTITUICOES.items():
        texto = texto.replace(origem, destino)
    return texto.encode("latin-1", errors="replace").decode("latin-1")


def _slug(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", sem_acento.lower()).strip("_")


class CurriculoPDF(FPDF):
    """PDF A4 com cabecalho de nome/cargo e rodape com aviso de dado ficticio."""

    def __init__(self, nome: str, cargo: str):
        super().__init__(format="A4", unit="mm")
        self.nome = _latin1(nome)
        self.cargo = _latin1(cargo)
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 16, 18)

    def header(self) -> None:
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(20, 40, 80)
        self.cell(0, 9, self.nome, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 11.5)
        self.set_text_color(80, 80, 80)
        self.cell(0, 6, self.cargo, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(20, 40, 80)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y() + 1.5, self.w - self.r_margin, self.get_y() + 1.5)
        self.ln(5)
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(130, 130, 130)
        rodape = (
            "Curriculo ficticio, gerado para demonstracao do Agente Mentor de Carreiras. "
            f"Pagina {self.page_no()}"
        )
        self.cell(0, 4, _latin1(rodape), align="C")

    def secao(self, titulo: str) -> None:
        self.ln(2)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(20, 40, 80)
        self.cell(0, 7, _latin1(titulo.upper()), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(190, 200, 215)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(1.5)
        self.set_text_color(0, 0, 0)

    def paragrafo(self, texto: str, tamanho: float = 10) -> None:
        self.set_font("Helvetica", "", tamanho)
        self.multi_cell(0, 5, _latin1(texto), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def item(self, texto: str) -> None:
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5, _latin1(f"- {texto}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def rotulo_valor(self, rotulo: str, valor: str) -> None:
        self.set_font("Helvetica", "B", 10)
        largura = self.get_string_width(_latin1(f"{rotulo}: ")) + 1
        self.cell(largura, 5, _latin1(f"{rotulo}:"))
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5, _latin1(valor), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def montar_pdf(dados: dict, destino: Path) -> Path:
    pdf = CurriculoPDF(dados["nome"], dados["cargo"])
    pdf.add_page()

    pdf.secao("Dados pessoais")
    pdf.rotulo_valor("Nome", dados["nome"])
    for rotulo, valor in dados["dados_pessoais"].items():
        pdf.rotulo_valor(rotulo, valor)

    pdf.secao("Resumo")
    pdf.paragrafo(dados["resumo"])

    pdf.secao("Experiencias profissionais")
    for exp in dados["experiencias"]:
        pdf.set_font("Helvetica", "B", 10.5)
        titulo_exp = f"{exp['cargo']} - {exp['empresa']}"
        pdf.multi_cell(0, 5.5, _latin1(titulo_exp), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "I", 9.5)
        pdf.set_text_color(90, 90, 90)
        pdf.multi_cell(0, 5, _latin1(exp["periodo"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        for atividade in exp["atividades"]:
            pdf.item(atividade)
        pdf.ln(2)

    pdf.secao("Formacao academica")
    for formacao in dados["formacao"]:
        pdf.item(formacao)

    pdf.secao("Habilidades tecnicas")
    for grupo, valor in dados["habilidades"].items():
        pdf.rotulo_valor(grupo, valor)

    pdf.secao("Idiomas")
    for idioma in dados["idiomas"]:
        pdf.item(idioma)

    destino.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(destino))
    return destino


def main() -> None:
    print(f"Gerando curriculos ficticios em: {CURRICULOS_DIR}")
    for dados in CURRICULOS:
        caminho = CURRICULOS_DIR / f"{_slug(dados['nome'])}.pdf"
        montar_pdf(dados, caminho)
        tamanho_kb = caminho.stat().st_size / 1024
        rotulo = f"{dados['nome']} - {dados['cargo']}"
        print(f"  [ok] {caminho.name:<22} {tamanho_kb:6.1f} KB  ({rotulo})")
    print(f"\n{len(CURRICULOS)} curriculos gerados.")
    print("Proximo passo: python scripts/indexar_curriculos.py")


if __name__ == "__main__":
    main()
