"""Geracao do PDI em formato estruturado (JSON), para alimentar os graficos.

A ferramenta `gerar_pdi` de `tools.py` devolve markdown para o mentor ler no
chat. A tela de PDI precisa de outra coisa: numeros e listas tipadas para
desenhar barras, criticidade e cronograma. Em vez de tentar extrair isso do
markdown com regex, pedimos ao Gemini a saida ja estruturada, usando
`response_schema` - o modelo e obrigado a responder no formato do schema.
"""

from __future__ import annotations

import json
import logging

from google.genai import types
from pydantic import BaseModel, Field

from app.agent.gemini_client import chamar_com_retentativa, modelo_chat, obter_client
from app.models.schemas import AcaoPDI, BlocoCronograma, GapPDI, HabilidadeAtual

logger = logging.getLogger(__name__)


class PDIGerado(BaseModel):
    """Exatamente o que o modelo precisa produzir - sem id, data ou metadados."""

    resumo: str = Field(description="2 a 3 frases sobre a distancia entre o perfil atual e a vaga.")
    aderencia: int = Field(
        ge=0, le=100, description="Percentual do que a vaga exige que o aluno ja atende hoje."
    )
    prazo_total_meses: int = Field(ge=1, le=36, description="Meses para o plano inteiro.")
    habilidades_atuais: list[HabilidadeAtual] = Field(
        description="O que o aluno JA tem e serve para a vaga, com a evidencia do curriculo."
    )
    gaps: list[GapPDI] = Field(description="O que a vaga exige e o curriculo nao mostra.")
    acoes: list[AcaoPDI] = Field(description="Acoes concretas, na ordem de execucao.")
    cronograma: list[BlocoCronograma] = Field(description="Blocos de tempo com objetivos e marco.")


PROMPT = """Voce e um mentor de carreiras senior em tecnologia. Analise o curriculo
abaixo contra a vaga-alvo e produza um Plano de Desenvolvimento Individual estruturado.

VAGA-ALVO: {vaga_alvo}

REGRAS DE ANALISE
- Baseie "habilidades_atuais" exclusivamente no material do aluno. Cada uma precisa
  de uma "evidencia": o trecho do curriculo que comprova (experiencia, projeto, formacao).
- Se o curriculo declarar explicitamente uma ausencia ("sem experiencia com cloud"),
  isso e um GAP, nunca uma habilidade atual.
- "nivel" e "nivel_atual" (0 a 100) refletem o dominio demonstrado no curriculo:
  0 = nunca tocou, 40 = usou pontualmente, 70 = usa no dia a dia, 90 = referencia no time.
- "criticidade" alta = sem isso o aluno nao passa na triagem da vaga; media = cobrado
  na entrevista tecnica; baixa = diferencial.
- "aderencia" e a fracao do que a vaga exige que o aluno ja atende hoje. Seja honesto:
  um frontend puro indo para full stack costuma ficar entre 35 e 55.
- Cada acao precisa ser verificavel. "Estudar Node.js" e ruim; "construir uma API REST
  em Express com autenticacao JWT e testes de integracao" e bom. Use "gap_relacionado"
  com o nome exato de um gap da lista.
- "esforco_horas" e a estimativa realista de horas de estudo/pratica da acao.
- O cronograma deve cobrir prazo_total_meses em 3 a 4 blocos, cada um com um marco de
  saida objetivo (algo que da para conferir se aconteceu ou nao).
- Considere o ponto de partida real do aluno: quem nunca programou backend nao vira
  pleno full stack em 2 meses.

Produza entre 4 e 7 habilidades atuais, 3 e 6 gaps e 4 e 7 acoes.

MATERIAL DO ALUNO ({nome_aluno}):
{curriculo}"""


class AnalisadorPDI:
    """Transforma curriculo + vaga-alvo num PDI tipado."""

    def __init__(self, temperatura: float = 0.35):
        self.temperatura = temperatura

    def analisar(self, nome_aluno: str, vaga_alvo: str, curriculo: str) -> PDIGerado:
        prompt = PROMPT.format(nome_aluno=nome_aluno, vaga_alvo=vaga_alvo, curriculo=curriculo)

        resposta = chamar_com_retentativa(
            lambda: obter_client().models.generate_content(
                model=modelo_chat(),
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self.temperatura,
                    response_mime_type="application/json",
                    response_schema=PDIGerado,
                ),
            )
        )

        # O SDK ja devolve o objeto validado em .parsed; o texto e o plano B.
        if isinstance(resposta.parsed, PDIGerado):
            return resposta.parsed

        bruto = (resposta.text or "").strip()
        if not bruto:
            raise RuntimeError("O modelo nao devolveu conteudo para o PDI estruturado.")
        try:
            return PDIGerado.model_validate(json.loads(bruto))
        except (json.JSONDecodeError, ValueError) as erro:
            logger.error("JSON invalido no PDI estruturado: %s", bruto[:400])
            raise RuntimeError(f"O modelo devolveu um PDI fora do formato esperado: {erro}") from erro
