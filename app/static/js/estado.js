/**
 * Estado compartilhado da aplicacao.
 *
 * Guarda o que precisa sobreviver a troca de tela (a conversa do mentor, o
 * perfil escolhido, o cache de status/alunos) e avisa quem estiver ouvindo
 * quando algo muda.
 */

const CHAVE_PERFIL = "agente-mentor:perfil";

export class Estado {
  constructor() {
    this.perfil = localStorage.getItem(CHAVE_PERFIL) || "mentor";
    this.status = null;
    this.alunos = [];
    this.alunoFoco = "";
    this.conversa = [];
    this.pdiSelecionado = null;
    this.documentoSelecionado = null;
    this._ouvintes = new Map();
  }

  /* --- eventos --- */

  em(evento, funcao) {
    if (!this._ouvintes.has(evento)) this._ouvintes.set(evento, new Set());
    this._ouvintes.get(evento).add(funcao);
    return () => this._ouvintes.get(evento).delete(funcao);
  }

  emitir(evento, dados = null) {
    for (const funcao of this._ouvintes.get(evento) || []) {
      try {
        funcao(dados);
      } catch (erro) {
        console.error(`Ouvinte de '${evento}' falhou:`, erro);
      }
    }
  }

  /* --- mutacoes --- */

  definirPerfil(perfil) {
    if (perfil === this.perfil) return;
    this.perfil = perfil;
    localStorage.setItem(CHAVE_PERFIL, perfil);
    this.emitir("perfil", perfil);
  }

  definirStatus(status) {
    this.status = status;
    this.emitir("status", status);
  }

  definirAlunos(alunos) {
    this.alunos = alunos || [];
    if (this.alunoFoco && !this.alunos.some((a) => a.nome === this.alunoFoco)) {
      this.alunoFoco = "";
    }
    this.emitir("alunos", this.alunos);
  }

  definirAlunoFoco(nome) {
    this.alunoFoco = nome || "";
    this.emitir("alunoFoco", this.alunoFoco);
  }

  adicionarMensagem(mensagem) {
    this.conversa.push(mensagem);
    this.emitir("conversa", this.conversa);
    return mensagem;
  }

  limparConversa() {
    this.conversa = [];
    this.emitir("conversa", this.conversa);
  }

  /** Historico no formato que a API espera, limitado as ultimas trocas. */
  historicoParaApi(limite = 10) {
    return this.conversa
      .filter((m) => !m.erro && m.texto)
      .slice(-limite)
      .map((m) => ({ role: m.papel === "usuario" ? "user" : "assistant", content: m.texto }));
  }

  get nomesDosAlunos() {
    return this.alunos.map((a) => a.nome);
  }
}
