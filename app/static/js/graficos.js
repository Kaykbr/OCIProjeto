/**
 * Graficos em SVG puro.
 *
 * Sem biblioteca externa de proposito: a instancia da OCI serve a pagina sem
 * acesso a CDN e o conjunto de graficos aqui e pequeno e fixo (medidor, barras,
 * barras de gap e rosca). Todos usam as variaveis de cor do design system.
 */

import { criar } from "./nucleo.js";

const NS = "http://www.w3.org/2000/svg";

function svg(tag, atributos = {}, filhos = []) {
  const elemento = document.createElementNS(NS, tag);
  for (const [chave, valor] of Object.entries(atributos)) {
    if (valor === null || valor === undefined) continue;
    if (chave === "texto") elemento.textContent = valor;
    else elemento.setAttribute(chave, valor);
  }
  for (const filho of [].concat(filhos)) if (filho) elemento.append(filho);
  return elemento;
}

/** Cor semantica a partir de um percentual (quanto maior, melhor). */
export function corPorNivel(valor) {
  if (valor >= 70) return "var(--ok)";
  if (valor >= 40) return "var(--alerta)";
  return "var(--erro)";
}

export const CORES_CRITICIDADE = {
  alta: "var(--erro)",
  media: "var(--alerta)",
  baixa: "var(--ciano)",
};

const PALETA = [
  "var(--marca)", "var(--ciano)", "var(--roxo)", "var(--ok)",
  "var(--alerta)", "#e06c9f", "#7d8fe0", "#5fb3a1",
];

function arco(cx, cy, raio, inicioGraus, fimGraus) {
  const rad = (graus) => ((graus - 90) * Math.PI) / 180;
  const x1 = cx + raio * Math.cos(rad(inicioGraus));
  const y1 = cy + raio * Math.sin(rad(inicioGraus));
  const x2 = cx + raio * Math.cos(rad(fimGraus));
  const y2 = cy + raio * Math.sin(rad(fimGraus));
  const maior = fimGraus - inicioGraus > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${raio} ${raio} 0 ${maior} 1 ${x2} ${y2}`;
}

export class Graficos {
  /**
   * Medidor circular (0 a 100). Usado para a aderencia do aluno a vaga.
   */
  static medidor(valor, { rotulo = "", tamanho = 150 } = {}) {
    const percentual = Math.max(0, Math.min(100, Math.round(valor || 0)));
    const centro = tamanho / 2;
    const raio = centro - 14;
    const cor = corPorNivel(percentual);

    const grafico = svg("svg", {
      class: "grafico",
      viewBox: `0 0 ${tamanho} ${tamanho}`,
      style: `max-width:${tamanho}px;margin:0 auto`,
      role: "img",
      "aria-label": `${rotulo || "Aderencia"}: ${percentual}%`,
    }, [
      svg("path", {
        d: arco(centro, centro, raio, 0, 359.99),
        fill: "none", stroke: "var(--painel-3)", "stroke-width": 11, "stroke-linecap": "round",
      }),
      percentual > 0 ? svg("path", {
        d: arco(centro, centro, raio, 0, Math.max(1, (percentual / 100) * 359.99)),
        fill: "none", stroke: cor, "stroke-width": 11, "stroke-linecap": "round",
      }) : null,
      svg("text", {
        x: centro, y: centro + 2, "text-anchor": "middle",
        "font-size": 30, "font-weight": 700, fill: cor, texto: `${percentual}`,
      }),
      svg("text", {
        x: centro, y: centro + 22, "text-anchor": "middle",
        "font-size": 11, fill: "var(--texto-3)", texto: "% de aderencia",
      }),
    ]);

    return grafico;
  }

  /**
   * Barras horizontais simples: [{ rotulo, valor, cor?, detalhe? }].
   * Renderizado em HTML (nao SVG) para o texto quebrar linha naturalmente.
   */
  static barrasHorizontais(dados, { maximo = null, sufixo = "", mostrarValor = true } = {}) {
    const teto = maximo ?? Math.max(1, ...dados.map((d) => d.valor || 0));
    return criar("div", {}, dados.map((item) => {
      const largura = Math.max(1, Math.round(((item.valor || 0) / teto) * 100));
      return criar("div", { classe: "linha-grafico" }, [
        criar("div", {}, [
          criar("div", { classe: "nome", texto: item.rotulo }),
          item.detalhe ? criar("div", { classe: "evidencia", texto: item.detalhe }) : null,
          criar("div", { classe: "barra", style: "margin-top:6px" }, [
            criar("span", { style: `width:${largura}%;background:${item.cor || corPorNivel(item.valor)}` }),
          ]),
        ]),
        mostrarValor
          ? criar("div", { classe: "numero", texto: `${item.valor}${sufixo}` })
          : null,
      ]);
    }));
  }

  /**
   * Barra de gap: mostra o nivel atual preenchido e o alvo como marcador.
   * dados: [{ rotulo, atual, alvo, criticidade, detalhe }]
   */
  static barrasGap(dados) {
    return criar("div", {}, dados.map((item) => {
      const atual = Math.max(0, Math.min(100, item.atual || 0));
      const alvo = Math.max(0, Math.min(100, item.alvo ?? 80));
      const cor = CORES_CRITICIDADE[item.criticidade] || "var(--alerta)";

      return criar("div", { classe: "linha-grafico" }, [
        criar("div", {}, [
          criar("div", { style: "display:flex;gap:8px;align-items:center;flex-wrap:wrap" }, [
            criar("span", { classe: "nome", texto: item.rotulo }),
            criar("span", {
              classe: `etiqueta ${item.criticidade === "alta" ? "erro" : item.criticidade === "media" ? "alerta" : "neutra"}`,
              texto: item.criticidade || "media",
            }),
          ]),
          item.detalhe ? criar("div", { classe: "evidencia", texto: item.detalhe }) : null,
          criar("div", { classe: "barra-dupla", title: `Hoje ${atual}% / alvo ${alvo}%` }, [
            criar("div", { classe: "alvo" }),
            criar("div", { classe: "atual", style: `width:${atual}%;background:${cor}` }),
            criar("div", { classe: "marcador", style: `left:calc(${alvo}% - 1px)` }),
          ]),
        ]),
        criar("div", { classe: "numero", texto: `${atual} → ${alvo}` }),
      ]);
    }));
  }

  /**
   * Rosca (donut) com legenda. dados: [{ rotulo, valor }].
   */
  static rosca(dados, { tamanho = 160, buracoTexto = "" } = {}) {
    const total = dados.reduce((soma, item) => soma + (item.valor || 0), 0);
    const centro = tamanho / 2;
    const raio = centro - 10;

    const fatias = [];
    let anguloAtual = 0;
    dados.forEach((item, indice) => {
      const fracao = total > 0 ? (item.valor || 0) / total : 0;
      const angulo = fracao * 359.99;
      if (angulo > 0.4) {
        fatias.push(svg("path", {
          d: arco(centro, centro, raio, anguloAtual, anguloAtual + angulo),
          fill: "none",
          stroke: PALETA[indice % PALETA.length],
          "stroke-width": 15,
        }));
      }
      anguloAtual += angulo;
    });

    const grafico = svg("svg", {
      class: "grafico",
      viewBox: `0 0 ${tamanho} ${tamanho}`,
      style: `max-width:${tamanho}px`,
    }, [
      ...(fatias.length ? fatias : [svg("circle", {
        cx: centro, cy: centro, r: raio, fill: "none", stroke: "var(--painel-3)", "stroke-width": 15,
      })]),
      buracoTexto ? svg("text", {
        x: centro, y: centro + 5, "text-anchor": "middle",
        "font-size": 20, "font-weight": 700, fill: "var(--texto)", texto: buracoTexto,
      }) : null,
    ]);

    const legenda = criar("div", { style: "display:flex;flex-direction:column;gap:6px;font-size:12.5px" },
      dados.map((item, indice) => criar("div", { style: "display:flex;align-items:center;gap:8px" }, [
        criar("span", {
          style: `width:9px;height:9px;border-radius:2px;flex:none;background:${PALETA[indice % PALETA.length]}`,
        }),
        criar("span", { style: "flex:1;color:var(--texto-2)", texto: item.rotulo }),
        criar("span", { style: "color:var(--texto-3);font-variant-numeric:tabular-nums", texto: String(item.valor) }),
      ]))
    );

    return criar("div", { style: "display:flex;gap:18px;align-items:center;flex-wrap:wrap" }, [
      grafico,
      criar("div", { style: "flex:1;min-width:150px" }, [legenda]),
    ]);
  }

  /**
   * Linha do tempo vertical do cronograma do PDI.
   * blocos: [{ bloco, periodo, objetivos[], marco }]
   */
  static cronograma(blocos) {
    return criar("div", { classe: "cronograma" }, blocos.map((item) =>
      criar("div", { classe: "bloco-cronograma" }, [
        criar("div", { classe: "titulo", texto: item.bloco }),
        item.periodo ? criar("div", { classe: "periodo", texto: item.periodo }) : null,
        item.objetivos && item.objetivos.length
          ? criar("ul", {}, item.objetivos.map((objetivo) => criar("li", { texto: objetivo })))
          : null,
        item.marco ? criar("div", { classe: "marco", texto: `Marco: ${item.marco}` }) : null,
      ])
    ));
  }
}
