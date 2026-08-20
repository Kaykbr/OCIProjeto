"""Pipeline de ingestao: PDF -> texto -> chunks -> embeddings -> ChromaDB.

Usa o mesmo `ServicoIndexacao` que o painel admin e a auto-indexacao da subida,
para que os tres caminhos nao possam divergir.

    python scripts/indexar_curriculos.py                 # reindexa tudo do zero
    python scripts/indexar_curriculos.py --arquivo x.pdf # so um curriculo
    python scripts/indexar_curriculos.py --status        # so mostra o indice atual
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
from app.agent.gemini_client import ERRO_SEM_CHAVE  # noqa: E402
from app.services.indexacao import ServicoIndexacao  # noqa: E402


def mostrar_status(servico: ServicoIndexacao) -> None:
    estatisticas = servico.estatisticas()
    print(f"\nColecao '{estatisticas.colecao}' em {estatisticas.caminho}")
    print(f"  {estatisticas.total_chunks} chunks | {estatisticas.total_alunos} alunos "
          f"| {estatisticas.total_documentos} PDFs na pasta")
    for aluno, quantidade in estatisticas.chunks_por_aluno.items():
        print(f"    {aluno:<20} {quantidade} chunks")
    if estatisticas.documentos_nao_indexados:
        print(f"  Fora do indice: {', '.join(estatisticas.documentos_nao_indexados)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Indexa os curriculos em PDF no vector store.")
    parser.add_argument("--arquivo", help="Indexa apenas este PDF (nome do arquivo em data/curriculos).")
    parser.add_argument("--status", action="store_true", help="Apenas mostra o estado do indice.")
    argumentos = parser.parse_args()

    servico = ServicoIndexacao()

    if argumentos.status:
        mostrar_status(servico)
        return 0

    if not config.GEMINI_API_KEY:
        print(f"ERRO: {ERRO_SEM_CHAVE}")
        return 1

    documentos = servico.documentos.listar_arquivos()
    if not documentos:
        print("ERRO: nenhum PDF encontrado. Rode antes: python scripts/gerar_curriculos_exemplo.py")
        return 1

    if argumentos.arquivo:
        print(f"Indexando {argumentos.arquivo}...")
        resultado = servico.indexar_documento(argumentos.arquivo)
    else:
        print(f"Lendo PDFs de {config.CURRICULOS_DIR}")
        for caminho in documentos:
            print(f"  {caminho.name}")
        print("\nReindexando tudo (a colecao e apagada antes)...")
        resultado = servico.reindexar_tudo()

    if resultado.avisos:
        for aviso in resultado.avisos:
            print(f"  [aviso] {aviso}")

    print(f"\n{resultado.chunks} chunks de {resultado.arquivos} curriculo(s) em {resultado.duracao_s}s.")
    if resultado.alunos:
        print(f"Alunos: {', '.join(resultado.alunos)}")
    mostrar_status(servico)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
