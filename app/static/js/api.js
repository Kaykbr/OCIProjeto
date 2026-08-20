/**
 * Cliente HTTP da API do agente.
 *
 * Uma classe unica com um metodo por endpoint: as telas nunca montam URL nem
 * tratam status HTTP na mao, so chamam `api.listarDocumentos()` e afins.
 */

export class ErroApi extends Error {
  constructor(mensagem, status = 0, detalhe = null) {
    super(mensagem);
    this.name = "ErroApi";
    this.status = status;
    this.detalhe = detalhe;
  }
}

export class ApiClient {
  constructor(base = "") {
    this.base = base;
  }

  async #requisitar(caminho, { metodo = "GET", corpo = null, formulario = null } = {}) {
    const opcoes = { method: metodo, headers: {} };

    if (formulario) {
      opcoes.body = formulario; // o browser define o Content-Type com o boundary
    } else if (corpo !== null) {
      opcoes.headers["Content-Type"] = "application/json";
      opcoes.body = JSON.stringify(corpo);
    }

    let resposta;
    try {
      resposta = await fetch(this.base + caminho, opcoes);
    } catch (erro) {
      throw new ErroApi(`Nao consegui falar com o servidor (${erro.message}).`, 0);
    }

    const tipo = resposta.headers.get("content-type") || "";
    const dados = tipo.includes("application/json") ? await resposta.json().catch(() => null) : null;

    if (!resposta.ok) {
      const detalhe = dados && dados.detail;
      throw new ErroApi(
        typeof detalhe === "string" ? detalhe : `Erro ${resposta.status} em ${caminho}.`,
        resposta.status,
        detalhe
      );
    }
    return dados;
  }

  /* --- diagnostico --- */
  status() { return this.#requisitar("/api/status"); }
  configuracao() { return this.#requisitar("/api/admin/configuracao"); }

  /* --- agente --- */
  perguntar(pergunta, historico = []) {
    return this.#requisitar("/api/chat", { metodo: "POST", corpo: { pergunta, historico } });
  }

  /* --- documentos --- */
  listarDocumentos() { return this.#requisitar("/api/documentos"); }
  obterDocumento(arquivo) { return this.#requisitar(`/api/documentos/${encodeURIComponent(arquivo)}`); }
  urlDownload(arquivo) { return `${this.base}/api/documentos/${encodeURIComponent(arquivo)}/download`; }
  removerDocumento(arquivo) {
    return this.#requisitar(`/api/documentos/${encodeURIComponent(arquivo)}`, { metodo: "DELETE" });
  }
  indexarDocumento(arquivo) {
    return this.#requisitar(`/api/documentos/${encodeURIComponent(arquivo)}/indexar`, { metodo: "POST" });
  }
  enviarDocumento(arquivo, substituir = false) {
    const formulario = new FormData();
    formulario.append("arquivo", arquivo);
    formulario.append("substituir", String(substituir));
    return this.#requisitar("/api/documentos", { metodo: "POST", formulario });
  }

  /* --- alunos --- */
  listarAlunos() { return this.#requisitar("/api/alunos"); }
  obterAluno(nome) { return this.#requisitar(`/api/alunos/${encodeURIComponent(nome)}`); }
  curriculoDoAluno(nome, formato = "secoes") {
    return this.#requisitar(`/api/alunos/${encodeURIComponent(nome)}/curriculo?formato=${formato}`);
  }

  /* --- PDI --- */
  listarPdis(aluno = null) {
    return this.#requisitar("/api/pdi" + (aluno ? `?aluno=${encodeURIComponent(aluno)}` : ""));
  }
  obterPdi(id) { return this.#requisitar(`/api/pdi/${encodeURIComponent(id)}`); }
  gerarPdi(nome_aluno, vaga_alvo, forcar_regeracao = false) {
    return this.#requisitar("/api/pdi", { metodo: "POST", corpo: { nome_aluno, vaga_alvo, forcar_regeracao } });
  }
  removerPdi(id) { return this.#requisitar(`/api/pdi/${encodeURIComponent(id)}`, { metodo: "DELETE" }); }

  /* --- validacoes --- */
  listarValidacoes(filtros = {}) {
    const parametros = new URLSearchParams();
    if (filtros.veredito) parametros.set("veredito", filtros.veredito);
    if (filtros.aluno) parametros.set("aluno", filtros.aluno);
    const consulta = parametros.toString();
    return this.#requisitar("/api/validacoes" + (consulta ? `?${consulta}` : ""));
  }
  resumoValidacoes() { return this.#requisitar("/api/validacoes/resumo"); }
  registrarValidacao(dados) { return this.#requisitar("/api/validacoes", { metodo: "POST", corpo: dados }); }
  atualizarValidacao(id, mudancas) {
    return this.#requisitar(`/api/validacoes/${encodeURIComponent(id)}`, { metodo: "PATCH", corpo: mudancas });
  }
  removerValidacao(id) {
    return this.#requisitar(`/api/validacoes/${encodeURIComponent(id)}`, { metodo: "DELETE" });
  }

  /* --- admin --- */
  estatisticasIndice() { return this.#requisitar("/api/admin/indice"); }
  reindexar() { return this.#requisitar("/api/admin/reindexar", { metodo: "POST" }); }
}
