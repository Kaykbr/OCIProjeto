/**
 * Base de documentos: qualquer perfil consulta os curriculos que alimentam o agente.
 *
 * A esquerda a lista de PDFs, a direita o conteudo extraido - quebrado nas
 * mesmas secoes que o parser usa para montar os chunks. E a resposta a
 * pergunta "de onde o agente tirou isso?".
 */

import { criar, limpar, estadoVazio, carregando, Formatar, Toast, Modal } from "../nucleo.js";
import { Tela } from "./base.js";

export class TelaDocumentos extends Tela {
  static rota = "documentos";
  static titulo = "Base de documentos";
  static subtitulo = "Curriculos indexados que sustentam as respostas do agente";
  static icone = "📄";
  static perfis = ["mentor", "aluno", "admin"];

  async montar(container) {
    this.container = container;

    this.busca = criar("input", {
      type: "search",
      placeholder: "Filtrar por aluno ou arquivo...",
      oninput: () => this.#renderizarLista(),
      style: "margin-bottom:12px",
    });

    this.lista = criar("div", { classe: "lista-documentos" });
    this.detalhe = criar("div", { classe: "cartao" }, [
      estadoVazio("📄", "Selecione um curriculo na lista para ver o conteudo extraido."),
    ]);

    container.append(
      criar("div", { classe: "divisao-documentos" }, [
        criar("div", {}, [this.busca, this.lista]),
        this.detalhe,
      ])
    );

    await this.#carregar();
  }

  async #carregar() {
    limpar(this.lista).append(carregando("Lendo a base de curriculos"));
    try {
      this.documentos = await this.api.listarDocumentos();
      this.#renderizarLista();
      if (this.documentos.length) {
        const preferido = this.estado.documentoSelecionado
          && this.documentos.find((d) => d.arquivo === this.estado.documentoSelecionado);
        this.#selecionar((preferido || this.documentos[0]).arquivo);
      }
    } catch (erro) {
      limpar(this.lista).append(estadoVazio("!", `Nao consegui listar os documentos: ${erro.message}`));
    }
  }

  #filtrados() {
    const termo = (this.busca.value || "").trim().toLowerCase();
    if (!termo) return this.documentos;
    return this.documentos.filter((documento) =>
      `${documento.aluno} ${documento.arquivo}`.toLowerCase().includes(termo)
    );
  }

  #renderizarLista() {
    limpar(this.lista);
    const documentos = this.#filtrados();

    if (!documentos.length) {
      this.lista.append(estadoVazio("📭", this.documentos.length
        ? "Nenhum documento bate com esse filtro."
        : "Nenhum curriculo na base. Envie um PDF pelo painel admin."));
      return;
    }

    for (const documento of documentos) {
      this.lista.append(criar("div", {
        classe: `item-documento ${documento.arquivo === this.estado.documentoSelecionado ? "ativo" : ""}`,
        onclick: () => this.#selecionar(documento.arquivo),
      }, [
        criar("span", { classe: "icone", texto: "📄" }),
        criar("div", { style: "flex:1;min-width:0" }, [
          criar("div", { classe: "nome", texto: documento.aluno || documento.arquivo }),
          criar("div", {
            classe: "meta",
            texto: `${documento.arquivo} · ${Formatar.plural(documento.paginas, "pagina", "paginas")} · ${Formatar.tamanho(documento.tamanho_kb)}`,
          }),
        ]),
        criar("span", {
          classe: `etiqueta ${documento.indexado ? "ok" : "alerta"}`,
          texto: documento.indexado ? `${documento.chunks} chunks` : "nao indexado",
        }),
      ]));
    }
  }

  async #selecionar(arquivo) {
    this.estado.documentoSelecionado = arquivo;
    this.#renderizarLista();
    limpar(this.detalhe).append(carregando("Extraindo o texto do PDF"));

    try {
      const documento = await this.api.obterDocumento(arquivo);
      this.#renderizarDetalhe(documento);
    } catch (erro) {
      limpar(this.detalhe).append(estadoVazio("!", `Nao consegui abrir o documento: ${erro.message}`));
    }
  }

  #renderizarDetalhe(documento) {
    limpar(this.detalhe);

    const cabecalho = criar("div", { style: "display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap" }, [
      criar("div", { style: "flex:1;min-width:200px" }, [
        criar("h3", { texto: documento.aluno || documento.arquivo, style: "font-size:16px" }),
        criar("div", { style: "font-size:12.5px;color:var(--texto-3);margin-top:2px" }, [
          `${documento.arquivo} · ${Formatar.plural(documento.paginas, "pagina", "paginas")} · `
          + `${documento.caracteres.toLocaleString("pt-BR")} caracteres · `
          + `atualizado em ${Formatar.data(documento.atualizado_em)}`,
        ]),
      ]),
      criar("a", {
        classe: "botao secundario pequeno",
        href: this.api.urlDownload(documento.arquivo),
        target: "_blank",
        rel: "noopener",
        texto: "Abrir PDF",
      }),
      this.estado.perfil === "admin"
        ? criar("button", {
            classe: "botao perigo pequeno",
            texto: "Remover",
            onclick: () => this.#remover(documento),
          })
        : null,
    ]);

    const etiquetas = criar("div", { style: "display:flex;gap:6px;flex-wrap:wrap;margin:12px 0 14px" }, [
      criar("span", {
        classe: `etiqueta ${documento.indexado ? "ok" : "alerta"}`,
        texto: documento.indexado ? `indexado · ${documento.chunks} chunks` : "fora do indice",
      }),
      ...documento.secoes.map((secao) =>
        criar("span", { classe: "etiqueta neutra", texto: `${secao.nome} (${secao.caracteres})` })
      ),
    ]);

    const abas = criar("div", { classe: "navegacao-secoes" });
    const corpo = criar("div", { classe: "texto-documento" });

    const mostrar = (nome) => {
      for (const aba of abas.children) aba.classList.toggle("ativa", aba.dataset.secao === nome);
      corpo.textContent = nome === "__tudo__"
        ? documento.texto
        : (documento.secoes.find((s) => s.nome === nome) || {}).texto || "";
    };

    abas.append(criar("button", {
      classe: "aba-secao", texto: "Documento completo",
      dataset: { secao: "__tudo__" }, onclick: () => mostrar("__tudo__"),
    }));
    for (const secao of documento.secoes) {
      abas.append(criar("button", {
        classe: "aba-secao", texto: secao.nome,
        dataset: { secao: secao.nome }, onclick: () => mostrar(secao.nome),
      }));
    }

    this.detalhe.append(cabecalho, etiquetas, abas, corpo);
    mostrar("__tudo__");
  }

  async #remover(documento) {
    const confirmado = await Modal.confirmar({
      titulo: "Remover curriculo",
      mensagem: `Isso apaga o PDF "${documento.arquivo}", os chunks dele no indice e os PDIs de ${documento.aluno || "esse aluno"}. Nao da para desfazer.`,
      textoConfirmar: "Remover",
      perigoso: true,
    });
    if (!confirmado) return;

    try {
      const resultado = await this.api.removerDocumento(documento.arquivo);
      Toast.ok(`Removido: ${resultado.chunks_removidos} chunks e ${resultado.pdis_removidos} PDI(s).`);
      this.estado.documentoSelecionado = null;
      await this.#carregar();
      this.app.atualizarStatus();
    } catch (erro) {
      Toast.erro(`Falha ao remover: ${erro.message}`);
    }
  }
}
