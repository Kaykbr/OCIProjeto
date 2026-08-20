"""Rotas do painel de administracao: saude do indice e reindexacao."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app import config
from app.agent.gemini_client import traduzir_erro_gemini
from app.api.dependencias import Indexacao
from app.models.schemas import EstatisticasIndice, ResultadoIndexacao

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/indice", response_model=EstatisticasIndice)
async def estatisticas_indice(indexacao: Indexacao) -> EstatisticasIndice:
    """Panorama do vector store: chunks por aluno, por secao e pendencias."""
    return await run_in_threadpool(indexacao.estatisticas)


@router.post("/reindexar", response_model=ResultadoIndexacao)
async def reindexar(indexacao: Indexacao) -> ResultadoIndexacao:
    """Apaga a colecao e reindexa todos os PDFs da base.

    Operacao cara (uma chamada de embeddings por lote de chunks), pensada para
    quando os PDFs mudaram fora da interface ou o indice ficou inconsistente.
    """
    if not config.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY nao configurada.")

    try:
        resultado = await run_in_threadpool(indexacao.reindexar_tudo)
    except Exception as erro:  # noqa: BLE001
        logger.exception("Falha na reindexacao")
        raise HTTPException(status_code=502, detail=traduzir_erro_gemini(erro)) from erro

    if resultado.avisos and not resultado.chunks:
        raise HTTPException(status_code=400, detail=" ".join(resultado.avisos))
    return resultado


@router.get("/configuracao", response_model=dict)
async def configuracao() -> dict:
    """Configuracao efetiva do processo (sem expor a chave)."""
    chave = config.GEMINI_API_KEY
    return {
        "versao": config.VERSAO,
        "porta": config.PORT,
        "chave_configurada": bool(chave),
        "chave_mascarada": f"{chave[:6]}...{chave[-4:]}" if len(chave) > 12 else "",
        "modelo_chat": config.GEMINI_MODEL or "(automatico)",
        "modelo_embedding": config.GEMINI_EMBEDDING_MODEL or "(automatico)",
        "pasta_curriculos": str(config.CURRICULOS_DIR),
        "pasta_chroma": str(config.CHROMA_DIR),
        "pasta_estado": str(config.ESTADO_DIR),
        "colecao": config.CHROMA_COLLECTION,
        "top_k": config.TOP_K,
        "chunk_tamanho": config.CHUNK_TAMANHO,
        "chunk_sobreposicao": config.CHUNK_SOBREPOSICAO,
        "auto_indexar": config.AUTO_INDEXAR,
        "upload_max_mb": config.UPLOAD_MAX_MB,
        "max_iteracoes_agente": config.MAX_ITERACOES_AGENTE,
    }
