"""API FastAPI do Agente Mentor de Carreiras.

Monta a aplicacao: middlewares, rotas (agrupadas por dominio em `app/api/`) e o
frontend estatico. Sem autenticacao - por definicao do desafio, o agente e
interno e aberto; os perfis (mentor, aluno, admin) sao visoes da interface, nao
controle de acesso.

    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app import config
from app.api import rotas_admin, rotas_agente, rotas_documentos, rotas_pdi, rotas_validacoes
from app.api.dependencias import (
    obter_servico_documentos,
    obter_servico_indexacao,
    obter_servico_pdi,
    obter_servico_validacoes,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agente-mentor")

DIRETORIO_ESTATICO = config.BASE_DIR / "app" / "static"

DESCRICAO = """
Agente de IA que responde perguntas em linguagem natural sobre os curriculos dos
alunos de uma mentoria: busca dados, padroniza curriculos, monta PDI comparando o
aluno com uma vaga-alvo e sugere projetos praticos.

**Telas:** mentor (chat + validacao), base de documentos, PDI grafico e painel admin.

Desafio final Alura Agent, implantado na Oracle Cloud Infrastructure.
""".strip()


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ESTADO_DIR.mkdir(parents=True, exist_ok=True)

    try:
        await run_in_threadpool(obter_servico_indexacao().indexar_se_vazio)
    except Exception as erro:  # noqa: BLE001 - a app sobe mesmo assim e avisa na interface
        logger.error("Indexacao automatica falhou: %s", erro)

    estado = await run_in_threadpool(
        rotas_agente.montar_status,
        obter_servico_pdi(),
        obter_servico_validacoes(),
        obter_servico_documentos(),
    )
    logger.info("Agente Mentor de Carreiras v%s na porta %s", config.VERSAO, config.PORT)
    logger.info(
        "Base: %s documentos | Indice: %s chunks | Alunos: %s",
        estado.documentos,
        estado.chunks_indexados,
        ", ".join(estado.alunos) or "(nenhum)",
    )
    if estado.aviso:
        logger.warning(estado.aviso)

    yield
    logger.info("Encerrando.")


app = FastAPI(
    title="Agente Mentor de Carreiras",
    description=DESCRICAO,
    version=config.VERSAO,
    lifespan=lifespan,
)

# Agente interno e aberto: sem login e sem restricao de origem.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rotas_agente.router)
app.include_router(rotas_documentos.router)
app.include_router(rotas_pdi.router)
app.include_router(rotas_validacoes.router)
app.include_router(rotas_admin.router)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(DIRETORIO_ESTATICO / "index.html")


app.mount("/static", StaticFiles(directory=DIRETORIO_ESTATICO), name="static")
