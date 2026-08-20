/**
 * Painel de administracao: entrada de novos curriculos e saude do indice.
 *
 * E aqui que a base cresce (upload de PDF, que ja indexa na hora) e que da
 * para enxergar se o vector store esta coerente com a pasta de documentos.
 */

import { criar, limpar, estadoVazio, carregando, Formatar, Toast, Modal, cartaoMetrica } from "../nucleo.js";
import { Graficos } from "../graficos.js";
import { Tela } from "./base.js";

export class TelaAdmin extends Tela {
  static rota = "admin";
  static titulo = "Painel admin";
  static subtitulo = "Curriculos da base, indice vetorial e configuracao";
  static icone = "⚙️";
  static perfis = ["admin"];

  async montar(container) {
    this.container = container;

    this.painelMetricas = criar("div", { classe: "grade c4" });
    this.painelUpload = criar("div", { classe: "cartao", style: "margin-top:14px" });
    this.painelGraficos = criar("div", { classe: "grade c2", style: "margin-top:14px" });
    this.painelDocumentos = criar("div", { classe: "cartao", style: "margin-top:14px" });
    this.painelConfig = criar("div", { classe: "cartao", style: "margin-top:14px" });

    container.append(
      this.painelMetricas,
      this.painelUpload,
      this.painelGraficos,
      this.painelDocumentos,
      this.painelConfig
    );

    this.#renderizarUpload();
    await this.#carregar();
  }

  /* --- upload --- */

  #renderizarUpload() {
    limpar(this.painelUpload);

    const entrada = criar("input", {
      type: "file",
      accept: "application/pdf,.pdf",
      multiple: true,
      style: "display:none",
      onchange: (evento) => this.#enviarArquivos([...evento.target.files]),
    });

    const area = criar("div", { classe: "area-upload", onclick: () => entrada.click() }, [
      criar("span", { classe: "icone", texto: "⬆" }),
      criar("div", { classe: "principal", texto: "Adicionar curriculos" }),
      criar("div", { classe: "secundario", texto: "Arraste PDFs aqui ou clique para escolher. O arquivo e indexado na hora." }),
    ]);

    for (const evento of ["dragenter", "dragover"]) {
      area.addEventListener(evento, (e) => { e.preventDefault(); area.classList.add("arrastando"); });
    }
    for (const evento of ["dragleave", "drop"]) {
      area.addEventListener(evento, (e) => { e.preventDefault(); area.classList.remove("arrastando"); });
    }
    area.addEventListener("drop", (e) => {
      const arquivos = [...(e.dataTransfer?.files || [])].filter((a) => a.type === "application/pdf" || a.name.toLowerCase().endsWith(".pdf"));
      if (!arquivos.length) { Toast.erro("Arraste arquivos PDF."); return; }
      this.#enviarArquivos(arquivos);
    });

    this.progresso = criar("div", { style: "margin-top:12px" });

    this.painelUpload.append(
      criar("h3", { texto: "Adicionar curriculo a base" }),
      criar("div", { classe: "dica", texto: "Somente PDF com texto selecionavel. PDFs escaneados (imagem) precisam de OCR antes." }),
      area, entrada, this.progresso
    );
  }

  async #enviarArquivos(arquivos) {
    if (!arquivos.length) return;
    limpar(this.progresso);

    for (const arquivo of arquivos) {
      const linha = criar("div", {
        style: "display:flex;gap:10px;align-items:center;font-size:13px;padding:6px 0",
      }, [
        criar("span", { classe: "girando" }),
        criar("span", { style: "flex:1", texto: arquivo.name }),
        criar("span", { style: "color:var(--texto-3)", texto: "enviando..." }),
      ]);
      this.progresso.append(linha);

      try {
        const documento = await this.api.enviarDocumento(arquivo);
        limpar(linha).append(
          criar("span", { texto: "✓", style: "color:var(--ok);font-weight:700" }),
          criar("span", { style: "flex:1", texto: `${documento.aluno || documento.arquivo}` }),
          criar("span", {
            classe: `etiqueta ${documento.indexado ? "ok" : "alerta"}`,
            texto: documento.indexado ? `${documento.chunks} chunks indexados` : "salvo, fora do indice",
          })
        );
        Toast.ok(`${documento.arquivo} adicionado a base.`);
      } catch (erro) {
        limpar(linha).append(
          criar("span", { texto: "×", style: "color:var(--erro);font-weight:700" }),
          criar("span", { style: "flex:1", texto: arquivo.name }),
          criar("span", { style: "color:var(--erro);font-size:12px", texto: erro.message })
        );
        Toast.erro(`${arquivo.name}: ${erro.message}`);
      }
    }

    await this.#carregar();
    this.app.atualizarStatus();
  }

  /* --- carga --- */

  async #carregar() {
    limpar(this.painelGraficos).append(carregando("Lendo o indice"));
    try {
      const [indice, documentos, configuracao] = await Promise.all([
        this.api.estatisticasIndice(),
        this.api.listarDocumentos(),
        this.api.configuracao(),
      ]);
      this.indice = indice;
      this.documentos = documentos;
      this.#renderizarMetricas();
      this.#renderizarGraficos();
      this.#renderizarDocumentos();
      this.#renderizarConfiguracao(configuracao);
    } catch (erro) {
      limpar(this.painelGraficos).append(estadoVazio("!", `Falha ao carregar o painel: ${erro.message}`));
    }
  }

  #renderizarMetricas() {
    limpar(this.painelMetricas);
    const pendentes = this.indice.documentos_nao_indexados.length;
    this.painelMetricas.append(
      cartaoMetrica(this.indice.total_documentos, "curriculos na base"),
      cartaoMetrica(this.indice.total_alunos, "alunos indexados"),
      cartaoMetrica(this.indice.total_chunks, "chunks no vector store"),
      cartaoMetrica(pendentes, "fora do indice", pendentes ? "alerta" : "ok")
    );
  }

  #renderizarGraficos() {
    limpar(this.painelGraficos);

    const porAluno = Object.entries(this.indice.chunks_por_aluno)
      .map(([rotulo, valor]) => ({ rotulo, valor, cor: "var(--marca)" }));
    const porSecao = Object.entries(this.indice.chunks_por_secao)
      .map(([rotulo, valor]) => ({ rotulo, valor }));

    this.painelGraficos.append(
      criar("div", { classe: "cartao" }, [
        criar("h3", { texto: "Chunks por aluno" }),
        criar("div", { classe: "dica", texto: "Quanto de cada curriculo esta disponivel para o agente buscar." }),
        porAluno.length
          ? Graficos.barrasHorizontais(porAluno, { sufixo: "" })
          : estadoVazio("—", "Indice vazio."),
      ]),
      criar("div", { classe: "cartao" }, [
        criar("h3", { texto: "Chunks por secao" }),
        criar("div", { classe: "dica", texto: "Distribuicao das secoes que o parser identificou nos PDFs." }),
        porSecao.length
          ? Graficos.rosca(porSecao, { buracoTexto: String(this.indice.total_chunks) })
          : estadoVazio("—", "Indice vazio."),
      ])
    );
  }

  #renderizarDocumentos() {
    limpar(this.painelDocumentos);

    const botaoReindexar = criar("button", {
      classe: "botao secundario pequeno",
      texto: "Reindexar tudo",
      onclick: () => this.#reindexar(botaoReindexar),
    });

    this.painelDocumentos.append(
      criar("div", { style: "display:flex;align-items:center;gap:12px;margin-bottom:12px" }, [
        criar("div", { style: "flex:1" }, [
          criar("h3", { texto: `Curriculos na base (${this.documentos.length})`, style: "margin:0" }),
          criar("div", { classe: "dica", style: "margin:2px 0 0", texto: "Reindexar apaga a colecao e reprocessa todos os PDFs." }),
        ]),
        botaoReindexar,
      ])
    );

    if (!this.documentos.length) {
      this.painelDocumentos.append(estadoVazio("📭", "Nenhum curriculo. Envie um PDF acima."));
      return;
    }

    const linhas = this.documentos.map((documento) => criar("tr", {}, [
      criar("td", {}, [
        criar("div", { style: "font-weight:600", texto: documento.aluno || "(nome nao identificado)" }),
        criar("div", { style: "font-size:11.5px;color:var(--texto-3)", texto: documento.arquivo }),
      ]),
      criar("td", { texto: String(documento.paginas) }),
      criar("td", { texto: Formatar.tamanho(documento.tamanho_kb) }),
      criar("td", {}, [
        criar("span", {
          classe: `etiqueta ${documento.indexado ? "ok" : "alerta"}`,
          texto: documento.indexado ? `${documento.chunks} chunks` : "fora do indice",
        }),
      ]),
      criar("td", { texto: Formatar.data(documento.atualizado_em), style: "font-size:12px;color:var(--texto-3)" }),
      criar("td", {}, [
        criar("div", { classe: "acoes" }, [
          criar("button", {
            classe: "mini-botao", texto: "Reindexar",
            onclick: () => this.#reindexarUm(documento.arquivo),
          }),
          criar("button", {
            classe: "mini-botao erro", texto: "Remover",
            onclick: () => this.#remover(documento),
          }),
        ]),
      ]),
    ]));

    this.painelDocumentos.append(criar("div", { style: "overflow-x:auto" }, [
      criar("table", { classe: "tabela" }, [
        criar("thead", {}, [
          criar("tr", {}, ["Aluno / arquivo", "Paginas", "Tamanho", "Indice", "Atualizado", ""].map((titulo) =>
            criar("th", { texto: titulo })
          )),
        ]),
        criar("tbody", {}, linhas),
      ]),
    ]));
  }

  #renderizarConfiguracao(configuracao) {
    limpar(this.painelConfig);

    const rotulos = {
      versao: "Versao", porta: "Porta", chave_configurada: "Chave configurada",
      chave_mascarada: "Chave (mascarada)", modelo_chat: "Modelo de chat",
      modelo_embedding: "Modelo de embedding", pasta_curriculos: "Pasta dos curriculos",
      pasta_chroma: "Pasta do ChromaDB", pasta_estado: "Pasta de estado",
      colecao: "Colecao", top_k: "Trechos por busca (top_k)",
      chunk_tamanho: "Tamanho do chunk", chunk_sobreposicao: "Sobreposicao",
      auto_indexar: "Auto-indexar na subida", upload_max_mb: "Limite de upload (MB)",
      max_iteracoes_agente: "Max. iteracoes do agente",
    };

    const itens = [];
    for (const [chave, rotulo] of Object.entries(rotulos)) {
      const valor = configuracao[chave];
      if (valor === "" || valor === null || valor === undefined) continue;
      itens.push(criar("dt", { texto: rotulo }));
      itens.push(criar("dd", { texto: String(valor) }));
    }

    this.painelConfig.append(
      criar("h3", { texto: "Configuracao efetiva" }),
      criar("div", { classe: "dica", texto: "Vem das variaveis de ambiente do processo. A chave nunca e exibida por inteiro." }),
      criar("dl", { classe: "lista-config" }, itens)
    );
  }

  /* --- acoes --- */

  async #reindexar(botao) {
    const confirmado = await Modal.confirmar({
      titulo: "Reindexar tudo",
      mensagem: "A colecao inteira e apagada e todos os PDFs sao reprocessados. Isso consome chamadas de embedding da sua chave.",
      textoConfirmar: "Reindexar",
    });
    if (!confirmado) return;

    botao.disabled = true;
    botao.textContent = "Reindexando...";
    try {
      const resultado = await this.api.reindexar();
      Toast.ok(`${resultado.chunks} chunks de ${resultado.arquivos} curriculos em ${resultado.duracao_s}s.`);
      await this.#carregar();
      this.app.atualizarStatus();
    } catch (erro) {
      Toast.erro(`Falha ao reindexar: ${erro.message}`);
    } finally {
      botao.disabled = false;
      botao.textContent = "Reindexar tudo";
    }
  }

  async #reindexarUm(arquivo) {
    try {
      const resultado = await this.api.indexarDocumento(arquivo);
      Toast.ok(`${arquivo}: ${resultado.chunks} chunks.`);
      await this.#carregar();
      this.app.atualizarStatus();
    } catch (erro) {
      Toast.erro(`Falha ao indexar ${arquivo}: ${erro.message}`);
    }
  }

  async #remover(documento) {
    const confirmado = await Modal.confirmar({
      titulo: "Remover curriculo",
      mensagem: `Isso apaga o PDF "${documento.arquivo}", os chunks dele e os PDIs de ${documento.aluno || "esse aluno"}.`,
      textoConfirmar: "Remover",
      perigoso: true,
    });
    if (!confirmado) return;

    try {
      const resultado = await this.api.removerDocumento(documento.arquivo);
      Toast.ok(`Removido: ${resultado.chunks_removidos} chunks, ${resultado.pdis_removidos} PDI(s).`);
      await this.#carregar();
      this.app.atualizarStatus();
    } catch (erro) {
      Toast.erro(`Falha ao remover: ${erro.message}`);
    }
  }
}
