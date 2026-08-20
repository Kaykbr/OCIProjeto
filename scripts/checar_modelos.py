"""Diagnostico da chave do Gemini: o que ela realmente consegue usar.

O endpoint de listagem do Google mostra modelos que, na hora de usar, respondem
404 ("no longer available to new users") ou 429 (sem creditos). Este script
faz uma chamada de verdade em cada candidato e mostra o que funciona, para voce
saber exatamente o que colocar em GEMINI_MODEL / GEMINI_EMBEDDING_MODEL.

    python scripts/checar_modelos.py            # testa os modelos preferidos
    python scripts/checar_modelos.py --todos    # testa todos os do catalogo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# No Windows o console usa cp1252 por padrao e quebra ao imprimir emoji/simbolos
# que o modelo devolve. Forcamos UTF-8 na saida para o script rodar igual em
# qualquer terminal (e quando a saida e redirecionada para arquivo).
for _fluxo in (sys.stdout, sys.stderr):
    if hasattr(_fluxo, "reconfigure"):
        _fluxo.reconfigure(encoding="utf-8", errors="replace")


from app import config  # noqa: E402
from app.agent.gemini_client import ERRO_SEM_CHAVE, obter_client, traduzir_erro_gemini  # noqa: E402

IGNORAR = ("audio", "tts", "image", "vision", "gemma", "learnlm", "aqa", "robotics", "lyria", "banana")


def _resumo_do_erro(erro: Exception) -> str:
    texto = str(erro)
    if "429" in texto:
        return "429 sem creditos/cota"
    if "404" in texto:
        return "404 indisponivel para esta chave"
    if "401" in texto or "403" in texto:
        return "sem permissao"
    return type(erro).__name__


def testar_chat(client, nome: str) -> tuple[bool, str]:
    try:
        resposta = client.models.generate_content(model=nome, contents="Responda apenas: ok")
        return True, (resposta.text or "").strip()[:30]
    except Exception as erro:  # noqa: BLE001
        return False, _resumo_do_erro(erro)


def testar_embedding(client, nome: str) -> tuple[bool, str]:
    try:
        resposta = client.models.embed_content(model=nome, contents=["teste"])
        return True, f"dimensao {len(resposta.embeddings[0].values or [])}"
    except Exception as erro:  # noqa: BLE001
        return False, _resumo_do_erro(erro)


def main() -> int:
    parser = argparse.ArgumentParser(description="Checa quais modelos do Gemini a chave aceita.")
    parser.add_argument("--todos", action="store_true", help="Testa todos os modelos do catalogo.")
    argumentos = parser.parse_args()

    if not config.GEMINI_API_KEY:
        print(f"ERRO: {ERRO_SEM_CHAVE}")
        return 1

    client = obter_client()
    chave = config.GEMINI_API_KEY
    print(f"Chave: {chave[:6]}...{chave[-4:]}\n")

    try:
        catalogo = list(client.models.list())
    except Exception as erro:  # noqa: BLE001
        print(f"ERRO ao listar modelos: {traduzir_erro_gemini(erro)}")
        return 1

    chat_catalogo, embed_catalogo = [], []
    for modelo in catalogo:
        nome = (modelo.name or "").removeprefix("models/")
        acoes = set(modelo.supported_actions or [])
        if not nome or any(x in nome for x in IGNORAR):
            continue
        if "embedContent" in acoes:
            embed_catalogo.append(nome)
        elif "generateContent" in acoes:
            chat_catalogo.append(nome)

    chat = sorted(chat_catalogo) if argumentos.todos else [
        n for n in config.MODELOS_CHAT_PREFERIDOS if n in chat_catalogo
    ]
    embeddings = sorted(embed_catalogo) if argumentos.todos else [
        n for n in config.MODELOS_EMBEDDING_PREFERIDOS if n in embed_catalogo
    ]

    funcionam_chat, funcionam_embed = [], []

    print(f"=== CHAT ({len(chat)} testados) ===")
    for nome in chat:
        ok, detalhe = testar_chat(client, nome)
        print(f"  [{'OK   ' if ok else 'FALHA'}] {nome:<28} {detalhe}")
        if ok:
            funcionam_chat.append(nome)

    print(f"\n=== EMBEDDINGS ({len(embeddings)} testados) ===")
    for nome in embeddings:
        ok, detalhe = testar_embedding(client, nome)
        print(f"  [{'OK   ' if ok else 'FALHA'}] {nome:<28} {detalhe}")
        if ok:
            funcionam_embed.append(nome)

    print("\n=== CONCLUSAO ===")
    if funcionam_chat and funcionam_embed:
        print("A chave esta pronta para o projeto. Sugestao de .env:")
        print(f"  GEMINI_MODEL={funcionam_chat[0]}")
        print(f"  GEMINI_EMBEDDING_MODEL={funcionam_embed[0]}")
        return 0

    if not funcionam_chat:
        print("  Nenhum modelo de chat respondeu.")
    if not funcionam_embed:
        print("  Nenhum modelo de embedding respondeu.")
    print(
        "\n  A chave e valida (o catalogo foi listado), mas o projeto por tras dela nao\n"
        "  consegue executar chamadas. Quase sempre e faturamento/cota:\n"
        "    1. Abra https://ai.studio/projects\n"
        "    2. Veja se o projeto tem creditos, ou crie uma chave nova num projeto\n"
        "       com free tier em https://aistudio.google.com/apikey\n"
        "    3. Atualize GEMINI_API_KEY no .env e rode este script de novo"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
