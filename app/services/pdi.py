"""Servico de PDI: gera, guarda e recupera os planos de desenvolvimento.

Gerar um PDI custa uma chamada de LLM de alguns segundos. A tela grafica e
navegada varias vezes (o mentor abre, fecha, compara), entao o resultado e
persistido: a mesma combinacao aluno + vaga so e gerada de novo se o mentor
pedir explicitamente.
"""

from __future__ import annotations

import logging
import unicodedata
from datetime import datetime

from app import config
from app.agent.analise import AnalisadorPDI
from app.models.schemas import PDIEstruturado, PDIResumo
from app.retrieval.vector_store import VectorStore, obter_store
from app.storage.repositorio_json import ColecaoJson

logger = logging.getLogger(__name__)


def _chave(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().split())


class ServicoPDI:
    """CRUD de PDIs estruturados, com cache por aluno + vaga."""

    def __init__(
        self,
        store: VectorStore | None = None,
        colecao: ColecaoJson | None = None,
        analisador: AnalisadorPDI | None = None,
    ):
        self._store = store
        self.colecao = colecao or ColecaoJson(config.ESTADO_DIR / "pdis.json")
        self.analisador = analisador or AnalisadorPDI()

    @property
    def store(self) -> VectorStore:
        return self._store or obter_store()

    # -- leitura -------------------------------------------------------------

    def listar(self, aluno: str | None = None) -> list[PDIResumo]:
        registros = self.colecao.listar()
        if aluno:
            alvo = _chave(aluno)
            registros = [r for r in registros if _chave(str(r.get("aluno", ""))) == alvo]
        return [
            PDIResumo(
                id=str(registro.get("id", "")),
                aluno=str(registro.get("aluno", "")),
                vaga_alvo=str(registro.get("vaga_alvo", "")),
                aderencia=int(registro.get("aderencia", 0) or 0),
                gaps=len(registro.get("gaps", []) or []),
                acoes=len(registro.get("acoes", []) or []),
                criado_em=registro.get("criado_em"),
            )
            for registro in registros
        ]

    def obter(self, identificador: str) -> PDIEstruturado | None:
        registro = self.colecao.obter(identificador)
        return PDIEstruturado.model_validate(registro) if registro else None

    def contar(self) -> int:
        return self.colecao.contar()

    def contar_por_aluno(self, aluno: str) -> int:
        alvo = _chave(aluno)
        return sum(1 for r in self.colecao.listar() if _chave(str(r.get("aluno", ""))) == alvo)

    def _existente(self, aluno: str, vaga_alvo: str) -> dict | None:
        alvo_aluno, alvo_vaga = _chave(aluno), _chave(vaga_alvo)
        return next(
            (
                r
                for r in self.colecao.listar()
                if _chave(str(r.get("aluno", ""))) == alvo_aluno
                and _chave(str(r.get("vaga_alvo", ""))) == alvo_vaga
            ),
            None,
        )

    # -- escrita -------------------------------------------------------------

    def gerar(self, nome_aluno: str, vaga_alvo: str, forcar: bool = False) -> PDIEstruturado:
        """Gera (ou recupera do cache) o PDI estruturado de um aluno para uma vaga."""
        store = self.store
        aluno = store.resolver_aluno(nome_aluno)

        if not forcar:
            existente = self._existente(aluno, vaga_alvo)
            if existente:
                logger.info("PDI reaproveitado do cache: %s / %s", aluno, vaga_alvo)
                return PDIEstruturado.model_validate(existente)

        curriculo = store.curriculo_completo(aluno)
        if not curriculo:
            raise LookupError(f"O curriculo de {aluno} nao esta indexado.")

        from app.agent.gemini_client import modelo_chat

        gerado = self.analisador.analisar(aluno, vaga_alvo, curriculo)
        pdi = PDIEstruturado(
            id=ColecaoJson.novo_id(),
            aluno=aluno,
            vaga_alvo=vaga_alvo.strip(),
            criado_em=datetime.now(),
            modelo=modelo_chat(),
            **gerado.model_dump(),
        )

        # Substitui a versao anterior da mesma combinacao, em vez de acumular.
        anterior = self._existente(aluno, vaga_alvo)
        if anterior:
            self.colecao.remover(str(anterior.get("id", "")))

        self.colecao.adicionar(pdi.model_dump(mode="json"))
        logger.info("PDI gerado: %s / %s (aderencia %s%%)", aluno, vaga_alvo, pdi.aderencia)
        return pdi

    def remover(self, identificador: str) -> bool:
        return self.colecao.remover(identificador)

    def remover_do_aluno(self, aluno: str) -> int:
        """Usado quando um curriculo sai da base: os PDIs dele perdem o sentido."""
        alvo = _chave(aluno)
        ids = [
            str(r.get("id", ""))
            for r in self.colecao.listar()
            if _chave(str(r.get("aluno", ""))) == alvo
        ]
        for identificador in ids:
            self.colecao.remover(identificador)
        return len(ids)
