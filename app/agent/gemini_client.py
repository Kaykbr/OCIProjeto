"""Cliente do Google Gemini e declaracao das ferramentas (function calling).

Responsabilidades deste modulo:

* criar (uma unica vez) o `genai.Client` a partir da GEMINI_API_KEY;
* descobrir quais modelos a chave realmente tem disponiveis, para o projeto nao
  quebrar quando o Google aposenta um nome de modelo (pode ser fixado por env);
* declarar o schema das 4 ferramentas que o agente pode chamar;
* guardar a instrucao de sistema que define o comportamento do mentor.

A implementacao das ferramentas fica em `app/agent/tools.py`; o loop que
conecta modelo e ferramentas fica em `app/agent/orchestrator.py`.
"""

from __future__ import annotations

import logging
import re
import time
from functools import lru_cache
from typing import Callable, TypeVar

from google import genai
from google.genai import types

from app import config

logger = logging.getLogger(__name__)

T = TypeVar("T")

_client: genai.Client | None = None

ERRO_SEM_CHAVE = (
    "GEMINI_API_KEY nao configurada. Crie um arquivo .env na raiz do projeto "
    "(copie de .env.example) com a chave obtida em https://aistudio.google.com/apikey, "
    "ou exporte a variavel de ambiente antes de subir o container."
)


def obter_client() -> genai.Client:
    """Devolve o client Gemini (singleton). Levanta erro claro se faltar a chave."""
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError(ERRO_SEM_CHAVE)
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


@lru_cache(maxsize=1)
def _modelos_disponiveis() -> dict[str, set[str]]:
    """Mapeia nome-base do modelo -> acoes suportadas, consultando a API.

    Falha de rede aqui nao pode derrubar o app: devolvemos vazio e o chamador
    cai no primeiro nome da lista de preferencia.
    """
    try:
        catalogo: dict[str, set[str]] = {}
        for modelo in obter_client().models.list():
            nome = (modelo.name or "").removeprefix("models/")
            if nome:
                catalogo[nome] = set(modelo.supported_actions or [])
        return catalogo
    except Exception as erro:  # noqa: BLE001 - diagnostico, nunca fatal
        logger.warning("Nao foi possivel listar modelos do Gemini (%s). Usando o default.", erro)
        return {}


def _escolher(preferidos: tuple[str, ...], acao: str) -> str:
    catalogo = _modelos_disponiveis()
    for nome in preferidos:
        acoes = catalogo.get(nome)
        if acoes is not None and (not acoes or acao in acoes):
            return nome
    return preferidos[0]


# Modelos cuja cota DIARIA do free tier ja acabou nesta execucao. A cota do
# Gemini e por dia E por modelo, entao trocar de modelo devolve o agente ao ar.
_modelos_esgotados: set[str] = set()
_modelo_chat_atual: str | None = None


def modelo_chat() -> str:
    """Modelo usado para conversar e chamar ferramentas."""
    global _modelo_chat_atual

    if config.GEMINI_MODEL and config.GEMINI_MODEL not in _modelos_esgotados:
        return config.GEMINI_MODEL

    if _modelo_chat_atual and _modelo_chat_atual not in _modelos_esgotados:
        return _modelo_chat_atual

    candidatos = [m for m in config.MODELOS_CHAT_PREFERIDOS if m not in _modelos_esgotados]
    if not candidatos:
        # Todos esgotados: volta para o primeiro e deixa o erro chegar ao usuario.
        _modelos_esgotados.clear()
        candidatos = list(config.MODELOS_CHAT_PREFERIDOS)

    _modelo_chat_atual = _escolher(tuple(candidatos), "generateContent")
    logger.info("Modelo de chat selecionado: %s", _modelo_chat_atual)
    return _modelo_chat_atual


def marcar_modelo_esgotado(nome: str) -> str | None:
    """Registra que a cota diaria do modelo acabou e devolve o substituto, se houver."""
    if not nome or nome in _modelos_esgotados:
        return None
    _modelos_esgotados.add(nome)
    restantes = [m for m in config.MODELOS_CHAT_PREFERIDOS if m not in _modelos_esgotados]
    if not restantes:
        return None
    global _modelo_chat_atual
    _modelo_chat_atual = None
    substituto = modelo_chat()
    logger.warning("Cota diaria de '%s' esgotada. Trocando para '%s'.", nome, substituto)
    return substituto


@lru_cache(maxsize=1)
def modelo_embedding() -> str:
    """Modelo usado para gerar embeddings dos chunks e das perguntas."""
    if config.GEMINI_EMBEDDING_MODEL:
        return config.GEMINI_EMBEDDING_MODEL
    escolhido = _escolher(config.MODELOS_EMBEDDING_PREFERIDOS, "embedContent")
    logger.info("Modelo de embedding selecionado: %s", escolhido)
    return escolhido


# ---------------------------------------------------------------------------
# Instrucao de sistema
# ---------------------------------------------------------------------------

INSTRUCAO_SISTEMA = """
Voce e o Agente Mentor de Carreiras, o assistente interno de uma equipe de mentoria.
Quem conversa com voce e um MENTOR (nao o aluno), que acompanha varios alunos e
precisa de respostas rapidas e fundamentadas nos curriculos que estao indexados.

REGRAS DE OURO
1. Toda afirmacao sobre um aluno precisa vir dos curriculos. Voce nao conhece
   nenhum aluno de memoria: SEMPRE use uma ferramenta antes de responder sobre
   dados, habilidades, experiencia, formacao ou idiomas de alguem.
2. Nunca invente experiencia, empresa, certificacao ou tecnologia que nao esteja
   no material recuperado. Se a informacao nao existir, diga com todas as letras
   que o curriculo nao traz esse dado e sugira o que perguntar ao aluno.
3. Se a pergunta envolver dois ou mais alunos, chame a ferramenta uma vez para
   CADA aluno antes de comparar.
4. Se o mentor nao disser de qual aluno esta falando, pergunte antes de agir.

QUAL FERRAMENTA USAR
- buscar_info_aluno: perguntas factuais sobre o que esta no curriculo
  ("quais as habilidades de X?", "quanto tempo de experiencia tem Y?").
- gerar_curriculo_padronizado: quando pedirem o curriculo formatado/padronizado de alguem.
- gerar_pdi: quando pedirem plano de desenvolvimento, plano de estudos ou
  "o que falta para o aluno chegar na vaga Z".
- sugerir_projetos: quando pedirem ideias de projeto pratico ou portfolio.

ESTILO
- Responda em portugues do Brasil, direto ao ponto, em markdown.
- Use listas e subtitulos quando ajudar a leitura; evite paragrafos gigantes.
- Seja concreto e acionavel: o mentor vai levar isso para uma conversa de 1:1.
- Distinga claramente o que veio do curriculo do que e recomendacao sua.
""".strip()


# ---------------------------------------------------------------------------
# Declaracao das ferramentas (o que o modelo enxerga)
# ---------------------------------------------------------------------------

def _texto(descricao: str) -> types.Schema:
    return types.Schema(type=types.Type.STRING, description=descricao)


DECLARACOES_FERRAMENTAS: list[types.FunctionDeclaration] = [
    types.FunctionDeclaration(
        name="buscar_info_aluno",
        description=(
            "Busca informacoes no curriculo de UM aluno especifico e responde a uma "
            "pergunta factual sobre ele (habilidades, experiencias, formacao, idiomas, "
            "tempo de carreira, objetivos). Use sempre que a resposta depender do que "
            "esta escrito no curriculo. Para comparar dois alunos, chame uma vez por aluno."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "nome_aluno": _texto("Nome do aluno como o mentor escreveu, ex.: 'Carlos Andrade'."),
                "pergunta": _texto(
                    "A pergunta especifica a ser respondida sobre esse aluno, "
                    "reescrita de forma autocontida."
                ),
            },
            required=["nome_aluno", "pergunta"],
        ),
    ),
    types.FunctionDeclaration(
        name="gerar_curriculo_padronizado",
        description=(
            "Reescreve o curriculo do aluno no template padrao da mentoria "
            "(Dados pessoais / Resumo profissional / Experiencias / Formacao / "
            "Habilidades / Idiomas). Use quando pedirem o curriculo padronizado, "
            "formatado ou 'no modelo da equipe'."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={"nome_aluno": _texto("Nome do aluno, ex.: 'Fernanda Lima'.")},
            required=["nome_aluno"],
        ),
    ),
    types.FunctionDeclaration(
        name="gerar_pdi",
        description=(
            "Monta um Plano de Desenvolvimento Individual (PDI) comparando o perfil "
            "atual do aluno com uma vaga-alvo: habilidades atuais, gaps, acoes "
            "recomendadas e prazo sugerido. Use quando pedirem plano de "
            "desenvolvimento, plano de estudos ou o caminho ate uma vaga."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "nome_aluno": _texto("Nome do aluno, ex.: 'Pedro Souza'."),
                "vaga_alvo": _texto(
                    "Descricao da vaga-alvo em texto livre, o mais fiel possivel ao que o "
                    "mentor disse, ex.: 'Desenvolvedor Full Stack Pleno com React e Node.js'."
                ),
            },
            required=["nome_aluno", "vaga_alvo"],
        ),
    ),
    types.FunctionDeclaration(
        name="sugerir_projetos",
        description=(
            "Sugere 3 projetos praticos de portfolio que fecham os gaps do aluno, cada "
            "um com objetivo, tecnologias e nivel de dificuldade. Use quando pedirem "
            "ideias de projeto, exercicios praticos ou o que construir para evoluir."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "nome_aluno": _texto("Nome do aluno, ex.: 'Ana Beatriz'."),
                "vaga_alvo": _texto(
                    "Vaga ou objetivo de carreira, se o mentor mencionar. "
                    "Pode ficar vazio, ex.: 'SDET'."
                ),
            },
            required=["nome_aluno"],
        ),
    ),
]

FERRAMENTAS_GEMINI = [types.Tool(function_declarations=DECLARACOES_FERRAMENTAS)]


TENTATIVAS_PADRAO = 4


def _e_falha_temporaria(erro: Exception) -> bool:
    """Distingue 'tente de novo daqui a pouco' de 'nao adianta insistir'.

    O free tier do Gemini limita requisicoes por minuto (429) e o modelo as
    vezes fica sobrecarregado (503). Os dois passam. Ja credito esgotado,
    chave invalida e modelo aposentado nao passam com retentativa.
    """
    texto = str(erro)
    if "503" in texto or "UNAVAILABLE" in texto:
        return True
    if "429" in texto or "RESOURCE_EXHAUSTED" in texto:
        if "prepayment" in texto or "billing" in texto.lower():
            return False
        # Cota DIARIA esgotada nao volta em segundos: insistir so gasta tempo.
        return "PerDay" not in texto
    return False


def _espera_sugerida(erro: Exception, tentativa: int) -> float:
    """Usa o retryDelay que a propria API manda; senao, espera exponencial."""
    texto = str(erro)
    for padrao in (r"retry in ([\d.]+)s", r"'retryDelay': '(\d+)s'"):
        casamento = re.search(padrao, texto)
        if casamento:
            return min(float(casamento.group(1)) + 1.0, 65.0)
    return float(min(2 ** tentativa, 32))


def chamar_com_retentativa(funcao: Callable[[], T], tentativas: int = TENTATIVAS_PADRAO) -> T:
    """Executa uma chamada ao Gemini reagindo a limite de cadencia e sobrecarga.

    E o que mantem a demo de pe no free tier: sem isso, duas perguntas seguidas
    ja estouram o limite de 5 requisicoes por minuto e o mentor ve um erro.
    """
    for tentativa in range(1, tentativas + 1):
        try:
            return funcao()
        except Exception as erro:  # noqa: BLE001
            # Cota diaria estourada: nao adianta esperar, mas trocar de modelo
            # resolve, porque a cota do free tier e contada por modelo.
            if "PerDay" in str(erro) and marcar_modelo_esgotado(modelo_chat()):
                continue
            if not _e_falha_temporaria(erro) or tentativa == tentativas:
                raise
            espera = _espera_sugerida(erro, tentativa)
            logger.warning(
                "Gemini indisponivel/limitado (tentativa %s/%s). Repetindo em %.0fs.",
                tentativa, tentativas, espera,
            )
            time.sleep(espera)
    raise RuntimeError("Retentativas esgotadas.")  # pragma: no cover


def traduzir_erro_gemini(erro: Exception) -> str:
    """Transforma um erro da API do Gemini em algo que o mentor consiga agir.

    As falhas mais comuns em demo sao de conta, nao de codigo: chave sem creditos
    e nome de modelo aposentado. Sem essa traducao, as duas viram um 500 opaco.
    """
    texto = str(erro)

    if "429" in texto or "RESOURCE_EXHAUSTED" in texto:
        if "prepayment credits" in texto or "billing" in texto.lower():
            return (
                "A chave do Gemini esta sem creditos. Abra https://ai.studio/projects, "
                "confira o faturamento do projeto ou gere uma chave nova num projeto "
                "com free tier, e atualize a GEMINI_API_KEY."
            )
        if "PerDay" in texto:
            modelo = ""
            casamento = re.search(r"model: ([\w.\-]+)", texto)
            if casamento:
                modelo = f" do modelo '{casamento.group(1)}'"
            return (
                f"A cota diaria gratuita{modelo} acabou. A cota do free tier e por dia E "
                "por modelo: defina outro em GEMINI_MODEL no .env (ex.: gemini-3.5-flash "
                "ou gemini-flash-lite-latest) e reinicie, ou espere a virada do dia."
            )
        return (
            "Limite de requisicoes por minuto do Gemini atingido. Espere alguns "
            "instantes e pergunte de novo."
        )

    if "404" in texto and ("no longer available" in texto or "not found" in texto.lower()):
        sugerido = ""
        marcador = "use models/"
        if marcador in texto:
            sugerido = texto.split(marcador, 1)[1].split()[0].strip(" .'\"")
        return (
            f"O modelo configurado nao existe mais para essa chave. "
            + (f"O Google sugere '{sugerido}'. " if sugerido else "")
            + "Defina GEMINI_MODEL no .env com um modelo disponivel "
            "(veja a lista com: python scripts/checar_modelos.py)."
        )

    if "401" in texto or "403" in texto or "API_KEY_INVALID" in texto:
        return (
            "A chave do Gemini foi recusada (invalida ou sem permissao). "
            "Gere outra em https://aistudio.google.com/apikey e atualize o .env."
        )

    return f"Falha ao falar com a API do Gemini: {texto[:300]}"


def configuracao_geracao() -> types.GenerateContentConfig:
    """Config do turno de conversa: ferramentas ligadas, chamada manual das funcoes.

    `automatic_function_calling.disable=True` porque quem executa a funcao e o
    nosso orquestrador - o requisito do desafio e ter esse loop explicito.
    """
    return types.GenerateContentConfig(
        system_instruction=INSTRUCAO_SISTEMA,
        tools=FERRAMENTAS_GEMINI,
        temperature=0.3,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode=types.FunctionCallingConfigMode.AUTO)
        ),
    )
