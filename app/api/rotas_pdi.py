"""Rotas do PDI estruturado - o que alimenta a tela grafica de PDI."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from app import config
from app.agent.gemini_client import traduzir_erro_gemini
from app.api.dependencias import PDI
from app.models.schemas import PDIEstruturado, PDIRequest, PDIResumo
from app.retrieval.vector_store import AlunoNaoEncontrado

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pdi", tags=["pdi"])


@router.get("", response_model=list[PDIResumo])
async def listar_pdis(pdi: PDI, aluno: str | None = Query(default=None)) -> list[PDIResumo]:
    """PDIs ja gerados, do mais recente para o mais antigo."""
    return await run_in_threadpool(pdi.listar, aluno)


@router.post("", response_model=PDIEstruturado, status_code=201)
async def gerar_pdi(requisicao: PDIRequest, pdi: PDI) -> PDIEstruturado:
    """Gera o PDI estruturado de um aluno para uma vaga-alvo.

    Reaproveita o PDI ja salvo da mesma combinacao aluno + vaga, a menos que
    `forcar_regeracao` seja verdadeiro - gerar custa uma chamada de LLM.
    """
    if not config.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY nao configurada.")

    try:
        return await run_in_threadpool(
            pdi.gerar, requisicao.nome_aluno, requisicao.vaga_alvo, requisicao.forcar_regeracao
        )
    except AlunoNaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except LookupError as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except Exception as erro:  # noqa: BLE001
        logger.exception("Falha ao gerar PDI")
        raise HTTPException(status_code=502, detail=traduzir_erro_gemini(erro)) from erro


@router.get("/{identificador}", response_model=PDIEstruturado)
async def obter_pdi(identificador: str, pdi: PDI) -> PDIEstruturado:
    resultado = await run_in_threadpool(pdi.obter, identificador)
    if not resultado:
        raise HTTPException(status_code=404, detail=f"PDI '{identificador}' nao encontrado.")
    return resultado


@router.delete("/{identificador}", response_model=dict)
async def remover_pdi(identificador: str, pdi: PDI) -> dict:
    removido = await run_in_threadpool(pdi.remover, identificador)
    if not removido:
        raise HTTPException(status_code=404, detail=f"PDI '{identificador}' nao encontrado.")
    return {"removido": identificador}
