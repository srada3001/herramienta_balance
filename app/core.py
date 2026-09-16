# coding: utf-8
"""
Núcleo de cálculo de la Herramienta IA para Calderas, Turbogeneradores y Turbogás.

@autor original: Edwin Quintero

Este módulo es una copia literal de la lógica de "Herramienta IA Calderas-Turbos.py":
regresiones, modelo de optimización de calderas (SLSQP) y modelo de generación
eléctrica (MILP con PuLP/CBC). Lo único que se retiró fue la capa de interfaz
Tkinter; los modelos, coeficientes y fórmulas no se modificaron.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pulp
import warnings
from scipy.optimize import curve_fit, minimize

warnings.filterwarnings('ignore')

# Rutas absolutas: el servidor web puede arrancar desde cualquier directorio.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATOS_TXT = DATA_DIR / "datos.txt"


def _crear_solver():
    """Devuelve el solver CBC, el mismo que usaba el script original.

    Se usa el binario que empaqueta PuLP, idéntico en Windows y en Linux, para
    que desarrollo y contenedor resuelvan con el mismo ejecutable. La variable
    de entorno CBC_PATH permite apuntar a otro CBC del sistema (por ejemplo el
    `coinor-cbc` de apt en arm64).
    """
    ruta = os.environ.get("CBC_PATH")
    if ruta:
        return pulp.COIN_CMD(path=ruta, msg=False)
    return pulp.PULP_CBC_CMD(msg=False)

# Pesos
w1, w2 = 0.7, 0.3

maxProdV, calDisp = 1150, 4
# puntos=[3,1,2,4]
indices = [0, 2, 3, 1]
Ab = np.zeros((4, 2))
AbV = np.zeros((4, 2))
# Los .parquet son copia exacta de los .csv originales, con el mismo encabezado
# ('Fecha', 'Flujo Gas', 'Flujo Aire', 'Producción Vapor', 'Temp. Vapor',
# 'Oxigeno', 'T Aire al Cal', 'Poder', 'IGV'). Se regeneran con
# tools/csv_a_parquet.py.
d1 = pd.read_parquet(DATA_DIR / "SB2951.parquet")
d3 = pd.read_parquet(DATA_DIR / "SB2953.parquet")
d4 = pd.read_parquet(DATA_DIR / "SB2954.parquet")
d5 = pd.read_parquet(DATA_DIR / "SB2955.parquet")
d1 = d1.dropna()
d3 = d3.dropna()
d4 = d4.dropna()
d5 = d5.dropna()


##### Cálculo de Regresión Lineal entre Variables ######
def fun(x, a, b):
    return a * x + b


def Oxi1(x):
    y = 1.97 + 0.8 * (x - d1['Poder'].mean()) / (d1['Poder'].max() - d1['Poder'].min())
    if y < 1.5:
        y = 1.5
    return y


def Oxi3(x):
    y = 2 + 0.75 * (x - d3['Poder'].mean()) / (d3['Poder'].max() - d3['Poder'].min())
    if y < 1.5:
        y = 1.5
    return y


def Oxi4(x):
    y = 2.06 + 0.6 * (x - d4['Poder'].mean()) / (d4['Poder'].max() - d4['Poder'].min())
    if y < 1.5:
        y = 1.5
    return y


def Oxi5(x):
    y = 2.03 + 0.65 * (x - d5['Poder'].mean()) / (d5['Poder'].max() - d5['Poder'].min())
    if y < 1.5:
        y = 1.5
    return y


[Ab[0, 0], Ab[0, 1]], cov = curve_fit(fun, d1['Poder'], d1['IGV'])
[Ab[1, 0], Ab[1, 1]], cov = curve_fit(fun, d3['Poder'], d3['IGV'])
[Ab[2, 0], Ab[2, 1]], cov = curve_fit(fun, d4['Poder'], d4['IGV'])
[Ab[3, 0], Ab[3, 1]], cov = curve_fit(fun, d5['Poder'], d5['IGV'])

d1['Dif_IGV'] = d1['IGV'] - fun(d1['Poder'], Ab[0, 0], Ab[0, 1])
d3['Dif_IGV'] = d3['IGV'] - fun(d3['Poder'], Ab[1, 0], Ab[1, 1])
d4['Dif_IGV'] = d4['IGV'] - fun(d4['Poder'], Ab[2, 0], Ab[2, 1])
d5['Dif_IGV'] = d5['IGV'] - fun(d5['Poder'], Ab[3, 0], Ab[3, 1])

# Primer cuartil de Dif_IGV
VarQ = 'Dif_IGV'
d1_bajo = d1[(d1[VarQ] < np.quantile(d1[VarQ], 0.25))]
d3_bajo = d3[(d3[VarQ] < np.quantile(d3[VarQ], 0.25))]
d4_bajo = d4[(d4[VarQ] < np.quantile(d4[VarQ], 0.25))]
d5_bajo = d5[(d5[VarQ] < np.quantile(d5[VarQ], 0.25))]

# Corte con el eje Y corregido, b corregido
b1 = Ab[0, 1] - ((Ab[0, 0] * d1_bajo['Poder'].mean() + Ab[0, 1]) - d1_bajo['IGV'].mean())
b3 = Ab[1, 1] - ((Ab[1, 0] * d3_bajo['Poder'].mean() + Ab[1, 1]) - d3_bajo['IGV'].mean())
b4 = Ab[2, 1] - ((Ab[2, 0] * d4_bajo['Poder'].mean() + Ab[2, 1]) - d4_bajo['IGV'].mean())
b5 = Ab[3, 1] - ((Ab[3, 0] * d5_bajo['Poder'].mean() + Ab[3, 1]) - d5_bajo['IGV'].mean())
bP = np.array([b1, b3, b4, b5])


## PROBLEMA DE OPTIMIZACIÓN

# Operación con 2 calderas
def objetivo2(x):
    x1, x2 = x[0], x[1]
    return x1 * (w1 * ef[indices[0]] + w2 * fun(x1, AbV[indices[0], 0], bV[indices[0]])) + x2 * (w1 * ef[indices[1]] + w2 * fun(x2, AbV[indices[1], 0], bV[indices[1]]))


def restriccion2(x):
    return x[0] + x[1] - req


# Operación con 3 calderas
def objetivo3(x):
    x1, x2, x3 = x[0], x[1], x[2]
    return x1 * (w1 * ef[indices[0]] + w2 * fun(x1, AbV[indices[0], 0], bV[indices[0]])) + x2 * (w1 * ef[indices[1]] + w2 * fun(x2, AbV[indices[1], 0], bV[indices[1]])) + x3 * (w1 * ef[indices[2]] + w2 * fun(x3, AbV[indices[2], 0], bV[indices[2]]))


def restriccion3(x):
    return x[0] + x[1] + x[2] - req


# Operación con 4 calderas
def objetivo4(x):
    x1, x2, x3, x4 = x[0], x[1], x[2], x[3]
    return x1 * (w1 * ef[indices[0]] + w2 * fun(x1, AbV[indices[0], 0], bV[indices[0]])) + x2 * (w1 * ef[indices[1]] + w2 * fun(x2, AbV[indices[1], 0], bV[indices[1]])) + x3 * (w1 * ef[indices[2]] + w2 * fun(x3, AbV[indices[2], 0], bV[indices[2]])) + x4 * (w1 * ef[indices[3]] + w2 * fun(x4, AbV[indices[3], 0], bV[indices[3]]))


def restriccion4(x):
    return x[0] + x[1] + x[2] + x[3] - req


def calcular_Prod(carga, pod1, pod3, pod4, pod5):
    global req, ef, ef1, ef3, ef4, ef5, bV, b1V, b3V, b4V, b5V

    ## caldera 1
    r1, n_min, cont = 5, 5000, 0
    d1V = d1[(d1['Poder'] > pod1 - r1) & (d1['Poder'] < pod1 + r1)]
    n_datos = len(d1V)
    while n_datos < n_min:
        cont += 1
        d1V = d1[(d1['Poder'] > pod1 - r1 * cont) & (d1['Poder'] < pod1 + r1 * cont)]
        n_datos = len(d1V)

    ## caldera 3
    cont = 0
    d3V = d3[(d3['Poder'] > pod3 - r1) & (d3['Poder'] < pod3 + r1)]
    n_datos = len(d3V)
    while n_datos < n_min:
        cont += 1
        d3V = d3[(d3['Poder'] > pod3 - r1 * cont) & (d3['Poder'] < pod3 + r1 * cont)]
        n_datos = len(d3V)

    ## caldera 4
    cont = 0
    d4V = d4[(d4['Poder'] > pod4 - r1) & (d4['Poder'] < pod4 + r1)]
    n_datos = len(d4V)
    while n_datos < n_min:
        cont += 1
        d4V = d4[(d4['Poder'] > pod4 - r1 * cont) & (d4['Poder'] < pod4 + r1 * cont)]
        n_datos = len(d4V)

    ## caldera 5
    cont = 0
    d5V = d5[(d5['Poder'] > pod5 - r1) & (d5['Poder'] < pod5 + r1)]
    n_datos = len(d5V)
    while n_datos < n_min:
        cont += 1
        d5V = d5[(d5['Poder'] > pod5 - r1 * cont) & (d5['Poder'] < pod5 + r1 * cont)]
        n_datos = len(d5V)

    ## Curvas de regresion segun el Vapor
    [AbV[0, 0], AbV[0, 1]], cov = curve_fit(fun, d1V['Producción Vapor'], d1V['IGV'])
    [AbV[1, 0], AbV[1, 1]], cov = curve_fit(fun, d3V['Producción Vapor'], d3V['IGV'])
    [AbV[2, 0], AbV[2, 1]], cov = curve_fit(fun, d4V['Producción Vapor'], d4V['IGV'])
    [AbV[3, 0], AbV[3, 1]], cov = curve_fit(fun, d5V['Producción Vapor'], d5V['IGV'])

    d1V = d1V.copy()
    d3V = d3V.copy()
    d4V = d4V.copy()
    d5V = d5V.copy()

    d1V['Dif_IGV_V'] = d1V['IGV'] - fun(d1V['Producción Vapor'], AbV[0, 0], AbV[0, 1])
    d3V['Dif_IGV_V'] = d3V['IGV'] - fun(d3V['Producción Vapor'], AbV[1, 0], AbV[1, 1])
    d4V['Dif_IGV_V'] = d4V['IGV'] - fun(d4V['Producción Vapor'], AbV[2, 0], AbV[2, 1])
    d5V['Dif_IGV_V'] = d5V['IGV'] - fun(d5V['Producción Vapor'], AbV[3, 0], AbV[3, 1])

    # Primer cuartil de Dif_IGV
    VarQV = 'Dif_IGV_V'
    d1_bajoV = d1V[(d1V[VarQV] < np.quantile(d1V[VarQV], 0.25))]
    d3_bajoV = d3V[(d3V[VarQV] < np.quantile(d3V[VarQV], 0.25))]
    d4_bajoV = d4V[(d4V[VarQV] < np.quantile(d4V[VarQV], 0.25))]
    d5_bajoV = d5V[(d5V[VarQV] < np.quantile(d5V[VarQV], 0.25))]

    # Corte con el eje Y corregido, b corregido segun el Vapor
    b1V = AbV[0, 1] - ((AbV[0, 0] * d1_bajoV['Producción Vapor'].mean() + AbV[0, 1]) - d1_bajoV['IGV'].mean())
    b3V = AbV[1, 1] - ((AbV[1, 0] * d3_bajoV['Producción Vapor'].mean() + AbV[1, 1]) - d3_bajoV['IGV'].mean())
    b4V = AbV[2, 1] - ((AbV[2, 0] * d4_bajoV['Producción Vapor'].mean() + AbV[2, 1]) - d4_bajoV['IGV'].mean())
    b5V = AbV[3, 1] - ((AbV[3, 0] * d5_bajoV['Producción Vapor'].mean() + AbV[3, 1]) - d5_bajoV['IGV'].mean())
    bV = np.array([b1V, b3V, b4V, b5V])

    # Eficiencias según el poder calorífico de Gas
    ef1 = fun(pod1, Ab[0, 0], b1)
    ef3 = fun(pod3, Ab[1, 0], b3)
    ef4 = fun(pod4, Ab[2, 0], b4)
    ef5 = fun(pod5, Ab[3, 0], b5)
    ef = np.array([ef1, ef3, ef4, ef5])

    rest2 = {'type': 'eq', 'fun': restriccion2}
    rest3 = {'type': 'eq', 'fun': restriccion3}
    rest4 = {'type': 'eq', 'fun': restriccion4}

    Lim1 = 180
    x0_2 = np.array([Lim1, Lim1])
    x0_3 = np.array([Lim1, Lim1, Lim1])
    x0_4 = np.array([Lim1, Lim1, Lim1, Lim1])

    bnd_x = np.zeros((4, 3)).tolist()
    for i in range(4):
        if indices[i] == 3:
            bnd_x[i][0] = (Lim1, 250)
            bnd_x[i][1] = (Lim1, 250)
            bnd_x[i][2] = (Lim1, 250)
        else:
            bnd_x[i][0] = (Lim1, 280)
            bnd_x[i][1] = (Lim1, 290)
            bnd_x[i][2] = (Lim1, 300)

    cald, disp = np.zeros((len(carga), 4)), np.zeros(len(carga))

    for i in range(len(carga)):
        req = carga[i]
        if (req < 300):
            cald[i, indices[0]] = carga[i]
        elif (req >= 300 and req < Lim1 * 2):
            cald[i, indices[0]], cald[i, indices[1]] = carga[i] / 2, carga[i] / 2
        elif (req >= Lim1 * 2 and req <= Lim1 * 3):
            sol2 = minimize(objetivo2, x0_2, constraints=rest2, bounds=[bnd_x[0][0], bnd_x[1][0]], method='SLSQP')  # 'SLSQP' y 'trust-constr'
            cald[i, indices[0]], cald[i, indices[1]] = sol2.x[0], sol2.x[1]
        if calDisp == 2:
            if (req > Lim1 * 3 and req <= maxProdV - 20):
                sol2 = minimize(objetivo2, x0_2, constraints=rest2, bounds=[bnd_x[0][1], bnd_x[1][1]], method='SLSQP')  # 'SLSQP' y 'trust-constr'
                cald[i, indices[0]], cald[i, indices[1]] = sol2.x[0], sol2.x[1]
            elif (req > maxProdV - 20):
                sol2 = minimize(objetivo2, x0_2, constraints=rest2, bounds=[bnd_x[0][2], bnd_x[1][2]], method='SLSQP')  # 'SLSQP' y 'trust-constr'
                cald[i, indices[0]], cald[i, indices[1]] = sol2.x[0], sol2.x[1]
        if calDisp == 3 or calDisp == 4:
            if (req > Lim1 * 3 and req <= 800):
                sol3 = minimize(objetivo3, x0_3, constraints=rest3, bounds=[bnd_x[0][0], bnd_x[1][0], bnd_x[2][0]], method='SLSQP')
                cald[i, indices[0]], cald[i, indices[1]], cald[i, indices[2]] = sol3.x[0], sol3.x[1], sol3.x[2]
        if (calDisp == 3 and maxProdV == 850):
            if (req > 800 and req <= maxProdV - 20):
                sol3 = minimize(objetivo3, x0_3, constraints=rest3, bounds=[bnd_x[0][1], bnd_x[1][1], bnd_x[2][1]], method='SLSQP')
                cald[i, indices[0]], cald[i, indices[1]], cald[i, indices[2]] = sol3.x[0], sol3.x[1], sol3.x[2]
            elif (req > maxProdV - 20):
                sol3 = minimize(objetivo3, x0_3, constraints=rest3, bounds=[bnd_x[0][2], bnd_x[1][2], bnd_x[2][2]], method='SLSQP')
                cald[i, indices[0]], cald[i, indices[1]], cald[i, indices[2]] = sol3.x[0], sol3.x[1], sol3.x[2]
        elif (calDisp == 3 and maxProdV == 900):
            if (req > 800 and req <= maxProdV - 30):
                sol3 = minimize(objetivo3, x0_3, constraints=rest3, bounds=[bnd_x[0][1], bnd_x[1][1], bnd_x[2][1]], method='SLSQP')
                cald[i, indices[0]], cald[i, indices[1]], cald[i, indices[2]] = sol3.x[0], sol3.x[1], sol3.x[2]
            elif (req > maxProdV - 30):
                sol3 = minimize(objetivo3, x0_3, constraints=rest3, bounds=[bnd_x[0][2], bnd_x[1][2], bnd_x[2][2]], method='SLSQP')
                cald[i, indices[0]], cald[i, indices[1]], cald[i, indices[2]] = sol3.x[0], sol3.x[1], sol3.x[2]
        if calDisp == 4:
            if (req > 800 and req < 1090):
                sol4 = minimize(objetivo4, x0_4, constraints=rest4, bounds=[bnd_x[0][0], bnd_x[1][0], bnd_x[2][0], bnd_x[3][0]], method='SLSQP')
                cald[i, indices[0]], cald[i, indices[1]], cald[i, indices[2]], cald[i, indices[3]] = sol4.x[0], sol4.x[1], sol4.x[2], sol4.x[3]
            elif (req >= 1090 and req < 1120):
                sol5 = minimize(objetivo4, x0_4, constraints=rest4, bounds=[bnd_x[0][1], bnd_x[1][1], bnd_x[2][1], bnd_x[3][1]], method='SLSQP')
                cald[i, indices[0]], cald[i, indices[1]], cald[i, indices[2]], cald[i, indices[3]] = sol5.x[0], sol5.x[1], sol5.x[2], sol5.x[3]
            elif (req >= 1120):
                sol5 = minimize(objetivo4, x0_4, constraints=rest4, bounds=[bnd_x[0][2], bnd_x[1][2], bnd_x[2][2], bnd_x[3][2]], method='SLSQP')
                cald[i, indices[0]], cald[i, indices[1]], cald[i, indices[2]], cald[i, indices[3]] = sol5.x[0], sol5.x[1], sol5.x[2], sol5.x[3]

    for i in range(len(carga)):
        if cald[i, 0] != 0:
            disp[i] += (300 - cald[i, 0])
        if cald[i, 1] != 0:
            disp[i] += (300 - cald[i, 1])
        if cald[i, 2] != 0:
            disp[i] += (300 - cald[i, 2])
        if cald[i, 3] != 0:
            disp[i] += (250 - cald[i, 3])
    return cald[:, 0], cald[:, 1], cald[:, 2], cald[:, 3], disp


def optimizar_generacion(
    Gen_elec,
    modo="gas",
    disp_t1=1,
    disp_t2=1,
    disp_t3=1,
    disp_tg=1,
    datosL=[8, 17, 8, 20, 8, 17, 8, 42]
):

    # =========================
    # Límites de equipos
    # =========================
    limites = {
        "t1": (datosL[0], datosL[1]),
        "t2": (datosL[2], datosL[3]),
        "t3": (datosL[4], datosL[5]),
        "tg": (datosL[6], datosL[7])
    }

    # =========================
    # Máxima generación posible
    # =========================
    max_gen = (
        limites["t1"][1] * disp_t1 +
        limites["t2"][1] * disp_t2 +
        limites["t3"][1] * disp_t3 +
        limites["tg"][1] * disp_tg
    )

    ordenM = np.sort(np.array([
        limites["t1"][0] * disp_t1,
        limites["t2"][0] * disp_t2,
        limites["t3"][0] * disp_t3,
        limites["tg"][0] * disp_tg
    ]))
    min_gen = 0
    for i in range(len(ordenM)):
        if ordenM[i] > 0:
            min_gen = ordenM[i]
            break

    alerta = None

    # =========================
    # VALIDACIÓN DE DEMANDA
    # =========================
    DispoGE = max_gen - Gen_elec  # Disponibilidad real para generar
    if Gen_elec > max_gen:
        alerta = f"⚠️ Demanda supera la capacidad máxima.\nMáx: {max_gen:.2f} MWh\n\nDéficit: {Gen_elec - max_gen:.2f} MWh"
        Gen_objetivo = max_gen

    elif Gen_elec < min_gen and min_gen > 0:
        alerta = f"⚠️ Demanda menor al mínimo técnico.\nMín: {min_gen:.2f} MWh"
        Gen_objetivo = min_gen

    else:
        Gen_objetivo = Gen_elec

    # =========================
    # MODELO
    # =========================
    model = pulp.LpProblem("Optimizacion_Energia", pulp.LpMinimize)

    # Variables
    x1 = pulp.LpVariable('Turbo1', lowBound=0)
    x2 = pulp.LpVariable('Turbo2', lowBound=0)
    x3 = pulp.LpVariable('Turbo3', lowBound=0)
    x4 = pulp.LpVariable('Turbogas', lowBound=0)

    y1 = pulp.LpVariable('y1', cat='Binary')
    y2 = pulp.LpVariable('y2', cat='Binary')
    y3 = pulp.LpVariable('y3', cat='Binary')
    y4 = pulp.LpVariable('y4', cat='Binary')

    # =========================
    # RESTRICCIÓN DE DEMANDA
    # =========================
    model += x1 + x2 + x3 + x4 == Gen_objetivo

    # =========================
    # DISPONIBILIDAD
    # =========================
    model += y1 <= disp_t1
    model += y2 <= disp_t2
    model += y3 <= disp_t3
    model += y4 <= disp_tg

    # =========================
    # RANGOS OPERATIVOS
    # =========================
    model += x1 >= limites["t1"][0] * y1
    model += x1 <= limites["t1"][1] * y1

    model += x2 >= limites["t2"][0] * y2
    model += x2 <= limites["t2"][1] * y2

    model += x3 >= limites["t3"][0] * y3
    model += x3 <= limites["t3"][1] * y3

    model += x4 >= limites["tg"][0] * y4
    model += x4 <= limites["tg"][1] * y4

    # =========================
    # FUNCIONES
    # =========================

    gas = (
        (389.0270857768606 * x1 - 569.0861979981702 * y1) +
        (298.2310010065771 * x2 + 42.444633942665234 * y2) +
        (333.4069961493692 * x3 + 197.52719471150525 * y3) +
        (127.2470145979009 * x4 + 1343.976645798325 * y4)
    )

    energia = (
        (357.07611463958744 * x1 - 567.8299892157046 * y1) +
        (262.85934906758905 * x2 + 109.02704952710621 * y2) +
        (267.64824867048566 * x3 + 592.961886370333 * y3) +
        (122.82716394953695 * x4 + 1149.3292951034657 * y4)
    )

    vaporC = (
        (13.30822224545888 * x1 - 22.462469454437944 * y1) +
        (10.01071382077395 * x2 + 72.58249825682918 * y2) +
        (10.459943715247121 * x3 + 15.09121320702406 * y3)
    )

    vaporT = (
        (13.30822224545888 * x1 - 22.462469454437944 * y1) +
        (9.76370441510356 * x2 + 3.8101078021226176 * y2) +
        (10.459943715247121 * x3 + 15.09121320702406 * y3) -
        (0.20236502112763388 * x4 + 60 * y4)
    )

    # =========================
    # FUNCIÓN OBJETIVO
    # =========================
    if modo == "gas":
        model += gas
    elif modo == "energia":
        model += energia

    # Resolver
    solver = _crear_solver()
    model.solve(solver)

    # =========================
    # RESULTADOS
    # =========================
    resultado = {
        "Turbo1": x1.varValue,
        "Turbo2": x2.varValue,
        "Turbo3": x3.varValue,
        "Turbogas": x4.varValue,
        "Gas_total": pulp.value(gas),
        "Energia_total": pulp.value(energia),
        "Vapor_cal": pulp.value(vaporC),
        "Vapor_total": pulp.value(vaporT),
        "Generacion_total": sum([x1.varValue, x2.varValue, x3.varValue, x4.varValue]),
        "Generacion": [x1.varValue, x2.varValue, x3.varValue, x4.varValue],
        "Consumo_vapor": [(13.30822224545888 * x1.varValue - 22.462469454437944) * bool(x1.varValue > 0),
                          (10.01071382077395 * x2.varValue + 72.58249825682918) * bool(x2.varValue > 0),
                          (10.459943715247121 * x3.varValue + 15.09121320702406) * bool(x3.varValue > 0), 0],
        "Consumo_gas": [(389.0270857768606 * x1.varValue - 569.0861979981702) * bool(x1.varValue > 0),
                        (308.39141678994275 * x2.varValue + 2066.1379362558937) * bool(x2.varValue > 0),
                        (333.4069961493692 * x3.varValue + 197.52719471150525) * bool(x3.varValue > 0),
                        (135.41465061565611 * x4.varValue + 3082.9548941061225) * bool(x4.varValue > 0)],
        "Consumo_energia": [(357.07611463958744 * x1.varValue - 567.8299892157046) * bool(x1.varValue > 0),
                            (268.9050115052876 * x2.varValue + 1972.225757407095) * bool(x2.varValue > 0),
                            (267.64824867048566 * x3.varValue + 592.961886370333) * bool(x3.varValue > 0),
                            (132.4087587404033 * x4.varValue + 2720.7537866721036) * bool(x4.varValue > 0)],
        "Extrac_vapor": [0,
                         (0.20236502112763388 * x2.varValue + 69.52703724847515) * bool(x2.varValue > 0),
                         0, (0.20236502112763388 * x4.varValue + 75) * bool(x4.varValue > 0)],
        "DispoGE": DispoGE,
        "Alerta": alerta

    }

    return resultado
