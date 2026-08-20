# Deploy na Oracle Cloud Infrastructure (OCI)

Passo a passo completo para colocar o **Agente Mentor de Carreiras** rodando numa
instância **Compute Always Free** com IP público, acessível em
`http://<IP_PUBLICO>:8000`.

**Serviços da OCI usados:** Compute (VM Ampere A1 Flex) + Networking (VCN, subnet
pública, Internet Gateway, Security List). Nada além do tier Always Free.

**Tempo estimado:** 25 a 40 minutos na primeira vez.

---

## 0. Antes de começar

Você precisa de:

- Conta na OCI (Always Free serve; a região escolhida no cadastro é onde a
  instância vai nascer).
- Uma chave da API do Gemini: <https://aistudio.google.com/apikey>.
- Um par de chaves SSH. Se ainda não tiver, no seu computador:

```bash
ssh-keygen -t ed25519 -C "oci-agente-mentor" -f ~/.ssh/oci_agente
```

Isso gera `~/.ssh/oci_agente` (privada, nunca compartilhe) e
`~/.ssh/oci_agente.pub` (pública, é a que você vai colar no console da OCI).

> **Sobre capacidade Ampere:** em algumas regiões o shape A1 fica sem capacidade
> e o console devolve "Out of host capacity". Se acontecer, tente outro
> *Availability Domain*, tente novamente mais tarde, ou use o shape
> `VM.Standard.E2.1.Micro` (x86, também Always Free) — o projeto roda nos dois,
> mas o Micro tem só 1 GB de RAM e fica apertado.

---

## 1. Criar a VCN com subnet pública e Internet Gateway

O caminho rápido é o assistente, que já cria subnet pública, Internet Gateway e
tabela de rotas de uma vez.

1. Console da OCI → menu ☰ → **Networking** → **Virtual Cloud Networks**.
2. Confirme o **Compartment** no canto esquerdo (use o seu, não o `root`, se a
   sua conta tiver vários).
3. Clique em **Start VCN Wizard** → **Create VCN with Internet Connectivity** → **Start VCN Wizard**.
4. Preencha:
   - **VCN Name:** `vcn-agente-mentor`
   - **VCN CIDR Block:** `10.0.0.0/16`
   - **Public Subnet CIDR Block:** `10.0.0.0/24`
   - **Private Subnet CIDR Block:** `10.0.1.0/24` (não vamos usar, pode deixar)
5. **Next** → **Create**.

Ao final você tem: a VCN, uma **subnet pública**, um **Internet Gateway** e uma
rota `0.0.0.0/0 → Internet Gateway`. É isso que dá IP público alcançável à VM.

---

## 2. Liberar a porta 8000 na Security List

Por padrão a Security List só libera SSH (22). A aplicação usa a 8000.

1. Na página da VCN → **Security Lists** → **Default Security List for vcn-agente-mentor**.
2. **Add Ingress Rules** → **+ Another Ingress Rule** e preencha:

   | Campo | Valor |
   |---|---|
   | Stateless | Não (desmarcado) |
   | Source Type | CIDR |
   | Source CIDR | `0.0.0.0/0` |
   | IP Protocol | TCP |
   | Source Port Range | *(vazio)* |
   | Destination Port Range | `8000` |
   | Description | `Agente Mentor de Carreiras (HTTP)` |

3. **Add Ingress Rules**.

> `0.0.0.0/0` é intencional: o desafio pede um agente **aberto, sem login**. Se
> quiser restringir à sua rede, troque pelo seu IP com `/32`.

---

## 3. Criar a instância Compute (Ampere A1 Flex)

1. Menu ☰ → **Compute** → **Instances** → **Create instance**.
2. **Name:** `agente-mentor-carreiras`
3. **Image and shape** → **Edit**:
   - **Image:** `Canonical Ubuntu 22.04` (ou 24.04).
   - **Shape:** aba **Ampere** → `VM.Standard.A1.Flex` →
     **OCPUs: 2**, **Memory (GB): 12**.

   > O Always Free dá até 4 OCPUs e 24 GB de RAM **no total** entre suas
   > instâncias A1. Usar 2 OCPU / 12 GB deixa metade da cota livre e sobra
   > muita folga para este projeto.

4. **Networking:**
   - **Virtual cloud network:** `vcn-agente-mentor`
   - **Subnet:** a subnet **pública** criada no passo 1.
   - ✅ **Assign a public IPv4 address** (essencial).
5. **Add SSH keys:** **Paste public keys** e cole o conteúdo de
   `~/.ssh/oci_agente.pub`.
6. *(Opcional, recomendado)* **Show advanced options** → aba **Management** →
   **Cloud-init script**: cole o script da [seção 4b](#4b-alternativa-cloud-init)
   para o Docker já vir instalado.
7. **Create**. Em 1-2 minutos a instância fica **RUNNING**. **Anote o Public IP address.**

---

## 4. Conectar via SSH e instalar o Docker

```bash
ssh -i ~/.ssh/oci_agente ubuntu@<IP_PUBLICO>
```

Já dentro da instância:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git
sudo systemctl enable --now docker
sudo usermod -aG docker ubuntu
```

Saia e entre de novo no SSH (`exit` e reconecte) para o grupo `docker` valer.
Confirme com:

```bash
docker run --rm hello-world
```

### 4a. Liberar a porta 8000 no firewall da própria VM

**Este é o passo que mais gente esquece.** A imagem Ubuntu da OCI vem com regras
de `iptables` que bloqueiam tudo menos SSH — mesmo com a Security List liberada
o acesso continua caindo em timeout.

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
sudo netfilter-persistent save
```

Confira se a regra entrou:

```bash
sudo iptables -L INPUT -n --line-numbers | head -12
```

> Se sua imagem usar `firewalld` (Oracle Linux) em vez de iptables puro:
> ```bash
> sudo firewall-cmd --permanent --add-port=8000/tcp && sudo firewall-cmd --reload
> ```

### 4b. Alternativa: cloud-init

Em vez dos passos 4 e 4a manuais, cole isto no campo **Cloud-init script** na
criação da instância — ela já nasce com Docker instalado e a porta liberada:

```yaml
#cloud-config
package_update: true
packages:
  - docker.io
  - docker-compose-v2
  - git
runcmd:
  - systemctl enable --now docker
  - usermod -aG docker ubuntu
  - iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8000 -j ACCEPT
  - netfilter-persistent save
```

---

## 5. Levar o projeto para a instância

### Opção A — clonar o repositório e buildar na própria VM (recomendado)

A A1 é ARM, e o build acontece nativamente nela: não precisa de buildx nem de
emulação.

```bash
git clone https://github.com/<SEU_USUARIO>/<SEU_REPOSITORIO>.git agente-mentor
cd agente-mentor
```

### Opção B — publicar a imagem num registry e só dar `pull`

Útil se você quiser evitar o build na VM (~3-5 min). No **seu computador**, com
buildx habilitado:

```bash
docker buildx build --platform linux/amd64,linux/arm64 \
  -t <SEU_USUARIO_DOCKERHUB>/agente-mentor-carreiras:1.0 --push .
```

E na instância:

```bash
docker pull <SEU_USUARIO_DOCKERHUB>/agente-mentor-carreiras:1.0
```

O `--platform linux/amd64,linux/arm64` é obrigatório aqui: uma imagem buildada
só para x86 **não roda** na Ampere A1.

---

## 6. Configurar a chave e subir o container

Ainda na instância, dentro da pasta do projeto:

```bash
cp .env.example .env
nano .env      # preencha GEMINI_API_KEY=... e salve (Ctrl+O, Enter, Ctrl+X)
```

O `.env` **nunca** vai para o repositório (está no `.gitignore`). A chave existe
apenas nesse arquivo, dentro da instância.

```bash
docker compose up -d --build
```

O primeiro `up` leva alguns minutos (build da imagem). Na subida o próprio
container detecta que o índice está vazio, lê os PDFs de `data/curriculos/`,
gera os embeddings e grava o ChromaDB — não há passo manual de indexação.

O `docker-compose.yml` monta três coisas:

| Montagem | Para quê |
|---|---|
| `./data/curriculos` (leitura **e escrita**) | Os PDFs. Precisa ser gravável porque o painel admin recebe upload de currículo |
| volume `chroma` | O índice vetorial, para não reindexar a cada restart |
| volume `estado` | PDIs gerados e validações do mentor |

Como `data/curriculos` é uma pasta do host, os currículos enviados pela interface
ficam visíveis em `~/agente-mentor/data/curriculos` dentro da instância — dá para
conferir por SSH e fazer backup com um `tar`.

Acompanhe:

```bash
docker compose logs -f
```

Espere as linhas:

```
Indice vazio: indexando 30 chunks de 4 curriculos...
Indexacao automatica concluida.
Agente Mentor de Carreiras subindo na porta 8000
Uvicorn running on http://0.0.0.0:8000
```

Teste de dentro da própria VM antes de tentar de fora:

```bash
curl -s http://localhost:8000/api/status
```

---

## 7. Testar o acesso público

No **seu navegador**:

```
http://<IP_PUBLICO_DA_INSTANCIA>:8000
```

O chat deve abrir com a bolinha de status **verde** e a lista de alunos
indexados. Faça uma pergunta de teste (ex.: *"Quais são as principais
habilidades técnicas do Carlos Andrade?"*) e tire o print para o README.

> **Antes de mostrar a demo para alguém:** o free tier do Gemini dá cerca de
> **20 requisições por dia por modelo**. O agente troca de modelo automaticamente
> quando uma cota acaba (o rodapé da interface mostra qual está em uso), mas se
> todos acabarem as respostas param até o dia seguinte. A tela de documentos e os
> PDIs já gerados continuam funcionando normalmente, porque não dependem do LLM.
> Se a demo for muito usada, habilite faturamento no projeto do Google.

Verificação rápida por linha de comando, do seu computador:

```bash
curl -s http://<IP_PUBLICO>:8000/api/status
```

---

## Deixar pronto para a avaliação

Depois que o container subir e o acesso público funcionar, faça este preparo. Ele
existe porque o free tier do Gemini dá cerca de **20 requisições por dia por
modelo** e o agente é aberto, sem login: a cota é compartilhada com quem abrir o link.

### 1. Confirme que o índice subiu sozinho

```bash
curl -s http://localhost:8000/api/status
```

Deve trazer `"pronto": true` com 30 chunks e 4 alunos. Se vier `chunks_indexados: 0`,
veja os logs (`docker compose logs | grep -i index`).

### 2. Pré-gere alguns PDIs

A tela de PDI lê os planos já salvos do disco: abrir um PDI existente **não gasta
nenhuma chamada de API**. Gerar 3 ou 4 agora garante que o avaliador veja a tela
gráfica cheia mesmo que a cota do dia acabe.

```bash
curl -s -X POST http://localhost:8000/api/pdi -H "Content-Type: application/json"   -d '{"nome_aluno":"Pedro Souza","vaga_alvo":"Desenvolvedor Full Stack Pleno, com React e Node.js"}'

curl -s -X POST http://localhost:8000/api/pdi -H "Content-Type: application/json"   -d '{"nome_aluno":"Carlos Andrade","vaga_alvo":"Desenvolvedor Backend Senior, com Python, cloud e Docker"}'

curl -s -X POST http://localhost:8000/api/pdi -H "Content-Type: application/json"   -d '{"nome_aluno":"Ana Beatriz","vaga_alvo":"SDET, com automacao de API e CI/CD"}'
```

Os PDIs ficam no volume `estado` e sobrevivem a `docker compose restart`.

### 3. Reserve a cota do dia da entrega

Faça seus testes num dia e mande o link no outro. Se testar muito e a cota acabar,
o agente avisa o motivo na interface, mas o avaliador não vê as respostas.

Para eliminar o limite de vez, habilite faturamento no projeto do Google em
<https://ai.studio/projects> — o volume de uma avaliação custa centavos.

### 4. O que continua funcionando sem cota

Vale saber para não entrar em pânico: **base de documentos, PDIs já gerados,
validações e painel admin não dependem do LLM**. Só o chat e a geração de PDI novo
precisam de cota.

---

## Diagnóstico de problemas

| Sintoma | Causa provável | Como resolver |
|---|---|---|
| `curl` funciona dentro da VM mas de fora dá timeout | firewall da VM | passo [4a](#4a-liberar-a-porta-8000-no-firewall-da-própria-vm) — regra de `iptables` |
| Timeout mesmo com iptables liberado | Security List sem a regra de ingress, ou instância na subnet privada | passo 2; confirme a subnet da instância |
| Página abre mas a bolinha fica vermelha com "GEMINI_API_KEY não configurada" | `.env` ausente ou vazio dentro da VM | passo 6; depois `docker compose up -d --force-recreate` |
| Bolinha vermelha com "Nenhum currículo indexado" | os PDFs não chegaram ou a indexação falhou | `docker compose logs \| grep -i index`; rode `docker compose exec agente python scripts/indexar_curriculos.py` |
| `exec format error` ao subir o container | imagem x86 numa VM ARM | rebuilde na própria VM (`docker compose up -d --build`) ou use buildx multi-plataforma |
| "Out of host capacity" ao criar a instância | região sem Ampere livre | outro Availability Domain, tentar mais tarde, ou shape E2.1.Micro |
| Container reiniciando em loop | erro na subida | `docker compose logs --tail=50` |
| Chat responde "cota diária gratuita acabou" | limite do free tier do Gemini (~20/dia por modelo) | espere a virada do dia, fixe outro modelo em `GEMINI_MODEL`, ou habilite faturamento no projeto Google |
| Chat responde "chave sem créditos" | projeto Google sem crédito | gere a chave num projeto com free tier em <https://aistudio.google.com/apikey> |

Comandos úteis do dia a dia:

```bash
docker compose ps                  # estado do container
docker compose logs -f --tail=50   # logs ao vivo
docker compose restart             # reiniciar
docker compose down                # derrubar (o índice fica no volume)
docker compose up -d --build       # atualizar depois de um git pull
```

---

## Custos

Tudo neste guia cabe no **Always Free** da OCI:

| Recurso | Uso | Limite Always Free |
|---|---|---|
| Compute VM.Standard.A1.Flex | 2 OCPU / 12 GB | 4 OCPU / 24 GB no total |
| Armazenamento em bloco | ~50 GB (boot volume) | 200 GB no total |
| VCN, subnet, Internet Gateway | 1 de cada | sem custo |
| Tráfego de saída | baixíssimo | 10 TB/mês |

O único custo possível fora da OCI é a API do Gemini, que tem um free tier
generoso — para uma demo de mentoria o consumo fica dentro dele.
