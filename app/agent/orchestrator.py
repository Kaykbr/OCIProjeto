"""Loop de function calling: pergunta do mentor -> ferramenta -> resposta final.

Fluxo de um turno:

    1. manda o historico + a pergunta para o Gemini, com as 4 ferramentas declaradas;
    2. se o modelo devolveu function calls, executamos cada uma aqui no Python;
    3. devolvemos os resultados para o modelo como `functionResponse`;
    4. repetimos ate o modelo responder em texto (ou ate o limite de iteracoes).

A execucao das funcoes e manual de proposito (`automatic_function_calling`
desligado no client): o desafio pede o loop explicito, e assim conseguimos
registrar quais ferramentas foram usadas para mostrar no frontend.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from google.genai import types

from app import config
from app.agent.gemini_client import (
    chamar_com_retentativa,
    configuracao_geracao,
    modelo_chat,
    obter_client,
)
from app.agent.tools import executar_ferramenta

logger = logging.getLogger(__name__)

LIMITE_RESUMO = 220


@dataclass
class PassoFerramenta:
    """Registro de uma chamada de ferramenta, para exibir a 'trilha' no chat."""

    nome: str
    argumentos: dict
    resumo_resultado: str
    duracao_ms: int


@dataclass
class RespostaAgente:
    texto: str
    ferramentas: list[PassoFerramenta] = field(default_factory=list)
    modelo: str = ""
    iteracoes: int = 0


def _para_contents(historico: list[dict] | None) -> list[types.Content]:
    """Converte o historico do frontend ({role, content}) no formato do SDK."""
    contents: list[types.Content] = []
    for mensagem in historico or []:
        texto = (mensagem.get("content") or "").strip()
        if not texto:
            continue
        papel = "model" if mensagem.get("role") in ("assistant", "model") else "user"
        contents.append(types.Content(role=papel, parts=[types.Part(text=texto)]))
    return contents


def _extrair_texto(resposta: types.GenerateContentResponse) -> str:
    """Junta as partes de texto da resposta (evita o warning do atalho .text)."""
    if not resposta.candidates:
        return ""
    partes = resposta.candidates[0].content.parts if resposta.candidates[0].content else None
    return "\n".join(parte.text for parte in (partes or []) if parte.text).strip()


def _motivo_de_parada(resposta: types.GenerateContentResponse) -> str:
    """Mensagem amigavel quando o modelo devolve vazio (bloqueio, limite, etc.)."""
    bloqueio = getattr(resposta.prompt_feedback, "block_reason", None) if resposta.prompt_feedback else None
    if bloqueio:
        return f"A pergunta foi bloqueada pelos filtros do modelo ({bloqueio}). Reformule e tente de novo."

    razao = resposta.candidates[0].finish_reason if resposta.candidates else None
    if razao and str(razao).upper().endswith("MAX_TOKENS"):
        return "A resposta ficou longa demais e foi cortada. Peca em partes menores."
    return "O modelo nao devolveu texto para essa pergunta. Tente reformular."


def responder(pergunta: str, historico: list[dict] | None = None) -> RespostaAgente:
    """Executa um turno completo do agente e devolve a resposta em linguagem natural."""
    client = obter_client()
    modelo = modelo_chat()
    configuracao = configuracao_geracao()

    contents = _para_contents(historico)
    contents.append(types.Content(role="user", parts=[types.Part(text=pergunta)]))

    passos: list[PassoFerramenta] = []

    for iteracao in range(1, config.MAX_ITERACOES_AGENTE + 1):
        # modelo_chat() e relido a cada tentativa: se a cota diaria de um modelo
        # acabar, a retentativa ja usa o substituto.
        resposta = chamar_com_retentativa(
            lambda: client.models.generate_content(
                model=modelo_chat(), contents=contents, config=configuracao
            )
        )
        chamadas = resposta.function_calls or []

        if not chamadas:
            texto = _extrair_texto(resposta) or _motivo_de_parada(resposta)
            return RespostaAgente(
                texto=texto, ferramentas=passos, modelo=modelo_chat(), iteracoes=iteracao
            )

        # O modelo pediu ferramentas: executa todas antes de devolver o controle a ele.
        conteudo_modelo = resposta.candidates[0].content if resposta.candidates else None
        if conteudo_modelo:
            contents.append(conteudo_modelo)

        respostas_ferramentas: list[types.Part] = []
        # O modelo as vezes pede a MESMA ferramenta com os MESMOS argumentos duas
        # vezes no mesmo turno. Como as tools de geracao fazem sua propria chamada
        # ao LLM, executar de novo custaria o dobro de cota pelo mesmo resultado.
        ja_executadas: dict[tuple[str, str], str] = {}

        for chamada in chamadas:
            argumentos = dict(chamada.args or {})
            assinatura = (chamada.name or "", repr(sorted(argumentos.items())))

            inicio = time.perf_counter()
            if assinatura in ja_executadas:
                logger.info("[iter %s] %s repetida no mesmo turno: reaproveitando.", iteracao, chamada.name)
                resultado = ja_executadas[assinatura]
            else:
                logger.info("[iter %s] chamando %s(%s)", iteracao, chamada.name, argumentos)
                resultado = executar_ferramenta(chamada.name or "", argumentos)
                ja_executadas[assinatura] = resultado
            duracao_ms = int((time.perf_counter() - inicio) * 1000)

            passos.append(
                PassoFerramenta(
                    nome=chamada.name or "?",
                    argumentos=argumentos,
                    resumo_resultado=resultado[:LIMITE_RESUMO] + ("..." if len(resultado) > LIMITE_RESUMO else ""),
                    duracao_ms=duracao_ms,
                )
            )
            respostas_ferramentas.append(
                types.Part.from_function_response(
                    name=chamada.name or "",
                    response={"resultado": resultado},
                )
            )

        contents.append(types.Content(role="user", parts=respostas_ferramentas))

    logger.warning("Limite de %s iteracoes atingido.", config.MAX_ITERACOES_AGENTE)
    return RespostaAgente(
        texto=(
            "Nao consegui fechar a resposta: o agente ficou chamando ferramentas em loop. "
            "Tente uma pergunta mais especifica (um aluno por vez, por exemplo)."
        ),
        ferramentas=passos,
        modelo=modelo,
        iteracoes=config.MAX_ITERACOES_AGENTE,
    )
