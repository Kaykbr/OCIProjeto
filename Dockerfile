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

# Usuario sem privilegios; /app/data precisa ser gravavel (indice + estado).
RUN useradd --create-home --uid 1000 agente \
    && mkdir -p /app/data/chroma /app/data/estado \
    && chown -R agente:agente /app
USER agente

# Documental: a porta real vem da variavel PORT.
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT','8000') + '/health')" || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
