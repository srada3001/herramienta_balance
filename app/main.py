# coding: utf-8
"""API FastAPI del Optimizador para los equipos de Balance."""

import anyio
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .core import BASE_DIR
from .limites import cargar_Datos, guardar_Datos
from .models import EntradaCalculo, EstadoEquipos, Limites, Resultado
from .service import ErrorDeCalculo, calcular, estado_calderas, estado_generadores

STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Optimizador para los equipos de Balance",
    description="Herramienta IA para Calderas, Turbogeneradores y Turbogás",
    version="1.0.0",
)


@app.get("/api/limites", response_model=Limites, tags=["Configuración"])
def obtener_limites():
    """Límites operativos de generación eléctrica guardados en datos.txt."""
    return Limites.desde_lista(cargar_Datos())


@app.put("/api/limites", response_model=Limites, tags=["Configuración"])
def actualizar_limites(limites: Limites):
    """Guarda los límites operativos (equivale al botón «Límites»)."""
    valores = limites.a_lista()
    for minimo, maximo, nombre in ((valores[0], valores[1], "Turbo 1"),
                                   (valores[2], valores[3], "Turbo 2"),
                                   (valores[4], valores[5], "Turbo 3"),
                                   (valores[6], valores[7], "Turbogás")):
        if minimo < 0 or maximo < 0:
            raise HTTPException(422, f"Los límites de {nombre} no pueden ser negativos.")
        if minimo > maximo:
            raise HTTPException(422, f"El mínimo de {nombre} no puede superar su máximo.")
    guardar_Datos(valores)
    return Limites.desde_lista(cargar_Datos())


@app.get("/api/estado", response_model=EstadoEquipos, tags=["Cálculo"])
def estado(caldera1: int = 1, caldera3: int = 1, caldera4: int = 1, caldera5: int = 1,
           turbo1: int = 1, turbo2: int = 1, turbo3: int = 1, turbogas: int = 1):
    """Producción y generación máximas según los equipos habilitados."""
    datosL = cargar_Datos()
    calDisp, _indices, maxProdV = estado_calderas(caldera1, caldera3, caldera4, caldera5)
    turDisp, max_gen = estado_generadores(turbo1, turbo2, turbo3, turbogas, datosL)
    return EstadoEquipos(
        calderas_habilitadas=calDisp,
        produccion_maxima=maxProdV,
        generadores_habilitados=turDisp,
        generacion_maxima=max_gen,
    )


@app.post("/api/calcular", response_model=Resultado, tags=["Cálculo"])
async def api_calcular(entrada: EntradaCalculo):
    """Ejecuta la optimización completa (generadores + calderas)."""
    try:
        # El cálculo es CPU-bound y bloqueante: fuera del bucle de eventos.
        return await anyio.to_thread.run_sync(calcular, entrada)
    except ErrorDeCalculo as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # equivale al messagebox genérico del original
        raise HTTPException(
            status_code=400,
            detail="Los valores deben ser numéricos y estar dentro del rango normal de "
                   "operación. Por favor corrige. (%s)" % exc)


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
