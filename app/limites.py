# coding: utf-8
"""Lectura y escritura de los límites operativos (equivalente a cargar_Datos/guardar_Datos)."""

from .core import DATOS_TXT

POR_DEFECTO = [8, 17, 8, 20, 8, 17, 8, 42]


def cargar_Datos():
    try:  # Lectura del archivo datos.txt
        datosL = []
        with open(DATOS_TXT, "r") as archivo:
            datos_leidos = archivo.readlines()

        for dato in datos_leidos:
            datosL.append(float(dato.strip()))
        if len(datosL) != 8:
            raise ValueError("datos.txt incompleto")
    except Exception:
        datosL = list(POR_DEFECTO)
    return datosL


def guardar_Datos(datosL):
    """Guarda los 8 límites en data/datos.txt, en el mismo formato del original."""
    datos = [str(float(d)) for d in datosL]
    with open(DATOS_TXT, "w") as archivo:
        for dato in datos:
            archivo.write(dato + "\n")
    return datos
