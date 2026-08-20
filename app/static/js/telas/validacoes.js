/**
 * Tela de validacoes: o historico do que o mentor aprovou, mandou ajustar ou rejeitou.
 *
 * E o contraponto humano do agente - serve tanto como fila de revisao quanto
 * como termometro de qualidade das respostas ao longo do tempo.
 */

import { criar, limpar, estadoVazio, carregando, Formatar, Markdown, Modal, Toast, cartaoMetrica } from "../nucleo.js";
import { Tela } from "./base.js";

const ETIQUETAS = {
  aprovado: { classe: "ok", texto: "aprovado" },
  ajustar: { classe: "alerta", texto: "precisa ajuste" },
  rejeitado: { classe: "erro", texto: "rejeitado" },
};

export class TelaValidacoes extends Tela {
  static rota = "validacoes";
  static titulo = "Validacoes";
  static subtitulo = "O que o mentor aprovou, mandou ajustar ou rejeitou";
  static icone = "✅";
  static perfis = ["mentor", "admin"];

  async montar(container) {
    this.container = container;
    this.filtro = "";

    this.painelMetricas = criar("div", { classe: "grade c4" });
    this.painelFiltros = criar("div", { style: "display:flex;gap:8px;margin:14px 0;flex-wrap:wrap" });
    this.painelLista = criar("div", { classe: "cartao" });

    container.append(this.painelMetricas, this.painelFiltros, this.painelLista);
    this.#renderizarFiltros();
    await this.#carregar();
  }

  #renderizarFiltros() {
    limpar(this.painelFiltros);
    const opcoes = [
      { valor: "", rotulo: "Todas" },
      { valor: "aprovado", rotulo: "Aprovadas" },
      { valor: "ajustar", rotulo: "Precisam ajuste" },
      { valor: "rejeitado", rotulo: "Rejeitadas" },
    ];
    for (const opcao of opcoes) {
      this.painelFiltros.append(criar("button", {
        classe: `sugestao ${this.filtro === opcao.valor ? "ativa" : ""}`,
        style: this.filtro === opcao.valor
          ? "border-color:var(--marca);color:var(--texto);font-weight:600" : "",
        texto: opcao.rotulo,
        onclick: () => { this.filtro = opcao.valor; this.#renderizarFiltros(); this.#carregar(); },
      }));
    }
  }

  async #carregar() {
    limpar(this.painelLista).append(carregando("Carregando validacoes"));
    try {
      const [validacoes, resumo] = await Promise.all([
        this.api.listarValidacoes(this.filtro ? { veredito: this.filtro } : {}),
        this.api.resumoValidacoes(),
      ]);
      this.validacoes = validacoes;
      this.#renderizarMetricas(resumo);
      this.#renderizarLista();
    } catch (erro) {
      limpar(this.painelLista).append(estadoVazio("!", `Falha ao carregar: ${erro.message}`));
    }
  }

  #renderizarMetricas(resumo) {
    limpar(this.painelMetricas);
    const total = resumo.aprovado + resumo.ajustar + resumo.rejeitado;
    const taxa = total ? Math.round((resumo.aprovado / total) * 100) : 0;

    this.painelMetricas.append(
      cartaoMetrica(total, "respostas avaliadas"),
      cartaoMetrica(resumo.aprovado, "aprovadas", "ok"),
      cartaoMetrica(resumo.ajustar, "precisam ajuste", resumo.ajustar ? "alerta" : ""),
      cartaoMetrica(`${taxa}%`, "taxa de aprovacao", taxa >= 70 ? "ok" : taxa >= 40 ? "alerta" : "erro")
    );
  }

  #renderizarLista() {
    limpar(this.painelLista);

    if (!this.validacoes.length) {
      this.painelLista.append(estadoVazio("✅", this.filtro
        ? "Nenhuma validacao com esse filtro."
        : "Nenhuma resposta avaliada ainda. Valide as respostas na tela do mentor."));
      return;
    }

    for (const validacao of this.validacoes) {
      this.painelLista.append(this.#item(validacao));
    }
  }

  #item(validacao) {
    const etiqueta = ETIQUETAS[validacao.veredito] || ETIQUETAS.aprovado;

    const resposta = criar("div", {
      classe: "resposta",
      html: Markdown.paraHtml(validacao.resposta),
    });

    return criar("div", { classe: "item-validacao" }, [
      criar("div", { style: "display:flex;gap:10px;align-items:flex-start" }, [
        criar("div", { style: "flex:1;min-width:0" }, [
          criar("div", { classe: "pergunta", texto: validacao.pergunta }),
          criar("div", { style: "font-size:11.5px;color:var(--texto-3);margin-top:3px" }, [
            [
              Formatar.data(validacao.criado_em),
              validacao.aluno || null,
              (validacao.ferramentas || []).join(", ") || null,
            ].filter(Boolean).join(" · "),
          ]),
        ]),
        criar("span", { classe: `etiqueta ${etiqueta.classe}`, texto: etiqueta.texto }),
      ]),
      resposta,
      validacao.observacao
        ? criar("div", { classe: "observacao", texto: `Observacao: ${validacao.observacao}` })
        : null,
      criar("div", { classe: "rodape" }, [
        criar("button", {
          classe: "mini-botao", texto: "Ver resposta completa",
          onclick: (evento) => {
            resposta.classList.toggle("aberta");
            evento.target.textContent = resposta.classList.contains("aberta")
              ? "Recolher" : "Ver resposta completa";
          },
        }),
        criar("button", {
          classe: "mini-botao", texto: "Mudar veredito",
          onclick: () => this.#editar(validacao),
        }),
        criar("button", {
          classe: "mini-botao erro", texto: "Excluir",
          onclick: () => this.#excluir(validacao),
        }),
      ]),
    ]);
  }

  #editar(validacao) {
    const seletor = criar("select", {}, [
      criar("option", { value: "aprovado", texto: "Aprovado", selected: validacao.veredito === "aprovado" }),
      criar("option", { value: "ajustar", texto: "Precisa ajuste", selected: validacao.veredito === "ajustar" }),
      criar("option", { value: "rejeitado", texto: "Rejeitado", selected: validacao.veredito === "rejeitado" }),
    ]);
    const observacao = criar("textarea", { rows: 3, texto: validacao.observacao || "" });

    Modal.abrir({
      titulo: "Atualizar validacao",
      corpo: [
        criar("div", { classe: "campo" }, [criar("label", { texto: "Veredito" }), seletor]),
        criar("div", { classe: "campo" }, [criar("label", { texto: "Observacao" }), observacao]),
      ],
      acoes: [
        { texto: "Cancelar", classe: "secundario" },
        {
          texto: "Salvar",
          aoClicar: async (fechar) => {
            fechar();
            try {
              await this.api.atualizarValidacao(validacao.id, {
                veredito: seletor.value,
                observacao: observacao.value.trim(),
              });
              Toast.ok("Validacao atualizada.");
              await this.#carregar();
              this.app.atualizarStatus();
            } catch (erro) {
              Toast.erro(`Falha ao atualizar: ${erro.message}`);
            }
          },
        },
      ],
    });
  }

  async #excluir(validacao) {
    const confirmado = await Modal.confirmar({
      titulo: "Excluir validacao",
      mensagem: "O registro sai do historico. Nao afeta a resposta original do agente.",
      textoConfirmar: "Excluir",
      perigoso: true,
    });
    if (!confirmado) return;

    try {
      await this.api.removerValidacao(validacao.id);
      Toast.ok("Validacao excluida.");
      await this.#carregar();
      this.app.atualizarStatus();
    } catch (erro) {
      Toast.erro(`Falha ao excluir: ${erro.message}`);
    }
  }
}
