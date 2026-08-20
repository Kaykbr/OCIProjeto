/**
 * Tela principal do mentor: conversa com o agente e valida cada resposta.
 *
 * O ciclo que essa tela materializa e "o agente propoe, o mentor valida":
 * abaixo de cada resposta ficam os botoes de aprovar / pedir ajuste / rejeitar,
 * que gravam a avaliacao e alimentam a tela de validacoes.
 */

import { ErroApi } from "../api.js";
import { criar, limpar, faixaAviso, Markdown, Modal, Toast, Formatar } from "../nucleo.js";
import { Tela } from "./base.js";

const SUGESTOES = [
  "Quais sao as principais habilidades tecnicas de {aluno}?",
  "Gere o curriculo padronizado de {aluno}.",
  "Monte um PDI para {aluno} mirando uma vaga de Desenvolvedor Full Stack Pleno, com React e Node.js.",
  "Quais projetos voce sugere para {aluno} evoluir na carreira?",
  "Compare a experiencia de {aluno} e {outro} em relacao a dados.",
];

export class TelaMentor extends Tela {
  static rota = "mentor";
  static titulo = "Mentor";
  static subtitulo = "Converse com o agente e valide cada resposta";
  static icone = "💬";
  static perfis = ["mentor", "admin"];
  static telaCheia = true;

  async montar(container) {
    this.container = container;

    this.mensagens = criar("div", { classe: "chat-mensagens" });
    this.sugestoes = criar("div", { classe: "sugestoes" });
    this.entrada = criar("textarea", {
      rows: 1,
      placeholder: "Pergunte sobre um aluno, peca um PDI, um curriculo padronizado...",
      onkeydown: (evento) => {
        if (evento.key === "Enter" && !evento.shiftKey) {
          evento.preventDefault();
          this.#enviarDoFormulario();
        }
      },
      oninput: (evento) => {
        const campo = evento.target;
        campo.style.height = "auto";
        campo.style.height = `${Math.min(campo.scrollHeight, 150)}px`;
      },
    });
    this.botaoEnviar = criar("button", { classe: "botao", texto: "Enviar", onclick: () => this.#enviarDoFormulario() });

    // O aviso de indisponibilidade vive aqui dentro: nas telas de rolagem normal
    // quem coloca a faixa e o roteador, mas o chat controla o proprio layout.
    this.aviso = criar("div", { style: "padding:14px 22px 0" });

    container.append(
      this.aviso,
      this.mensagens,
      this.sugestoes,
      criar("div", { classe: "chat-entrada" }, [this.entrada, this.botaoEnviar])
    );

    this.#renderizarAviso();
    this.aoDestruir(this.estado.em("status", () => this.#renderizarAviso()));

    this.#renderizarConversa();
    this.#renderizarSugestoes();

    this.aoDestruir(this.estado.em("alunos", () => this.#renderizarSugestoes()));
    this.aoDestruir(this.estado.em("alunoFoco", () => this.#renderizarSugestoes()));

    this.entrada.focus();
  }

  acoesDoTopo() {
    const seletor = criar("select", {
      style: "width:auto;min-width:170px;padding:6px 10px;font-size:13px",
      onchange: (evento) => this.estado.definirAlunoFoco(evento.target.value),
    });
    const preencher = () => {
      limpar(seletor);
      seletor.append(criar("option", { value: "", texto: "Todos os alunos" }));
      for (const aluno of this.estado.alunos) {
        seletor.append(criar("option", {
          value: aluno.nome,
          texto: aluno.nome,
          selected: aluno.nome === this.estado.alunoFoco,
        }));
      }
    };
    preencher();
    this.aoDestruir(this.estado.em("alunos", preencher));

    const limparConversa = criar("button", {
      classe: "botao secundario pequeno",
      texto: "Limpar conversa",
      onclick: () => {
        this.estado.limparConversa();
        this.#renderizarConversa();
      },
    });

    return [seletor, limparConversa];
  }

  /* --- render --- */

  #renderizarAviso() {
    limpar(this.aviso);
    const status = this.estado.status;
    if (status && status.aviso) {
      this.aviso.append(faixaAviso(status.aviso, status.chave_configurada ? "" : "erro"));
    }
  }

  #renderizarSugestoes() {
    limpar(this.sugestoes);
    const nomes = this.estado.nomesDosAlunos;
    if (!nomes.length) return;

    const foco = this.estado.alunoFoco || nomes[0];
    const outro = nomes.find((n) => n !== foco) || foco;

    for (const modelo of SUGESTOES) {
      const texto = modelo.replace("{aluno}", foco).replace("{outro}", outro);
      this.sugestoes.append(criar("button", {
        classe: "sugestao",
        texto: texto.length > 58 ? `${texto.slice(0, 58)}...` : texto,
        title: texto,
        onclick: () => this.#enviar(texto),
      }));
    }
  }

  #renderizarConversa() {
    limpar(this.mensagens);

    if (!this.estado.conversa.length) {
      this.mensagens.append(this.#balaoBoasVindas());
      return;
    }
    for (const mensagem of this.estado.conversa) {
      this.mensagens.append(this.#renderizarMensagem(mensagem));
    }
    this.#rolarParaBaixo();
  }

  #balaoBoasVindas() {
    const texto =
      "Ola! Sou o assistente da mentoria. Posso **buscar dados nos curriculos**, " +
      "**gerar curriculos padronizados**, **montar PDIs** comparando o aluno com uma vaga-alvo e " +
      "**sugerir projetos praticos**.\n\n" +
      "Toda resposta minha vem dos curriculos indexados - e voce pode aprovar, pedir ajuste ou " +
      "rejeitar cada uma delas ali embaixo.";
    return criar("div", { classe: "mensagem" }, [
      criar("div", { classe: "autor", texto: "Agente" }),
      criar("div", { classe: "balao", html: Markdown.paraHtml(texto) }),
    ]);
  }

  #renderizarMensagem(mensagem) {
    if (mensagem.papel === "usuario") {
      return criar("div", { classe: "mensagem usuario" }, [
        criar("div", { classe: "autor", texto: "Mentor" }),
        criar("div", { classe: "balao", texto: mensagem.texto }),
      ]);
    }

    const partes = [
      criar("div", { classe: "autor", texto: "Agente" }),
      criar("div", {
        classe: `balao ${mensagem.erro ? "erro" : ""}`,
        html: mensagem.erro ? null : Markdown.paraHtml(mensagem.texto),
        texto: mensagem.erro ? mensagem.texto : null,
      }),
    ];

    if (mensagem.ferramentas && mensagem.ferramentas.length) {
      partes.push(criar("div", { classe: "trilha" }, mensagem.ferramentas.map((ferramenta) => {
        const argumento = Object.values(ferramenta.argumentos || {})[0] || "";
        return criar("span", {
          classe: "chip-ferramenta",
          texto: `${ferramenta.nome}(${String(argumento).slice(0, 30)}) ${ferramenta.duracao_ms}ms`,
          title: JSON.stringify(ferramenta.argumentos, null, 2),
        });
      })));
    }

    if (!mensagem.erro && mensagem.texto) {
      partes.push(this.#barraDeValidacao(mensagem));
    }

    return criar("div", { classe: "mensagem" }, partes);
  }

  #barraDeValidacao(mensagem) {
    const barra = criar("div", { classe: "acoes-mensagem" });

    const marcar = (veredito) => {
      mensagem.veredito = veredito;
      limpar(barra);
      barra.append(criar("span", {
        classe: `etiqueta ${veredito === "aprovado" ? "ok" : veredito === "ajustar" ? "alerta" : "erro"}`,
        texto: veredito === "aprovado" ? "aprovado pelo mentor"
          : veredito === "ajustar" ? "marcado para ajuste" : "rejeitado",
      }));
      if (mensagem.observacao) {
        barra.append(criar("span", { style: "font-size:11.5px;color:var(--texto-3)", texto: mensagem.observacao }));
      }
      if (mensagem.duracao_ms) {
        barra.append(criar("span", {
          style: "font-size:11.5px;color:var(--texto-3);margin-left:auto",
          texto: `${Formatar.duracao(mensagem.duracao_ms)} · ${mensagem.modelo || ""}`,
        }));
      }
    };

    const registrar = async (veredito, observacao = "") => {
      try {
        await this.api.registrarValidacao({
          pergunta: mensagem.pergunta || "",
          resposta: mensagem.texto,
          veredito,
          observacao,
          aluno: this.#alunoDaMensagem(mensagem),
          ferramentas: (mensagem.ferramentas || []).map((f) => f.nome),
        });
        mensagem.observacao = observacao;
        marcar(veredito);
        Toast.ok(veredito === "aprovado" ? "Resposta aprovada." : "Avaliacao registrada.");
        this.app.atualizarStatus();
      } catch (erro) {
        Toast.erro(`Nao consegui registrar: ${erro.message}`);
      }
    };

    const comObservacao = (veredito, titulo) => {
      const campo = criar("textarea", { rows: 4, placeholder: "O que precisa mudar nessa resposta?" });
      Modal.abrir({
        titulo,
        corpo: [
          criar("div", { classe: "campo" }, [
            criar("label", { texto: "Observacao para o historico" }),
            campo,
          ]),
        ],
        acoes: [
          { texto: "Cancelar", classe: "secundario" },
          {
            texto: "Registrar",
            aoClicar: (fechar) => {
              const observacao = campo.value.trim();
              if (!observacao) {
                Toast.erro("Escreva uma observacao para o mentor saber o que ajustar.");
                return;
              }
              fechar();
              registrar(veredito, observacao);
            },
          },
        ],
      });
    };

    if (mensagem.veredito) {
      marcar(mensagem.veredito);
      return barra;
    }

    barra.append(
      criar("span", { classe: "dica", texto: "Validar:" }),
      criar("button", { classe: "mini-botao ok", texto: "Aprovar", onclick: () => registrar("aprovado") }),
      criar("button", {
        classe: "mini-botao alerta", texto: "Precisa ajuste",
        onclick: () => comObservacao("ajustar", "Pedir ajuste na resposta"),
      }),
      criar("button", {
        classe: "mini-botao erro", texto: "Rejeitar",
        onclick: () => comObservacao("rejeitado", "Rejeitar resposta"),
      }),
      criar("button", {
        classe: "mini-botao", texto: "Copiar",
        onclick: async (evento) => {
          try {
            await navigator.clipboard.writeText(mensagem.texto);
            evento.target.textContent = "Copiado!";
            setTimeout(() => { evento.target.textContent = "Copiar"; }, 1600);
          } catch {
            Toast.erro("O navegador bloqueou a copia.");
          }
        },
      })
    );

    if (mensagem.duracao_ms) {
      barra.append(criar("span", {
        style: "font-size:11.5px;color:var(--texto-3);margin-left:auto",
        texto: `${Formatar.duracao(mensagem.duracao_ms)} · ${mensagem.modelo || ""}`,
      }));
    }
    return barra;
  }

  #alunoDaMensagem(mensagem) {
    for (const ferramenta of mensagem.ferramentas || []) {
      const nome = (ferramenta.argumentos || {}).nome_aluno;
      if (nome) return nome;
    }
    return this.estado.alunoFoco || "";
  }

  /* --- envio --- */

  #enviarDoFormulario() {
    const texto = this.entrada.value.trim();
    if (!texto || this.botaoEnviar.disabled) return;
    this.entrada.value = "";
    this.entrada.style.height = "auto";
    this.#enviar(texto);
  }

  async #enviar(pergunta) {
    if (this.botaoEnviar.disabled) return;

    this.estado.adicionarMensagem({ papel: "usuario", texto: pergunta });
    const historico = this.estado.historicoParaApi().slice(0, -1);

    if (this.estado.conversa.length === 1) limpar(this.mensagens);
    this.mensagens.append(this.#renderizarMensagem({ papel: "usuario", texto: pergunta }));

    const carregando = criar("div", { classe: "mensagem" }, [
      criar("div", { classe: "autor", texto: "Agente" }),
      criar("div", { classe: "balao" }, [
        criar("span", { classe: "pontinhos", html: "<span></span><span></span><span></span>" }),
      ]),
    ]);
    this.mensagens.append(carregando);
    this.#rolarParaBaixo();
    this.botaoEnviar.disabled = true;

    try {
      const resposta = await this.api.perguntar(pergunta, historico);
      carregando.remove();

      const mensagem = this.estado.adicionarMensagem({
        papel: "agente",
        pergunta,
        texto: resposta.resposta,
        ferramentas: resposta.ferramentas,
        modelo: resposta.modelo,
        duracao_ms: resposta.duracao_ms,
      });
      this.mensagens.append(this.#renderizarMensagem(mensagem));
    } catch (erro) {
      carregando.remove();
      const texto = erro instanceof ErroApi ? erro.message : `Falha inesperada: ${erro.message}`;
      const mensagem = this.estado.adicionarMensagem({ papel: "agente", texto, erro: true });
      this.mensagens.append(this.#renderizarMensagem(mensagem));
    } finally {
      this.botaoEnviar.disabled = false;
      this.#rolarParaBaixo();
      this.entrada.focus();
    }
  }

  #rolarParaBaixo() {
    requestAnimationFrame(() => {
      this.mensagens.scrollTop = this.mensagens.scrollHeight;
    });
  }
}
