#!/bin/sh
# Ponto de entrada do container. Roda como root por um instante so para
# corrigir a posse de /app/data, depois derruba privilegio e sobe a API.
#
# Por que isso existe: data/curriculos e um bind mount do HOST (nao um volume
# gerenciado pelo Docker). A UID de quem clonou o repositorio no host quase
# nunca bate com a UID do usuario 'agente' (1000) usado dentro da imagem -
# sem este ajuste, o upload de curriculo pelo painel admin falha com
# "Permission denied" em qualquer host Linux real. Isso nao aparece testando
# no Docker Desktop (Windows/Mac), que nao aplica UID/GID do jeito que um
# host Linux de verdade aplica - so foi descoberto em producao na OCI.
set -e

chown -R agente:agente /app/data 2>/dev/null || true

exec su -s /bin/sh agente -c "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
