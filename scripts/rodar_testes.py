"""Roda o roteiro de testes (tests/test_agent_manual.md) contra o agente de verdade.

Alem de imprimir tudo no terminal, o script:

* salva a transcricao completa em `tests/resultados_execucao.md`;
* injeta os exemplos no README.md, entre os marcadores
  <!-- INICIO_EXEMPLOS --> e <!-- FIM_EXEMPLOS -->.

Assim os exemplos do README sao sempre respostas reais do agente, nunca escritas a mao.

Uso:
    python scripts/rodar_testes.py               # roda os 5 casos principais
    python scripts/rodar_testes.py --com-bordas  # inclui os casos de borda
    python scripts/rodar_testes.py --sem-readme  # nao mexe no README
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# No Windows o console usa cp1252 por padrao e quebra ao imprimir emoji/simbolos
# que o modelo devolve. Forcamos UTF-8 na saida para o script rodar igual em
# qualquer terminal (e quando a saida e redirecionada para arquivo).
for _fluxo in (sys.stdout, sys.stderr):
    if hasattr(_fluxo, "reconfigure"):
        _fluxo.reconfigure(encoding="utf-8", errors="replace")


from app import config  # noqa: E402
from app.agent.gemini_client import ERRO_SEM_CHAVE  # noqa: E402
from app.agent.orchestrator import responder  # noqa: E402
from app.retrieval.vector_store import obter_store  # noqa: E402

MARCADOR_INICIO = "<!-- INICIO_EXEMPLOS -->"
MARCADOR_FIM = "<!-- FIM_EXEMPLOS -->"

CASOS: list[tuple[str, str]] = [
    ("Quais sao as principais habilidades tecnicas do Carlos Andrade?", "buscar_info_aluno"),
    ("Gere o curriculo padronizado da Fernanda Lima.", "gerar_curriculo_padronizado"),
    (
        "Monte um PDI para o Pedro Souza mirando uma vaga de Desenvolvedor Full Stack "
        "Pleno, com React e Node.js.",
        "gerar_pdi",
    ),
    ("Quais projetos voce sugere para a Ana Beatriz evoluir para SDET?", "sugerir_projetos"),
    ("Compare a experiencia de Carlos e Fernanda em relacao a dados.", "buscar_info_aluno (2x)"),
]

CASOS_BORDA: list[tuple[str, str]] = [
    ("Fale sobre o Carlos.", "buscar_info_aluno (resolve nome parcial)"),
    ("Quais as habilidades do Joao Silva?", "erro tratado: aluno inexistente"),
    ("Monte um PDI.", "nenhuma: deve perguntar de qual aluno"),
    ("O Carlos tem certificacao AWS?", "buscar_info_aluno (deve dizer que nao consta)"),
]


def _formatar_chamada(passo) -> str:
    argumentos = ", ".join(f"{chave}={valor!r}" for chave, valor in passo.argumentos.items())
    return f"`{passo.nome}({argumentos})` — {passo.duracao_ms} ms"


def executar(casos: list[tuple[str, str]], pausa: float = 0.0) -> list[dict]:
    resultados = []
    for numero, (pergunta, esperado) in enumerate(casos, start=1):
        # O free tier limita requisicoes por minuto e cada caso faz mais de uma
        # chamada (orquestrador + ferramenta): sem pausa, o roteiro estoura sozinho.
        if numero > 1 and pausa > 0:
            print(f"\n(aguardando {pausa:.0f}s para respeitar o limite por minuto)")
            time.sleep(pausa)
        print(f"\n{'=' * 78}\n[{numero}/{len(casos)}] {pergunta}\n{'-' * 78}")
        inicio = time.perf_counter()
        try:
            resposta = responder(pergunta)
            texto, ferramentas, erro = resposta.texto, resposta.ferramentas, ""
        except Exception as falha:  # noqa: BLE001 - queremos o relatorio mesmo com erro
            texto, ferramentas, erro = "", [], str(falha)
            print(f"FALHOU: {falha}")

        duracao = time.perf_counter() - inicio
        for passo in ferramentas:
            print(f"  -> {passo.nome}({passo.argumentos})  {passo.duracao_ms} ms")
        if texto:
            print(f"\n{texto}\n\n({duracao:.1f}s)")

        resultados.append(
            {
                "numero": numero,
                "pergunta": pergunta,
                "esperado": esperado,
                "texto": texto,
                "ferramentas": ferramentas,
                "duracao": duracao,
                "erro": erro,
            }
        )
    return resultados


def montar_markdown(resultados: list[dict], modelo: str) -> str:
    agora = datetime.now().strftime("%d/%m/%Y as %H:%M")
    linhas = [
        f"> Respostas reais do agente, capturadas em {agora} com o modelo `{modelo}`.",
        "> Reproduza com `python scripts/rodar_testes.py`.",
        "",
    ]

    for item in resultados:
        linhas.append(f"### {item['numero']}. {item['pergunta']}")
        linhas.append("")
        if item["erro"]:
            linhas += [f"**Falhou:** `{item['erro']}`", ""]
            continue

        if item["ferramentas"]:
            linhas.append("**Ferramentas acionadas pelo agente:**")
            linhas.append("")
            linhas += [f"- {_formatar_chamada(passo)}" for passo in item["ferramentas"]]
        else:
            linhas.append("**Ferramentas acionadas pelo agente:** nenhuma (resposta direta).")
        linhas.append("")
        linhas.append("**Resposta:**")
        linhas.append("")
        linhas += [f"> {linha}" if linha.strip() else ">" for linha in item["texto"].splitlines()]
        linhas += ["", f"*Tempo total: {item['duracao']:.1f}s*", ""]

    return "\n".join(linhas)


def injetar_no_readme(markdown: str, readme: Path) -> bool:
    if not readme.exists():
        return False
    conteudo = readme.read_text(encoding="utf-8")
    if MARCADOR_INICIO not in conteudo or MARCADOR_FIM not in conteudo:
        return False

    antes = conteudo.split(MARCADOR_INICIO)[0]
    depois = conteudo.split(MARCADOR_FIM)[1]
    readme.write_text(
        f"{antes}{MARCADOR_INICIO}\n\n{markdown}\n{MARCADOR_FIM}{depois}",
        encoding="utf-8",
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Roda o roteiro de testes do agente.")
    parser.add_argument("--com-bordas", action="store_true", help="Inclui os casos de borda.")
    parser.add_argument("--sem-readme", action="store_true", help="Nao injeta os exemplos no README.")
    parser.add_argument(
        "--pausa",
        type=float,
        default=20.0,
        help=(
            "Segundos de espera entre os casos. O free tier do Gemini permite "
            "poucas requisicoes por minuto e cada caso faz mais de uma; 0 desliga."
        ),
    )
    argumentos = parser.parse_args()

    if not config.GEMINI_API_KEY:
        print(f"ERRO: {ERRO_SEM_CHAVE}")
        return 1

    store = obter_store()
    if store.esta_vazio():
        print("ERRO: indice vazio. Rode antes: python scripts/indexar_curriculos.py")
        return 1
    print(f"Indice: {store.total_chunks()} chunks | alunos: {', '.join(store.listar_alunos())}")

    casos = CASOS + (CASOS_BORDA if argumentos.com_bordas else [])
    resultados = executar(casos, pausa=argumentos.pausa)

    from app.agent.gemini_client import modelo_chat

    modelo = modelo_chat()
    principais = [r for r in resultados if r["numero"] <= len(CASOS)]
    markdown = montar_markdown(principais, modelo)

    destino = config.BASE_DIR / "tests" / "resultados_execucao.md"
    cabecalho = f"# Resultados da execucao do roteiro\n\nModelo: `{modelo}`\n\n"
    destino.write_text(cabecalho + montar_markdown(resultados, modelo), encoding="utf-8")
    print(f"\n{'=' * 78}\nTranscricao salva em: {destino}")

    if not argumentos.sem_readme:
        if injetar_no_readme(markdown, config.BASE_DIR / "README.md"):
            print("Exemplos injetados no README.md (entre os marcadores).")
        else:
            print("AVISO: marcadores nao encontrados no README.md - nada injetado.")

    falhas = [r for r in resultados if r["erro"]]
    sucesso = len(resultados) - len(falhas)
    print(f"\n{sucesso}/{len(resultados)} casos responderam sem erro.")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
