# Resultados da execucao do roteiro

Modelo: `gemini-3.5-flash`

> Respostas reais do agente, capturadas em 19/08/2026 as 22:20 com o modelo `gemini-3.5-flash`.
> Reproduza com `python scripts/rodar_testes.py`.

### 1. Quais sao as principais habilidades tecnicas do Carlos Andrade?

**Ferramentas acionadas pelo agente:**

- `buscar_info_aluno(pergunta='Quais sao as principais habilidades tecnicas do Carlos Andrade?', nome_aluno='Carlos Andrade')` — 418 ms

**Resposta:**

> Com base no currículo de **Carlos Andrade**, as suas principais habilidades técnicas são:
>
> ### 💻 Linguagens e Frameworks
> *   **Python (Avançado):** Foco em desenvolvimento backend, APIs REST e sistemas transacionais. Tem experiência com Python 3.10 e migração de sistemas legados (Python 2.7).
> *   **SQL (Avançado):** Forte em modelagem de dados relacionais e otimização de consultas complexas.
> *   **JavaScript (Básico).**
> *   **Frameworks e Bibliotecas:** Django, Django REST Framework, Celery, pytest e Pandas (básico).
>
> ### 🗄️ Bancos de Dados
> *   PostgreSQL, MySQL e Redis.
>
> ### 🛠️ Ferramentas e Metodologias
> *   **Ferramentas:** Git, GitHub Actions (uso básico), Linux e Postman.
> *   **Metodologias:** Scrum, *code review* e TDD parcial (testes automatizados).
>
> ---
>
> ### ⚠️ Observações importantes para o Mentor (Gaps de Infraestrutura):
> Se o objetivo do Carlos for evoluir para uma posição Sênior (como mencionado em seu objetivo de carreira), vale notar que ele:
> *   **Não tem experiência prática com Cloud:** Nunca provisionou recursos em AWS, Azure, GCP ou OCI (os deploys que acompanhou eram feitos por um time de infraestrutura separado em servidores *on-premise*).
> *   **Não tem experiência com Docker em produção.**

*Tempo total: 6.5s*

### 2. Gere o curriculo padronizado da Fernanda Lima.

**Ferramentas acionadas pelo agente:**

- `gerar_curriculo_padronizado(nome_aluno='Fernanda Lima')` — 36821 ms

**Resposta:**

> Aqui está o currículo padronizado da **Fernanda Lima**, formatado no modelo da mentoria:
>
> ---
>
> ## Dados pessoais
>
> * **Nome:** Fernanda Lima
> * **E-mail:** fernanda.lima@exemplo.com.br
> * **Telefone:** (31) 90000-0002
> * **Cidade:** Belo Horizonte - MG (Disponibilidade para modelo híbrido)
> * **LinkedIn:** linkedin.com/in/fernanda-lima-exemplo
>
> ## Resumo profissional
>
> Analista de dados com 4 anos de experiência em construção de indicadores e dashboards corporativos, com domínio de SQL analítico e Power BI. Atualmente em transição para Ciência de Dados, cursa pós-graduação na área e estuda Python (Pandas) para análises exploratórias básicas. Tem como objetivo de carreira atuar como Cientista de Dados Júnior.
>
> ## Experiências profissionais
>
> **Analista de Dados Pleno** — *Rede Varejo Colina* (Ago/2022 - Atual)
> * Construção e manutenção de 12 dashboards em Power BI para as áreas comercial, logística e financeira.
> * Escrita de consultas SQL analíticas em SQL Server (CTEs, window functions) sobre um data warehouse de 2 TB.
> * Modelagem dimensional (*star schema*) das áreas de vendas e estoque junto ao time de engenharia de dados.
> * Análise exploratória de dados de vendas em Python com Pandas para identificar sazonalidade por região.
> * Treinamento de usuários de negócio no autoatendimento dos painéis.
>
> **Analista de Dados Júnior** — *Consultoria Prisma Analytics* (Fev/2021 - Jul/2022)
> * Extração e tratamento de dados de múltiplas fontes (Excel, CSV, APIs) para relatórios de clientes.
> * Automação de relatórios recorrentes que antes eram montados manualmente em planilhas.
> * Apresentação de resultados para clientes não técnicos.
>
> ## Formação acadêmica
>
> * **Pós-graduação (MBA) em Ciência de Dados** — *Instituto Exemplo* (Em andamento, previsão de conclusão em 2026)
> * **Bacharelado em Estatística** — *Universidade Exemplo de Minas Gerais* (Concluído em 2020)
> * **Curso livre: Python para Data Science** — *Alura* (Concluído em 2024)
>
> ## Habilidades técnicas
>
> * **Linguagens:** SQL (avançado), Python (básico), DAX (intermediário), R (noções)
> * **Bancos de dados:** SQL Server, PostgreSQL, BigQuery (noções)
> * **Visualização:** Power BI (avançado), Excel avançado, Looker Studio (básico)
> * **Bibliotecas Python:** Pandas (básico), Matplotlib (básico). *Sem experiência com scikit-learn.*
> * **Estatística:** Estatística descritiva, testes de hipótese, regressão linear (base acadêmica)
> * **Cloud e engenharia:** *Sem experiência com pipelines em nuvem, Airflow, Spark ou versionamento de modelos.*
>
> ## Idiomas
>
> * **Português:** Nativo
> * **Inglês:** Avançado (leitura, escrita e reuniões)

*Tempo total: 57.6s*

### 3. Monte um PDI para o Pedro Souza mirando uma vaga de Desenvolvedor Full Stack Pleno, com React e Node.js.

**Ferramentas acionadas pelo agente:**

- `gerar_pdi(vaga_alvo='Desenvolvedor Full Stack Pleno, com React e Node.js', nome_aluno='Pedro Souza')` — 40201 ms

**Resposta:**

> Aqui está o **Plano de Desenvolvimento Individual (PDI)** estruturado para o **Pedro Souza**, focado na transição de Desenvolvedor Frontend Júnior para **Desenvolvedor Full Stack Pleno (React e Node.js)**. 
>
> Este plano foi desenhado considerando que ele já possui uma base sólida e prática em Frontend (React/TypeScript), mas precisa construir sua maturidade no ecossistema Backend do zero.
>
> ---
>
> # Plano de Desenvolvimento Individual (PDI)
> **Aluno:** Pedro Souza  
> **Objetivo de Carreira:** Desenvolvedor Full Stack Pleno (React/Node.js)  
> **Prazo Estimado:** 6 meses (dedicação paralela ao trabalho atual)
>
> ---
>
> ## 1. Perfil Atual (Habilidades Consolidadas)
> *   **Frontend SPA com React & TypeScript:** Domínio de React 18, gerenciamento de estado, rotas e tipagem estática (experiência prática na Agência Pixel Sul).
> *   **Otimização de Performance (Core Web Vitals):** Histórico comprovado de otimização (redução de LCP de 4,1s para 1,8s usando *code splitting* e *lazy loading*).
> *   **Testes no Frontend:** Criação de testes unitários e de componentes com Jest e React Testing Library.
> *   **Design Systems e Acessibilidade:** Criação de interfaces responsivas e acessíveis (Styled Components, Storybook, WCAG 2.1 AA).
> *   **Formação Acadêmica:** Tecnólogo em Análise e Desenvolvimento de Sistemas (concluído em 2023).
>
> ---
>
> ## 2. Gaps Identificados (Foco de Desenvolvimento)
> Para atingir o nível Pleno como Full Stack, Pedro precisa suprir a falta de experiência prática no Backend:
>
> 1.  **Desenvolvimento de APIs REST com Node.js e Express/NestJS (Crítico):** Aprender a estruturar servidores, rotas, middlewares e controllers de forma autônoma.
> 2.  **Modelagem e Persistência de Dados (Crítico):** Domínio de bancos de dados relacionais (PostgreSQL/MySQL) e uso de ORMs (Prisma ou Sequelize).
> 3.  **Segurança e Autenticação (Alto):** Implementação de fluxos de login seguros usando criptografia de senhas (bcrypt) e tokens (JWT).
> 4.  **Testes Automatizados no Backend (Médio):** Criação de testes de integração e unitários para garantir a estabilidade das regras de negócio no servidor.
> 5.  **Deploy e CI/CD Full Stack (Baixo):** Capacidade de colocar a aplicação completa no ar (Vercel para Frontend, Render/Railway para Backend e Banco de Dados).
>
> ---
>
> ## 3. Plano de Ação Recomendado
>
> *   **Ação 1: Construção da Base Backend (Node.js + Express)**
>     *   *O que fazer:* Realizar um curso prático de Node.js com TypeScript e Express. Criar uma API REST estruturada do zero, aplicando boas práticas de arquitetura de pastas.
> *   **Ação 2: Integração com Banco de Dados**
>     *   *O que fazer:* Integrar um banco de dados PostgreSQL à API criada. Utilizar o **Prisma ORM** para gerenciar as tabelas (migrations) e realizar operações de CRUD completas.
> *   **Ação 3: Camada de Segurança**
>     *   *O que fazer:* Implementar autenticação JWT na API. Proteger rotas específicas e garantir que as senhas dos usuários sejam salvas com hash seguro (`bcrypt`).
> *   **Ação 4: Testes de Integração**
>     *   *O que fazer:* Escrever testes automatizados para as rotas da API utilizando **Jest** e **Supertest**, buscando cobrir cenários de sucesso e erro (mínimo de 80% de cobertura).
> *   **Ação 5: Projeto Integrado (Full Stack) e Deploy**
>     *   *O que fazer:* Desenvolver um projeto autoral completo (ex: gerenciador de tarefas ou sistema de agendamentos) conectando o frontend em React (usando React Query) à API Node.js. Fazer o deploy de ambas as partes em produção.
>
> ---
>
> ## 4. Cronograma Sugerido (6 meses)
>
> ### 📅 Mês 1 e 2: Fundamentos de Node.js, Express e Banco de Dados
> *   **Foco:** Entender o fluxo de requisição/resposta, protocolo HTTP, criação de rotas e persistência de dados.
> *   **Entregável:** Uma API REST funcional em Node.js (TypeScript) integrada ao PostgreSQL via Prisma ORM, realizando operações de CRUD.
>
> ### 📅 Mês 3 e 4: Segurança, Testes e Robustez
> *   **Foco:** Deixar a API segura, validada e testada contra falhas.
> *   **Entregável:** Implementação de autenticação JWT, tratamento global de erros, validação de dados de entrada (com Zod ou Yup) e cobertura de testes de integração com Jest/Supertest.
>
> ### 📅 Mês 5 e 6: Integração Full Stack, Deploy e Portfólio
> *   **Foco:** Conectar as duas pontas (React + Node.js) e preparar a transição de carreira.
> *   **Entregável:** 
>     *   Projeto Full Stack completo publicado no GitHub (com README detalhado) e deploy ativo em produção (Vercel + Railway/Render).
>     *   Atualização do LinkedIn e currículo destacando as novas habilidades em Node.js.
>
> ---
>
> ## 💡 Dica para o Mentor (Conversa 1:1)
> Incentive o Pedro a tentar **buscar demandas de backend dentro da própria empresa atual** (Agência Pixel Sul) à medida que ele for avançando no Mês 3. Conseguir colocar a mão no código de produção do backend deles, mesmo que em tarefas simples, vai acelerar drasticamente a maturidade dele para o nível Pleno.

*Tempo total: 266.9s*

### 4. Quais projetos voce sugere para a Ana Beatriz evoluir para SDET?

**Ferramentas acionadas pelo agente:**

- `sugerir_projetos(nome_aluno='Ana Beatriz', vaga_alvo='SDET')` — 30808 ms

**Resposta:**

> Aqui estão as sugestões de projetos práticos de portfólio para a **Ana Beatriz** focar na transição para o perfil de **SDET**. 
>
> Esses projetos foram desenhados para aproveitar a base que ela já possui (como Java) e fechar lacunas cruciais de mercado (como automação de APIs, CI/CD, Docker, testes de contrato e performance).
>
> ---
>
> ### 1. API-Health-Secure: Automação de Testes de API de Agendamento Hospitalar
> * **Objetivo:** Fecha o gap de falta de experiência em automação de APIs (atualmente ela realiza testes manuais com Postman). Prova que ela domina o protocolo HTTP, manipulação de payloads dinâmicos em Java (POJOs), validação de schemas JSON e asserções avançadas de back-end.
> * **Tecnologias:** Java, RestAssured, JUnit 5 (evoluindo do TestNG), Jackson/Lombok (para serialização/deserialização de dados), Java-Faker (geração de dados dinâmicos) e Maven.
> * **Nível de Dificuldade:** Intermediário | **Esforço estimado:** 25 horas.
> * **Entregável:** Repositório no GitHub com uma suíte de testes estruturada contra uma API de saúde (pode ser mockada com WireMock ou uma API pública). O código deve usar o padrão de *Request/Response Specifications* do RestAssured, conter validações de JSON Schema, cobertura de verbos HTTP (GET, POST, PUT, DELETE) e um `README.md` detalhado explicando como rodar os testes e analisar os resultados.
>
> ---
>
> ### 2. Pipeline-Clinica-CI: Containerização e Pipeline de CI/CD para Regressão de Saúde
> * **Objetivo:** Elimina as lacunas de Docker e CI/CD (GitHub Actions). Prova que ela sabe integrar testes automatizados no fluxo de deploy contínuo (DevOps), garantindo execuções isoladas, paralelas e independentes de ambiente ("funciona na minha máquina").
> * **Tecnologias:** Selenium WebDriver em modo Headless, RestAssured (consolidando o projeto anterior), Docker e Docker Compose, GitHub Actions e Allure Reports.
> * **Nível de Dificuldade:** Intermediário para Avançado | **Esforço estimado:** 40 horas.
> * **Entregável:** Repositório no GitHub com um fluxo de CI configurado via `.github/workflows/main.yml`. O pipeline deve rodar a cada *push* e realizar:
>   1. Subida de um container Docker com a aplicação web/API de prontuário eletrônico.
>   2. Subida de um container com Selenium Grid (Chrome/Firefox headless).
>   3. Execução paralela da suíte de testes híbrida (UI com Selenium + API com RestAssured).
>   4. Geração e publicação automática do relatório Allure Reports no GitHub Pages.
>
> ---
>
> ### 3. Telemed-Performance-Contract: Testes de Contrato e Carga em Microsserviços de Telemedicina
> * **Objetivo:** Consolida o perfil de SDET ao fechar os gaps de testes de performance e testes de contrato. Prova a capacidade de garantir a resiliência e a integridade de sistemas distribuídos (microsserviços) sob alta carga de acessos.
> * **Tecnologias:** k6 (ferramenta moderna de performance baseada em JS), Pact framework com Java (testes de contrato) e Docker.
> * **Nível de Dificuldade:** Avançado | **Esforço estimado:** 50 horas.
> * **Entregável:** Repositório contendo duas frentes de validação para um sistema de Telemedicina:
>   1. **Testes de Contrato:** Arquivos de pacto gerados em Java validando a integração entre o microsserviço de "Agendamento" (Consumer) e o de "Notificação de Pacientes" (Provider).
>   2. **Testes de Performance:** Scripts em k6 simulando cenários de carga (médicos e pacientes entrando em salas virtuais simultaneamente), testes de estresse e testes de pico (*Spike Tests*). Deve incluir a definição de *Thresholds* (SLAs de erro < 1% e tempo de resposta < 500ms) e um relatório técnico no `README.md` analisando o comportamento do sistema sob carga.
>
> ---
>
> ### Dica para a 1:1 com a Ana:
> Sugiro orientá-la a começar pelo **Projeto 1 (APIs)**, que é o passo mais imediato para quem já programa em Java mas ainda testa APIs manualmente. Assim que ela dominar o RestAssured, o **Projeto 2** entra como a evolução natural para colocar essa automação em uma esteira de CI/CD.

*Tempo total: 37.2s*

### 5. Compare a experiencia de Carlos e Fernanda em relacao a dados.

**Ferramentas acionadas pelo agente:**

- `buscar_info_aluno(pergunta='Qual é a experiência, histórico profissional e habilidades de Carlos na área de dados?', nome_aluno='Carlos')` — 438 ms
- `buscar_info_aluno(nome_aluno='Fernanda', pergunta='Qual é a experiência, histórico profissional e habilidades de Fernanda na área de dados?')` — 681 ms

**Resposta:**

> Com base nos currículos de **Carlos Andrade** e **Fernanda Lima**, aqui está uma comparação detalhada da experiência de ambos na área de dados. 
>
> Embora ambos possuam excelente domínio de SQL, eles aplicam esse conhecimento em contextos completamente diferentes: Carlos tem um perfil voltado para o **desenvolvimento backend e engenharia de software (dados transacionais)**, enquanto Fernanda tem foco em **análise de dados e business intelligence (dados analíticos)**.
>
> ---
>
> ### 1. Foco de Atuação e Perfil Geral
> * **Carlos Andrade (Desenvolvedor Backend Pleno):** Atua com foco em sistemas transacionais (OLTP). Sua experiência com dados está ligada à performance de APIs, modelagem relacional para persistência de dados de aplicações e otimização de consultas para rotinas de sistemas.
> * **Fernanda Lima (Analista de Dados Pleno):** Atua diretamente na área de dados há 4 anos, focada em inteligência de negócios (BI), geração de insights, relatórios gerenciais e análise exploratória (OLAP). Atualmente, está em transição de carreira para Ciência de Dados.
>
> ### 2. Domínio de SQL e Modelagem de Dados
> * **Carlos Andrade (SQL Avançado):**
>   * **Foco:** Modelagem relacional e otimização de banco de dados para aplicações.
>   * **Experiência prática:** Escrita de *migrations* em PostgreSQL, criação de índices compostos e reescrita de consultas (usando `select_related` no Django) que reduziram em 60% o tempo de rotinas de fechamento mensal. Também possui experiência com consultas complexas em MySQL para relatórios financeiros.
>   * **Bancos de dados:** PostgreSQL, MySQL e Redis (NoSQL para cache/filas).
> * **Fernanda Lima (SQL Avançado):**
>   * **Foco:** SQL analítico para manipulação de grandes volumes de dados e modelagem dimensional.
>   * **Experiência prática:** Escrita de consultas analíticas complexas (utilizando CTEs e *window functions*) sobre um Data Warehouse de 2 TB (SQL Server). Atuou na modelagem dimensional (*star schema*) para as áreas de vendas e estoque junto ao time de engenharia de dados.
>   * **Bancos de dados:** SQL Server, PostgreSQL e noções de BigQuery.
>
> ### 3. Uso de Python e Bibliotecas de Dados
> * **Carlos Andrade (Python Avançado):**
>   * Domina a linguagem para desenvolvimento de software (Django, Celery, pytest).
>   * No contexto de dados, possui conhecimento **básico em Pandas**, mas seu foco principal é a lógica de negócios no backend e automação de rotinas com scripts.
> * **Fernanda Lima (Python Básico):**
>   * Utiliza a linguagem de forma focada em análise de dados.
>   * Realiza análises exploratórias de vendas utilizando **Pandas** e **Matplotlib** para identificar sazonalidades. 
>   * Não possui experiência com bibliotecas de Machine Learning (como *scikit-learn*) e nunca colocou modelos em produção, embora esteja cursando um MBA em Ciência de Dados para evoluir nesse ponto.
>
> ### 4. Visualização de Dados e Ferramentas de BI
> * **Carlos Andrade:** Não possui experiência descrita com ferramentas de BI ou visualização de dados (como Power BI ou Looker). Seu foco de entrega de dados é via APIs REST ou relatórios gerados por scripts.
> * **Fernanda Lima (Power BI Avançado):**
>   * Especialista em visualização. Construiu e mantém 12 dashboards corporativos em Power BI para as áreas comercial, logística e financeira.
>   * Domina **DAX (intermediário)** e Excel Avançado, além de ter noções de Looker Studio. Tem forte experiência em traduzir dados para áreas de negócios e treinar usuários em autoatendimento.
>
> ### 5. Formação Acadêmica Relacionada
> * **Carlos Andrade:** Bacharel em Ciência da Computação (2021). Seu aprendizado em dados é mais voltado à engenharia de software e cursos livres de SQL/Modelagem.
> * **Fernanda Lima:** Bacharel em Estatística (2020) e pós-graduanda (MBA) em Ciência de Dados (previsão 2026). Possui forte base teórica em estatística descritiva, testes de hipótese e regressão linear.
>
> ---
>
> ### Resumo para o Mentor (Direcionamento de Conversa)
> * **Use o Carlos se o objetivo for:** Discutir otimização de banco de dados de produção, modelagem de tabelas para novos recursos de sistemas, índices, performance de queries e integração de bancos relacionais com APIs.
> * **Use a Fernanda se o objetivo for:** Discutir estruturação de Data Warehouses, modelagem dimensional (*star schema*), criação de métricas de negócios (KPIs), relatórios gerenciais e transição para a carreira de Ciência de Dados (focando nos gaps de Python e Machine Learning).

*Tempo total: 14.2s*
