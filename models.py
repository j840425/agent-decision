# models.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class ResourceType(str, Enum):
    """Tipos de recursos que pueden ser costos"""
    # Recursos tangibles
    DINERO = "dinero"
    TIEMPO = "tiempo"
    
    # Recursos personales
    ENERGIA = "energia"
    SALUD = "salud"
    ESTRES = "estres"
    BIENESTAR = "bienestar"
    
    # Recursos sociales
    REPUTACION = "reputacion"
    RELACIONES = "relaciones"
    FAMILIA = "familia"
    RED_CONTACTOS = "red_contactos"
    
    # Recursos profesionales
    CARRERA = "carrera"
    EDUCACION = "educacion"
    EXPERIENCIA = "experiencia"
    HABILIDADES = "habilidades"
    CONOCIMIENTO = "conocimiento"
    CREDENCIALES = "credenciales"
    
    # Recursos estratégicos
    OPORTUNIDAD = "oportunidad"
    CALIDAD_VIDA = "calidad_vida"
    LIBERTAD = "libertad"
    FLEXIBILIDAD = "flexibilidad"
    SEGURIDAD = "seguridad"
    ESTABILIDAD = "estabilidad"
    
    # Recursos financieros específicos
    AHORROS = "ahorros"
    DEUDA = "deuda"
    INVERSION = "inversion"
    PATRIMONIO = "patrimonio"
    
    # Otros
    RIESGO = "riesgo"
    INCERTIDUMBRE = "incertidumbre"
    OTRO = "otro"

class Cost(BaseModel):
    """Representa un costo asociado a una decisión"""
    resource_type: ResourceType
    amount: Optional[float] = 0.0  # CAMBIO: Ahora opcional con default 0
    unit: str = ""  # CAMBIO: Ahora opcional con default vacío
    description: Optional[str] = None

class DecisionNode(BaseModel):
    """Nodo del árbol de decisión"""
    id: str
    description: str
    probability: float = Field(ge=0, le=100)  # Probabilidad en porcentaje
    costs: List[Cost] = Field(default_factory=list)
    benefits: List[Cost] = Field(default_factory=list)  # Beneficios también como "costos negativos"
    children: List['DecisionNode'] = Field(default_factory=list)
    level: int = Field(ge=0)
    reasoning: Optional[str] = None  # Por qué se generó este escenario

class UserProfile(BaseModel):
    """Perfil del usuario"""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # Información básica
    edad: Optional[int] = None
    sexo: Optional[str] = None
    estado_civil: Optional[str] = None
    numero_hijos: Optional[int] = None
    
    # Información profesional
    ocupacion: Optional[str] = None
    ingreso_mensual: Optional[float] = None
    anos_experiencia: Optional[int] = None
    
    # Información de salud
    peso: Optional[float] = None
    altura: Optional[float] = None
    enfermedades: List[str] = Field(default_factory=list)
    
    # Información familiar
    padres_vivos: Optional[bool] = None
    
    # Preferencias
    preferencias_alimentacion: List[str] = Field(default_factory=list)
    
    # Contexto adicional (campo flexible para info extra)
    additional_context: Dict[str, Any] = Field(default_factory=dict)
    
    def to_context_string(self) -> str:
        """Convierte el perfil a un string de contexto para el LLM"""
        context_parts = []

        # AGREGAR AL INICIO:
        context_parts.append("UBICACIÓN: Perú")
        context_parts.append("MONEDA: Soles (PEN)")
        context_parts.append("")
        
        if self.edad:
            context_parts.append(f"Edad: {self.edad} años")
        if self.sexo:
            context_parts.append(f"Sexo: {self.sexo}")
        if self.estado_civil:
            context_parts.append(f"Estado civil: {self.estado_civil}")
        if self.numero_hijos:
            context_parts.append(f"Hijos: {self.numero_hijos}")
        if self.ocupacion:
            context_parts.append(f"Ocupación: {self.ocupacion}")
        if self.ingreso_mensual:
            context_parts.append(f"Ingreso mensual: ${self.ingreso_mensual}")
        if self.anos_experiencia:
            context_parts.append(f"Años de experiencia: {self.anos_experiencia}")
        if self.enfermedades:
            context_parts.append(f"Enfermedades: {', '.join(self.enfermedades)}")
        if self.padres_vivos is not None:
            context_parts.append(f"Padres vivos: {'Sí' if self.padres_vivos else 'No'}")
        if self.preferencias_alimentacion:
            context_parts.append(f"Preferencias alimentación: {', '.join(self.preferencias_alimentacion)}")
        
        # Agregar contexto adicional
        for key, value in self.additional_context.items():
            context_parts.append(f"{key}: {value}")
        
        return "\n".join(context_parts)

# Necesario para referencias circulares en Pydantic
DecisionNode.model_rebuild()