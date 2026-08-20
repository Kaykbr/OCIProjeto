"""Servico do agente: fachada sobre o orquestrador de function calling.

Existe para que as rotas nao falem diretamente com o loop do Gemini e para
centralizar a traducao do resultado interno (`RespostaAgente`) no contrato
publico da API (`RespostaChat`).
"""

from __future__ import annotations

import logging
import time

from app import config
from app.agent.orchestrator import responder
from app.models.schemas import FerramentaUsada, MensagemChat, RespostaChat

logger = logging.getLogger(__name__)


class AgenteIndisponivel(RuntimeError):
    """Falta chave ou indice para o agente funcionar."""


class ServicoAgente:
    """Ponto unico de entrada para conversar com o agente."""

    def perguntar(self, pergunta: str, historico: list[MensagemChat] | None = None) -> RespostaChat:
        if not config.GEMINI_API_KEY:
            raise AgenteIndisponivel(
                "GEMINI_API_KEY nao configurada: copie .env.example para .env e preencha a chave."
            )

        inicio = time.perf_counter()
        mensagens = [mensagem.model_dump() for mensagem in (historico or [])]
        resultado = responder(pergunta, mensagens)

        return RespostaChat(
            resposta=resultado.texto,
            ferramentas=[
                FerramentaUsada(
                    nome=passo.nome,
                    argumentos=passo.argumentos,
                    duracao_ms=passo.duracao_ms,
                    resumo_resultado=passo.resumo_resultado,
                )
                for passo in resultado.ferramentas
            ],
            modelo=resultado.modelo,
            iteracoes=resultado.iteracoes,
            duracao_ms=int((time.perf_counter() - inicio) * 1000),
        )
