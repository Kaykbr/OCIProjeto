/**
 * Tela de PDI: o Plano de Desenvolvimento Individual em formato grafico.
 *
 * O mesmo conteudo que o agente escreve em texto no chat aparece aqui
 * estruturado - medidor de aderencia, barras de habilidade, gaps com
 * criticidade, acoes ordenadas e cronograma - para o mentor bater o olho e
 * conduzir a conversa de 1:1.
 */

import { criar, limpar, estadoVazio, carregando, Formatar, Toast, Modal, cartaoMetrica } from "../nucleo.js";
import { Graficos, corPorNivel } from "../graficos.js";
import { Tela } from "./base.js";

const VAGAS_SUGERIDAS = [
  "Desenvolvedor Full Stack Pleno, com React e Node.js",
  "Engenheiro de Dados Junior, com Python, SQL e Airflow",
  "SDET - Software Development Engineer in Test, com automacao de API e CI/CD",
  "Desenvolvedor Backend Senior, com Python, cloud e Docker",
  "Cientista de Dados Junior, com Python, Pandas e scikit-learn",
];

export class TelaPDI extends Tela {
  static rota = "pdi";
  static titulo = "PDI";
  static subtitulo = "Plano de Desenvolvimento Individual, comparado com uma vaga-alvo";
  static icone = "📊";
  static perfis = ["mentor", "aluno", "admin"];

  async montar(container) {
    this.container = container;

    this.painelLista = criar("div", {});
    this.painelDetalhe = criar("div", {});

    container.append(
      this.#formulario(),
      criar("div", { classe: "divisao-pdi" }, [
        this.painelLista,
        this.painelDetalhe,
      ])
    );

    await this.#carregarLista();
  }

  /* --- formulario de geracao --- */

  #formulario() {
    this.seletorAluno = criar("select", {});
    this.campoVaga = criar("input", {
      type: "text",
      placeholder: "Ex.: Desenvolvedor Full Stack Pleno, com React e Node.js",
      list: "vagas-sugeridas",
      onkeydown: (evento) => { if (evento.key === "Enter") this.#gerar(); },
    });
    this.botaoGerar = criar("button", { classe: "botao", texto: "Gerar PDI", onclick: () => this.#gerar() });

    const preencherAlunos = () => {
      limpar(this.seletorAluno);
      if (!this.estado.alunos.length) {
        this.seletorAluno.append(criar("option", { value: "", texto: "Nenhum aluno indexado" }));
        return;
      }
      for (const aluno of this.estado.alunos) {
        this.seletorAluno.append(criar("option", {
          value: aluno.nome, texto: aluno.nome,
          selected: aluno.nome === this.estado.alunoFoco,
        }));
      }
    };
    preencherAlunos();
    this.aoDestruir(this.estado.em("alunos", preencherAlunos));

    return criar("div", { classe: "cartao" }, [
      criar("h3", { texto: "Gerar um novo PDI" }),
      criar("div", { classe: "dica", texto: "O agente compara o curriculo indexado do aluno com a vaga-alvo e devolve habilidades atuais, gaps, acoes e cronograma." }),
      criar("div", { classe: "formulario-pdi" }, [
        criar("div", { classe: "campo" }, [criar("label", { texto: "Aluno" }), this.seletorAluno]),
        criar("div", { classe: "campo" }, [
          criar("label", { texto: "Vaga-alvo" }),
          this.campoVaga,
          criar("datalist", { id: "vagas-sugeridas" },
            VAGAS_SUGERIDAS.map((vaga) => criar("option", { value: vaga }))),
        ]),
        this.botaoGerar,
      ]),
    ]);
  }

  async #gerar() {
    const aluno = this.seletorAluno.value;
    const vaga = this.campoVaga.value.trim();

    if (!aluno) { Toast.erro("Nenhum aluno indexado para gerar PDI."); return; }
    if (vaga.length < 4) { Toast.erro("Descreva a vaga-alvo com um pouco mais de detalhe."); return; }

    this.botaoGerar.disabled = true;
    this.botaoGerar.textContent = "Gerando...";
    limpar(this.painelDetalhe).append(carregando(`Analisando o perfil de ${aluno} contra a vaga`));

    try {
      const pdi = await this.api.gerarPdi(aluno, vaga);
      this.estado.pdiSelecionado = pdi.id;
      await this.#carregarLista();
      this.#renderizarDetalhe(pdi);
      Toast.ok(`PDI de ${pdi.aluno} pronto: ${pdi.aderencia}% de aderencia.`);
      this.app.atualizarStatus();
    } catch (erro) {
      limpar(this.painelDetalhe).append(estadoVazio("!", `Nao consegui gerar o PDI: ${erro.message}`));
      Toast.erro(erro.message);
    } finally {
      this.botaoGerar.disabled = false;
      this.botaoGerar.textContent = "Gerar PDI";
    }
  }

  /* --- lista --- */

  async #carregarLista() {
    limpar(this.painelLista).append(carregando("Carregando PDIs"));
    try {
      this.pdis = await this.api.listarPdis();
      this.#renderizarLista();
      if (this.pdis.length && !this.painelDetalhe.firstChild) {
        const preferido = this.pdis.find((p) => p.id === this.estado.pdiSelecionado) || this.pdis[0];
        await this.#abrir(preferido.id);
      } else if (!this.pdis.length) {
        limpar(this.painelDetalhe).append(estadoVazio("📊",
          "Nenhum PDI gerado ainda. Escolha um aluno e uma vaga-alvo acima."));
      }
    } catch (erro) {
      limpar(this.painelLista).append(estadoVazio("!", `Falha ao listar: ${erro.message}`));
    }
  }

  #renderizarLista() {
    limpar(this.painelLista);
    this.painelLista.append(criar("h3", {
      texto: `PDIs gerados (${this.pdis.length})`,
      style: "font-size:13px;color:var(--texto-3);margin-bottom:10px;text-transform:uppercase;letter-spacing:.6px",
    }));

    if (!this.pdis.length) {
      this.painelLista.append(estadoVazio("—", "Nada por aqui ainda."));
      return;
    }

    for (const pdi of this.pdis) {
      this.painelLista.append(criar("div", {
        classe: `item-documento ${pdi.id === this.estado.pdiSelecionado ? "ativo" : ""}`,
        style: "margin-bottom:8px",
        onclick: () => this.#abrir(pdi.id),
      }, [
        criar("div", { style: "flex:1;min-width:0" }, [
          criar("div", { classe: "nome", texto: pdi.aluno }),
          criar("div", { classe: "meta", texto: pdi.vaga_alvo }),
          criar("div", { classe: "meta", style: "margin-top:3px", texto:
            `${Formatar.plural(pdi.gaps, "gap", "gaps")} · ${Formatar.plural(pdi.acoes, "acao", "acoes")} · ${Formatar.data(pdi.criado_em)}` }),
        ]),
        criar("span", {
          style: `font-size:15px;font-weight:700;color:${corPorNivel(pdi.aderencia)}`,
          texto: `${pdi.aderencia}%`,
        }),
      ]));
    }
  }

  async #abrir(id) {
    this.estado.pdiSelecionado = id;
    this.#renderizarLista();
    limpar(this.painelDetalhe).append(carregando("Abrindo o PDI"));
    try {
      this.#renderizarDetalhe(await this.api.obterPdi(id));
    } catch (erro) {
      limpar(this.painelDetalhe).append(estadoVazio("!", `Falha ao abrir: ${erro.message}`));
    }
  }

  /* --- detalhe --- */

  #renderizarDetalhe(pdi) {
    limpar(this.painelDetalhe);

    const horasTotais = (pdi.acoes || []).reduce((soma, acao) => soma + (acao.esforco_horas || 0), 0);
    const gapsCriticos = (pdi.gaps || []).filter((gap) => gap.criticidade === "alta").length;

    this.painelDetalhe.append(
      this.#cabecalho(pdi),
      criar("div", { classe: "grade c4", style: "margin-top:14px" }, [
        cartaoMetrica(`${pdi.aderencia}%`, "aderencia a vaga",
          pdi.aderencia >= 70 ? "ok" : pdi.aderencia >= 40 ? "alerta" : "erro"),
        cartaoMetrica(pdi.gaps.length, `gaps (${gapsCriticos} criticos)`, gapsCriticos ? "alerta" : ""),
        cartaoMetrica(`${pdi.prazo_total_meses}m`, "prazo sugerido"),
        cartaoMetrica(`${horasTotais}h`, "esforco estimado"),
      ]),
      pdi.resumo
        ? criar("div", { classe: "cartao", style: "margin-top:14px" }, [
            criar("h3", { texto: "Leitura do mentor" }),
            criar("p", { texto: pdi.resumo, style: "margin:0;color:var(--texto-2)" }),
          ])
        : null,
      criar("div", { classe: "grade c2", style: "margin-top:14px" }, [
        this.#cartaoHabilidades(pdi),
        this.#cartaoGaps(pdi),
      ]),
      this.#cartaoAcoes(pdi),
      this.#cartaoCronograma(pdi)
    );
  }

  #cabecalho(pdi) {
    return criar("div", { classe: "cartao" }, [
      criar("div", { classe: "cabecalho-pdi" }, [
        Graficos.medidor(pdi.aderencia, { tamanho: 132 }),
        criar("div", { classe: "info" }, [
          criar("h3", { texto: pdi.aluno }),
          criar("div", { classe: "vaga", texto: `Vaga-alvo: ${pdi.vaga_alvo}` }),
          criar("div", { style: "font-size:11.5px;color:var(--texto-3);margin-top:6px" }, [
            `Gerado em ${Formatar.data(pdi.criado_em)}${pdi.modelo ? ` · modelo ${pdi.modelo}` : ""}`,
          ]),
          criar("div", { style: "display:flex;gap:8px;margin-top:12px;flex-wrap:wrap" }, [
            criar("button", {
              classe: "botao secundario pequeno", texto: "Regerar",
              onclick: () => this.#regerar(pdi),
            }),
            criar("button", {
              classe: "botao secundario pequeno", texto: "Imprimir / PDF",
              onclick: () => window.print(),
            }),
            this.estado.perfil !== "aluno"
              ? criar("button", {
                  classe: "botao perigo pequeno", texto: "Excluir",
                  onclick: () => this.#excluir(pdi),
                })
              : null,
          ]),
        ]),
      ]),
    ]);
  }

  #cartaoHabilidades(pdi) {
    const dados = (pdi.habilidades_atuais || []).map((habilidade) => ({
      rotulo: habilidade.nome,
      valor: habilidade.nivel,
      detalhe: habilidade.evidencia,
      cor: corPorNivel(habilidade.nivel),
    }));

    return criar("div", { classe: "cartao" }, [
      criar("h3", { texto: `Habilidades atuais (${dados.length})` }),
      criar("div", { classe: "dica", texto: "O que ja existe no curriculo e conta para a vaga. A barra e o dominio estimado." }),
      dados.length
        ? Graficos.barrasHorizontais(dados, { maximo: 100, sufixo: "" })
        : estadoVazio("—", "Nenhuma habilidade aproveitavel identificada."),
    ]);
  }

  #cartaoGaps(pdi) {
    const dados = (pdi.gaps || []).map((gap) => ({
      rotulo: gap.nome,
      atual: gap.nivel_atual,
      alvo: gap.nivel_alvo,
      criticidade: gap.criticidade,
      detalhe: gap.justificativa,
    }));

    return criar("div", { classe: "cartao" }, [
      criar("h3", { texto: `Gaps identificados (${dados.length})` }),
      criar("div", { classe: "dica", texto: "Barra colorida = onde o aluno esta hoje; marcador claro = onde a vaga exige que ele chegue." }),
      dados.length ? Graficos.barrasGap(dados) : estadoVazio("—", "Nenhum gap relevante."),
    ]);
  }

  #cartaoAcoes(pdi) {
    const acoes = [...(pdi.acoes || [])].sort((a, b) => (a.ordem || 0) - (b.ordem || 0));
    const maiorEsforco = Math.max(1, ...acoes.map((acao) => acao.esforco_horas || 0));

    return criar("div", { classe: "cartao", style: "margin-top:14px" }, [
      criar("h3", { texto: `Acoes recomendadas (${acoes.length})` }),
      criar("div", { classe: "dica", texto: "Na ordem de execucao. A barra compara o esforco relativo de cada acao." }),
      acoes.length
        ? criar("div", {}, acoes.map((acao, indice) =>
            criar("div", { classe: "acao-pdi" }, [
              criar("div", { classe: "ordem", texto: String(acao.ordem || indice + 1) }),
              criar("div", { style: "flex:1;min-width:0" }, [
                criar("div", { classe: "titulo", texto: acao.titulo }),
                acao.descricao ? criar("div", { classe: "descricao", texto: acao.descricao }) : null,
                criar("div", { classe: "rodape" }, [
                  acao.gap_relacionado
                    ? criar("span", { classe: "etiqueta marca", texto: acao.gap_relacionado })
                    : null,
                  criar("span", { style: "font-size:11.5px;color:var(--texto-3)", texto: `${acao.esforco_horas}h` }),
                  criar("div", { classe: "barra", style: "flex:1;max-width:180px" }, [
                    criar("span", { style: `width:${Math.round(((acao.esforco_horas || 0) / maiorEsforco) * 100)}%` }),
                  ]),
                ]),
              ]),
            ])
          ))
        : estadoVazio("—", "Nenhuma acao proposta."),
    ]);
  }

  #cartaoCronograma(pdi) {
    return criar("div", { classe: "cartao", style: "margin-top:14px" }, [
      criar("h3", { texto: `Cronograma sugerido (${pdi.prazo_total_meses} meses)` }),
      (pdi.cronograma || []).length
        ? Graficos.cronograma(pdi.cronograma)
        : estadoVazio("—", "Sem cronograma."),
    ]);
  }

  /* --- acoes --- */

  async #regerar(pdi) {
    const confirmado = await Modal.confirmar({
      titulo: "Regerar PDI",
      mensagem: `Isso substitui o PDI atual de ${pdi.aluno} para essa vaga por uma nova analise do agente.`,
      textoConfirmar: "Regerar",
    });
    if (!confirmado) return;

    limpar(this.painelDetalhe).append(carregando("Refazendo a analise"));
    try {
      const novo = await this.api.gerarPdi(pdi.aluno, pdi.vaga_alvo, true);
      this.estado.pdiSelecionado = novo.id;
      await this.#carregarLista();
      this.#renderizarDetalhe(novo);
      Toast.ok("PDI regerado.");
    } catch (erro) {
      Toast.erro(`Falha ao regerar: ${erro.message}`);
      this.#renderizarDetalhe(pdi);
    }
  }

  async #excluir(pdi) {
    const confirmado = await Modal.confirmar({
      titulo: "Excluir PDI",
      mensagem: `O PDI de ${pdi.aluno} para "${pdi.vaga_alvo}" sera apagado.`,
      textoConfirmar: "Excluir",
      perigoso: true,
    });
    if (!confirmado) return;

    try {
      await this.api.removerPdi(pdi.id);
      this.estado.pdiSelecionado = null;
      limpar(this.painelDetalhe);
      await this.#carregarLista();
      Toast.ok("PDI excluido.");
      this.app.atualizarStatus();
    } catch (erro) {
      Toast.erro(`Falha ao excluir: ${erro.message}`);
    }
  }
}
