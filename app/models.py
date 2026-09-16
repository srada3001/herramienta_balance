# coding: utf-8
"""Esquemas de entrada/salida de la API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EntradaCalculo(BaseModel):
    # Variables de entrada
    generacion_electrica: float = Field(50, description="Generación eléctrica requerida [MWh]")
    vapor_industrial: float = Field(450, description="Vapor industrial requerido [Klb/h]")

    # Poderes caloríficos
    poder_gas_natural: float = Field(934, description="Poder calorífico gas natural [BTU/pce]")
    poder_gas_combustible: float = Field(898, description="Poder calorífico gas combustible [BTU/pce]")

    # Mezclas (% de gas natural por caldera)
    mezcla1: float = Field(100, ge=0, le=100)
    mezcla3: float = Field(100, ge=0, le=100)
    mezcla4: float = Field(0, ge=0, le=100)
    mezcla5: float = Field(0, ge=0, le=100)

    # Disponibilidad de calderas
    caldera1: int = Field(1, ge=0, le=1)
    caldera3: int = Field(1, ge=0, le=1)
    caldera4: int = Field(1, ge=0, le=1)
    caldera5: int = Field(1, ge=0, le=1)

    # Disponibilidad de generadores
    turbo1: int = Field(1, ge=0, le=1)
    turbo2: int = Field(1, ge=0, le=1)
    turbo3: int = Field(1, ge=0, le=1)
    turbogas: int = Field(1, ge=0, le=1)


class Limites(BaseModel):
    """Límites operativos de generación eléctrica [MWh]."""
    t1_min: float
    t1_max: float
    t2_min: float
    t2_max: float
    t3_min: float
    t3_max: float
    tg_min: float
    tg_max: float

    @classmethod
    def desde_lista(cls, datosL: List[float]) -> "Limites":
        return cls(t1_min=datosL[0], t1_max=datosL[1], t2_min=datosL[2], t2_max=datosL[3],
                   t3_min=datosL[4], t3_max=datosL[5], tg_min=datosL[6], tg_max=datosL[7])

    def a_lista(self) -> List[float]:
        return [self.t1_min, self.t1_max, self.t2_min, self.t2_max,
                self.t3_min, self.t3_max, self.tg_min, self.tg_max]


class EstadoEquipos(BaseModel):
    """Resumen reactivo que muestra la cabecera sin necesidad de calcular."""
    calderas_habilitadas: int
    produccion_maxima: float
    generadores_habilitados: int
    generacion_maxima: float


class Resultado(BaseModel):
    modo_optimizacion: str
    alerta: Optional[str] = None
    generadores: Dict[str, Any]
    calderas: Dict[str, Any]
    tabla_calderas: List[Dict[str, str]]
    tabla_generadores: List[Dict[str, str]]
