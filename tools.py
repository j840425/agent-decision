# tools.py
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import List
import math
from tavily import TavilyClient
from config import config

class WebSearchInput(BaseModel):
    """Input para búsqueda web con Tavily"""
    query: str = Field(description="Consulta de búsqueda en lenguaje natural")

class CalculatorInput(BaseModel):
    """Input para calculadora"""
    expression: str = Field(description="Expresión matemática a evaluar")

class ProbabilityInput(BaseModel):
    """Input para cálculo de probabilidades"""
    favorable_outcomes: int = Field(description="Número de resultados favorables")
    total_outcomes: int = Field(description="Número total de resultados posibles")

def web_search_tool(query: str) -> str:
    """
    Realiza búsquedas en internet usando Tavily API.
    Retorna información actualizada y relevante.
    """
    try:
        client = TavilyClient(api_key=config.TAVILY_API_KEY)
        
        # Realizar búsqueda con Tavily
        response = client.search(
            query=query,
            search_depth="advanced",  # "basic" o "advanced"
            max_results=5,
            include_answer=True  # Tavily genera un resumen
        )
        
        # Formatear respuesta
        result_parts = []
        
        # Agregar respuesta resumida si existe
        if response.get('answer'):
            result_parts.append(f"RESUMEN: {response['answer']}\n")
        
        # Agregar resultados detallados
        result_parts.append("FUENTES:")
        for i, result in enumerate(response.get('results', [])[:3], 1):
            title = result.get('title', 'Sin título')
            content = result.get('content', 'Sin contenido')
            url = result.get('url', '')
            
            result_parts.append(f"\n{i}. {title}")
            result_parts.append(f"   {content[:200]}...")
            result_parts.append(f"   URL: {url}")
        
        return "\n".join(result_parts)
        
    except Exception as e:
        return f"Error en búsqueda web: {str(e)}"

def calculator_tool(expression: str) -> str:
    """
    Evalúa expresiones matemáticas de forma segura
    """
    try:
        # Lista blanca de operaciones permitidas
        allowed_names = {
            'abs': abs, 'round': round, 'min': min, 'max': max,
            'sum': sum, 'pow': pow, 'sqrt': math.sqrt,
            'sin': math.sin, 'cos': math.cos, 'tan': math.tan,
            'log': math.log, 'exp': math.exp, 'pi': math.pi,
            'e': math.e
        }
        
        # Evaluar de forma segura
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"Resultado: {result}"
    except Exception as e:
        return f"Error en cálculo: {str(e)}"

def probability_calculator(favorable_outcomes: int, total_outcomes: int) -> str:
    """
    Calcula probabilidades simples
    """
    try:
        if total_outcomes <= 0:
            return "Error: Total de resultados debe ser mayor a 0"
        
        probability = (favorable_outcomes / total_outcomes) * 100
        return f"Probabilidad: {probability:.2f}%"
    except Exception as e:
        return f"Error en cálculo de probabilidad: {str(e)}"

def create_agent_tools() -> List[StructuredTool]:
    """
    Crea la lista de herramientas disponibles para el agente
    """
    tools = [
        StructuredTool(
            name="web_search",
            description="Busca información actualizada en internet usando Tavily. Úsala para encontrar: precios actuales, salarios de mercado, datos de empresas, costos de servicios, información económica, noticias recientes, estadísticas, etc. Input: consulta clara en lenguaje natural.",
            func=web_search_tool,
            args_schema=WebSearchInput
        ),
        StructuredTool(
            name="calculator",
            description="Calcula expresiones matemáticas. Soporta operaciones básicas (+, -, *, /), potencias (pow), raíz cuadrada (sqrt), y funciones trigonométricas. Input: expresión matemática válida.",
            func=calculator_tool,
            args_schema=CalculatorInput
        ),
        StructuredTool(
            name="probability_calculator",
            description="Calcula probabilidades simples dados resultados favorables y totales. Input: número de resultados favorables y número total de resultados posibles.",
            func=probability_calculator,
            args_schema=ProbabilityInput
        )
    ]
    
    return tools