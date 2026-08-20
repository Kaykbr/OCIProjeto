"""Wrapper do ChromaDB: indexacao, busca semantica e filtro por aluno.

O Chroma roda embutido no proprio processo e persiste em disco (data/chroma/),
entao nao existe servico externo para provisionar na OCI - o container e
autossuficiente.

Os embeddings sao gerados por nos (Gemini) e passados prontos para o Chroma;
a embedding function default da lib nunca e usada.
"""

from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass
from functools import lru_cache

import chromadb
from chromadb.config import Settings

from app import config
from app.ingestion.chunking import Chunk, slug
from app.retrieval.embeddings import embedding_da_consulta, gerar_embeddings

logger = logging.getLogger(__name__)


@dataclass
class Trecho:
    """Um chunk recuperado do vector store, com sua distancia para a consulta."""

    texto: str
    aluno: str
    secao: str
    arquivo: str
    distancia: float

    @property
    def similaridade(self) -> float:
        """Distancia cosseno (0..2) convertida em similaridade legivel (0..1)."""
        return max(0.0, 1.0 - self.distancia)


class AlunoNaoEncontrado(LookupError):
    """Nome pedido pelo mentor nao bate com nenhum aluno indexado."""


class VectorStore:
    """Colecao de chunks de curriculos no ChromaDB."""

    def __init__(self, caminho=None, colecao: str | None = None):
        self.caminho = caminho or config.CHROMA_DIR
        self.nome_colecao = colecao or config.CHROMA_COLLECTION
        self.caminho.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self.caminho),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        self._colecao = self._client.get_or_create_collection(
            name=self.nome_colecao,
            metadata={"hnsw:space": "cosine", "descricao": "chunks de curriculos"},
        )

    # -- escrita ------------------------------------------------------------

    def resetar(self) -> None:
        """Apaga a colecao inteira (usado antes de uma reindexacao completa)."""
        self._client.delete_collection(self.nome_colecao)
        self._colecao = self._client.get_or_create_collection(
            name=self.nome_colecao,
            metadata={"hnsw:space": "cosine", "descricao": "chunks de curriculos"},
        )

    def indexar(self, chunks: list[Chunk], lote: int = 32) -> int:
        """Gera os embeddings e grava os chunks. Devolve quantos foram gravados."""
        if not chunks:
            return 0

        gravados = 0
        for inicio in range(0, len(chunks), lote):
            fatia = chunks[inicio : inicio + lote]
            vetores = gerar_embeddings([c.texto for c in fatia])
            self._colecao.upsert(
                ids=[c.id for c in fatia],
                documents=[c.texto for c in fatia],
                embeddings=vetores,
                metadatas=[c.metadados() for c in fatia],
            )
            gravados += len(fatia)
            logger.info("Indexados %s/%s chunks", gravados, len(chunks))
        return gravados

    def remover_documento(self, arquivo: str) -> int:
        """Apaga todos os chunks vindos de um PDF. Devolve quantos saiu."""
        registros = self._colecao.get(where={"arquivo": arquivo}, include=[])
        ids = registros.get("ids") or []
        if ids:
            self._colecao.delete(ids=ids)
        return len(ids)

    def remover_aluno(self, aluno: str) -> int:
        """Apaga todos os chunks de um aluno. Devolve quantos saiu."""
        registros = self._colecao.get(where={"aluno_normalizado": slug(aluno)}, include=[])
        ids = registros.get("ids") or []
        if ids:
            self._colecao.delete(ids=ids)
        return len(ids)

    # -- leitura ------------------------------------------------------------

    def total_chunks(self) -> int:
        return self._colecao.count()

    def esta_vazio(self) -> bool:
        return self.total_chunks() == 0

    def listar_alunos(self) -> list[str]:
        """Nomes dos alunos indexados, em ordem alfabetica."""
        if self.esta_vazio():
            return []
        registros = self._colecao.get(include=["metadatas"])
        nomes = {
            str(meta.get("aluno", "")).strip()
            for meta in (registros.get("metadatas") or [])
            if meta and meta.get("aluno")
        }
        return sorted(nomes)

    def contar_chunks(self, aluno: str) -> int:
        """Quantos chunks um aluno tem indexados."""
        registros = self._colecao.get(where={"aluno_normalizado": slug(aluno)}, include=[])
        return len(registros.get("ids") or [])

    def arquivo_do_aluno(self, aluno: str) -> str:
        """Nome do PDF de origem do aluno."""
        registros = self._colecao.get(
            where={"aluno_normalizado": slug(aluno)},
            limit=1,
            include=["metadatas"],
        )
        metadados = registros.get("metadatas") or []
        return str(metadados[0].get("arquivo", "")) if metadados else ""

    def secoes_do_aluno(self, aluno: str) -> list[str]:
        """Seccoes do curriculo de um aluno, na ordem em que aparecem no PDF."""
        registros = self._colecao.get(
            where={"aluno_normalizado": slug(aluno)},
            include=["metadatas"],
        )
        metadados = registros.get("metadatas") or []
        vistas: list[str] = []
        for meta in sorted(metadados, key=lambda m: int(m.get("indice", 0) if m else 0)):
            secao = str((meta or {}).get("secao", "")).strip()
            if secao and secao not in vistas:
                vistas.append(secao)
        return vistas

    def estatisticas(self) -> dict:
        """Panorama do indice para o painel admin: chunks por aluno e por secao."""
        if self.esta_vazio():
            return {"chunks_por_aluno": {}, "chunks_por_secao": {}, "arquivos": []}

        registros = self._colecao.get(include=["metadatas"])
        por_aluno: dict[str, int] = {}
        por_secao: dict[str, int] = {}
        arquivos: set[str] = set()

        for meta in registros.get("metadatas") or []:
            if not meta:
                continue
            aluno = str(meta.get("aluno", "")).strip()
            secao = str(meta.get("secao", "")).strip()
            arquivo = str(meta.get("arquivo", "")).strip()
            if aluno:
                por_aluno[aluno] = por_aluno.get(aluno, 0) + 1
            if secao:
                por_secao[secao] = por_secao.get(secao, 0) + 1
            if arquivo:
                arquivos.add(arquivo)

        return {
            "chunks_por_aluno": dict(sorted(por_aluno.items())),
            "chunks_por_secao": dict(sorted(por_secao.items(), key=lambda par: -par[1])),
            "arquivos": sorted(arquivos),
        }

    def resolver_aluno(self, nome: str) -> str:
        """Converte o que o mentor digitou no nome exato do aluno indexado.

        Aceita nome parcial ("Carlos"), sem acento e com caixa diferente.
        Levanta AlunoNaoEncontrado com a lista de opcoes se nao houver match.
        """
        alunos = self.listar_alunos()
        if not alunos:
            raise AlunoNaoEncontrado(
                "Nenhum curriculo foi indexado ainda. Rode: python scripts/indexar_curriculos.py"
            )

        pedido = slug(nome)
        indice = {slug(a): a for a in alunos}

        if pedido in indice:
            return indice[pedido]

        # Match por prefixo/substring (primeiro nome, sobrenome, nome incompleto).
        parciais = [nome_real for chave, nome_real in indice.items() if pedido and pedido in chave]
        if len(parciais) == 1:
            return parciais[0]
        if len(parciais) > 1:
            raise AlunoNaoEncontrado(
                f"'{nome}' e ambiguo: pode ser {', '.join(parciais)}. Peca o nome completo ao mentor."
            )

        # Ultimo recurso: similaridade textual (erros de digitacao).
        aproximados = difflib.get_close_matches(pedido, list(indice), n=1, cutoff=0.72)
        if aproximados:
            return indice[aproximados[0]]

        raise AlunoNaoEncontrado(
            f"Nao encontrei nenhum aluno chamado '{nome}'. Alunos indexados: {', '.join(alunos)}."
        )

    def buscar(self, pergunta: str, aluno: str | None = None, top_k: int | None = None) -> list[Trecho]:
        """Busca semantica, opcionalmente restrita a um aluno."""
        if self.esta_vazio():
            return []

        top_k = top_k or config.TOP_K
        filtro = {"aluno_normalizado": slug(aluno)} if aluno else None

        resultado = self._colecao.query(
            query_embeddings=[embedding_da_consulta(pergunta)],
            n_results=min(top_k, self.total_chunks()),
            where=filtro,
            include=["documents", "metadatas", "distances"],
        )

        documentos = (resultado.get("documents") or [[]])[0]
        metadados = (resultado.get("metadatas") or [[]])[0]
        distancias = (resultado.get("distances") or [[]])[0]

        return [
            Trecho(
                texto=documento,
                aluno=str(meta.get("aluno", "")),
                secao=str(meta.get("secao", "")),
                arquivo=str(meta.get("arquivo", "")),
                distancia=float(distancia),
            )
            for documento, meta, distancia in zip(documentos, metadados, distancias)
        ]

    def curriculo_completo(self, aluno: str) -> str:
        """Devolve o curriculo inteiro do aluno, chunks em ordem original.

        Usado pelas ferramentas que precisam do documento todo (curriculo
        padronizado, PDI) em vez de apenas os trechos mais parecidos.
        """
        registros = self._colecao.get(
            where={"aluno_normalizado": slug(aluno)},
            include=["documents", "metadatas"],
        )
        documentos = registros.get("documents") or []
        metadados = registros.get("metadatas") or []
        if not documentos:
            return ""

        ordenados = sorted(
            zip(documentos, metadados),
            key=lambda par: int(par[1].get("indice", 0) if par[1] else 0),
        )
        return "\n\n".join(documento for documento, _ in ordenados)


@lru_cache(maxsize=1)
def obter_store() -> VectorStore:
    """VectorStore compartilhado pelo processo (o Chroma nao gosta de multiplos clients)."""
    return VectorStore()
