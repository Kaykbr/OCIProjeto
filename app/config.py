"""Configuracao central da aplicacao.

Tudo vem de variavel de ambiente (carregada de um `.env` na raiz do projeto),
para que nenhuma chave precise ser commitada e para que o mesmo container
rode identico local e na instancia da OCI.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# override=False: variaveis ja exportadas no ambiente (o caso da OCI/Docker)
# tem precedencia sobre o .env local.
load_dotenv(BASE_DIR / ".env", override=False)


def _env(nome: str, default: str = "") -> str:
    """Le uma variavel de ambiente tratando string vazia como 'nao definida'."""
    valor = os.getenv(nome, "")
    return valor.strip() or default


def _dir(nome: str, default: str) -> Path:
    """Le um caminho de pasta; relativos sao resolvidos a partir da raiz do projeto."""
    bruto = Path(_env(nome, default))
    return bruto if bruto.is_absolute() else BASE_DIR / bruto


# --- Credenciais / modelos --------------------------------------------------
GEMINI_API_KEY: str = _env("GEMINI_API_KEY")

# Se vazios, `app.agent.gemini_client` descobre o melhor modelo disponivel na chave.
GEMINI_MODEL: str = _env("GEMINI_MODEL")
GEMINI_EMBEDDING_MODEL: str = _env("GEMINI_EMBEDDING_MODEL")

# Ordem de preferencia usada quando o modelo nao e fixado por env var.
#
# O Google aposenta nomes de modelo com frequencia: em ago/2026 o `gemini-2.5-flash`
# passou a responder 404 "no longer available to new users", apontando o
# `gemini-3.6-flash` como sucessor. Por isso a lista comeca pelos modelos atuais e
# mantem os antigos so como rede de seguranca para chaves mais velhas.
# Esta lista e tambem uma escada de sobrevivencia de cota, nao so de preferencia.
#
# Medido na pratica (ago/2026) no free tier do Gemini: cada modelo flash da
# ~20 requisicoes POR DIA, e a cota e contada POR MODELO. Uma demo publica esgota
# isso em poucas conversas. Por isso `chamar_com_retentativa` marca o modelo como
# esgotado ao receber um 429 "PerDay" e desce para o proximo da lista
# automaticamente - somando a cota de todos, a demo aguenta o dia.
#
# Os `-lite` ficam no fim: entregam menos qualidade, mas seguram o agente de pe
# quando os flash acabam. Para fixar um modelo, use GEMINI_MODEL no .env.
MODELOS_CHAT_PREFERIDOS: tuple[str, ...] = (
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
)
# `gemini-embedding-001` vem primeiro de proposito, mesmo nao sendo o mais novo:
# ele respeita o envio em lote (N textos -> N vetores), enquanto o
# `gemini-embedding-2` devolve so o primeiro vetor e obriga uma chamada por chunk.
# Com free tier isso e a diferenca entre 2 e 30 requisicoes por indexacao.
MODELOS_EMBEDDING_PREFERIDOS: tuple[str, ...] = (
    "gemini-embedding-001",
    "gemini-embedding-2",
    "text-embedding-004",
)

# --- Dados ------------------------------------------------------------------
CURRICULOS_DIR: Path = _dir("CURRICULOS_DIR", "data/curriculos")
CHROMA_DIR: Path = _dir("CHROMA_DIR", "data/chroma")
CHROMA_COLLECTION: str = _env("CHROMA_COLLECTION", "curriculos")

# Estado da aplicacao (PDIs gerados, validacoes do mentor) em arquivos JSON.
ESTADO_DIR: Path = _dir("ESTADO_DIR", "data/estado")

# Limite de tamanho para upload de curriculo pela interface.
UPLOAD_MAX_MB: float = float(_env("UPLOAD_MAX_MB", "10"))

VERSAO: str = "2.0.0"

# --- Retrieval --------------------------------------------------------------
TOP_K: int = int(_env("TOP_K", "6"))
CHUNK_TAMANHO: int = int(_env("CHUNK_TAMANHO", "900"))       # caracteres
CHUNK_SOBREPOSICAO: int = int(_env("CHUNK_SOBREPOSICAO", "150"))

# --- Servidor ---------------------------------------------------------------
PORT: int = int(_env("PORT", "8000"))

# Indexa os curriculos automaticamente na subida se a colecao estiver vazia.
# E o que faz `docker compose up` funcionar de primeira na OCI, sem passo manual.
AUTO_INDEXAR: bool = _env("AUTO_INDEXAR", "true").lower() in ("1", "true", "yes", "sim")

# Quantas iteracoes de function calling o orquestrador aceita antes de desistir.
MAX_ITERACOES_AGENTE: int = int(_env("MAX_ITERACOES_AGENTE", "6"))
