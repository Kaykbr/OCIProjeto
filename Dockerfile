# Imagem unica com API + frontend + vector store embutido.
#
# Build multi-plataforma (a instancia Ampere A1 da OCI e ARM):
#   docker buildx build --platform linux/amd64,linux/arm64 -t agente-mentor-carreiras .
#
# Rodar:
#   docker run -p 8000:8000 --env-file .env agente-mentor-carreiras

# --------------------------------------------------------------------------
# Estagio 1: instala as dependencias em um virtualenv isolado.
# Separar em dois estagios deixa a imagem final sem compilador nem cache do pip.
# --------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# build-essential so entra aqui: cobre o caso de alguma dependencia nao ter
# wheel pronta para linux/arm64 e precisar compilar.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r /tmp/requirements.txt

# --------------------------------------------------------------------------
# Estagio 2: imagem final, enxuta.
# --------------------------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY app ./app
COPY scripts ./scripts
COPY data/curriculos ./data/curriculos
COPY entrypoint.sh /entrypoint.sh

# Usuario sem privilegios que roda a aplicacao (o entrypoint derruba para ele
# depois de ajustar a posse de /app/data - ver entrypoint.sh para o motivo).
RUN useradd --create-home --uid 1000 agente \
    && mkdir -p /app/data/chroma /app/data/estado \
    && chown -R agente:agente /app \
    && chmod +x /entrypoint.sh

# Documental: a porta real vem da variavel PORT.
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT','8000') + '/health')" || exit 1

# Sobe como root de proposito: o entrypoint corrige a posse de /app/data
# (que pode vir de um bind mount do host com UID diferente) e so entao
# derruba privilegio para o usuario 'agente' antes de rodar o uvicorn.
CMD ["/entrypoint.sh"]
