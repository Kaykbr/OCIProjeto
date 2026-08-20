/**
 * Utilitarios compartilhados: construcao de DOM, markdown, toasts e modais.
 *
 * Tudo que insere conteudo vindo do servidor passa por `escapar()` antes de
 * virar HTML - o texto do LLM e do usuario nunca e injetado cru.
 */

/* ---------------------------------------------------------------------------
 * DOM
 * ------------------------------------------------------------------------- */

/**
 * Cria um elemento. `atributos` aceita classe, texto, html, dataset, on* e
 * qualquer atributo comum. `filhos` aceita nos, strings ou null.
 */
export function criar(tag, atributos = {}, filhos = []) {
  const elemento = document.createElement(tag);

  for (const [chave, valor] of Object.entries(atributos)) {
    if (valor === null || valor === undefined || valor === false) continue;
    if (chave === "classe") elemento.className = valor;
    else if (chave === "texto") elemento.textContent = valor;
    else if (chave === "html") elemento.innerHTML = valor;
    else if (chave === "dataset") Object.assign(elemento.dataset, valor);
    else if (chave.startsWith("on") && typeof valor === "function") {
      elemento.addEventListener(chave.slice(2).toLowerCase(), valor);
    } else if (valor === true) elemento.setAttribute(chave, "");
    else elemento.setAttribute(chave, valor);
  }

  for (const filho of [].concat(filhos)) {
    if (filho === null || filho === undefined || filho === false) continue;
    elemento.append(filho instanceof Node ? filho : document.createTextNode(String(filho)));
  }
  return elemento;
}

export function limpar(elemento) {
  while (elemento.firstChild) elemento.removeChild(elemento.firstChild);
  return elemento;
}

export function escapar(texto) {
  return String(texto ?? "").replace(/[&<>"']/g, (caractere) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[caractere]
  ));
}

/* ---------------------------------------------------------------------------
 * Formatacao
 * ------------------------------------------------------------------------- */

export const Formatar = {
  data(valor) {
    if (!valor) return "-";
    const data = new Date(valor);
    if (Number.isNaN(data.getTime())) return String(valor);
    return data.toLocaleString("pt-BR", {
      day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
  },
  duracao(ms) {
    if (!ms && ms !== 0) return "-";
    return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
  },
  tamanho(kb) {
    return kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb} KB`;
  },
  plural(quantidade, singular, plural) {
    return `${quantidade} ${quantidade === 1 ? singular : plural}`;
  },
  primeiroNome(nome) {
    return String(nome || "").trim().split(/\s+/)[0] || "";
  },
};

/* ---------------------------------------------------------------------------
 * Markdown minimo
 * ------------------------------------------------------------------------- */

export class Markdown {
  /** Converte markdown simples em HTML seguro (o texto e escapado antes). */
  static paraHtml(texto) {
    const linhas = escapar(texto || "").split("\n");
    let html = "";
    let emLista = false;
    let emTabela = false;

    const fecharLista = () => { if (emLista) { html += "</ul>"; emLista = false; } };
    const fecharTabela = () => { if (emTabela) { html += "</tbody></table>"; emTabela = false; } };

    const inline = (t) => t
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+?)`/g, "<code>$1</code>")
      .replace(/(^|[^*])\*([^*\n]+?)\*(?!\*)/g, "$1<em>$2</em>");

    for (const linha of linhas) {
      const l = linha.trim();
      if (!l) { fecharLista(); fecharTabela(); continue; }

      // separador de tabela: |---|---|
      if (/^\|[\s:|-]+\|$/.test(l) && emTabela) continue;

      if (l.startsWith("|") && l.endsWith("|")) {
        const celulas = l.slice(1, -1).split("|").map((c) => inline(c.trim()));
        if (!emTabela) {
          fecharLista();
          html += "<table><thead><tr>" + celulas.map((c) => `<th>${c}</th>`).join("") + "</tr></thead><tbody>";
          emTabela = true;
        } else {
          html += "<tr>" + celulas.map((c) => `<td>${c}</td>`).join("") + "</tr>";
        }
        continue;
      }
      fecharTabela();

      const titulo = l.match(/^(#{1,4})\s+(.*)$/);
      if (titulo) {
        fecharLista();
        const nivel = Math.min(titulo[1].length + 1, 4);
        html += `<h${nivel}>${inline(titulo[2])}</h${nivel}>`;
        continue;
      }

      const item = l.match(/^(?:[-*]|\d+\.)\s+(.*)$/);
      if (item) {
        if (!emLista) { html += "<ul>"; emLista = true; }
        html += `<li>${inline(item[1])}</li>`;
        continue;
      }

      fecharLista();
      html += `<p>${inline(l)}</p>`;
    }
    fecharLista();
    fecharTabela();
    return html;
  }

  /** Versao em texto puro, para previews curtos. */
  static paraTexto(markdown, limite = 220) {
    const limpo = String(markdown || "")
      .replace(/[#*`>]/g, "")
      .replace(/\n+/g, " ")
      .trim();
    return limpo.length > limite ? `${limpo.slice(0, limite)}...` : limpo;
  }
}

/* ---------------------------------------------------------------------------
 * Toast
 * ------------------------------------------------------------------------- */

export class Toast {
  static #container() {
    let container = document.getElementById("toasts");
    if (!container) {
      container = criar("div", { id: "toasts" });
      document.body.append(container);
    }
    return container;
  }

  static mostrar(mensagem, tipo = "info", duracaoMs = 4200) {
    const elemento = criar("div", { classe: `toast ${tipo}`, texto: mensagem });
    Toast.#container().append(elemento);
    setTimeout(() => {
      elemento.style.transition = "opacity .25s";
      elemento.style.opacity = "0";
      setTimeout(() => elemento.remove(), 250);
    }, duracaoMs);
    return elemento;
  }

  static ok(mensagem) { return Toast.mostrar(mensagem, "ok"); }
  static erro(mensagem) { return Toast.mostrar(mensagem, "erro", 6500); }
  static info(mensagem) { return Toast.mostrar(mensagem, "info"); }
}

/* ---------------------------------------------------------------------------
 * Modal
 * ------------------------------------------------------------------------- */

export class Modal {
  /**
   * Abre um modal. `corpo` e um no ou lista de nos.
   * `acoes` e uma lista de { texto, classe, aoClicar(fechar) }.
   */
  static abrir({ titulo, corpo, acoes = [], aoFechar = null }) {
    const fundo = criar("div", { classe: "fundo-modal" });
    const fechar = () => { fundo.remove(); document.removeEventListener("keydown", aoTeclar); if (aoFechar) aoFechar(); };
    const aoTeclar = (evento) => { if (evento.key === "Escape") fechar(); };

    const rodape = criar("footer", {}, acoes.map((acao) =>
      criar("button", {
        classe: `botao ${acao.classe || "secundario"}`,
        texto: acao.texto,
        onclick: () => acao.aoClicar ? acao.aoClicar(fechar) : fechar(),
      })
    ));

    const modal = criar("div", { classe: "modal" }, [
      criar("header", {}, [criar("h3", { texto: titulo })]),
      criar("div", { classe: "corpo" }, corpo),
      acoes.length ? rodape : null,
    ]);

    fundo.append(modal);
    fundo.addEventListener("click", (evento) => { if (evento.target === fundo) fechar(); });
    document.addEventListener("keydown", aoTeclar);
    document.body.append(fundo);

    const primeiroCampo = modal.querySelector("input, textarea, select");
    if (primeiroCampo) primeiroCampo.focus();
    return fechar;
  }

  static confirmar({ titulo, mensagem, textoConfirmar = "Confirmar", perigoso = false }) {
    return new Promise((resolver) => {
      let confirmado = false;
      Modal.abrir({
        titulo,
        corpo: [criar("p", { texto: mensagem, style: "margin:0;color:var(--texto-2)" })],
        acoes: [
          { texto: "Cancelar", classe: "secundario", aoClicar: (fechar) => fechar() },
          {
            texto: textoConfirmar,
            classe: perigoso ? "perigo" : "",
            aoClicar: (fechar) => { confirmado = true; fechar(); },
          },
        ],
        aoFechar: () => resolver(confirmado),
      });
    });
  }
}

/* ---------------------------------------------------------------------------
 * Blocos visuais reutilizados por varias telas
 * ------------------------------------------------------------------------- */

export function cartaoMetrica(valor, rotulo, tom = "") {
  return criar("div", { classe: "cartao metrica" }, [
    criar("div", { classe: `valor ${tom}`, texto: String(valor) }),
    criar("div", { classe: "rotulo", texto: rotulo }),
  ]);
}

export function estadoVazio(icone, mensagem, acao = null) {
  return criar("div", { classe: "vazio" }, [
    criar("span", { classe: "icone", texto: icone }),
    criar("div", { texto: mensagem }),
    acao,
  ]);
}

export function carregando(mensagem = "Carregando") {
  return criar("div", { classe: "vazio" }, [
    criar("span", { classe: "girando", style: "margin-bottom:10px" }),
    criar("div", { texto: mensagem }),
  ]);
}

export function faixaAviso(mensagem, tipo = "") {
  return criar("div", { classe: `aviso-faixa ${tipo}` }, [
    criar("span", { texto: tipo === "erro" ? "!" : "!" , style: "font-weight:700" }),
    criar("span", { texto: mensagem }),
  ]);
}
