/**
 * Montagem da aplicacao: navegacao lateral, roteador por hash e barra de status.
 *
 * Cada tela e uma classe que estende `Tela`; registrar a classe em TELAS ja
 * cria o item de navegacao, a rota e o titulo do topo. Os perfis (mentor,
 * aluno, admin) filtram quais telas aparecem - sao visoes da interface, nao
 * controle de acesso: o desafio pede um agente aberto, sem login.
 */

import { ApiClient } from "./api.js";
import { Estado } from "./estado.js";
import { criar, limpar, Toast, faixaAviso } from "./nucleo.js";
import { TelaMentor } from "./telas/mentor.js";
import { TelaDocumentos } from "./telas/documentos.js";
import { TelaPDI } from "./telas/pdi.js";
import { TelaValidacoes } from "./telas/validacoes.js";
import { TelaAdmin } from "./telas/admin.js";

const TELAS = [TelaMentor, TelaDocumentos, TelaPDI, TelaValidacoes, TelaAdmin];

const PERFIS = [
  { id: "mentor", rotulo: "Mentor" },
  { id: "aluno", rotulo: "Aluno" },
  { id: "admin", rotulo: "Admin" },
];

const ROTA_PADRAO = { mentor: "mentor", admin: "mentor", aluno: "documentos" };

export class Aplicacao {
  constructor(raiz) {
    this.raiz = raiz;
    this.api = new ApiClient();
    this.estado = new Estado();
    this.telaAtual = null;
  }

  async iniciar() {
    this.#montarEsqueleto();
    this.#renderizarNavegacao();

    window.addEventListener("hashchange", () => this.#rotear());
    this.estado.em("perfil", () => {
      this.#renderizarNavegacao();
      const classe = this.#classeDaRota(this.#rotaAtual());
      if (!classe || !classe.perfis.includes(this.estado.perfil)) {
        this.navegar(ROTA_PADRAO[this.estado.perfil]);
      } else {
        this.#rotear();
      }
    });
    this.estado.em("status", () => this.#renderizarStatus());

    this.#rotear();
    await this.atualizarStatus();
  }

  /* --- esqueleto --- */

  #montarEsqueleto() {
    this.navegacao = criar("nav", { classe: "navegacao" });
    this.rodapeLateral = criar("div", { classe: "rodape-lateral" });

    this.tituloTela = criar("h2", { texto: "" });
    this.subtituloTela = criar("div", { classe: "subtitulo", texto: "" });
    this.acoesTopo = criar("div", { style: "display:flex;gap:8px;align-items:center" });
    this.pilulaStatus = criar("div", { classe: "pilula" }, [
      criar("span", { classe: "ponto" }),
      criar("span", { texto: "verificando..." }),
    ]);

    this.seletorPerfil = criar("div", { classe: "seletor-perfil" }, PERFIS.map((perfil) =>
      criar("button", {
        texto: perfil.rotulo,
        classe: perfil.id === this.estado.perfil ? "ativo" : "",
        dataset: { perfil: perfil.id },
        onclick: () => this.estado.definirPerfil(perfil.id),
      })
    ));

    this.conteudo = criar("div", { classe: "tela" });

    this.botaoMenu = criar("button", {
      classe: "abrir-menu botao secundario pequeno",
      texto: "≡",
      title: "Abrir navegacao",
      onclick: () => this.lateral.classList.toggle("aberta"),
    });

    this.lateral = criar("aside", { classe: "lateral" }, [
      criar("div", { classe: "marca" }, [
        criar("h1", { texto: "Agente Mentor de Carreiras" }),
        criar("span", { texto: "Alura Agent · Oracle Cloud" }),
      ]),
      this.navegacao,
      this.rodapeLateral,
    ]);
    // Em tela estreita a navegacao e off-canvas: escolher um item ja fecha.
    this.lateral.addEventListener("click", (evento) => {
      if (evento.target.closest(".nav-item")) this.lateral.classList.remove("aberta");
    });

    this.raiz.append(criar("div", { classe: "aplicacao" }, [
      this.lateral,
      criar("main", { classe: "conteudo" }, [
        criar("header", { classe: "topo" }, [
          this.botaoMenu,
          criar("div", { classe: "identificacao" }, [this.tituloTela, this.subtituloTela]),
          criar("div", { classe: "direita" }, [this.acoesTopo, this.seletorPerfil, this.pilulaStatus]),
        ]),
        this.conteudo,
      ]),
    ]));
  }

  #renderizarNavegacao() {
    limpar(this.navegacao);
    this.navegacao.append(criar("div", { classe: "rotulo", texto: "Navegacao" }));

    for (const Classe of TELAS) {
      if (!Classe.perfis.includes(this.estado.perfil)) continue;
      const ativo = this.#rotaAtual() === Classe.rota;
      this.navegacao.append(criar("a", {
        classe: `nav-item ${ativo ? "ativo" : ""}`,
        href: `#/${Classe.rota}`,
        dataset: { rota: Classe.rota },
      }, [
        criar("span", { classe: "icone", texto: Classe.icone }),
        criar("span", { texto: Classe.titulo }),
        this.#contadorDaRota(Classe.rota),
      ]));
    }

    for (const botao of this.seletorPerfil.children) {
      botao.classList.toggle("ativo", botao.dataset.perfil === this.estado.perfil);
    }
  }

  #contadorDaRota(rota) {
    const status = this.estado.status;
    if (!status) return null;
    const valores = {
      documentos: status.documentos,
      pdi: status.pdis,
      validacoes: status.validacoes_pendentes,
    };
    const valor = valores[rota];
    return valor ? criar("span", { classe: "contador", texto: String(valor) }) : null;
  }

  #renderizarStatus() {
    const status = this.estado.status;
    limpar(this.pilulaStatus);

    if (!status) {
      this.pilulaStatus.append(criar("span", { classe: "ponto" }), criar("span", { texto: "verificando..." }));
      return;
    }

    this.pilulaStatus.append(
      criar("span", { classe: `ponto ${status.pronto ? "ok" : "ruim"}` }),
      criar("span", {
        texto: status.pronto
          ? `${status.chunks_indexados} trechos · ${status.alunos.length} alunos · ${status.modelo_chat}`
          : "agente indisponivel",
      })
    );

    limpar(this.rodapeLateral).append(
      criar("div", { texto: `v${status.versao || "-"}` }),
      criar("div", { texto: status.modelo_chat ? `chat: ${status.modelo_chat}` : "chat: -" }),
      criar("div", { texto: status.modelo_embedding ? `embeddings: ${status.modelo_embedding}` : "embeddings: -" }),
      criar("div", { texto: "acesso aberto · sem login" })
    );

    this.#renderizarNavegacao();
  }

  async atualizarStatus() {
    try {
      const status = await this.api.status();
      this.estado.definirStatus(status);
      if (status.chunks_indexados > 0) {
        this.estado.definirAlunos(await this.api.listarAlunos());
      } else {
        this.estado.definirAlunos([]);
      }
    } catch (erro) {
      console.error("Falha ao consultar status:", erro);
      this.estado.definirStatus(null);
      Toast.erro("Nao consegui falar com a API do agente.");
    }
  }

  /* --- roteamento --- */

  #rotaAtual() {
    return (location.hash || "").replace(/^#\/?/, "").split("?")[0];
  }

  #classeDaRota(rota) {
    return TELAS.find((Classe) => Classe.rota === rota) || null;
  }

  navegar(rota) {
    location.hash = `#/${rota}`;
  }

  async #rotear() {
    const rota = this.#rotaAtual();
    let Classe = this.#classeDaRota(rota);

    if (!Classe || !Classe.perfis.includes(this.estado.perfil)) {
      const destino = ROTA_PADRAO[this.estado.perfil] || "documentos";
      if (rota !== destino) { this.navegar(destino); return; }
      Classe = this.#classeDaRota(destino);
    }
    if (!Classe) return;

    if (this.telaAtual) {
      this.telaAtual.destruir();
      this.telaAtual = null;
    }

    this.tituloTela.textContent = Classe.titulo;
    this.subtituloTela.textContent = Classe.subtitulo;
    this.conteudo.className = Classe.telaCheia ? "tela-cheia chat" : "tela";
    limpar(this.conteudo);
    limpar(this.acoesTopo);
    this.#renderizarNavegacao();

    const tela = new Classe({ api: this.api, estado: this.estado, app: this });
    this.telaAtual = tela;

    const status = this.estado.status;
    if (status && status.aviso && !Classe.telaCheia) {
      this.conteudo.append(faixaAviso(status.aviso, status.chave_configurada ? "" : "erro"));
    }

    try {
      await tela.montar(this.conteudo);
      for (const acao of tela.acoesDoTopo()) this.acoesTopo.append(acao);
    } catch (erro) {
      console.error(`Falha ao montar a tela '${Classe.rota}':`, erro);
      limpar(this.conteudo).append(faixaAviso(`Erro ao abrir a tela: ${erro.message}`, "erro"));
    }
  }
}

const aplicacao = new Aplicacao(document.getElementById("raiz"));
aplicacao.iniciar();
window.aplicacao = aplicacao; // facilita inspecionar pelo console durante a demo
