"""Rotas do agente e do diagnostico da aplicacao."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app import config
from app.api.dependencias import Agente, Documentos, PDI, Validacoes
from app.models.schemas import PerguntaRequest, RespostaChat, StatusApp
from app.retrieval.vector_store import obter_store
from app.agent.gemini_client import traduzir_erro_gemini
from app.services.agente import AgenteIndisponivel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agente"])


def montar_status(pdi=None, validacoes=None, documentos=None) -> StatusApp:
    """Diagnostico completo: chave, indice, base e contadores das telas."""
    chave = bool(config.GEMINI_API_KEY)

    try:
        store = obter_store()
        total, alunos = store.total_chunks(), store.listar_alunos()
    except Exception as erro:  # noqa: BLE001 - status nunca pode explodir
        logger.warning("Falha ao consultar o vector store: %s", erro)
        total, alunos = 0, []

    modelo_chat_nome = modelo_embedding_nome = ""
    if chave:
        try:
            from app.agent.gemini_client import modelo_chat, modelo_embedding

            modelo_chat_nome, modelo_embedding_nome = modelo_chat(), modelo_embedding()
        except Exception as erro:  # noqa: BLE001
            logger.warning("Falha ao resolver os modelos: %s", erro)

    total_documentos = len(documentos.listar_arquivos()) if documentos else 0

    aviso = ""
    if not chave:
        aviso = "GEMINI_API_KEY nao configurada: copie .env.example para .env e preencha a chave."
    elif total == 0:
        aviso = "Nenhum curriculo indexado: envie um PDF no painel admin ou rode a reindexacao."

    return StatusApp(
        pronto=chave and total > 0,
        chave_configurada=chave,
        chunks_indexados=total,
        alunos=alunos,
        documentos=total_documentos,
        pdis=pdi.contar() if pdi else 0,
        validacoes_pendentes=validacoes.contar(veredito="ajustar") if validacoes else 0,
        modelo_chat=modelo_chat_nome,
        modelo_embedding=modelo_embedding_nome,
        aviso=aviso,
        versao=config.VERSAO,
    )


@router.get("/api/status", response_model=StatusApp, tags=["diagnostico"])
async def status(pdi: PDI, validacoes: Validacoes, documentos: Documentos) -> StatusApp:
    """Estado do agente: usado pelo cabecalho e pelos cartoes do painel."""
    return await run_in_threadpool(montar_status, pdi, validacoes, documentos)


@router.post("/api/chat", response_model=RespostaChat)
async def chat(
    requisicao: PerguntaRequest,
    agente: Agente,
    pdi: PDI,
    validacoes: Validacoes,
    documentos: Documentos,
) -> RespostaChat:
    """Endpoint principal: manda a pergunta do mentor para o agente."""
    estado = await run_in_threadpool(montar_status, pdi, validacoes, documentos)
    if not estado.pronto:
        raise HTTPException(status_code=503, detail=estado.aviso or "Agente indisponivel.")

    try:
        return await run_in_threadpool(
            agente.perguntar, requisicao.pergunta, requisicao.historico
        )
    except AgenteIndisponivel as erro:
        raise HTTPException(status_code=503, detail=str(erro)) from erro
    except Exception as erro:  # noqa: BLE001
        logger.exception("Falha ao responder")
        raise HTTPException(status_code=502, detail=traduzir_erro_gemini(erro)) from erro


@router.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    """Health check simples (usado pelo Docker e por checagens externas)."""
    return {"status": "ok"}
