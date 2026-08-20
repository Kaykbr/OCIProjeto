"""Injecao de dependencia das rotas.

Cada servico e um singleton do processo (`lru_cache`), o que evita reabrir o
ChromaDB e reler os arquivos JSON a cada requisicao. As rotas recebem os
servicos via `Depends`, o que tambem deixa cada um substituivel num teste.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.services.agente import ServicoAgente
from app.services.documentos import ServicoDocumentos
from app.services.indexacao import ServicoIndexacao
from app.services.pdi import ServicoPDI
from app.services.validacoes import ServicoValidacoes


@lru_cache(maxsize=1)
def obter_servico_documentos() -> ServicoDocumentos:
    return ServicoDocumentos()


@lru_cache(maxsize=1)
def obter_servico_indexacao() -> ServicoIndexacao:
    return ServicoIndexacao(documentos=obter_servico_documentos())


@lru_cache(maxsize=1)
def obter_servico_pdi() -> ServicoPDI:
    return ServicoPDI()


@lru_cache(maxsize=1)
def obter_servico_validacoes() -> ServicoValidacoes:
    return ServicoValidacoes()


@lru_cache(maxsize=1)
def obter_servico_agente() -> ServicoAgente:
    return ServicoAgente()


Documentos = Annotated[ServicoDocumentos, Depends(obter_servico_documentos)]
Indexacao = Annotated[ServicoIndexacao, Depends(obter_servico_indexacao)]
PDI = Annotated[ServicoPDI, Depends(obter_servico_pdi)]
Validacoes = Annotated[ServicoValidacoes, Depends(obter_servico_validacoes)]
Agente = Annotated[ServicoAgente, Depends(obter_servico_agente)]
