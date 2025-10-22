# tools.py - Versión refactorizada con decorador @tool
from langchain_core.tools import tool
from typing import List
import math
from tavily import TavilyClient
from config import config

@tool
def web_search(query: str) -> str:
    """Busca información actualizada en internet usando Tavily. Úsala para encontrar: precios actuales, salarios de mercado, datos de empresas, costos de servicios, información económica, noticias recientes, estadísticas, etc. Input: consulta clara en lenguaje natural.

    Args:
        query: Consulta de búsqueda en lenguaje natural

    Returns:
        Información relevante encontrada en internet
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

@tool
def calculator(expression: str) -> str:
    """Calcula expresiones matemáticas. Soporta operaciones básicas (+, -, *, /), potencias (pow), raíz cuadrada (sqrt), y funciones trigonométricas. Input: expresión matemática válida.

    Args:
        expression: Expresión matemática a evaluar

    Returns:
        Resultado del cálculo
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

@tool
def probability_calculator(favorable_outcomes: int, total_outcomes: int) -> str:
    """Calcula probabilidades simples dados resultados favorables y totales. Input: número de resultados favorables y número total de resultados posibles.

    Args:
        favorable_outcomes: Número de resultados favorables
        total_outcomes: Número total de resultados posibles

    Returns:
        Probabilidad en porcentaje
    """
    try:
        if total_outcomes <= 0:
            return "Error: Total de resultados debe ser mayor a 0"

        probability = (favorable_outcomes / total_outcomes) * 100
        return f"Probabilidad: {probability:.2f}%"
    except Exception as e:
        return f"Error en cálculo de probabilidad: {str(e)}"

def create_agent_tools() -> List:
    """
    Crea la lista de herramientas disponibles para el agente

    Returns:
        Lista de herramientas decoradas con @tool
    """
    return [web_search, calculator, probability_calculator]