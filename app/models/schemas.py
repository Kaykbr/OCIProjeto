"""Contratos de entrada e saida da API (Pydantic v2).

Organizados por dominio: chat/agente, documentos, indice, PDI e validacoes.
Sao a fonte da verdade tanto para o FastAPI (validacao + OpenAPI) quanto para o
frontend, que consome exatamente estes campos.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Criticidade = Literal["alta", "media", "baixa"]
Veredito = Literal["aprovado", "ajustar", "rejeitado"]
Perfil = Literal["mentor", "aluno", "admin"]


# ---------------------------------------------------------------------------
# Chat / agente
# ---------------------------------------------------------------------------

class MensagemChat(BaseModel):
    """Uma mensagem do historico da conversa."""

    role: Literal["user", "assistant"]
    content: str


class PerguntaRequest(BaseModel):
    """Corpo do POST /api/chat."""

    pergunta: str = Field(min_length=2, max_length=4000, description="Pergunta do mentor.")
    historico: list[MensagemChat] = Field(
        default_factory=list,
        description="Mensagens anteriores da conversa, em ordem cronologica.",
        max_length=40,
    )


class FerramentaUsada(BaseModel):
    """Trilha de execucao: qual ferramenta o agente chamou e com quais argumentos."""

    nome: str
    argumentos: dict = Field(default_factory=dict)
    duracao_ms: int = 0
    resumo_resultado: str = ""


class RespostaChat(BaseModel):
    """Corpo da resposta do POST /api/chat."""

    resposta: str
    ferramentas: list[FerramentaUsada] = Field(default_factory=list)
    modelo: str = ""
    iteracoes: int = 0
    duracao_ms: int = 0


# ---------------------------------------------------------------------------
# Documentos (curriculos em PDF)
# ---------------------------------------------------------------------------

class SecaoDocumento(BaseModel):
    """Uma secao do curriculo, como o parser identificou."""

    nome: str
    texto: str
    caracteres: int = 0


class DocumentoInfo(BaseModel):
    """Metadados de um curriculo na base."""

    arquivo: str
    aluno: str = ""
    paginas: int = 0
    tamanho_kb: float = 0.0
    caracteres: int = 0
    indexado: bool = False
    chunks: int = 0
    atualizado_em: datetime | None = None


class DocumentoDetalhe(DocumentoInfo):
    """Documento com o conteudo extraido, para leitura na interface."""

    texto: str = ""
    secoes: list[SecaoDocumento] = Field(default_factory=list)


class Aluno(BaseModel):
    """Um aluno com curriculo indexado."""

    nome: str
    chunks: int = 0
    arquivo: str = ""
    secoes: list[str] = Field(default_factory=list)
    pdis: int = 0


# ---------------------------------------------------------------------------
# Indice / administracao
# ---------------------------------------------------------------------------

class ResultadoIndexacao(BaseModel):
    """Retorno de uma operacao de indexacao."""

    arquivos: int = 0
    chunks: int = 0
    alunos: list[str] = Field(default_factory=list)
    duracao_s: float = 0.0
    avisos: list[str] = Field(default_factory=list)


class EstatisticasIndice(BaseModel):
    """Panorama do vector store, para o painel admin."""

    total_chunks: int = 0
    total_alunos: int = 0
    total_documentos: int = 0
    chunks_por_aluno: dict[str, int] = Field(default_factory=dict)
    chunks_por_secao: dict[str, int] = Field(default_factory=dict)
    documentos_nao_indexados: list[str] = Field(default_factory=list)
    colecao: str = ""
    caminho: str = ""
    modelo_embedding: str = ""


class StatusApp(BaseModel):
    """Diagnostico do GET /api/status - o que a interface mostra no cabecalho."""

    pronto: bool
    chave_configurada: bool
    chunks_indexados: int
    alunos: list[str] = Field(default_factory=list)
    documentos: int = 0
    pdis: int = 0
    validacoes_pendentes: int = 0
    modelo_chat: str = ""
    modelo_embedding: str = ""
    aviso: str = ""
    versao: str = ""


# ---------------------------------------------------------------------------
# PDI estruturado (o que alimenta os graficos)
# ---------------------------------------------------------------------------

class HabilidadeAtual(BaseModel):
    """Habilidade que o aluno ja tem e serve para a vaga-alvo."""

    nome: str
    evidencia: str = Field(default="", description="Trecho do curriculo que comprova.")
    nivel: int = Field(default=50, ge=0, le=100, description="Dominio atual estimado, 0 a 100.")
    relevancia_para_vaga: int = Field(default=50, ge=0, le=100)


class GapPDI(BaseModel):
    """Requisito da vaga que o curriculo nao cobre."""

    nome: str
    criticidade: Criticidade = "media"
    justificativa: str = ""
    nivel_atual: int = Field(default=0, ge=0, le=100)
    nivel_alvo: int = Field(default=80, ge=0, le=100)


class AcaoPDI(BaseModel):
    """Acao concreta recomendada para fechar um gap."""

    titulo: str
    descricao: str = ""
    gap_relacionado: str = ""
    esforco_horas: int = Field(default=20, ge=1, le=1000)
    ordem: int = 1


class BlocoCronograma(BaseModel):
    """Um bloco do prazo sugerido."""

    bloco: str
    periodo: str = ""
    objetivos: list[str] = Field(default_factory=list)
    marco: str = ""


class PDIEstruturado(BaseModel):
    """PDI completo, em formato que a interface consegue desenhar."""

    id: str = ""
    aluno: str
    vaga_alvo: str
    resumo: str = ""
    aderencia: int = Field(default=0, ge=0, le=100, description="Aderencia do perfil a vaga, 0 a 100.")
    prazo_total_meses: int = Field(default=6, ge=1, le=36)
    habilidades_atuais: list[HabilidadeAtual] = Field(default_factory=list)
    gaps: list[GapPDI] = Field(default_factory=list)
    acoes: list[AcaoPDI] = Field(default_factory=list)
    cronograma: list[BlocoCronograma] = Field(default_factory=list)
    criado_em: datetime | None = None
    modelo: str = ""


class PDIRequest(BaseModel):
    """Corpo do POST /api/pdi."""

    nome_aluno: str = Field(min_length=2, max_length=120)
    vaga_alvo: str = Field(min_length=3, max_length=600)
    forcar_regeracao: bool = Field(
        default=False,
        description="Ignora o PDI ja salvo para essa combinacao aluno + vaga e gera de novo.",
    )


class PDIResumo(BaseModel):
    """Item da listagem de PDIs."""

    id: str
    aluno: str
    vaga_alvo: str
    aderencia: int = 0
    gaps: int = 0
    acoes: int = 0
    criado_em: datetime | None = None


# ---------------------------------------------------------------------------
# Validacoes do mentor
# ---------------------------------------------------------------------------

class ValidacaoRequest(BaseModel):
    """O mentor avalia uma resposta do agente."""

    pergunta: str = Field(min_length=2, max_length=4000)
    resposta: str = Field(min_length=1, max_length=40000)
    veredito: Veredito = "aprovado"
    observacao: str = Field(default="", max_length=2000)
    aluno: str = ""
    ferramentas: list[str] = Field(default_factory=list)


class AtualizarValidacao(BaseModel):
    """Muda o veredito ou a observacao de uma validacao ja registrada."""

    veredito: Veredito | None = None
    observacao: str | None = Field(default=None, max_length=2000)


class Validacao(ValidacaoRequest):
    """Validacao persistida."""

    id: str
    criado_em: datetime
    atualizado_em: datetime | None = None
