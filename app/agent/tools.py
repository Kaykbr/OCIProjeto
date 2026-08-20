"""Implementacao das 4 ferramentas que o agente pode chamar.

Todas seguem o mesmo contrato: recebem argumentos simples (strings), consultam
o vector store e devolvem texto. Nenhuma delas inventa dado de aluno - o que
nao estiver no curriculo indexado nao aparece na resposta.

Duas familias de ferramenta:

* `buscar_info_aluno` e uma ferramenta de RECUPERACAO: devolve os trechos
  relevantes do curriculo e deixa a sintese com o modelo orquestrador. Isso
  economiza uma chamada de LLM por pergunta e permite que o proprio agente
  cruze informacao de dois alunos numa unica resposta.
* `gerar_curriculo_padronizado`, `gerar_pdi` e `sugerir_projetos` sao
  ferramentas de GERACAO: montam um prompt especializado com o curriculo
  inteiro do aluno e fazem sua propria chamada ao Gemini, porque cada uma tem
  um formato de saida rigido para respeitar.
"""

from __future__ import annotations

import logging
from typing import Callable

from google.genai import types

from app import config
from app.agent.gemini_client import chamar_com_retentativa, modelo_chat, obter_client
from app.retrieval.vector_store import AlunoNaoEncontrado, Trecho, obter_store

logger = logging.getLogger(__name__)

TEMPLATE_CURRICULO = """\
Dados pessoais
Resumo profissional
Experiencias profissionais
Formacao academica
Habilidades tecnicas
Idiomas"""


# ---------------------------------------------------------------------------
# Apoio
# ---------------------------------------------------------------------------

def _formatar_trechos(trechos: list[Trecho]) -> str:
    partes = []
    for numero, trecho in enumerate(trechos, start=1):
        partes.append(
            f"[Trecho {numero} | {trecho.aluno} | secao: {trecho.secao} | "
            f"fonte: {trecho.arquivo} | similaridade: {trecho.similaridade:.2f}]\n{trecho.texto}"
        )
    return "\n\n".join(partes)


def _chamar_llm(prompt: str, temperatura: float = 0.4) -> str:
    """Chamada simples ao Gemini, sem ferramentas (usada pelas tools de geracao)."""
    resposta = chamar_com_retentativa(
        lambda: obter_client().models.generate_content(
            model=modelo_chat(),
            contents=prompt,
            config=types.GenerateContentConfig(temperature=temperatura),
        )
    )
    return (resposta.text or "").strip()


def _curriculo_ou_erro(nome_aluno: str) -> tuple[str, str]:
    """Resolve o nome e devolve (nome_oficial, texto_do_curriculo)."""
    store = obter_store()
    nome_oficial = store.resolver_aluno(nome_aluno)
    curriculo = store.curriculo_completo(nome_oficial)
    if not curriculo:
        raise AlunoNaoEncontrado(f"O curriculo de {nome_oficial} esta indexado mas veio vazio.")
    return nome_oficial, curriculo


# ---------------------------------------------------------------------------
# Ferramenta 1 - busca no curriculo
# ---------------------------------------------------------------------------

def buscar_info_aluno(nome_aluno: str, pergunta: str) -> str:
    """Busca no vector store (filtrado por aluno) e devolve os trechos recuperados."""
    store = obter_store()
    nome_oficial = store.resolver_aluno(nome_aluno)
    trechos = store.buscar(pergunta, aluno=nome_oficial, top_k=config.TOP_K)

    if not trechos:
        return (
            f"Nenhum trecho do curriculo de {nome_oficial} respondeu a '{pergunta}'. "
            "Informe ao mentor que esse dado nao consta no curriculo."
        )

    return (
        f"Trechos recuperados do curriculo de {nome_oficial} para a pergunta "
        f"'{pergunta}'. Responda SOMENTE com base neles:\n\n{_formatar_trechos(trechos)}"
    )


# ---------------------------------------------------------------------------
# Ferramenta 2 - curriculo padronizado
# ---------------------------------------------------------------------------

def gerar_curriculo_padronizado(nome_aluno: str) -> str:
    """Reestrutura os dados do aluno no template fixo da mentoria."""
    nome_oficial, curriculo = _curriculo_ou_erro(nome_aluno)

    prompt = f"""Voce e um especialista em curriculos tecnicos. Reescreva o curriculo abaixo
no template padrao da mentoria, sem inventar absolutamente nada.

TEMPLATE (use exatamente estas secoes, nesta ordem, como titulos de nivel 2 em markdown):
{TEMPLATE_CURRICULO}

REGRAS
- Use apenas informacoes presentes no material. Nao acrescente empresas, tecnologias,
  certificacoes, datas ou numeros que nao estejam la.
- Se uma secao nao tiver informacao, escreva "Nao informado no curriculo original".
- No "Resumo profissional", escreva 3 a 4 linhas em terceira pessoa, destacando
  senioridade, principais tecnologias e objetivo de carreira.
- Em "Experiencias profissionais", mantenha ordem cronologica inversa e use o formato
  "**Cargo** - Empresa (periodo)" seguido de bullets de realizacao. Preserve os numeros
  e metricas que existirem.
- Em "Habilidades tecnicas", agrupe por categoria (linguagens, frameworks, bancos,
  ferramentas) e preserve os niveis declarados.
- Nao escreva nenhum comentario antes ou depois do curriculo.

MATERIAL DO ALUNO ({nome_oficial}):
{curriculo}"""

    return _chamar_llm(prompt, temperatura=0.25)


# ---------------------------------------------------------------------------
# Ferramenta 3 - PDI
# ---------------------------------------------------------------------------

def gerar_pdi(nome_aluno: str, vaga_alvo: str) -> str:
    """Compara o perfil do aluno com a vaga-alvo e monta o PDI."""
    nome_oficial, curriculo = _curriculo_ou_erro(nome_aluno)

    prompt = f"""Voce e um mentor de carreiras senior em tecnologia. Monte um Plano de
Desenvolvimento Individual (PDI) para {nome_oficial} mirando a vaga-alvo abaixo.

VAGA-ALVO: {vaga_alvo}

ESTRUTURA OBRIGATORIA. Copie os quatro titulos abaixo EXATAMENTE como estao
escritos - mesma grafia, sem numerar, sem acrescentar parenteses e sem trocar por
sinonimos. Nao crie nenhum outro titulo de nivel 2:

## Habilidades atuais
## Gaps identificados
## Acoes recomendadas
## Prazo sugerido

O que entra em cada um:
- Habilidades atuais: o que o aluno JA tem que serve para essa vaga. Cite a
  evidencia do curriculo (experiencia, projeto, formacao) ao lado de cada item.
- Gaps identificados: o que a vaga exige e o curriculo nao mostra. Ordene do mais
  critico ao menos critico e explique em uma linha por que importa para a vaga.
- Acoes recomendadas: acoes concretas e verificaveis (curso especifico, projeto
  pratico, certificacao, pedir uma tarefa nova no trabalho atual). Uma acao por
  gap critico, na ordem em que devem ser feitas.
- Prazo sugerido: cronograma realista dividido por blocos (ex.: mes 1-2, mes 3-4,
  mes 5-6), dizendo o que deve estar concluido ao fim de cada bloco e qual o marco
  de saida do plano. Aqui subtitulos de nivel 3 por bloco sao bem-vindos.

REGRAS
- Baseie as "Habilidades atuais" exclusivamente no material do aluno; nao presuma
  conhecimento que nao esta escrito.
- Se o curriculo declarar explicitamente uma ausencia (ex.: "sem experiencia com cloud"),
  isso e um gap, nao uma habilidade.
- Seja especifico: "estudar Node.js" e ruim; "construir uma API REST em Express com
  autenticacao JWT e testes" e bom.
- Considere o ponto de partida real do aluno ao definir o prazo.

MATERIAL DO ALUNO ({nome_oficial}):
{curriculo}"""

    return _chamar_llm(prompt, temperatura=0.4)


# ---------------------------------------------------------------------------
# Ferramenta 4 - projetos praticos
# ---------------------------------------------------------------------------

def sugerir_projetos(nome_aluno: str, vaga_alvo: str = "") -> str:
    """Sugere 3 projetos praticos que fecham os gaps do aluno."""
    nome_oficial, curriculo = _curriculo_ou_erro(nome_aluno)
    alvo = vaga_alvo.strip() or "o objetivo de carreira declarado no proprio curriculo"

    prompt = f"""Voce e um mentor de carreiras senior em tecnologia. Sugira exatamente 3
projetos praticos de portfolio para {nome_oficial}, considerando o alvo: {alvo}.

Para CADA projeto use este formato (titulo de nivel 3 em markdown):
### N. Nome do projeto
- **Objetivo:** que gap especifico do aluno esse projeto fecha e o que ele prova para um recrutador.
- **Tecnologias:** stack concreta, comecando pelo que o aluno ja domina e acrescentando o que ele precisa aprender.
- **Nivel de dificuldade:** Iniciante, Intermediario ou Avancado (relativo ao nivel atual do aluno) + estimativa de esforco.
- **Entregavel:** o que precisa existir no repositorio para o projeto contar como concluido.

REGRAS
- Os 3 projetos devem ter dificuldade crescente e cobrir gaps diferentes.
- Aproveite o contexto de dominio que o aluno ja conhece (fintech, varejo, saude...)
  para propor algo com cara de mundo real, e nao um to-do list generico.
- Nao proponha projeto que exija tecnologia paga ou infraestrutura cara.
- Nada de texto de abertura ou encerramento: comece direto no primeiro projeto.

MATERIAL DO ALUNO ({nome_oficial}):
{curriculo}"""

    return _chamar_llm(prompt, temperatura=0.6)


# ---------------------------------------------------------------------------
# Registro / despacho
# ---------------------------------------------------------------------------

FERRAMENTAS: dict[str, Callable[..., str]] = {
    "buscar_info_aluno": buscar_info_aluno,
    "gerar_curriculo_padronizado": gerar_curriculo_padronizado,
    "gerar_pdi": gerar_pdi,
    "sugerir_projetos": sugerir_projetos,
}


def executar_ferramenta(nome: str, argumentos: dict) -> str:
    """Executa uma ferramenta pelo nome, convertendo falhas em texto para o modelo.

    O modelo precisa receber o erro como resultado (e nao como excecao) para
    conseguir se recuperar - por exemplo, pedindo o nome completo do aluno.
    """
    funcao = FERRAMENTAS.get(nome)
    if funcao is None:
        return f"ERRO: ferramenta '{nome}' nao existe. Disponiveis: {', '.join(FERRAMENTAS)}."

    try:
        return funcao(**argumentos)
    except AlunoNaoEncontrado as erro:
        logger.info("Aluno nao resolvido em %s: %s", nome, erro)
        return f"ERRO_ALUNO: {erro}"
    except TypeError as erro:
        logger.warning("Argumentos invalidos para %s: %s", nome, erro)
        return f"ERRO: argumentos invalidos para '{nome}': {erro}"
    except Exception as erro:  # noqa: BLE001 - falha de ferramenta nao pode derrubar o chat
        logger.exception("Falha ao executar %s", nome)
        return f"ERRO: a ferramenta '{nome}' falhou: {erro}"
