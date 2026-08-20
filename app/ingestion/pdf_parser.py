"""Leitura e limpeza dos curriculos em PDF.

Codigo proprio de parsing (requisito do desafio): usa `pypdf` para extrair o
texto pagina a pagina e depois normaliza o resultado - remove cabecalhos e
rodapes repetidos, junta linhas quebradas e descobre o nome do aluno.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

# Rodapes/cabecalhos que se repetem em toda pagina e nao sao conteudo do curriculo.
_LINHAS_RUIDO = (
    re.compile(r"^\s*p[aá]gina\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d+\s*/\s*\d+\s*$"),
    re.compile(r"curriculo\s+ficticio.*p[aá]gina\s+\d+", re.IGNORECASE),
)

# Secoes que esperamos encontrar num curriculo (usadas pelo chunking).
SECOES_CONHECIDAS: dict[str, str] = {
    "dados pessoais": "Dados pessoais",
    "contato": "Dados pessoais",
    "resumo": "Resumo",
    "resumo profissional": "Resumo",
    "objetivo": "Resumo",
    "perfil": "Resumo",
    "experiencia": "Experiencias profissionais",
    "experiencias": "Experiencias profissionais",
    "experiencia profissional": "Experiencias profissionais",
    "experiencias profissionais": "Experiencias profissionais",
    "formacao": "Formacao academica",
    "formacao academica": "Formacao academica",
    "educacao": "Formacao academica",
    "habilidades": "Habilidades tecnicas",
    "habilidades tecnicas": "Habilidades tecnicas",
    "competencias": "Habilidades tecnicas",
    "conhecimentos": "Habilidades tecnicas",
    "idiomas": "Idiomas",
    "certificacoes": "Certificacoes",
    "cursos": "Cursos",
    "projetos": "Projetos",
}


@dataclass
class CurriculoBruto:
    """Um curriculo lido do disco, ja limpo mas ainda inteiro (sem chunking)."""

    nome_aluno: str
    arquivo: str
    texto: str
    paginas: int
    caminho: Path = field(repr=False, default=Path())

    @property
    def caracteres(self) -> int:
        return len(self.texto)


def normalizar(texto: str) -> str:
    """Minusculas, sem acento e sem espacos duplicados - para comparacoes."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def eh_cabecalho_de_secao(linha: str) -> str | None:
    """Devolve o nome canonico da secao se a linha for um titulo de secao.

    Reconhece tanto os titulos conhecidos (com ou sem acento) quanto linhas
    curtas totalmente em maiusculas, que e a convencao mais comum em curriculos.
    """
    bruta = linha.strip().rstrip(":").strip()
    if not bruta or len(bruta) > 60:
        return None

    chave = normalizar(bruta)
    if chave in SECOES_CONHECIDAS:
        return SECOES_CONHECIDAS[chave]

    # Heuristica generica: linha curta, toda em maiusculas, sem digitos e sem
    # pontuacao final - o formato tipico de titulo de secao em curriculos.
    # As restricoes evitam confundir com trechos de frase quebrados pelo PDF
    # (ex.: "2 TB." no meio de um paragrafo).
    letras = [c for c in bruta if c.isalpha()]
    if (
        len(letras) >= 4
        and all(c.isupper() for c in letras)
        and len(bruta.split()) <= 5
        and not any(c.isdigit() for c in bruta)
        and bruta[-1] not in ".,;"
    ):
        return bruta.title()
    return None


def _limpar_paginas(paginas: list[str]) -> str:
    """Remove ruido de rodape e o cabecalho repetido a partir da 2a pagina."""
    cabecalho_pagina1 = [ln.strip() for ln in paginas[0].splitlines()[:2] if ln.strip()] if paginas else []

    linhas_finais: list[str] = []
    for indice, pagina in enumerate(paginas):
        linhas = pagina.splitlines()
        if indice > 0:
            # Descarta o cabecalho (nome/cargo) que o gerador repete em toda pagina.
            while linhas and linhas[0].strip() in cabecalho_pagina1:
                linhas.pop(0)
        for linha in linhas:
            if any(padrao.search(linha) for padrao in _LINHAS_RUIDO):
                continue
            linhas_finais.append(linha.rstrip())

    texto = "\n".join(linhas_finais)
    texto = re.sub(r"[ \t]{2,}", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def extrair_texto(caminho: Path) -> tuple[str, int]:
    """Extrai o texto de um PDF. Devolve (texto_limpo, numero_de_paginas)."""
    leitor = PdfReader(str(caminho))
    paginas = [(pagina.extract_text() or "") for pagina in leitor.pages]
    return _limpar_paginas(paginas), len(leitor.pages)


def descobrir_nome_aluno(texto: str, caminho: Path) -> str:
    """Descobre o nome do aluno: campo 'Nome:', 1a linha do PDF ou nome do arquivo."""
    casamento = re.search(r"^\s*nome\s*:\s*(.+)$", texto, re.IGNORECASE | re.MULTILINE)
    if casamento:
        candidato = casamento.group(1).strip()
        if 2 <= len(candidato.split()) <= 6:
            return candidato

    for linha in texto.splitlines():
        linha = linha.strip()
        if 2 <= len(linha.split()) <= 6 and not eh_cabecalho_de_secao(linha):
            return linha

    return caminho.stem.replace("_", " ").replace("-", " ").title()


def ler_curriculo(caminho: Path) -> CurriculoBruto:
    texto, paginas = extrair_texto(caminho)
    if not texto.strip():
        raise ValueError(f"Nenhum texto extraido de {caminho.name} (PDF escaneado/imagem?)")
    return CurriculoBruto(
        nome_aluno=descobrir_nome_aluno(texto, caminho),
        arquivo=caminho.name,
        texto=texto,
        paginas=paginas,
        caminho=caminho,
    )


def listar_curriculos(pasta: Path) -> list[Path]:
    return sorted(p for p in pasta.glob("*.pdf") if p.is_file())


def ler_todos(pasta: Path) -> list[CurriculoBruto]:
    """Le todos os PDFs de uma pasta. PDFs com erro sao avisados, nao derrubam o lote."""
    curriculos: list[CurriculoBruto] = []
    for caminho in listar_curriculos(pasta):
        try:
            curriculos.append(ler_curriculo(caminho))
        except Exception as erro:  # noqa: BLE001 - um PDF ruim nao pode parar a ingestao
            print(f"  [aviso] falha ao ler {caminho.name}: {erro}")
    return curriculos
