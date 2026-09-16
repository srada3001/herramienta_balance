# ============================================================
# Optimizador para los equipos de Balance
#
#   produccion (por defecto) -> imagen autocontenida, lista para desplegar
#   dev                      -> base del devcontainer de VS Code
# ============================================================

# ---------- Base común: intérprete y dependencias ----------
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

# Dependencias primero: esta capa se reutiliza mientras requirements.txt no cambie.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CBC: se usa el binario que empaqueta PuLP, igual que en desarrollo.
# En arm64, si PuLP no trae binario, descomenta estas dos líneas:
# RUN apt-get update && apt-get install -y --no-install-recommends coinor-cbc \
#     && rm -rf /var/lib/apt/lists/*
# ENV CBC_PATH=/usr/bin/cbc

EXPOSE 8000


# ---------- Desarrollo: el código llega montado desde el host ----------
FROM base AS dev

# git para el control de versiones dentro del contenedor; curl para probar la API.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/*

# Sin COPY: VS Code monta el proyecto en /app, así que editas en el host y el
# contenedor ve los cambios al instante. Corre como root para que no haya
# conflictos de permisos con los archivos del host.
CMD ["sleep", "infinity"]


# ---------- Producción: imagen autocontenida ----------
FROM base AS produccion

# Código y estáticos
COPY run.py ./
COPY app/ ./app/
COPY static/ ./static/

# Datos y límites operativos.
# Son ~130 MB en parquet: si prefieres una imagen más ligera, añade "data/"
# a .dockerignore y monta la carpeta al arrancar.
COPY data/ ./data/

# Usuario sin privilegios; necesita escribir datos.txt al guardar los límites.
RUN useradd --create-home --uid 1000 balance \
    && chown -R balance:balance /app/data
USER balance

# El arranque carga los cuatro parquet y ajusta las regresiones: da margen antes
# de marcar el contenedor como sano.
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/limites', timeout=4)"

CMD ["python", "run.py"]
