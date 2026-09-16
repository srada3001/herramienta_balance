# coding: utf-8
"""
Orquestación de un cálculo completo.

Equivale a `on_button_toggle()` + `fCalcular()` de la aplicación Tkinter, pero
devolviendo estructuras de datos en lugar de pintar widgets. Las fórmulas, los
coeficientes y el orden de las operaciones son los mismos que en el original.
"""

import threading

import numpy as np
from scipy.optimize import curve_fit

from . import core
from .core import AbV, Oxi1, Oxi3, Oxi4, Oxi5, d1, d3, d4, d5, fun, w1, w2
from .limites import cargar_Datos

# El núcleo replica el diseño original basado en variables globales
# (maxProdV, calDisp, indices, req, ef, bV...). Serializamos los cálculos para
# que dos peticiones simultáneas no se pisen esas variables.
_lock = threading.Lock()


class ErrorDeCalculo(Exception):
    """Equivale a los messagebox de error de la app de escritorio."""


def estado_calderas(cal1, cal3, cal4, cal5):
    """Equivalente a on_button_toggle(): calDisp, indices y producción máxima."""
    calDisp = cal1 + cal3 + cal4 + cal5
    puntosa = np.array([cal1, cal3, cal4, cal5]) * np.array([4, 1, 3, 2])
    puntos = puntosa.tolist()
    pun_orden = sorted(puntos, reverse=True)
    indices = [puntos.index(pun_orden[0]), puntos.index(pun_orden[1]),
               puntos.index(pun_orden[2]), puntos.index(pun_orden[3])]

    maxProdV = 0
    if calDisp == 4:
        maxProdV = 1150
    elif calDisp == 3:
        maxProdV = 850 if cal5 == 1 else 900
    elif calDisp == 2:
        maxProdV = 550 if cal5 == 1 else 600
    elif calDisp == 1:
        maxProdV = 250 if cal5 == 1 else 300

    return calDisp, indices, maxProdV


def estado_generadores(t1, t2, t3, tg, datosL):
    """Equivalente a on_button_Turbos()."""
    TurDisp = t1 + t2 + t3 + tg
    max_gen = datosL[1] * t1 + datosL[3] * t2 + datosL[5] * t3 + datosL[7] * tg
    return TurDisp, max_gen


def _tabla_generadores(res_sal):
    """Equivale a la construcción de Tabla_Gen en fCalcular()."""
    equipos = ["Turbo 1", "Turbo 2", "Turbo 3", "Turbogás"]
    gen = res_sal['Generacion']
    vapor = res_sal['Consumo_vapor']
    gas = res_sal['Consumo_gas']
    energia = res_sal['Consumo_energia']
    ext = res_sal['Extrac_vapor']
    std_gen = [1.192499 * bool(res_sal['Turbo1'] > 0), 3.334151 * bool(res_sal['Turbo2'] > 0),
               1.601820 * bool(res_sal['Turbo3'] > 0), 6.232518 * bool(res_sal['Turbogas'] > 0)]
    std_vapor = [16.209786 * bool(res_sal['Turbo1'] > 0), 35.022389 * bool(res_sal['Turbo2'] > 0),
                 19.304467 * bool(res_sal['Turbo3'] > 0), 0]
    std_gas = [482.156888 * bool(res_sal['Turbo1'] > 0), 1085.259441 * bool(res_sal['Turbo2'] > 0),
               604.168952 * bool(res_sal['Turbo3'] > 0), 976.892086 * bool(res_sal['Turbogas'] > 0)]
    std_energia = [469.425930 * bool(res_sal['Turbo1'] > 0), 1012.668187 * bool(res_sal['Turbo2'] > 0),
                   543.456526 * bool(res_sal['Turbo3'] > 0), 1070.520182 * bool(res_sal['Turbogas'] > 0)]
    std_ext = [0, 10.613377 * bool(res_sal['Turbo2'] > 0), 0, 12.6842 * bool(res_sal['Turbogas'] > 0)]

    filas = []
    for i in range(4):
        if gen[i] is None or gen[i] <= 1:  # Eliminar ceros
            continue
        filas.append({
            "Equipo": equipos[i],
            "Generación": '%.2f' % gen[i] + ' ± ' + '%.2f' % std_gen[i],
            "Consumo Vapor": '%.1f' % vapor[i] + ' ± ' + '%.1f' % std_vapor[i],
            "Consumo Gas": '%.0f' % gas[i] + ' ± ' + '%.0f' % std_gas[i],
            "Consumo Energía": '%.0f' % energia[i] + ' ± ' + '%.0f' % std_energia[i],
            "Extracción Vapor": '%.0f' % ext[i] + ' ± ' + '%.0f' % std_ext[i],
        })
    return filas


def _tabla_calderas(cald, pod1, pod3, pod4, pod5, poder1):
    """Equivale a la construcción de Tabla_DF en fCalcular()."""
    num = (cald > 0).astype(int).sum()  # Número de calderas en operación

    Tabla = np.zeros([num, 16])
    cal_Title, poder, oxi, eficiencia = [], [], [], []
    i, rango, rangoP, rango2, rangoP2, rango3, rango4 = 0, 5, 5, 20, 10, 10, 30
    for (j, prod) in enumerate(cald):
        if prod > 0:
            if j == 0:
                cal_Title.append('Caldera 1')
                eficiencia.append(w1 * core.ef1 + w2 * fun(prod, AbV[0, 0], core.b1V))
                poder.append(pod1)
                oxi.append(Oxi1(pod1))
                d = d1[(d1['Poder'] > pod1 - rango) & (d1['Poder'] < pod1 + rango) & (d1['IGV'] < np.quantile(d1['IGV'], 0.25))]
                parte = d[(d['Producción Vapor'] > prod - rangoP) & (d['Producción Vapor'] < prod + rangoP)]
                if len(parte) < 2:
                    d = d1[(d1['Poder'] > pod1 - rango2) & (d1['Poder'] < pod1 + rango2) & (d1['IGV'] < np.quantile(d1['IGV'], 0.25))]
                    parte = d[(d['Producción Vapor'] > prod - rangoP2) & (d['Producción Vapor'] < prod + rangoP2)]
                    if len(parte) < 2:
                        Ab2 = np.zeros((4, 2))
                        dProd = d1[(d1['IGV'] < np.quantile(d1['IGV'], 0.5))]
                        [Ab2[0, 0], Ab2[0, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['Flujo Gas'])
                        [Ab2[1, 0], Ab2[1, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['Flujo Aire'])
                        [Ab2[2, 0], Ab2[2, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['Temp. Vapor'])
                        [Ab2[3, 0], Ab2[3, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['T Aire al Cal'])

            elif j == 1:
                cal_Title.append('Caldera 3')
                eficiencia.append(w1 * core.ef3 + w2 * fun(prod, AbV[1, 0], core.b3V))
                poder.append(pod3)
                oxi.append(Oxi3(pod3))
                d = d3[(d3['Poder'] > pod3 - rango) & (d3['Poder'] < pod3 + rango) & (d3['IGV'] < np.quantile(d3['IGV'], 0.25))]
                parte = d[(d['Producción Vapor'] > prod - rangoP) & (d['Producción Vapor'] < prod + rangoP)]
                if len(parte) < 2:
                    d = d3[(d3['Poder'] > pod3 - rango2) & (d3['Poder'] < pod3 + rango2) & (d3['IGV'] < np.quantile(d3['IGV'], 0.25))]
                    parte = d[(d['Producción Vapor'] > prod - rangoP2) & (d['Producción Vapor'] < prod + rangoP2)]
                    if len(parte) < 2:
                        Ab2 = np.zeros((5, 2))
                        dProd = d3[(d3['IGV'] < np.quantile(d3['IGV'], 0.5))]
                        [Ab2[0, 0], Ab2[0, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['Flujo Gas'])
                        [Ab2[1, 0], Ab2[1, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['Flujo Aire'])
                        [Ab2[2, 0], Ab2[2, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['Temp. Vapor'])
                        [Ab2[3, 0], Ab2[3, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['T Aire al Cal'])

            elif j == 2:
                cal_Title.append('Caldera 4')
                eficiencia.append(w1 * core.ef4 + w2 * fun(prod, AbV[2, 0], core.b4V))
                poder.append(pod4)
                oxi.append(Oxi4(pod4))
                d = d4[(d4['Poder'] > pod4 - rango3) & (d4['Poder'] < pod4 + rango3) & (d4['IGV'] < np.quantile(d4['IGV'], 0.25))]
                parte = d[(d['Producción Vapor'] > prod - rangoP) & (d['Producción Vapor'] < prod + rangoP)]
                if len(parte) < 2:
                    d = d4[(d4['Poder'] > pod4 - rango4) & (d4['Poder'] < pod4 + rango4) & (d4['IGV'] < np.quantile(d4['IGV'], 0.25))]
                    parte = d[(d['Producción Vapor'] > prod - rangoP2) & (d['Producción Vapor'] < prod + rangoP2)]
                    if len(parte) < 2:
                        Ab2 = np.zeros((5, 2))
                        dProd = d4[(d4['IGV'] < np.quantile(d4['IGV'], 0.5))]
                        [Ab2[0, 0], Ab2[0, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['Flujo Gas'])
                        [Ab2[1, 0], Ab2[1, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['Flujo Aire'])
                        [Ab2[2, 0], Ab2[2, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['Temp. Vapor'])
                        [Ab2[3, 0], Ab2[3, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['T Aire al Cal'])

            else:
                cal_Title.append('Caldera 5')
                eficiencia.append(w1 * core.ef5 + w2 * fun(prod, AbV[3, 0], core.b5V))
                poder.append(pod5)
                oxi.append(Oxi5(pod5))
                d = d5[(d5['Poder'] > pod5 - rango3) & (d5['Poder'] < pod5 + rango3) & (d5['IGV'] < np.quantile(d5['IGV'], 0.25))]
                parte = d[(d['Producción Vapor'] > prod - rangoP) & (d['Producción Vapor'] < prod + rangoP)]
                if len(parte) < 2:
                    d = d5[(d5['Poder'] > pod5 - rango4) & (d5['Poder'] < pod5 + rango4) & (d5['IGV'] < np.quantile(d5['IGV'], 0.25))]
                    parte = d[(d['Producción Vapor'] > prod - rangoP2) & (d['Producción Vapor'] < prod + rangoP2)]
                    if len(parte) < 2:
                        Ab2 = np.zeros((5, 2))
                        dProd = d5[(d5['IGV'] < np.quantile(d5['IGV'], 0.5))]
                        [Ab2[0, 0], Ab2[0, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['Flujo Gas'])
                        [Ab2[1, 0], Ab2[1, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['Flujo Aire'])
                        [Ab2[2, 0], Ab2[2, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['Temp. Vapor'])
                        [Ab2[3, 0], Ab2[3, 1]], cov = curve_fit(fun, dProd['Producción Vapor'], dProd['T Aire al Cal'])

            if len(parte) < 2:
                Tabla[i, 0], Tabla[i, 1] = prod, 1.5
                Tabla[i, 2], Tabla[i, 3] = 0, 0.12
                Tabla[i, 4], Tabla[i, 5] = fun(prod, Ab2[0, 0], Ab2[0, 1]), 150
                Tabla[i, 6], Tabla[i, 7] = fun(prod, Ab2[1, 0], Ab2[1, 1]), 1800
                Tabla[i, 8], Tabla[i, 9] = fun(prod, Ab2[2, 0], Ab2[2, 1]), 5.2
                Tabla[i, 10], Tabla[i, 11] = fun(prod, Ab2[3, 0], Ab2[3, 1]), 7.3
                Tabla[i, 12], Tabla[i, 13] = poder1, 5.1
                Tabla[i, 14], Tabla[i, 15] = 0, 0.031
            else:
                Tabla[i, 0], Tabla[i, 1] = prod, np.round(parte['Producción Vapor'].std(), 2)
                Tabla[i, 2], Tabla[i, 3] = 0, np.round(parte['Oxigeno'].std(), 2)
                Tabla[i, 4], Tabla[i, 5] = np.round(parte['Flujo Gas'].mean(), 2), np.round(parte['Flujo Gas'].std(), 2)
                Tabla[i, 6], Tabla[i, 7] = np.round(parte['Flujo Aire'].mean(), 2), np.round(parte['Flujo Aire'].std(), 2)
                Tabla[i, 8], Tabla[i, 9] = np.round(parte['Temp. Vapor'].mean(), 2), np.round(parte['Temp. Vapor'].std(), 2)
                Tabla[i, 10], Tabla[i, 11] = np.round(parte['T Aire al Cal'].mean(), 2), np.round(parte['T Aire al Cal'].std(), 2)
                Tabla[i, 12], Tabla[i, 13] = poder1, np.round(parte['Poder'].std(), 2)
                Tabla[i, 14], Tabla[i, 15] = 0, np.round(parte['IGV'].std(), 3)
            i += 1

    filas = []
    for k in range(num):
        filas.append({
            "No.": cal_Title[k],
            "Prod Vapor": '%.1f' % Tabla[k, 0] + ' ± ' + '%.1f' % Tabla[k, 1],
            "% Oxígeno": '%.2f' % oxi[k] + ' ± ' + '%.2f' % Tabla[k, 3],
            "Flujo de Gas": '%d' % Tabla[k, 4] + ' ± ' + '%d' % Tabla[k, 5],
            "Flujo de Aire": '%d' % Tabla[k, 6] + ' ± ' + '%d' % Tabla[k, 7],
            "Temp. Vapor": '%.1f' % Tabla[k, 8] + ' ± ' + '%.1f' % Tabla[k, 9],
            "T Aire Calent": '%.1f' % Tabla[k, 10] + ' ± ' + '%.1f' % Tabla[k, 11],
            "Poder Calor.": '%.1f' % poder[k] + ' ± ' + '%.1f' % Tabla[k, 13],
            "IGV": '%.3f' % eficiencia[k] + ' ± ' + '%.3f' % Tabla[k, 15],
        })
    return filas


def calcular(entrada):
    """Ejecuta el cálculo completo. `entrada` es un objeto EntradaCalculo."""
    with _lock:
        datosL = cargar_Datos()

        calDisp, indices, maxProdV = estado_calderas(
            entrada.caldera1, entrada.caldera3, entrada.caldera4, entrada.caldera5)

        if calDisp == 0:
            raise ErrorDeCalculo("Debe habilitar al menos una caldera.")
        if entrada.turbo1 + entrada.turbo2 + entrada.turbo3 + entrada.turbogas == 0:
            raise ErrorDeCalculo("Debe habilitar al menos un generador.")

        # Se publican en el núcleo, igual que hacía on_button_toggle() con las globales
        core.calDisp = calDisp
        core.indices = indices
        core.maxProdV = maxProdV

        # Turbos
        Gen_elec = entrada.generacion_electrica
        VaporProc = entrada.vapor_industrial

        res_gas = core.optimizar_generacion(
            Gen_elec, modo="gas", disp_t1=entrada.turbo1, disp_t2=entrada.turbo2,
            disp_t3=entrada.turbo3, disp_tg=entrada.turbogas, datosL=datosL)
        res_energia = core.optimizar_generacion(
            Gen_elec, modo="energia", disp_t1=entrada.turbo1, disp_t2=entrada.turbo2,
            disp_t3=entrada.turbo3, disp_tg=entrada.turbogas, datosL=datosL)

        if res_gas['Vapor_total'] < res_energia['Vapor_total']:
            res_sal = res_gas
            modo = "gas"
        else:
            res_sal = res_energia
            modo = "energia"

        if res_sal['Turbo1'] is None:
            raise ErrorDeCalculo(
                "No existe una combinación factible de generadores para la demanda indicada.")

        # Cálculos para los Generadores
        tabla_generadores = _tabla_generadores(res_sal)

        # Cálculos para las Calderas
        carga = res_sal['Vapor_cal'] + VaporProc - (res_sal['Turbo2'] * 0.20236502112763388 + 69.52703724847515) * bool(res_sal['Turbo2'] > 0)

        poder1 = entrada.poder_gas_natural
        poder4 = entrada.poder_gas_combustible
        mezcla1 = entrada.mezcla1
        mezcla3 = entrada.mezcla3
        mezcla4 = entrada.mezcla4
        mezcla5 = entrada.mezcla5
        pod1 = (poder1 * mezcla1 + poder4 * (100 - mezcla1)) / 100
        pod3 = (poder1 * mezcla3 + poder4 * (100 - mezcla3)) / 100
        pod4 = (poder1 * mezcla4 + poder4 * (100 - mezcla4)) / 100
        pod5 = (poder1 * mezcla5 + poder4 * (100 - mezcla5)) / 100

        if not (carga >= 150 and carga <= maxProdV):
            aviso = (res_sal['Alerta'] + "\n\n") if res_sal['Alerta'] else ""
            raise ErrorDeCalculo(
                aviso +
                "La carga total de calderas resultante (%.1f Klb/h) debe estar entre 150 y %s Klb/h. "
                "Ajusta el vapor industrial, la generación eléctrica o las calderas habilitadas."
                % (carga, maxProdV))

        cal1, cal3, cal4, cal5, disp = core.calcular_Prod([carga], pod1, pod3, pod4, pod5)

        cald = np.array([cal1[0], cal3[0], cal4[0], cal5[0]])
        tabla_calderas = _tabla_calderas(cald, pod1, pod3, pod4, pod5, poder1)

        TurDisp, max_gen = estado_generadores(
            entrada.turbo1, entrada.turbo2, entrada.turbo3, entrada.turbogas, datosL)

        return {
            "modo_optimizacion": modo,
            "alerta": res_sal['Alerta'],
            "generadores": {
                "total": res_sal["Generacion_total"],
                "turbo1": res_sal["Turbo1"],
                "turbo2": res_sal["Turbo2"],
                "turbo3": res_sal["Turbo3"],
                "turbogas": res_sal["Turbogas"],
                "disponibilidad": res_sal["DispoGE"],
                "habilitados": TurDisp,
                "generacion_maxima": max_gen,
            },
            "calderas": {
                "carga": carga,
                "caldera1": cal1[0],
                "caldera3": cal3[0],
                "caldera4": cal4[0],
                "caldera5": cal5[0],
                "disponibilidad": disp[0],
                "habilitadas": calDisp,
                "produccion_maxima": maxProdV,
            },
            "tabla_calderas": tabla_calderas,
            "tabla_generadores": tabla_generadores,
        }
