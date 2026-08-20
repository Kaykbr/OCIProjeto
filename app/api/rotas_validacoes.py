"""Rotas das validacoes do mentor sobre as respostas do agente."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from app.api.dependencias import Validacoes
from app.models.schemas import AtualizarValidacao, Validacao, ValidacaoRequest, Veredito

router = APIRouter(prefix="/api/validacoes", tags=["validacoes"])


@router.get("", response_model=list[Validacao])
async def listar_validacoes(
    validacoes: Validacoes,
    veredito: Veredito | None = Query(default=None),
    aluno: str | None = Query(default=None),
) -> list[Validacao]:
    """Historico de validacoes, do mais recente para o mais antigo."""
    return await run_in_threadpool(validacoes.listar, veredito, aluno)


@router.get("/resumo", response_model=dict)
async def resumo_validacoes(validacoes: Validacoes) -> dict:
    """Contagem por veredito, para os cartoes da tela do mentor."""
    return await run_in_threadpool(validacoes.resumo)


@router.post("", response_model=Validacao, status_code=201)
async def registrar_validacao(pedido: ValidacaoRequest, validacoes: Validacoes) -> Validacao:
    """O mentor avalia uma resposta do agente."""
    return await run_in_threadpool(validacoes.registrar, pedido)


@router.patch("/{identificador}", response_model=Validacao)
async def atualizar_validacao(
    identificador: str, mudancas: AtualizarValidacao, validacoes: Validacoes
) -> Validacao:
    resultado = await run_in_threadpool(validacoes.atualizar, identificador, mudancas)
    if not resultado:
        raise HTTPException(status_code=404, detail=f"Validacao '{identificador}' nao encontrada.")
    return resultado


@router.delete("/{identificador}", response_model=dict)
async def remover_validacao(identificador: str, validacoes: Validacoes) -> dict:
    removido = await run_in_threadpool(validacoes.remover, identificador)
    if not removido:
        raise HTTPException(status_code=404, detail=f"Validacao '{identificador}' nao encontrada.")
    return {"removido": identificador}
