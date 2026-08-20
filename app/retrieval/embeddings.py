"""Geracao de embeddings via API do Gemini.

Usamos o mesmo provedor do LLM de proposito: nao precisamos instalar torch nem
sentence-transformers na imagem, o que mantem o container leve o suficiente para
a instancia Always Free da OCI.

Um detalhe descoberto na pratica: nem todo modelo de embedding respeita o lote.
O `gemini-embedding-001` devolve N vetores para N textos, mas o
`gemini-embedding-2` devolve **um unico vetor** e ignora o resto, sem erro. Se
confiassemos no retorno, os chunks receberiam vetores desalinhados - um bug
silencioso que estragaria toda a busca. Por isso cada lote e conferido, e o
modulo cai para envio um-a-um assim que percebe que o modelo nao suporta lote.
"""

from __future__ import annotations

import logging
import time

from google.genai import types

from app.agent.gemini_client import modelo_embedding, obter_client

logger = logging.getLogger(__name__)

# O Gemini usa task types diferentes para o documento indexado e para a consulta;
# respeitar isso melhora bastante a qualidade do retrieval.
TAREFA_DOCUMENTO = "RETRIEVAL_DOCUMENT"
TAREFA_CONSULTA = "RETRIEVAL_QUERY"

TAMANHO_LOTE = 16
TENTATIVAS_RATE_LIMIT = 4

# Modelos que ja se mostraram incapazes de lote nesta execucao: evita repetir a
# chamada em lote (e o desperdicio de cota) a cada nova fatia.
_sem_suporte_a_lote: set[str] = set()


def _e_rate_limit(erro: Exception) -> bool:
    """429 de cadencia (tentar de novo resolve), nao de credito esgotado."""
    texto = str(erro)
    if "429" not in texto and "RESOURCE_EXHAUSTED" not in texto:
        return False
    return "prepayment" not in texto and "billing" not in texto.lower()


def _embed(textos: list[str], tarefa: str) -> list[list[float]]:
    """Uma chamada a API, com espera progressiva se bater no limite de cadencia."""
    modelo = modelo_embedding()
    for tentativa in range(1, TENTATIVAS_RATE_LIMIT + 1):
        try:
            resposta = obter_client().models.embed_content(
                model=modelo,
                contents=textos,
                config=types.EmbedContentConfig(task_type=tarefa),
            )
            return [list(item.values or []) for item in (resposta.embeddings or [])]
        except Exception as erro:  # noqa: BLE001
            if not _e_rate_limit(erro) or tentativa == TENTATIVAS_RATE_LIMIT:
                raise
            espera = 2 ** tentativa
            logger.warning("Limite de cadencia no embedding; nova tentativa em %ss.", espera)
            time.sleep(espera)
    return []


def _um_a_um(textos: list[str], tarefa: str) -> list[list[float]]:
    return [_embed([texto], tarefa)[0] for texto in textos]


def gerar_embeddings(textos: list[str], tarefa: str = TAREFA_DOCUMENTO) -> list[list[float]]:
    """Gera um embedding por texto, na mesma ordem da entrada.

    Tenta em lote (bem mais rapido e economico em cota) e cai para um-a-um
    quando o modelo recusa ou devolve menos vetores do que o pedido.
    """
    if not textos:
        return []

    modelo = modelo_embedding()
    vetores: list[list[float]] = []

    for inicio in range(0, len(textos), TAMANHO_LOTE):
        lote = textos[inicio : inicio + TAMANHO_LOTE]

        if len(lote) == 1 or modelo in _sem_suporte_a_lote:
            vetores.extend(_um_a_um(lote, tarefa))
            continue

        try:
            resultado = _embed(lote, tarefa)
        except Exception as erro:  # noqa: BLE001 - o lote pode ser recusado por tamanho
            logger.warning("Lote de embeddings falhou (%s). Enviando um a um.", erro)
            _sem_suporte_a_lote.add(modelo)
            vetores.extend(_um_a_um(lote, tarefa))
            continue

        # O ponto critico: alguns modelos truncam o lote sem sinalizar erro.
        if len(resultado) != len(lote):
            logger.warning(
                "O modelo '%s' devolveu %s vetores para %s textos: ele nao suporta lote. "
                "Passando a enviar um a um.",
                modelo, len(resultado), len(lote),
            )
            _sem_suporte_a_lote.add(modelo)
            vetores.extend(_um_a_um(lote, tarefa))
            continue

        vetores.extend(resultado)

    if len(vetores) != len(textos):
        raise RuntimeError(
            f"Esperava {len(textos)} embeddings e obtive {len(vetores)}. "
            "Indexacao abortada para nao gravar vetores desalinhados."
        )
    if any(not vetor for vetor in vetores):
        raise RuntimeError("A API devolveu ao menos um embedding vazio; indexacao abortada.")

    return vetores


def embedding_da_consulta(pergunta: str) -> list[float]:
    """Embedding de uma pergunta (task type de consulta)."""
    return gerar_embeddings([pergunta], TAREFA_CONSULTA)[0]
