"""Persistencia simples em arquivo JSON.

PDIs gerados e validacoes do mentor precisam sobreviver a um restart, mas nao
justificam subir um banco: sao dezenas de registros, escritos raramente e lidos
por uma pessoa de cada vez. Um arquivo JSON com escrita atomica resolve, mantem
o container autossuficiente na OCI e nao adiciona nenhuma dependencia.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class RepositorioJson:
    """Um arquivo JSON com leitura/escrita protegidas por lock."""

    def __init__(self, caminho: Path, padrao: Any = None):
        self.caminho = caminho
        self._padrao = padrao if padrao is not None else []
        self._lock = threading.RLock()
        self.caminho.parent.mkdir(parents=True, exist_ok=True)

    def ler(self) -> Any:
        with self._lock:
            if not self.caminho.exists():
                return json.loads(json.dumps(self._padrao))
            try:
                return json.loads(self.caminho.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as erro:
                logger.error("Arquivo %s ilegivel (%s). Comecando vazio.", self.caminho, erro)
                return json.loads(json.dumps(self._padrao))

    def escrever(self, dados: Any) -> None:
        """Escrita atomica: grava num temporario e troca, para nunca deixar
        o arquivo pela metade se o processo morrer no meio."""
        with self._lock:
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            temporario = None
            try:
                with tempfile.NamedTemporaryFile(
                    "w", encoding="utf-8", dir=self.caminho.parent, delete=False, suffix=".tmp"
                ) as arquivo:
                    json.dump(dados, arquivo, ensure_ascii=False, indent=2, default=str)
                    temporario = Path(arquivo.name)
                os.replace(temporario, self.caminho)
            except Exception:
                if temporario and temporario.exists():
                    temporario.unlink(missing_ok=True)
                raise

    def transacao(self, funcao: Callable[[Any], Any]) -> Any:
        """Le, aplica `funcao` e grava, tudo sob o mesmo lock."""
        with self._lock:
            dados = self.ler()
            resultado = funcao(dados)
            self.escrever(dados)
            return resultado


class ColecaoJson(RepositorioJson):
    """Uma lista de registros com `id`, no estilo de uma tabela simples."""

    def __init__(self, caminho: Path):
        super().__init__(caminho, padrao=[])

    @staticmethod
    def novo_id() -> str:
        return uuid.uuid4().hex[:12]

    @staticmethod
    def agora() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def listar(self) -> list[dict]:
        registros = self.ler()
        return registros if isinstance(registros, list) else []

    def obter(self, identificador: str) -> dict | None:
        return next((r for r in self.listar() if r.get("id") == identificador), None)

    def adicionar(self, registro: dict) -> dict:
        registro = dict(registro)
        registro.setdefault("id", self.novo_id())
        registro.setdefault("criado_em", self.agora())

        def aplicar(dados: list) -> dict:
            dados.insert(0, registro)  # mais recente primeiro
            return registro

        return self.transacao(aplicar)

    def atualizar(self, identificador: str, mudancas: dict) -> dict | None:
        def aplicar(dados: list) -> dict | None:
            for registro in dados:
                if registro.get("id") == identificador:
                    registro.update({k: v for k, v in mudancas.items() if v is not None})
                    registro["atualizado_em"] = self.agora()
                    return registro
            return None

        return self.transacao(aplicar)

    def remover(self, identificador: str) -> bool:
        def aplicar(dados: list) -> bool:
            for indice, registro in enumerate(dados):
                if registro.get("id") == identificador:
                    dados.pop(indice)
                    return True
            return False

        return self.transacao(aplicar)

    def remover_onde(self, campo: str, valor: Any) -> int:
        def aplicar(dados: list) -> int:
            restantes = [r for r in dados if r.get(campo) != valor]
            removidos = len(dados) - len(restantes)
            dados[:] = restantes
            return removidos

        return self.transacao(aplicar)

    def contar(self) -> int:
        return len(self.listar())
