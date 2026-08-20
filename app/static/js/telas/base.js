/**
 * Contrato de uma tela.
 *
 * O roteador instancia a classe, chama `montar()` com o container ja limpo e
 * chama `destruir()` antes de trocar de tela. Os metadados estaticos (rota,
 * titulo, icone, perfis) alimentam a navegacao lateral automaticamente.
 */

export class Tela {
  /** Rota sem o '#/', ex.: "mentor". */
  static rota = "";
  /** Texto do item na navegacao lateral. */
  static titulo = "";
  /** Subtitulo mostrado na barra do topo. */
  static subtitulo = "";
  /** Icone (emoji) do item de navegacao. */
  static icone = "•";
  /** Perfis que enxergam esta tela. */
  static perfis = ["mentor", "aluno", "admin"];
  /** true = a tela controla a propria rolagem (ex.: chat). */
  static telaCheia = false;

  constructor({ api, estado, app }) {
    this.api = api;
    this.estado = estado;
    this.app = app;
    this._descartes = [];
  }

  /** Registra um cancelador de ouvinte para ser chamado no destruir(). */
  aoDestruir(funcao) {
    this._descartes.push(funcao);
  }

  /** Monta o conteudo da tela dentro do container. */
  async montar(_container) {
    throw new Error("montar() precisa ser implementado pela tela.");
  }

  /** Acoes extras exibidas na barra do topo (nos DOM). */
  acoesDoTopo() {
    return [];
  }

  destruir() {
    for (const descartar of this._descartes) {
      try {
        descartar();
      } catch (erro) {
        console.error("Falha ao descartar ouvinte:", erro);
      }
    }
    this._descartes = [];
  }
}
