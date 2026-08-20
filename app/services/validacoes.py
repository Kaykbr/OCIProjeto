"""Servico de validacoes: o registro humano em cima das respostas do agente.

O agente propoe, o mentor valida. Cada resposta pode ser marcada como aprovada,
"precisa ajuste" ou rejeitada, com uma observacao. Isso vira a fila de revisao da
tela de validacoes e o historico de qualidade do agente - que e exatamente o que
a tela principal do mentor precisa mostrar.
"""

from __future__ import annotations

import logging
from datetime import datetime

from app import config
from app.models.schemas import AtualizarValidacao, Validacao, ValidacaoRequest
from app.storage.repositorio_json import ColecaoJson

logger = logging.getLogger(__name__)


class ServicoValidacoes:
    """CRUD das validacoes feitas pelo mentor."""

    def __init__(self, colecao: ColecaoJson | None = None):
        self.colecao = colecao or ColecaoJson(config.ESTADO_DIR / "validacoes.json")

    def listar(self, veredito: str | None = None, aluno: str | None = None) -> list[Validacao]:
        registros = self.colecao.listar()
        if veredito:
            registros = [r for r in registros if r.get("veredito") == veredito]
        if aluno:
            registros = [r for r in registros if str(r.get("aluno", "")).lower() == aluno.lower()]
        return [Validacao.model_validate(r) for r in registros]

    def obter(self, identificador: str) -> Validacao | None:
        registro = self.colecao.obter(identificador)
        return Validacao.model_validate(registro) if registro else None

    def registrar(self, pedido: ValidacaoRequest) -> Validacao:
        registro = pedido.model_dump()
        registro["id"] = ColecaoJson.novo_id()
        registro["criado_em"] = datetime.now().isoformat(timespec="seconds")
        self.colecao.adicionar(registro)
        logger.info("Validacao registrada (%s) para '%s'", pedido.veredito, pedido.aluno or "-")
        return Validacao.model_validate(registro)

    def atualizar(self, identificador: str, mudancas: AtualizarValidacao) -> Validacao | None:
        registro = self.colecao.atualizar(
            identificador, mudancas.model_dump(exclude_none=True)
        )
        return Validacao.model_validate(registro) if registro else None

    def remover(self, identificador: str) -> bool:
        return self.colecao.remover(identificador)

    def contar(self, veredito: str | None = None) -> int:
        return len(self.listar(veredito=veredito))

    def resumo(self) -> dict[str, int]:
        """Contagem por veredito, para os cartoes do painel."""
        contagem = {"aprovado": 0, "ajustar": 0, "rejeitado": 0}
        for registro in self.colecao.listar():
            chave = str(registro.get("veredito", ""))
            if chave in contagem:
                contagem[chave] += 1
        return contagem
