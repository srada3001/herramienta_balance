# coding: utf-8
"""Arranque del servidor web. Ejecuta: python run.py

HOST y PORT se pueden fijar por variable de entorno; el contenedor usa HOST=0.0.0.0.
"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )
