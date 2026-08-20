"""Rotas da base de documentos: curriculos em PDF e alunos indexados.

Sao as rotas que sustentam a tela "Base de documentos" (qualquer perfil pode
consultar) e a parte de upload/remocao do painel admin.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app import config
from app.api.dependencias import Documentos, Indexacao, PDI
from app.models.schemas import Aluno, DocumentoDetalhe, DocumentoInfo, ResultadoIndexacao
from app.agent.gemini_client import traduzir_erro_gemini
from app.retrieval.vector_store import AlunoNaoEncontrado, obter_store
from app.services.documentos import DocumentoInvalido, DocumentoNaoEncontrado, FalhaDeArmazenamento

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documentos"])


@router.get("/api/documentos", response_model=list[DocumentoInfo])
async def listar_documentos(documentos: Documentos, indexacao: Indexacao) -> list[DocumentoInfo]:
    """Todos os curriculos da base, com o status de indexacao de cada um."""

    def _consultar() -> list[DocumentoInfo]:
        return documentos.listar(indexacao.chunks_por_arquivo())

    return await run_in_threadpool(_consultar)


@router.get("/api/documentos/{arquivo}", response_model=DocumentoDetalhe)
async def detalhar_documento(
    arquivo: str, documentos: Documentos, indexacao: Indexacao
) -> DocumentoDetalhe:
    """Texto extraido do PDF, quebrado nas secoes que o parser identificou."""

    def _consultar() -> DocumentoDetalhe:
        return documentos.detalhe(arquivo, indexacao.chunks_por_arquivo())

    try:
        return await run_in_threadpool(_consultar)
    except DocumentoNaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except DocumentoInvalido as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro


@router.get("/api/documentos/{arquivo}/download", response_class=FileResponse)
async def baixar_documento(arquivo: str, documentos: Documentos) -> FileResponse:
    """Devolve o PDF original, para o usuario abrir ou baixar."""
    try:
        caminho = documentos.caminho_existente(arquivo)
    except DocumentoNaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except DocumentoInvalido as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro

    return FileResponse(caminho, media_type="application/pdf", filename=caminho.name)


@router.post("/api/documentos", response_model=DocumentoInfo, status_code=201)
async def enviar_documento(
    documentos: Documentos,
    indexacao: Indexacao,
    arquivo: UploadFile = File(..., description="Curriculo em PDF."),
    substituir: bool = Form(default=False, description="Sobrescreve se ja existir um com o mesmo nome."),
) -> DocumentoInfo:
    """Recebe um curriculo em PDF, grava na base e indexa na hora."""
    conteudo = await arquivo.read()

    def _gravar() -> DocumentoInfo:
        return documentos.salvar(arquivo.filename or "curriculo.pdf", conteudo, substituir=substituir)

    try:
        informacao = await run_in_threadpool(_gravar)
    except DocumentoInvalido as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
    except FalhaDeArmazenamento as erro:
        raise HTTPException(status_code=500, detail=str(erro)) from erro

    if not config.GEMINI_API_KEY:
        logger.warning("Upload gravado sem indexar: falta GEMINI_API_KEY.")
        return informacao

    try:
        resultado = await run_in_threadpool(indexacao.indexar_documento, informacao.arquivo)
        informacao.indexado = resultado.chunks > 0
        informacao.chunks = resultado.chunks
    except Exception as erro:  # noqa: BLE001 - o arquivo ja esta salvo; indexa depois
        logger.exception("Falha ao indexar %s", informacao.arquivo)
        raise HTTPException(
            status_code=502,
            detail=(
                f"O curriculo foi salvo, mas a indexacao falhou. {traduzir_erro_gemini(erro)} "
                "Depois de resolver, use 'Reindexar tudo' no painel admin."
            ),
        ) from erro

    return informacao


@router.delete("/api/documentos/{arquivo}", response_model=dict)
async def remover_documento(
    arquivo: str, documentos: Documentos, indexacao: Indexacao, pdi: PDI
) -> dict:
    """Remove o PDF, seus chunks do indice e os PDIs daquele aluno."""

    def _remover() -> dict:
        aluno = documentos.remover(arquivo)
        chunks = indexacao.remover_documento(arquivo)
        pdis = pdi.remover_do_aluno(aluno) if aluno else 0
        return {"arquivo": arquivo, "aluno": aluno, "chunks_removidos": chunks, "pdis_removidos": pdis}

    try:
        return await run_in_threadpool(_remover)
    except DocumentoNaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except DocumentoInvalido as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
    except FalhaDeArmazenamento as erro:
        raise HTTPException(status_code=500, detail=str(erro)) from erro


@router.post("/api/documentos/{arquivo}/indexar", response_model=ResultadoIndexacao)
async def indexar_documento(arquivo: str, indexacao: Indexacao) -> ResultadoIndexacao:
    """(Re)indexa um unico curriculo."""
    if not config.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY nao configurada.")
    try:
        return await run_in_threadpool(indexacao.indexar_documento, arquivo)
    except DocumentoNaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
    except Exception as erro:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=traduzir_erro_gemini(erro)) from erro


# ---------------------------------------------------------------------------
# Alunos (a visao do indice, nao a do disco)
# ---------------------------------------------------------------------------

@router.get("/api/alunos", response_model=list[Aluno], tags=["alunos"])
async def listar_alunos(pdi: PDI) -> list[Aluno]:
    """Alunos com curriculo indexado."""

    def _consultar() -> list[Aluno]:
        store = obter_store()
        return [
            Aluno(
                nome=nome,
                chunks=store.contar_chunks(nome),
                arquivo=store.arquivo_do_aluno(nome),
                secoes=store.secoes_do_aluno(nome),
                pdis=pdi.contar_por_aluno(nome),
            )
            for nome in store.listar_alunos()
        ]

    return await run_in_threadpool(_consultar)


@router.get("/api/alunos/{nome}", response_model=Aluno, tags=["alunos"])
async def detalhar_aluno(nome: str, pdi: PDI) -> Aluno:
    """Um aluno especifico. Aceita nome parcial ('Carlos')."""

    def _consultar() -> Aluno:
        store = obter_store()
        oficial = store.resolver_aluno(nome)
        return Aluno(
            nome=oficial,
            chunks=store.contar_chunks(oficial),
            arquivo=store.arquivo_do_aluno(oficial),
            secoes=store.secoes_do_aluno(oficial),
            pdis=pdi.contar_por_aluno(oficial),
        )

    try:
        return await run_in_threadpool(_consultar)
    except AlunoNaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro


@router.get("/api/alunos/{nome}/curriculo", response_model=dict, tags=["alunos"])
async def curriculo_do_aluno(
    nome: str,
    formato: str = Query(default="texto", pattern="^(texto|secoes)$"),
) -> dict:
    """Curriculo indexado de um aluno, remontado a partir dos chunks."""

    def _consultar() -> dict:
        store = obter_store()
        oficial = store.resolver_aluno(nome)
        texto = store.curriculo_completo(oficial)
        if formato == "secoes":
            from app.ingestion.chunking import dividir_por_secoes

            return {
                "aluno": oficial,
                "secoes": [{"nome": s, "texto": t} for s, t in dividir_por_secoes(texto)],
            }
        return {"aluno": oficial, "texto": texto}

    try:
        return await run_in_threadpool(_consultar)
    except AlunoNaoEncontrado as erro:
        raise HTTPException(status_code=404, detail=str(erro)) from erro
