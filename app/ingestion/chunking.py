"""Divide o texto de um curriculo em chunks pesquisaveis.

Estrategia em dois niveis:

1. Quebra por secao (Dados pessoais, Resumo, Experiencias, ...). Curriculo e um
   documento naturalmente seccionado, entao respeitar a secao mantem cada chunk
   semanticamente coeso e da um metadado util para filtrar/citar depois.
2. Se uma secao for maior que `tamanho`, ela e subdividida por linhas inteiras,
   com sobreposicao entre os pedacos para nao cortar uma frase no meio.

Cada chunk carrega um cabecalho com aluno e secao. Isso melhora o embedding
(o texto fica auto-contido) e faz o LLM saber de quem esta falando.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from app.ingestion.pdf_parser import CurriculoBruto, eh_cabecalho_de_secao


@dataclass
class Chunk:
    """Um pedaco indexavel do curriculo, com os metadados que vao para o Chroma."""

    id: str
    texto: str
    aluno: str
    secao: str
    arquivo: str
    indice: int

    def metadados(self) -> dict[str, str | int]:
        return {
            "aluno": self.aluno,
            "aluno_normalizado": slug(self.aluno),
            "secao": self.secao,
            "arquivo": self.arquivo,
            "indice": self.indice,
        }


def slug(nome: str) -> str:
    """Nome do aluno em forma canonica: 'Ana Beatriz' -> 'ana beatriz'."""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9 ]", " ", sem_acento)).strip().lower()


def dividir_por_secoes(texto: str) -> list[tuple[str, str]]:
    """Quebra o texto em pares (secao, conteudo), preservando a ordem original."""
    secoes: list[tuple[str, list[str]]] = []
    atual = "Apresentacao"
    acumulado: list[str] = []

    for linha in texto.splitlines():
        titulo = eh_cabecalho_de_secao(linha)
        if titulo:
            if acumulado:
                secoes.append((atual, acumulado))
            atual, acumulado = titulo, []
            continue
        if linha.strip():
            acumulado.append(linha.strip())

    if acumulado:
        secoes.append((atual, acumulado))

    return [(nome, "\n".join(linhas).strip()) for nome, linhas in secoes if "".join(linhas).strip()]


def _quebrar_texto(texto: str, tamanho: int, sobreposicao: int) -> list[str]:
    """Divide um texto longo em pedacos de ate `tamanho` caracteres, por linha inteira."""
    if len(texto) <= tamanho:
        return [texto]

    linhas = texto.splitlines()
    pedacos: list[str] = []
    atual: list[str] = []
    tamanho_atual = 0

    for linha in linhas:
        # Linha unica maior que o limite: quebra dura por caracteres.
        if len(linha) > tamanho:
            if atual:
                pedacos.append("\n".join(atual))
                atual, tamanho_atual = [], 0
            for inicio in range(0, len(linha), tamanho):
                pedacos.append(linha[inicio : inicio + tamanho])
            continue

        if tamanho_atual + len(linha) + 1 > tamanho and atual:
            pedacos.append("\n".join(atual))
            # Sobreposicao: repete o final do pedaco anterior no proximo.
            cauda: list[str] = []
            total = 0
            for anterior in reversed(atual):
                if total + len(anterior) > sobreposicao:
                    break
                cauda.insert(0, anterior)
                total += len(anterior) + 1
            atual = cauda
            tamanho_atual = total

        atual.append(linha)
        tamanho_atual += len(linha) + 1

    if atual:
        pedacos.append("\n".join(atual))

    return [p.strip() for p in pedacos if p.strip()]


def gerar_chunks(curriculo: CurriculoBruto, tamanho: int = 900, sobreposicao: int = 150) -> list[Chunk]:
    """Transforma um curriculo lido em uma lista de chunks prontos para indexar."""
    chunks: list[Chunk] = []
    # Baseado no ARQUIVO, nao no nome do aluno: dois documentos podem descrever
    # a mesma pessoa (reenvio, teste, nome em comum) e, se o id dependesse so
    # do nome, colidiriam no upsert do Chroma - um upload sobrescreveria em
    # silencio os chunks do outro, e apagar o duplicado apagaria o original
    # junto. O nome do arquivo e garantidamente unico (ServicoDocumentos
    # sempre gera "_2", "_3"... em caso de colisao).
    identificador = slug(Path(curriculo.arquivo).stem).replace(" ", "_")

    for secao, conteudo in dividir_por_secoes(curriculo.texto):
        for pedaco in _quebrar_texto(conteudo, tamanho, sobreposicao):
            indice = len(chunks)
            cabecalho = f"Curriculo de {curriculo.nome_aluno} | Secao: {secao}"
            chunks.append(
                Chunk(
                    id=f"{identificador}--{indice:03d}",
                    texto=f"{cabecalho}\n{pedaco}",
                    aluno=curriculo.nome_aluno,
                    secao=secao,
                    arquivo=curriculo.arquivo,
                    indice=indice,
                )
            )

    return chunks
