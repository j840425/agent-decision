# agent.py - VERSIÓN FINAL CORREGIDA
from langchain_google_vertexai import ChatVertexAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from config import config
from storage import storage
from tools import create_agent_tools
from models import UserProfile, DecisionNode, Cost, ResourceType
from typing import List, Dict, Any, Optional
import json
import uuid
import streamlit as st
from custom_callback import StreamlitAgentCallback
import re
import time
from datetime import datetime

class ImprovedDecisionAgent:
    """Agente ReAct robusto para análisis de decisiones variadas"""
    
    def __init__(self):
        
        # LLM para el agente - temperatura muy baja para máximo control
        self.llm = ChatVertexAI(
            model_name=config.VERTEX_AI_MODEL,
            project=config.GOOGLE_CLOUD_PROJECT,
            location=config.GOOGLE_CLOUD_REGION,
            temperature=0.1,
            max_output_tokens=config.MAX_OUTPUT_TOKENS,            
            verbose=True,
            max_retries=2
        )
        
        # LLM para árbol
        self.llm_tree = ChatVertexAI(
            model_name=config.VERTEX_AI_MODEL,
            project=config.GOOGLE_CLOUD_PROJECT,
            location=config.GOOGLE_CLOUD_REGION,
            temperature=0.2,
            max_output_tokens=config.MAX_OUTPUT_TOKENS
        )
        
        self.tools = create_agent_tools()
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        self.agent = self._create_robust_agent()
    
    def _create_robust_agent(self):
        """Crea un agente ReAct robusto con manejo mejorado de errores"""
        
        # PROMPT ESTRICTO Y CLARO
        template = """Eres un agente que analiza decisiones usando herramientas específicas.

CONTEXTO del usuario (Perú):
{user_context}

HERRAMIENTAS DISPONIBLES: {tool_names}
{tools}

REQUISITOS DE ANÁLISIS PROFUNDO:
✅ DEBES usar MÍNIMO 4 herramientas antes de dar tu Final Answer
✅ DEBES investigar al menos:
- Costos/precios actuales
- Tendencias del mercado
- Alternativas disponibles
- Riesgos específicos
- Beneficios cuantificados
✅ DEBES hacer cálculos cuando tengas números
✅ NO des Final Answer hasta tener toda la información relevante necesaria para dar un analisis completo

FORMATO OBLIGATORIO - SÍGUELO EXACTAMENTE:
Para usar herramientas escribe EXACTAMENTE así (sin comillas, sin dos puntos después de Thought):
Thought: [una sola oración sobre qué necesitas hacer]
Action: [nombre exacto de la herramienta]
Action Input: [tu consulta]

Después de recibir Observation, continúa:
Thought: [qué aprendiste del resultado]
Action: [siguiente herramienta]
Action Input: [siguiente consulta]

Para terminar SOLO cuando tengas suficiente información:
Thought: Ya tengo suficiente información para el análisis completo
Final Answer: [Análisis completo en español de 3-4 párrafos con datos concretos]

⚠️ ERROR CRÍTICO QUE DEBES EVITAR - NUNCA HAGAS ESTO:
❌ INCORRECTO (mezclar Action con Final Answer):
Thought: Necesito más datos
Action: web_search
Action Input: salarios
Final Answer: Basándome en...

✅ CORRECTO (elegir UNO u OTRO):
Thought: Necesito más datos sobre salarios
Action: web_search
Action Input: salarios jefe datos Perú

O SI YA TIENES SUFICIENTE:
Thought: Ya tengo información completa de salarios, costos y riesgos
Final Answer: [Tu análisis detallado de 3-4 párrafos]

REGLA DE ORO: 
- SI escribes "Action:", NO puedes escribir "Final Answer:" en la MISMA respuesta
- SI escribes "Final Answer:", NO puedes escribir "Action:" en la MISMA respuesta
- Son MUTUAMENTE EXCLUYENTES

EJEMPLOS REALES:

Ejemplo de búsqueda:
Thought: Necesito buscar información sobre salarios actuales
Action: web_search
Action Input: salario promedio jefe datos Perú 2024

Ejemplo de cálculo:
Thought: Necesito calcular el porcentaje de aumento
Action: calculator
Action Input: ((15000 - 13000) / 13000) * 100

Ejemplo de terminar (SOLO cuando tengas datos de al menos 4 búsquedas):
Thought: Ya recopilé información de salarios, costos, riesgos y beneficios
Final Answer: Basándome en el análisis realizado, considerando que tu salario actual de 13,000 PEN...
[Continúa con 3-4 párrafos detallados]

PROHIBIDO:
❌ NO escribas "Mi plan es..." o "Voy a..."
❌ NO hagas listas numeradas de acciones futuras
❌ NO uses comillas triples ```
❌ NO pongas dos puntos después de Thought
❌ NO escribas planes, ejecuta acciones DIRECTAMENTE
❌ NO MEZCLES Action con Final Answer en la MISMA respuesta

TAREA: {input}

Historial previo (si existe):
{agent_scratchpad}

RECUERDA: 
- Cada respuesta debe tener O una acción (Thought + Action + Action Input) O una respuesta final (Thought + Final Answer)
- NUNCA ambas en la misma respuesta
- Si ya tienes 4+ búsquedas exitosas con datos concretos, da tu Final Answer

Empieza AHORA con UNA acción directa:"""

        prompt = PromptTemplate(
            input_variables=["input", "agent_scratchpad", "tools", "tool_names", "user_context"],
            template=template
        )
        
        # Crear el agente estándar
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Estado para tracking
        loop_state = {
            'action_history': [],
            'error_count': 0,
            'consecutive_errors': 0
        }
        
        # Función de manejo de errores mejorada
        def handle_parsing_errors(error: Exception) -> str:
            """Maneja errores con retroalimentación específica y detección de patrones"""
            error_str = str(error)
            
            # Incrementar contadores
            loop_state['error_count'] += 1
            loop_state['consecutive_errors'] += 1
            
            # Si hay demasiados errores consecutivos, forzar una respuesta
            if loop_state['consecutive_errors'] >= 4:
                loop_state['consecutive_errors'] = 0
                return """Has tenido múltiples errores de formato.

        TERMINA AHORA con Final Answer:

        Thought: Basándome en la información disponible
        Final Answer: [Proporciona un análisis de al menos 3 párrafos con estos elementos:
        1. Contexto de la decisión y factores relevantes
        2. Riesgos identificados con datos específicos si los tienes
        3. Oportunidades y beneficios potenciales
        4. Recomendación basada en el análisis]

        NO uses Action ni Action Input. Solo Final Answer."""
            
            # Caso: mezcló Final Answer con Action (el más común)
            if "both a final answer and a parse-able action" in error_str.lower():
                loop_state['consecutive_errors'] = 0  # Reset porque es un error específico
                
                # Incrementar contador específico
                if 'final_answer_attempts' not in loop_state:
                    loop_state['final_answer_attempts'] = 0
                loop_state['final_answer_attempts'] += 1
                
                # Si ya intentó varias veces, forzar que termine
                if loop_state['final_answer_attempts'] >= 2:
                    return """Has mezclado formatos varias veces. 

        DEBES ELEGIR UNO:

        Opción A - Si necesitas MÁS datos:
        Thought: Necesito buscar [información específica que falta]
        Action: web_search
        Action Input: [búsqueda concreta]

        Opción B - Si tienes SUFICIENTE información:
        Thought: Ya tengo información suficiente
        Final Answer: [Tu análisis completo de 3-4 párrafos]

        ⚠️ NO mezcles Action con Final Answer en el mismo bloque."""
                
                return """ERROR: Mezclaste acción con respuesta final.

        CORRECTO si necesitas más info:
        Thought: Necesito investigar X
        Action: web_search
        Action Input: [búsqueda específica]

        CORRECTO si ya tienes suficiente:
        Thought: Tengo la información necesaria
        Final Answer: [análisis completo de 3-4 párrafos]

        INCORRECTO (no hagas esto):
        Thought: Necesito buscar X
        Final Answer: Mi análisis es...

        Elige UNO solo."""
            
            # Caso: formato incorrecto o no puede parsear
            elif "could not parse" in error_str.lower():
                loop_state['consecutive_errors'] = 0
                
                # Si menciona "thought" pero está mal formateado
                if "thought" in error_str.lower():
                    # Detectar si está haciendo planes
                    if "plan" in error_str.lower() or "voy a" in error_str.lower() or "necesito" in error_str.lower() and ":" in error_str:
                        return """ERROR: Estás escribiendo planes en lugar de ejecutar acciones.

        NO hagas esto:
        Thought: Mi plan es:
        1. Buscar X
        2. Calcular Y

        HAZ esto:
        Thought: Necesito buscar información sobre salarios
        Action: web_search
        Action Input: salario maestría IA Perú 2024

        Ejecuta UNA acción AHORA, no escribas planes."""
                    
                    return """ERROR: Formato incorrecto del Thought.

        Escribe EXACTAMENTE así (sin comillas, sin dos puntos después de Thought):

        Thought: Necesito buscar información sobre X
        Action: web_search
        Action Input: [tu búsqueda]

        Cada elemento en su propia línea. NO uses símbolos especiales."""
                
                # Error genérico de parseo
                return """ERROR: No puedo entender tu formato.

        USA ESTE FORMATO EXACTO:

        Para buscar:
        Thought: Necesito buscar [qué]
        Action: web_search
        Action Input: [búsqueda]

        Para calcular:
        Thought: Necesito calcular [qué]
        Action: calculator
        Action Input: [expresión matemática]

        Para terminar:
        Thought: Ya tengo la información
        Final Answer: [análisis de 3-4 párrafos]

        Sin comillas, sin caracteres especiales."""
            
            # Caso: herramienta no válida
            elif "invalid tool" in error_str.lower() or "no such tool" in error_str.lower() or "not a valid tool" in error_str.lower():
                return """ERROR: Esa herramienta no existe.

        HERRAMIENTAS DISPONIBLES:
        - web_search - Para buscar información en internet
        - calculator - Para hacer cálculos matemáticos
        - probability_calculator - Para calcular probabilidades

        Ejemplo correcto:
        Thought: Necesito buscar costos de maestrías
        Action: web_search
        Action Input: costo maestría IA universidades Perú"""
            
            # Caso: loop detectado
            elif "loop" in error_str.lower():
                return """LOOP DETECTADO: Estás repitiendo la misma acción.

        Opciones:
        1. Cambia tu búsqueda (usa términos diferentes)
        2. Usa una herramienta diferente (calculator si necesitas cálculos)
        3. Si ya tienes suficiente información, termina:

        Thought: Con la información actual puedo dar el análisis
        Final Answer: [Tu análisis con los datos que ya tienes]"""
            
            # Caso: timeout o problemas de generación
            elif "generation" in error_str.lower() or "timeout" in error_str.lower():
                return """ERROR: Problema generando respuesta.

        Intenta con una acción más simple:

        Thought: Busco información básica
        Action: web_search
        Action Input: [consulta corta y específica]

        O termina con lo que tienes:

        Thought: Proporciono análisis con información actual
        Final Answer: [tu análisis]"""
            
            # Caso por defecto
            else:
                # Reducir errores consecutivos si es un error diferente
                if loop_state['consecutive_errors'] > 0:
                    loop_state['consecutive_errors'] -= 1
                
                return f"""ERROR: {error_str[:150]}

        FORMATO CORRECTO:

        Para acciones:
        Thought: [qué necesitas]
        Action: [herramienta]
        Action Input: [entrada]

        Para terminar:
        Thought: [conclusión]
        Final Answer: [análisis completo]

        Sigue el formato EXACTAMENTE."""
        
        # Crear ejecutor con configuración optimizada
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=handle_parsing_errors,
            max_iterations=12,
            max_execution_time=600,
            return_intermediate_steps=True,
            early_stopping_method="force"  # Genera respuesta si se acaban iteraciones
        )
        
        return agent_executor
        
    def analyze_decision_with_retry(self, user_question: str, max_depth: int = None,
                               thinking_container=None) -> Dict[str, Any]:
        """
        Analiza una decisión con reintentos inteligentes y visualización mejorada
        """
        if max_depth is None:
            max_depth = config.MAX_TREE_DEPTH
        
        profile = storage.load_profile()
        user_context = profile.to_context_string()
        
        # Mejorar la pregunta con contexto específico
        decision_type = self._identify_decision_type(user_question)
        enhanced_question = self._enhance_question(user_question, decision_type)
        
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Mostrar progreso
                if thinking_container:
                    with thinking_container:
                        if attempt > 0:
                            st.warning(f"🔄 Reintento {attempt + 1}/{max_retries}")
                        
                        # Título dinámico según el tipo de decisión
                        st.markdown(f"### 🧠 Analizando tu decisión {decision_type}")
                        st.markdown("---")
                        
                        # Crear container para el proceso
                        with st.expander("Ver proceso de razonamiento", expanded=True):
                            iterations_container = st.container()
                            custom_callback = StreamlitAgentCallback(iterations_container)
                        
                        # Barra de progreso
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Ejecutar agente con callback DENTRO del container
                        status_text.text("🔍 Iniciando análisis...")
                        progress_bar.progress(10)
                        
                        # IMPORTANTE: Ejecutar el agente AQUÍ, dentro del with thinking_container
                        result = self.agent.invoke(
                            {
                                "user_context": user_context,
                                "input": enhanced_question,
                                "tool_names": ", ".join([tool.name for tool in self.tools]),
                                "tools": "\n".join([f"- {tool.name}: {tool.description}" 
                                                for tool in self.tools])
                            },
                            config={
                                "callbacks": [custom_callback],
                                "verbose": True  # Agregar verbose
                            }
                        )
                        
                        # DEBUG: Mostrar los pasos intermedios
                        if "intermediate_steps" in result and result["intermediate_steps"]:
                            with st.expander("🔍 Pasos intermedios (Debug)", expanded=False):
                                for i, step in enumerate(result["intermediate_steps"]):
                                    st.write(f"Paso {i+1}:")
                                    if isinstance(step, tuple) and len(step) == 2:
                                        action, observation = step
                                        if hasattr(action, 'tool'):
                                            st.write(f"  Herramienta: {action.tool}")
                                        st.write(f"  Resultado: {str(observation)[:500]}...")
                        
                        progress_bar.progress(70)
                        status_text.text("📊 Procesando resultados...")
                        
                        # Continuar con el procesamiento dentro del container
                        analysis = result.get("output", "")
                        
                        # Si el análisis es muy corto, intentar construir desde pasos
                        if len(analysis) < 200 and "intermediate_steps" in result:
                            analysis = self._build_comprehensive_analysis(
                                user_question,
                                result["intermediate_steps"],
                                user_context,
                                decision_type
                            )
                        
                        # Validación final
                        if len(analysis) < 100:
                            raise ValueError(f"Análisis insuficiente ({len(analysis)} caracteres)")
                        
                        # Generar árbol de decisión
                        progress_bar.progress(90)
                        status_text.text("🌳 Generando árbol de decisión...")
                        
                        tree = self._generate_decision_tree(user_question, analysis, max_depth, decision_type)
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Análisis completado!")
                        time.sleep(0.5)
                        progress_bar.empty()
                        status_text.empty()
                        
                        # Retornar resultado
                        return {
                            "question": user_question,
                            "analysis": analysis,
                            "decision_tree": tree,
                            "decision_type": decision_type,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                else:
                    # Sin visualización
                    result = self.agent.invoke({
                        "user_context": user_context,
                        "input": enhanced_question,
                        "tool_names": ", ".join([tool.name for tool in self.tools]),
                        "tools": "\n".join([f"- {tool.name}: {tool.description}" 
                                        for tool in self.tools])
                    })
                    
                    # Procesar resultado
                    analysis = result.get("output", "")
                    
                    if len(analysis) < 200 and "intermediate_steps" in result:
                        analysis = self._build_comprehensive_analysis(
                            user_question,
                            result["intermediate_steps"],
                            user_context,
                            decision_type
                        )
                    
                    if len(analysis) < 100:
                        raise ValueError(f"Análisis insuficiente ({len(analysis)} caracteres)")
                    
                    tree = self._generate_decision_tree(user_question, analysis, max_depth, decision_type)
                    
                    return {
                        "question": user_question,
                        "analysis": analysis,
                        "decision_tree": tree,
                        "decision_type": decision_type,
                        "timestamp": datetime.now().isoformat()
                    }
                    
            except Exception as e:
                last_error = e
                if thinking_container:
                    with thinking_container:
                        st.error(f"⚠️ Error en intento {attempt + 1}: {str(e)[:200]}")
                
                # Esperar antes de reintentar
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        # Si todos los reintentos fallan, retornar None con mensaje de error
        if thinking_container:
            with thinking_container:
                error_message = f"""
                ❌ **No se pudo completar el análisis**
                
                El sistema tuvo dificultades procesando tu pregunta. Por favor:
                1. Intenta reformular tu pregunta de manera más específica
                2. Divide decisiones complejas en partes más simples
                3. Verifica que tu pregunta sea sobre una decisión concreta
                
                **Último error:** {str(last_error)[:200] if last_error else "Error desconocido"}
                """
                st.error(error_message)
        
        return None

    def analyze_decision_with_retry_ant(self, user_question: str, max_depth: int = None,
                                   thinking_container=None) -> Dict[str, Any]:
        """
        Analiza una decisión con reintentos inteligentes y visualización mejorada
        """
        if max_depth is None:
            max_depth = config.MAX_TREE_DEPTH
        
        profile = storage.load_profile()
        user_context = profile.to_context_string()
        
        # Mejorar la pregunta con contexto específico
        decision_type = self._identify_decision_type(user_question)
        enhanced_question = self._enhance_question(user_question, decision_type)
        
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Mostrar progreso
                if thinking_container:
                    with thinking_container:
                        if attempt > 0:
                            st.warning(f"🔄 Reintento {attempt + 1}/{max_retries}")
                        
                        # Título dinámico según el tipo de decisión
                        st.markdown(f"### 🧠 Analizando tu decisión {decision_type}")
                        st.markdown("---")
                        
                        # Crear container para el proceso
                        with st.expander("Ver proceso de razonamiento", expanded=True):
                            iterations_container = st.container()
                            custom_callback = StreamlitAgentCallback(iterations_container)
                        
                        # Barra de progreso
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Ejecutar agente con callback
                        status_text.text("🔍 Iniciando análisis...")
                        progress_bar.progress(10)
                        
                        result = self.agent.invoke(
                            {
                                "user_context": user_context,
                                "input": enhanced_question,
                                "tool_names": ", ".join([tool.name for tool in self.tools]),
                                "tools": "\n".join([f"- {tool.name}: {tool.description}" 
                                                  for tool in self.tools])
                            },
                            config={"callbacks": [custom_callback]}
                        )
                        
                        progress_bar.progress(70)
                        status_text.text("📊 Procesando resultados...")
                else:
                    # Sin visualización
                    result = self.agent.invoke({
                        "user_context": user_context,
                        "input": enhanced_question,
                        "tool_names": ", ".join([tool.name for tool in self.tools]),
                        "tools": "\n".join([f"- {tool.name}: {tool.description}" 
                                          for tool in self.tools])
                    })
                
                # Extraer y validar el análisis
                analysis = result.get("output", "")
                
                # Si el análisis es muy corto, intentar construir desde pasos
                if len(analysis) < 200 and "intermediate_steps" in result:
                    analysis = self._build_comprehensive_analysis(
                        user_question,
                        result["intermediate_steps"],
                        user_context,
                        decision_type
                    )
                
                # Validación final
                if len(analysis) < 100:
                    raise ValueError(f"Análisis insuficiente ({len(analysis)} caracteres)")
                
                # Generar árbol de decisión
                if thinking_container:
                    progress_bar.progress(90)
                    status_text.text("🌳 Generando árbol de decisión...")
                
                tree = self._generate_decision_tree(user_question, analysis, max_depth, decision_type)
                
                if thinking_container:
                    progress_bar.progress(100)
                    status_text.text("✅ Análisis completado!")
                    time.sleep(0.5)
                    progress_bar.empty()
                    status_text.empty()
                
                return {
                    "question": user_question,
                    "analysis": analysis,
                    "decision_tree": tree,
                    "decision_type": decision_type,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                last_error = e
                if thinking_container:
                    with thinking_container:
                        st.error(f"⚠️ Error en intento {attempt + 1}: {str(e)[:200]}")
                
                # Esperar antes de reintentar
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        # Si todos los reintentos fallan, retornar None con mensaje de error
        if thinking_container:
            with thinking_container:
                error_message = f"""
                ❌ **No se pudo completar el análisis**
                
                El sistema tuvo dificultades procesando tu pregunta. Por favor:
                1. Intenta reformular tu pregunta de manera más específica
                2. Divide decisiones complejas en partes más simples
                3. Verifica que tu pregunta sea sobre una decisión concreta
                
                **Último error:** {str(last_error)[:200] if last_error else "Error desconocido"}
                """
                st.error(error_message)
        
        return None
    
    def _identify_decision_type(self, question: str) -> str:
        """Identifica el tipo de decisión para personalizar el análisis"""
        question_lower = question.lower()
        
        # Palabras clave por categoría
        categories = {
            "financiera": ["dinero", "invertir", "comprar", "vender", "préstamo", 
                          "ahorro", "deuda", "sueldo", "salario", "costo", "precio",
                          "pagar", "gastar", "ahorrar", "banco", "crédito"],
            "laboral": ["trabajo", "empleo", "empresa", "jefe", "cargo", "puesto",
                       "carrera", "profesión", "negocio", "emprender", "renunciar",
                       "ascenso", "promoción", "contrato", "sueldo"],
            "educativa": ["estudiar", "curso", "carrera", "universidad", "maestría",
                         "certificación", "aprender", "capacitación", "título",
                         "diploma", "posgrado", "doctorado", "especialización"],
            "personal": ["mudanza", "casa", "familia", "hijo", "pareja", "relación",
                        "salud", "viajar", "vivir", "matrimonio", "divorcio",
                        "mascota", "hogar", "departamento"],
            "tecnológica": ["software", "sistema", "aplicación", "tecnología", 
                           "herramienta", "plataforma", "actualizar", "migrar",
                           "computadora", "programa", "app", "digital"]
        }
        
        for tipo, keywords in categories.items():
            if any(keyword in question_lower for keyword in keywords):
                return tipo
        
        return "general"
    
    def _enhance_question(self, question: str, decision_type: str) -> str:
        """Mejora la pregunta con instrucciones específicas según el tipo"""
        
        enhancements = {
            "financiera": """
Analiza esta decisión financiera considerando:
- ROI esperado y tiempo de recuperación
- Costos iniciales y recurrentes en PEN
- Comparación con alternativas de inversión
- Riesgos financieros específicos
""",
            "laboral": """
Analiza esta decisión laboral evaluando:
- Impacto en desarrollo profesional
- Diferencias salariales y beneficios
- Oportunidades de crecimiento
- Balance vida-trabajo
""",
            "educativa": """
Analiza esta decisión educativa considerando:
- Costos vs retorno educativo
- Tiempo de dedicación requerido
- Valor en el mercado laboral peruano
- Alternativas de formación
""",
            "personal": """
Analiza esta decisión personal evaluando:
- Impacto en calidad de vida
- Costos emocionales y económicos
- Efectos en relaciones familiares
- Bienestar a largo plazo
""",
            "tecnológica": """
Analiza esta decisión tecnológica considerando:
- Costos de implementación y mantenimiento
- Curva de aprendizaje y capacitación
- Beneficios de productividad
- Riesgos de obsolescencia
""",
            "general": """
Analiza esta decisión considerando:
- Costos y beneficios principales
- Riesgos y oportunidades
- Impacto a corto y largo plazo
- Alternativas disponibles
"""
        }
        
        enhancement = enhancements.get(decision_type, enhancements["general"])
        
        return f"""{enhancement}

DECISIÓN A ANALIZAR: {question}

IMPORTANTE: 
- Busca datos específicos del mercado peruano
- Proporciona números y porcentajes concretos
- Considera el contexto económico actual
- Da una recomendación clara y fundamentada"""
    
    def _build_comprehensive_analysis(self, question: str, steps: List, 
                                     context: str, decision_type: str) -> str:
        """Construye un análisis desde los pasos intermedios reales del agente"""
        
        # Extraer información real de los pasos
        search_results = []
        calculations = []
        all_observations = []
        
        for step in steps:
            if isinstance(step, tuple) and len(step) == 2:
                action, observation = step
                obs_str = str(observation)
                all_observations.append(obs_str)
                
                if hasattr(action, 'tool'):
                    if action.tool == 'web_search':
                        # Extraer información relevante de búsquedas
                        if len(obs_str) > 50:
                            search_results.append(obs_str[:500])
                    elif action.tool == 'calculator':
                        # Guardar cálculos realizados
                        calculations.append(obs_str)
        
        # Construir análisis basado en lo que realmente se encontró
        analysis_parts = [
            f"**Análisis de Decisión: {question}**\n"
        ]
        
        # Agregar información de búsquedas si existe
        if search_results:
            analysis_parts.append("**Información Encontrada:**")
            for i, result in enumerate(search_results[:3], 1):
                # Limpiar y formatear resultado
                clean_result = result.replace("\n", " ").strip()
                if len(clean_result) > 200:
                    clean_result = clean_result[:200] + "..."
                analysis_parts.append(f"{i}. {clean_result}")
            analysis_parts.append("")
        
        # Agregar cálculos si existen
        if calculations:
            analysis_parts.append("**Análisis Cuantitativo:**")
            for calc in calculations[:3]:
                analysis_parts.append(f"- {calc}")
            analysis_parts.append("")
        
        # Agregar evaluación basada en tipo
        analysis_parts.append(f"**Evaluación para Decisión {decision_type.title()}:**")
        
        # Análisis basado en observaciones reales
        if all_observations:
            # Buscar patrones en las observaciones
            combined_obs = " ".join(all_observations).lower()
            
            # Identificar elementos positivos y negativos encontrados
            if any(word in combined_obs for word in ["beneficio", "ganancia", "mejora", "oportunidad"]):
                analysis_parts.append("- Se identificaron oportunidades potenciales en los datos analizados")
            
            if any(word in combined_obs for word in ["riesgo", "costo", "pérdida", "problema"]):
                analysis_parts.append("- Se detectaron factores de riesgo que requieren consideración")
            
            # Buscar números significativos
            import re
            numbers = re.findall(r'\b\d+(?:\.\d+)?(?:%|k|K|mil|millones)?\b', combined_obs)
            if numbers:
                analysis_parts.append(f"- Valores numéricos relevantes encontrados: {', '.join(numbers[:5])}")
        
        # Recomendación basada en datos reales
        analysis_parts.append("\n**Recomendación:**")
        if search_results or calculations:
            analysis_parts.append(
                "Basándome en la información recopilada, esta decisión requiere evaluar cuidadosamente "
                "los datos específicos encontrados. Se recomienda considerar tanto los aspectos cuantitativos "
                "como cualitativos antes de proceder."
            )
        else:
            analysis_parts.append(
                "Se requiere más información específica para proporcionar una recomendación detallada. "
                "Considera buscar datos concretos sobre costos, beneficios y experiencias similares."
            )
        
        return "\n".join(analysis_parts)
    
    def _generate_simple_tree(self, question: str, decision_type: str = "general") -> DecisionNode:
        """Genera un árbol de decisión mínimo cuando falla el LLM"""
        
        # Árbol genérico simple - solo estructura básica sin valores inventados
        return DecisionNode(
            id="root",
            description=f"Decisión: {question[:100]}{'...' if len(question) > 100 else ''}",
            probability=100,
            level=0,
            reasoning=f"Análisis de decisión tipo {decision_type}",
            costs=[
                Cost(resource_type=ResourceType.TIEMPO, amount=0, unit="", 
                     description="Por determinar"),
                Cost(resource_type=ResourceType.DINERO, amount=0, unit="PEN",
                     description="Por calcular")
            ],
            benefits=[
                Cost(resource_type=ResourceType.OPORTUNIDAD, amount=0, unit="%",
                     description="Potencial por evaluar")
            ],
            children=[
                DecisionNode(
                    id="opt1",
                    description="Proceder con la decisión",
                    probability=50,
                    level=1,
                    reasoning="Opción principal",
                    costs=[],
                    benefits=[],
                    children=[]
                ),
                DecisionNode(
                    id="opt2",
                    description="No proceder o buscar alternativas",
                    probability=50,
                    level=1,
                    reasoning="Opción alternativa",
                    costs=[],
                    benefits=[],
                    children=[]
                )
            ]
        )
    
    def _generate_decision_tree(self, question: str, analysis: str, 
                               max_depth: int, decision_type: str) -> DecisionNode:
        """Genera árbol de decisión mejorado con contexto del tipo de decisión"""
        profile = storage.load_profile()
        
        # Prompt especializado por tipo
        type_context = {
            "financiera": "Enfócate en ROI, flujos de caja, y métricas financieras.",
            "laboral": "Considera salario, beneficios, desarrollo profesional y balance vida-trabajo.",
            "educativa": "Evalúa costos educativos, tiempo de estudio, y retorno profesional.",
            "personal": "Pondera bienestar emocional, impacto familiar, y calidad de vida.",
            "tecnológica": "Analiza costos de implementación, curva de aprendizaje, y obsolescencia.",
            "general": "Considera costos, beneficios, riesgos y oportunidades de manera integral."
        }
        
        prompt = f"""Genera un árbol de decisión JSON para esta situación.

CONTEXTO: {profile.to_context_string()}
TIPO DE DECISIÓN: {decision_type}
ENFOQUE: {type_context.get(decision_type, type_context['general'])}
PREGUNTA: {question}
ANÁLISIS PREVIO: {analysis[:500]}

Genera un JSON con EXACTAMENTE esta estructura:
{{
  "id": "root",
  "description": "descripción clara de la decisión",
  "probability": 100,
  "costs": [
    {{"resource_type": "dinero", "amount": 10000, "unit": "PEN", "description": "descripción"}}
  ],
  "benefits": [
    {{"resource_type": "dinero", "amount": 2000, "unit": "PEN/mes", "description": "descripción"}}
  ],
  "level": 0,
  "reasoning": "razonamiento para esta decisión",
  "children": [
    {{
      "id": "opt1",
      "description": "Primera opción",
      "probability": 40,
      "costs": [],
      "benefits": [],
      "level": 1,
      "reasoning": "por qué esta opción",
      "children": []
    }},
    {{
      "id": "opt2",
      "description": "Segunda opción",
      "probability": 35,
      "costs": [],
      "benefits": [],
      "level": 1,
      "reasoning": "por qué esta opción",
      "children": []
    }},
    {{
      "id": "opt3",
      "description": "Tercera opción",
      "probability": 25,
      "costs": [],
      "benefits": [],
      "level": 1,
      "reasoning": "por qué esta opción",
      "children": []
    }}
  ]
}}

IMPORTANTE: 
- Las probabilidades de los hijos deben sumar 100%
- Usa moneda PEN para valores monetarios
- Máximo {max_depth} niveles de profundidad
- Incluye costs y benefits relevantes al tipo de decisión
- Solo devuelve el JSON, sin texto adicional"""

        try:
            response = self.llm_tree.invoke(prompt)
            content = response.content.strip()
            
            # Limpiar respuesta
            if "```json" in content.lower():
                content = re.sub(r'```json\s*', '', content, flags=re.IGNORECASE)
                content = re.sub(r'```\s*', '', content)
            elif "```" in content:
                content = re.sub(r'```\s*', '', content)
            
            # Buscar el JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            tree_data = json.loads(content)
            return self._parse_tree_node(tree_data)
            
        except Exception as e:
            print(f"Error generando árbol: {e}")
            # Usar árbol simple como fallback
            return self._generate_simple_tree(question, decision_type)
    
    def _parse_tree_node(self, data: Dict[str, Any]) -> DecisionNode:
        """Convierte datos JSON a DecisionNode con validación mejorada"""
        
        # Parsear costos
        costs = []
        for cost_data in data.get("costs", []):
            try:
                resource_type_str = cost_data.get("resource_type", "otro").lower()
                resource_type = ResourceType(resource_type_str)
            except ValueError:
                resource_type = ResourceType.OTRO
            
            costs.append(Cost(
                resource_type=resource_type,
                amount=float(cost_data.get("amount", 0)),
                unit=cost_data.get("unit", ""),
                description=cost_data.get("description", "")
            ))
        
        # Parsear beneficios
        benefits = []
        for benefit_data in data.get("benefits", []):
            try:
                resource_type_str = benefit_data.get("resource_type", "otro").lower()
                resource_type = ResourceType(resource_type_str)
            except ValueError:
                resource_type = ResourceType.OTRO
            
            benefits.append(Cost(
                resource_type=resource_type,
                amount=float(benefit_data.get("amount", 0)),
                unit=benefit_data.get("unit", ""),
                description=benefit_data.get("description", "")
            ))
        
        # Parsear hijos recursivamente
        children = []
        for child_data in data.get("children", []):
            try:
                children.append(self._parse_tree_node(child_data))
            except Exception as e:
                print(f"Error parseando hijo: {e}")
                continue
        
        # Validar y normalizar probabilidades de los hijos
        if children:
            total_prob = sum(child.probability for child in children)
            if total_prob > 0 and abs(total_prob - 100) > 5:  # Tolerancia de 5%
                # Normalizar probabilidades
                for child in children:
                    child.probability = (child.probability / total_prob) * 100
        
        return DecisionNode(
            id=data.get("id", str(uuid.uuid4())),
            description=data.get("description", "Decisión"),
            probability=float(data.get("probability", 50)),
            costs=costs,
            benefits=benefits,
            level=int(data.get("level", 0)),
            reasoning=data.get("reasoning", ""),
            children=children
        )

# Instancia global
decision_agent = ImprovedDecisionAgent()