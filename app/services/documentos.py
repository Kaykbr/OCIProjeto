"""Servico de documentos: os curriculos em PDF que formam a base de conhecimento.

Cuida do ciclo de vida do arquivo (listar, ler, receber upload, remover) e da
leitura do conteudo. Quem indexa e o `ServicoIndexacao` - a separacao mantem
este servico livre de qualquer dependencia de LLM, o que permite navegar pela
base mesmo sem GEMINI_API_KEY configurada.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from app import config
from app.ingestion.chunking import dividir_por_secoes, gerar_chunks
from app.ingestion.pdf_parser import CurriculoBruto, ler_curriculo, listar_curriculos
from app.models.schemas import DocumentoDetalhe, DocumentoInfo, SecaoDocumento

logger = logging.getLogger(__name__)

ASSINATURA_PDF = b"%PDF-"


class DocumentoInvalido(ValueError):
    """Arquivo enviado nao serve como curriculo."""


class DocumentoNaoEncontrado(FileNotFoundError):
    """O PDF pedido nao existe na base."""


class FalhaDeArmazenamento(OSError):
    """Nao foi possivel gravar/apagar o arquivo (pasta somente leitura, disco cheio...)."""


class ServicoDocumentos:
    """Repositorio de curriculos em PDF numa pasta do disco."""

    def __init__(self, pasta: Path | None = None):
        self.pasta = pasta or config.CURRICULOS_DIR
        self.pasta.mkdir(parents=True, exist_ok=True)

    # -- caminho seguro ------------------------------------------------------

    def caminho(self, arquivo: str) -> Path:
        """Resolve o nome recebido do cliente para um caminho dentro da pasta.

        Protege contra path traversal: qualquer coisa que escape da pasta de
        curriculos e recusada, mesmo que o nome venha com `../` ou caminho absoluto.
        """
        nome = Path(arquivo).name
        if not nome or nome in (".", ".."):
            raise DocumentoInvalido(f"Nome de arquivo invalido: '{arquivo}'")

        destino = (self.pasta / nome).resolve()
        if not destino.is_relative_to(self.pasta.resolve()):
            raise DocumentoInvalido(f"Caminho fora da base de curriculos: '{arquivo}'")
        return destino

    def caminho_existente(self, arquivo: str) -> Path:
        destino = self.caminho(arquivo)
        if not destino.exists():
            raise DocumentoNaoEncontrado(f"Curriculo '{arquivo}' nao encontrado na base.")
        return destino

    # -- leitura -------------------------------------------------------------

    def listar_arquivos(self) -> list[Path]:
        return listar_curriculos(self.pasta)

    def ler(self, arquivo: str) -> CurriculoBruto:
        return ler_curriculo(self.caminho_existente(arquivo))

    def info(self, caminho: Path, chunks_por_arquivo: dict[str, int] | None = None) -> DocumentoInfo:
        """Metadados de um PDF, sem carregar o texto inteiro para a resposta."""
        chunks_por_arquivo = chunks_por_arquivo or {}
        estatistica = caminho.stat()
        try:
            curriculo = ler_curriculo(caminho)
            aluno, paginas, caracteres = curriculo.nome_aluno, curriculo.paginas, curriculo.caracteres
        except Exception as erro:  # noqa: BLE001 - PDF corrompido nao pode sumir da listagem
            logger.warning("Falha ao ler %s: %s", caminho.name, erro)
            aluno, paginas, caracteres = "", 0, 0

        chunks = chunks_por_arquivo.get(caminho.name, 0)
        return DocumentoInfo(
            arquivo=caminho.name,
            aluno=aluno,
            paginas=paginas,
            tamanho_kb=round(estatistica.st_size / 1024, 1),
            caracteres=caracteres,
            indexado=chunks > 0,
            chunks=chunks,
            atualizado_em=datetime.fromtimestamp(estatistica.st_mtime),
        )

    def listar(self, chunks_por_arquivo: dict[str, int] | None = None) -> list[DocumentoInfo]:
        return [self.info(caminho, chunks_por_arquivo) for caminho in self.listar_arquivos()]

    def detalhe(self, arquivo: str, chunks_por_arquivo: dict[str, int] | None = None) -> DocumentoDetalhe:
        """Documento com o texto extraido e as secoes identificadas pelo parser."""
        caminho = self.caminho_existente(arquivo)
        curriculo = ler_curriculo(caminho)
        base = self.info(caminho, chunks_por_arquivo)

        secoes = [
            SecaoDocumento(nome=nome, texto=texto, caracteres=len(texto))
            for nome, texto in dividir_por_secoes(curriculo.texto)
        ]
        return DocumentoDetalhe(**base.model_dump(), texto=curriculo.texto, secoes=secoes)

    # -- escrita -------------------------------------------------------------

    @staticmethod
    def _nome_seguro(nome_original: str) -> str:
        """Normaliza o nome do upload: sem acento, sem espaco, sempre .pdf."""
        base = Path(nome_original).stem
        sem_acento = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
        limpo = re.sub(r"[^a-zA-Z0-9]+", "_", sem_acento).strip("_").lower()
        return f"{limpo or 'curriculo'}.pdf"

    def _nome_disponivel(self, nome: str) -> str:
        destino = self.caminho(nome)
        if not destino.exists():
            return nome
        raiz = destino.stem
        for sufixo in range(2, 100):
            candidato = f"{raiz}_{sufixo}.pdf"
            if not self.caminho(candidato).exists():
                return candidato
        raise DocumentoInvalido("Nao consegui achar um nome livre para o arquivo.")

    def salvar(self, nome_original: str, conteudo: bytes, substituir: bool = False) -> DocumentoInfo:
        """Valida e grava um PDF enviado pela interface."""
        limite = int(config.UPLOAD_MAX_MB * 1024 * 1024)
        if not conteudo:
            raise DocumentoInvalido("Arquivo vazio.")
        if len(conteudo) > limite:
            raise DocumentoInvalido(
                f"Arquivo tem {len(conteudo) / 1024 / 1024:.1f} MB; o limite e {config.UPLOAD_MAX_MB} MB."
            )
        if not conteudo.startswith(ASSINATURA_PDF):
            raise DocumentoInvalido("O arquivo nao e um PDF valido (assinatura %PDF- ausente).")

        nome = self._nome_seguro(nome_original)
        if not substituir:
            nome = self._nome_disponivel(nome)

        destino = self.caminho(nome)
        try:
            destino.write_bytes(conteudo)
        except OSError as erro:
            raise FalhaDeArmazenamento(
                f"Nao consegui gravar '{nome}' em {self.pasta}: {erro}. "
                "Se estiver rodando em container, confirme que a pasta de curriculos "
                "esta montada com permissao de escrita (sem ':ro' no docker-compose)."
            ) from erro

        try:
            curriculo = ler_curriculo(destino)
        except Exception as erro:  # noqa: BLE001 - PDF ilegivel nao entra na base
            destino.unlink(missing_ok=True)
            raise DocumentoInvalido(
                f"Nao consegui extrair texto do PDF ({erro}). "
                "PDFs escaneados (imagem) precisam de OCR antes de entrar na base."
            ) from erro

        if not gerar_chunks(curriculo):
            destino.unlink(missing_ok=True)
            raise DocumentoInvalido("O PDF nao produziu nenhum trecho indexavel.")

        logger.info("Curriculo recebido: %s (%s)", nome, curriculo.nome_aluno)
        return self.info(destino)

    def remover(self, arquivo: str) -> str:
        """Apaga o PDF da base. Devolve o nome do aluno que estava nele."""
        caminho = self.caminho_existente(arquivo)
        try:
            aluno = ler_curriculo(caminho).nome_aluno
        except Exception:  # noqa: BLE001
            aluno = ""

        try:
            caminho.unlink()
        except OSError as erro:
            raise FalhaDeArmazenamento(
                f"Nao consegui apagar '{arquivo}': {erro}. "
                "Verifique a permissao de escrita na pasta de curriculos."
            ) from erro

        logger.info("Curriculo removido: %s", arquivo)
        return aluno
