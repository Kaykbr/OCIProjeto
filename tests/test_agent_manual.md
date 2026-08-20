# Roteiro de testes manuais — Agente Mentor de Carreiras

Dois blocos: **A. o agente** (pergunta → ferramenta → resposta fundamentada) e
**B. o sistema** (as quatro telas, upload, PDI gráfico e validações).

Há duas formas de executar o bloco A:

- **Automática:** `python scripts/rodar_testes.py` roda os 5 casos, imprime o
  resultado e injeta as respostas reais no `README.md`.
- **Manual:** abra a interface e digite cada pergunta na tela **Mentor**. Os chips
  embaixo de cada resposta mostram qual ferramenta foi chamada — é por eles que
  você confere a coluna "ferramenta esperada".

## Pré-requisitos

```bash
cp .env.example .env          # e preencha GEMINI_API_KEY
python scripts/gerar_curriculos_exemplo.py
python scripts/indexar_curriculos.py
uvicorn app.main:app --reload
```

O `GET /api/status` deve responder `"pronto": true` com 4 alunos indexados, e a
bolinha no canto superior direito da interface deve ficar **verde**.

---

# A. O agente

### A1. Busca factual no currículo

> **Pergunta:** Quais são as principais habilidades técnicas do Carlos Andrade?

- **Ferramenta esperada:** `buscar_info_aluno`
- **Aprovado se a resposta:**
  - [ ] cita Python, Django/DRF, SQL, PostgreSQL, Celery, pytest;
  - [ ] menciona que ele **não tem experiência com cloud/Docker** (está explícito no currículo);
  - [ ] **não inventa** nenhuma tecnologia que não está no PDF (ex.: AWS, Kubernetes, React).

### A2. Currículo padronizado

> **Pergunta:** Gere o currículo padronizado da Fernanda Lima.

- **Ferramenta esperada:** `gerar_curriculo_padronizado`
- **Aprovado se a resposta:**
  - [ ] traz as 6 seções do template, nesta ordem: Dados pessoais, Resumo profissional,
        Experiências profissionais, Formação acadêmica, Habilidades técnicas, Idiomas;
  - [ ] mantém as duas experiências em ordem cronológica inversa;
  - [ ] preserva números e métricas do original (12 dashboards, data warehouse de 2 TB);
  - [ ] preserva os níveis declarados (SQL avançado, Python básico).

### A3. PDI contra uma vaga-alvo

> **Pergunta:** Monte um PDI para o Pedro Souza mirando uma vaga de Desenvolvedor
> Full Stack Pleno, com React e Node.js.

- **Ferramenta esperada:** `gerar_pdi`
- **Aprovado se a resposta:**
  - [ ] tem as 4 seções: Habilidades atuais, Gaps identificados, Ações recomendadas, Prazo sugerido;
  - [ ] classifica React/TypeScript como habilidade **atual**;
  - [ ] classifica backend (Node.js/Express, modelagem de banco, APIs) como **gap** —
        o currículo diz explicitamente que ele não tem isso;
  - [ ] as ações são específicas e verificáveis ("estudar Node.js" reprova);
  - [ ] o prazo é dividido em blocos com marco de saída.

### A4. Sugestão de projetos práticos

> **Pergunta:** Quais projetos você sugere para a Ana Beatriz evoluir para SDET?

- **Ferramenta esperada:** `sugerir_projetos`
- **Aprovado se a resposta:**
  - [ ] traz exatamente 3 projetos, com objetivo, tecnologias, dificuldade e entregável;
  - [ ] parte do que ela já domina (Selenium, Java, TestNG) e ataca os gaps declarados
        (testes de API, performance, CI/CD, Docker);
  - [ ] a dificuldade é crescente entre os três.

### A5. Comparação entre dois alunos

> **Pergunta:** Compare a experiência de Carlos e Fernanda em relação a dados.

- **Ferramenta esperada:** `buscar_info_aluno` **duas vezes**
- **Aprovado se a resposta:**
  - [ ] os chips mostram duas chamadas, uma para cada aluno;
  - [ ] distingue os perfis: Carlos usa SQL de forma transacional (PostgreSQL,
        migrations, otimização de query), Fernanda de forma analítica (SQL analítico,
        Power BI, modelagem dimensional);
  - [ ] não mistura o histórico de um com o do outro.

### Casos de borda do agente

| # | Pergunta | Comportamento esperado |
|---|---|---|
| A6 | "Fale sobre o Carlos" | Resolve o nome parcial para **Carlos Andrade** |
| A7 | "Quais as habilidades do João Silva?" | Diz que não há currículo desse aluno e **lista os indexados** |
| A8 | "Monte um PDI" (sem dizer o aluno) | **Pergunta de qual aluno** antes de chamar ferramenta |
| A9 | "O Carlos tem certificação AWS?" | Responde que **não consta no currículo** |
| A10 | "Qual a capital da França?" | Responde sem ferramenta, ou reconduz ao escopo da mentoria |

---

# B. O sistema (telas)

### B1. Perfis e navegação

- [ ] O seletor **Mentor / Aluno / Admin** no topo troca os itens da lateral.
- [ ] Perfil **Aluno** não vê "Mentor", "Validações" nem "Painel admin"; ao entrar,
      cai em "Base de documentos".
- [ ] Perfil **Admin** vê as 5 telas.
- [ ] O perfil escolhido sobrevive ao recarregar a página (fica no `localStorage`).
- [ ] Abrir `#/admin` com o perfil Aluno **redireciona** em vez de mostrar a tela.

### B2. Base de documentos (todos os perfis)

- [ ] Lista os 4 currículos com aluno, páginas, tamanho e a etiqueta de chunks.
- [ ] O filtro de busca reduz a lista por nome de aluno ou de arquivo.
- [ ] Clicar num item mostra o texto extraído com as abas de seção
      (Dados pessoais, Resumo, Experiências, Formação, Habilidades, Idiomas).
- [ ] A aba "Documento completo" mostra o texto inteiro.
- [ ] "Abrir PDF" baixa/abre o arquivo original.
- [ ] O botão "Remover" só aparece no perfil Admin.

### B3. Painel admin — upload

- [ ] Arrastar um PDF para a área de upload envia e **indexa na hora**
      (a linha de progresso termina com "N chunks indexados").
- [ ] Enviar um arquivo que não é PDF é recusado com mensagem clara.
- [ ] Enviar o mesmo nome duas vezes gera `nome_2.pdf` em vez de sobrescrever.
- [ ] Um nome com acento e espaço vira `nome_normalizado.pdf`.
- [ ] Depois do upload, o aluno novo aparece na lista de alunos do seletor da tela Mentor.

### B4. Painel admin — índice

- [ ] Os 4 cartões batem com a realidade (currículos na base, alunos, chunks, fora do índice).
- [ ] "Chunks por aluno" e "Chunks por seção" desenham os gráficos.
- [ ] "Reindexar tudo" pede confirmação e, ao final, mostra chunks e tempo.
- [ ] "Remover" um currículo apaga o PDF, os chunks **e** os PDIs daquele aluno.
- [ ] A configuração efetiva aparece com a chave **mascarada** (nunca por inteiro).

### B5. PDI gráfico

- [ ] Escolher aluno + vaga-alvo e clicar em "Gerar PDI" produz o plano em alguns segundos.
- [ ] O medidor mostra a aderência e muda de cor (verde ≥ 70, amarelo ≥ 40, vermelho abaixo).
- [ ] Os 4 cartões trazem aderência, gaps (com quantos críticos), prazo e esforço total.
- [ ] "Habilidades atuais" mostra a evidência do currículo em cada linha.
- [ ] "Gaps" mostra a barra do nível atual, o marcador do nível-alvo e a etiqueta de criticidade.
- [ ] As ações vêm numeradas, com o gap relacionado e o esforço em horas.
- [ ] O cronograma aparece como linha do tempo, com marco por bloco.
- [ ] Gerar de novo o **mesmo aluno + mesma vaga** devolve na hora (veio do cache, sem nova chamada ao LLM).
- [ ] "Regerar" força uma análise nova e **substitui** a anterior (a lista não duplica).
- [ ] "Imprimir / PDF" abre a impressão só com o conteúdo do PDI, sem menu nem botões.

### B6. Validação das respostas (tela Mentor)

- [ ] Cada resposta do agente traz os botões Aprovar / Precisa ajuste / Rejeitar / Copiar.
- [ ] "Aprovar" grava direto; "Precisa ajuste" e "Rejeitar" exigem uma observação.
- [ ] Depois de validar, a barra vira uma etiqueta com o veredito.
- [ ] O contador de "Validações" na lateral reflete as pendências.
- [ ] Na tela **Validações**, os cartões mostram total, aprovadas, pendentes e taxa de aprovação.
- [ ] Os filtros (Todas / Aprovadas / Precisam ajuste / Rejeitadas) funcionam.
- [ ] "Mudar veredito" atualiza o registro; "Excluir" some com ele.
- [ ] "Limpar conversa" esvazia o chat sem apagar as validações já gravadas.

### B7. Degradação sem chave / sem índice

Pare o servidor, esvazie `GEMINI_API_KEY` no `.env` e suba de novo:

- [ ] A aplicação **sobe** mesmo assim.
- [ ] A bolinha fica vermelha e a faixa de aviso explica o que falta.
- [ ] A base de documentos continua navegável (não depende do LLM).
- [ ] Perguntar no chat devolve erro **503 com mensagem clara**, não um 500 opaco.
- [ ] Gerar PDI e reindexar avisam que falta a chave.

---

## Registro da execução

| # | Data | Resultado | Observações |
|---|---|---|---|
| A1 |  |  |  |
| A2 |  |  |  |
| A3 |  |  |  |
| A4 |  |  |  |
| A5 |  |  |  |
| B1–B7 |  |  |  |
