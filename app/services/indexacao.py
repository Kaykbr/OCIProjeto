"""Servico de indexacao: mantem o vector store em sincronia com a pasta de PDFs.

Concentra o pipeline PDF -> texto -> chunks -> embeddings -> ChromaDB num unico
lugar, usado por tres caminhos diferentes: o script de linha de comando, a
auto-indexacao na subida do container e o painel admin.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from app import config
from app.ingestion.chunking import gerar_chunks
from app.ingestion.pdf_parser import ler_curriculo, ler_todos
from app.models.schemas import EstatisticasIndice, ResultadoIndexacao
from app.retrieval.vector_store import VectorStore, obter_store
from app.services.documentos import ServicoDocumentos

logger = logging.getLogger(__name__)


class ServicoIndexacao:
    """Operacoes de escrita e diagnostico do indice vetorial."""

    def __init__(self, store: VectorStore | None = None, documentos: ServicoDocumentos | None = None):
        self._store = store
        self.documentos = documentos or ServicoDocumentos()

    @property
    def store(self) -> VectorStore:
        # Resolvido tarde: o Chroma so e aberto quando alguem realmente precisa.
        return self._store or obter_store()

    # -- escrita -------------------------------------------------------------

    def reindexar_tudo(self) -> ResultadoIndexacao:
        """Apaga a colecao e reindexa todos os PDFs da pasta."""
        inicio = time.perf_counter()
        curriculos = ler_todos(config.CURRICULOS_DIR)
        if not curriculos:
            return ResultadoIndexacao(avisos=["Nenhum PDF encontrado em data/curriculos."])

        chunks = [
            chunk
            for curriculo in curriculos
            for chunk in gerar_chunks(curriculo, config.CHUNK_TAMANHO, config.CHUNK_SOBREPOSICAO)
        ]

        self.store.resetar()
        gravados = self.store.indexar(chunks)

        return ResultadoIndexacao(
            arquivos=len(curriculos),
            chunks=gravados,
            alunos=sorted({c.nome_aluno for c in curriculos}),
            duracao_s=round(time.perf_counter() - inicio, 2),
        )

    def indexar_documento(self, arquivo: str) -> ResultadoIndexacao:
        """(Re)indexa um unico PDF, substituindo os chunks antigos dele."""
        inicio = time.perf_counter()
        caminho: Path = self.documentos.caminho_existente(arquivo)
        curriculo = ler_curriculo(caminho)
        chunks = gerar_chunks(curriculo, config.CHUNK_TAMANHO, config.CHUNK_SOBREPOSICAO)

        self.store.remover_documento(arquivo)
        gravados = self.store.indexar(chunks)

        logger.info("%s indexado: %s chunks (%s)", arquivo, gravados, curriculo.nome_aluno)
        return ResultadoIndexacao(
            arquivos=1,
            chunks=gravados,
            alunos=[curriculo.nome_aluno],
            duracao_s=round(time.perf_counter() - inicio, 2),
        )

    def remover_documento(self, arquivo: str) -> int:
        """Tira do indice os chunks de um PDF."""
        return self.store.remover_documento(arquivo)

    def indexar_se_vazio(self) -> ResultadoIndexacao | None:
        """Indexa na subida quando ainda nao ha indice. Devolve None se nao fez nada."""
        if not (config.AUTO_INDEXAR and config.GEMINI_API_KEY):
            return None
        if not self.store.esta_vazio():
            return None
        if not self.documentos.listar_arquivos():
            logger.warning("Nenhum PDF em %s para indexar.", config.CURRICULOS_DIR)
            return None

        logger.info("Indice vazio: indexando a base de curriculos...")
        resultado = self.reindexar_tudo()
        logger.info(
            "Indexacao automatica concluida: %s chunks de %s curriculos em %ss",
            resultado.chunks,
            resultado.arquivos,
            resultado.duracao_s,
        )
        return resultado

    # -- diagnostico ---------------------------------------------------------

    def chunks_por_arquivo(self) -> dict[str, int]:
        """Quantos chunks cada PDF gerou - usado para marcar 'indexado' na listagem."""
        store = self.store
        if store.esta_vazio():
            return {}
        contagem: dict[str, int] = {}
        for aluno in store.listar_alunos():
            arquivo = store.arquivo_do_aluno(aluno)
            if arquivo:
                contagem[arquivo] = contagem.get(arquivo, 0) + store.contar_chunks(aluno)
        return contagem

    def estatisticas(self) -> EstatisticasIndice:
        store = self.store
        dados = store.estatisticas()
        arquivos_na_pasta = {caminho.name for caminho in self.documentos.listar_arquivos()}
        indexados = set(dados.get("arquivos", []))

        modelo = ""
        if config.GEMINI_API_KEY:
            try:
                from app.agent.gemini_client import modelo_embedding

                modelo = modelo_embedding()
            except Exception as erro:  # noqa: BLE001
                logger.warning("Nao resolvi o modelo de embedding: %s", erro)

        return EstatisticasIndice(
            total_chunks=store.total_chunks(),
            total_alunos=len(dados.get("chunks_por_aluno", {})),
            total_documentos=len(arquivos_na_pasta),
            chunks_por_aluno=dados.get("chunks_por_aluno", {}),
            chunks_por_secao=dados.get("chunks_por_secao", {}),
            documentos_nao_indexados=sorted(arquivos_na_pasta - indexados),
            colecao=store.nome_colecao,
            caminho=str(store.caminho),
            modelo_embedding=modelo,
        )
