# questionnaire.py
from langchain_google_vertexai import ChatVertexAI
from langchain.prompts import ChatPromptTemplate
from config import config
from storage import storage
from models import UserProfile
from typing import Optional, Dict, Any

class AdaptiveQuestionnaire:
    """Cuestionario adaptativo que usa el LLM para hacer preguntas inteligentes"""
    
    def __init__(self):
        self.llm = ChatVertexAI(
            model_name=config.VERTEX_AI_MODEL,
            project=config.GOOGLE_CLOUD_PROJECT,
            location=config.GOOGLE_CLOUD_REGION,
            temperature=0.3,  # Más bajo para preguntas consistentes
            max_output_tokens=2000
        )
        self.profile_data: Dict[str, Any] = {}
    
    def generate_next_question(self, previous_answers: Dict[str, Any]) -> Optional[str]:
        """
        Genera la siguiente pregunta basada en respuestas previas
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un asistente que hace un cuestionario para conocer al usuario.
    Tu objetivo es recopilar información relevante para ayudar al usuario a tomar mejores decisiones.

    INFORMACIÓN YA RECOPILADA:
    {answered_fields}

    REGLAS:
    1. Puedes hacer UNA o DOS preguntas relacionadas en la misma línea
    2. SIEMPRE debes obtener: edad, sexo, estado civil, ocupación, ingresos
    3. Si no tienes edad NI sexo, pregunta AMBOS juntos: "¿Cuál es tu edad y sexo?"
    4. Se adaptativo: si el usuario dice "casado", pregunta sobre hijos
    5. Si el usuario dice que tiene hijos, pregunta cuántos y sus edades
    6. Si dice que trabaja, pregunta sobre su ocupación e ingresos
    7. Pregunta sobre salud (peso, enfermedades crónicas)
    8. Pregunta sobre familia (padres vivos)
    9. Pregunta sobre preferencias de alimentación
    10. Cuando hayas recopilado suficiente información básica (al menos 8-10 campos), responde exactamente: "CUESTIONARIO_COMPLETO"

    EJEMPLOS DE PREGUNTAS:
    - Primera pregunta (si no hay datos): "¿Cuál es tu edad y sexo?"
    - "¿Estás casado/a o soltero/a?"
    - "¿Cuál es tu ocupación?"
    - "¿Cuál es tu ingreso mensual aproximado en soles (PEN)?"
            
    IMPORTANTE: 
    - Haz preguntas naturales y conversacionales
    - No hagas preguntas invasivas innecesarias
    - Si ya tienes información sobre un tema, no preguntes de nuevo
    - Cuando determines que tienes suficiente información, responde SOLO "CUESTIONARIO_COMPLETO"
    """),
            ("human", "Genera la siguiente pregunta.")
        ])
        
        # Formatear respuestas previas
        if not previous_answers:
            answered = "Ninguna (primera pregunta)"
        else:
            answered_parts = []
            
            # Mostrar campos estructurados
            for key, value in previous_answers.items():
                if key not in ["respuestas_originales", "additional_context"]:
                    answered_parts.append(f"- {key}: {value}")
            
            # Mostrar contexto adicional
            if "additional_context" in previous_answers:
                answered_parts.append("\nCONTEXTO ADICIONAL:")
                for ctx_key, ctx_val in previous_answers["additional_context"].items():
                    answered_parts.append(f"- {ctx_val}")
            
            # Mostrar respuestas originales completas
            if "respuestas_originales" in previous_answers:
                answered_parts.append("\nRESPUESTAS ORIGINALES COMPLETAS:")
                for i, resp in enumerate(previous_answers["respuestas_originales"], 1):
                    answered_parts.append(f"{i}. P: {resp['pregunta']}")
                    answered_parts.append(f"   R: {resp['respuesta']}")
            
            answered = "\n".join(answered_parts)
        
        try:
            response = self.llm.invoke(prompt.format(answered_fields=answered))
            question = response.content.strip()
            
            # Verificar si el cuestionario está completo
            if "CUESTIONARIO_COMPLETO" in question:
                return None
            
            return question
        except Exception as e:
            print(f"Error generando pregunta: {e}")
            return None
    
    def process_answer(self, question: str, answer: str, previous_answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa la respuesta y extrae campos estructurados usando el LLM
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Eres un asistente que procesa respuestas de un cuestionario.
    Dada una pregunta y respuesta, extrae los campos estructurados relevantes.

    CAMPOS ESTRUCTURADOS PRINCIPALES:
    - edad (int)
    - sexo (str)
    - estado_civil (str)
    - numero_hijos (int)
    - ocupacion (str)
    - ingreso_mensual (float)
    - anos_experiencia (int)
    - peso (float en kg)
    - altura (float en cm)
    - enfermedades (lista de strings)
    - padres_vivos (bool)
    - preferencias_alimentacion (lista de strings)

    CAMPOS ADICIONALES: 
    - ubicacion (str) - si menciona ciudad o país
    - situacion_vivienda (str) - si menciona casa propia, alquiler, etc
    - educacion (str) - si menciona estudios
    - objetivos (str) - si menciona metas o planes
    - CUALQUIER otra información relevante debe ir en "contexto_adicional"

    RESPONDE SOLO CON UN OBJETO JSON VÁLIDO. 

    EJEMPLOS:
    Pregunta: "¿Cuál es tu edad y sexo?"
    Respuesta: "35 años, masculino, vivo en Lima"
    {{"edad": 35, "sexo": "masculino", "ubicacion": "Lima"}}

    Pregunta: "¿Cuál es tu edad?"
    Respuesta: "tengo 41 años y trabajo en sistemas"
    {{"edad": 41, "contexto_adicional": "trabajo en sistemas"}}

    Pregunta: "¿Estás casado/a?"
    Respuesta: "Sí, casado desde hace 10 años"
    {{"estado_civil": "casado", "contexto_adicional": "casado desde hace 10 años"}}

    RESPONDE SOLO JSON, SIN TEXTO ADICIONAL."""),
            ("human", "Pregunta: {question}\nRespuesta: {answer}\n\nJSON:")
        ])
        
        try:
            response = self.llm.invoke(prompt.format(question=question, answer=answer))
            extracted = response.content.strip()
            
            # Debug: mostrar respuesta del LLM
            print(f"DEBUG - Respuesta del LLM: {extracted}")
            
            # Limpiar respuesta si viene con markdown o texto extra
            if extracted.startswith("```json"):
                extracted = extracted.replace("```json", "").replace("```", "").strip()
            elif extracted.startswith("```"):
                extracted = extracted.replace("```", "").strip()
            
            # Buscar el JSON en caso de que haya texto adicional
            import re
            json_match = re.search(r'\{[^}]+\}', extracted)
            if json_match:
                extracted = json_match.group(0)
            
            # Intentar parsear como JSON
            import json
            fields = json.loads(extracted)
            
            # Debug: mostrar campos extraídos
            print(f"DEBUG - Campos extraídos: {fields}")
            
            # Si hay contexto_adicional del LLM, agregarlo al additional_context
            if "contexto_adicional" in fields:
                if "additional_context" not in previous_answers:
                    previous_answers["additional_context"] = {}
                # Usar la pregunta como key para el contexto
                key = f"contexto_{len(previous_answers.get('additional_context', {}))}"
                previous_answers["additional_context"][key] = fields.pop("contexto_adicional")
            
            # Combinar con respuestas previas
            previous_answers.update(fields)
            
            # NUEVO: También guardar la respuesta original completa
            if "respuestas_originales" not in previous_answers:
                previous_answers["respuestas_originales"] = []
            previous_answers["respuestas_originales"].append({
                "pregunta": question,
                "respuesta": answer
            })
            
            return previous_answers
            
        except json.JSONDecodeError as e:
            print(f"Error parseando JSON: {e}")
            print(f"Contenido recibido: {extracted}")
            # Si falla JSON, intentar extraer manualmente
            manual_extract = self._manual_extract(question, answer)
            if manual_extract:
                previous_answers.update(manual_extract)
            
            # Guardar respuesta original de todos modos
            if "respuestas_originales" not in previous_answers:
                previous_answers["respuestas_originales"] = []
            previous_answers["respuestas_originales"].append({
                "pregunta": question,
                "respuesta": answer
            })
            return previous_answers
            
        except Exception as e:
            print(f"Error procesando respuesta: {e}")
            # Intentar extracción manual
            manual_extract = self._manual_extract(question, answer)
            if manual_extract:
                previous_answers.update(manual_extract)
            
            # Guardar respuesta original
            if "respuestas_originales" not in previous_answers:
                previous_answers["respuestas_originales"] = []
            previous_answers["respuestas_originales"].append({
                "pregunta": question,
                "respuesta": answer
            })
            return previous_answers
    
    def _manual_extract(self, question: str, answer: str) -> Dict[str, Any]:
        """
        Extracción manual como fallback si el LLM falla
        """
        import re
        result = {}
        
        answer_lower = answer.lower()
        question_lower = question.lower()
        
        # Edad
        if "edad" in question_lower:
            edad_match = re.search(r'\b(\d{1,3})\b', answer)
            if edad_match:
                result["edad"] = int(edad_match.group(1))
        
        # Sexo
        if "sexo" in question_lower or "género" in question_lower:
            if any(word in answer_lower for word in ["masculino", "hombre", "m", "male"]):
                result["sexo"] = "masculino"
            elif any(word in answer_lower for word in ["femenino", "mujer", "f", "female"]):
                result["sexo"] = "femenino"
        
        # Estado civil
        if "estado civil" in question_lower or "casado" in question_lower:
            if any(word in answer_lower for word in ["casado", "casada"]):
                result["estado_civil"] = "casado"
            elif any(word in answer_lower for word in ["soltero", "soltera"]):
                result["estado_civil"] = "soltero"
            elif any(word in answer_lower for word in ["divorciado", "divorciada"]):
                result["estado_civil"] = "divorciado"
        
        # Hijos
        if "hijos" in question_lower or "niños" in question_lower:
            hijos_match = re.search(r'\b(\d+)\b', answer)
            if hijos_match:
                result["numero_hijos"] = int(hijos_match.group(1))
        
        # Ingresos
        if "ingreso" in question_lower or "salario" in question_lower or "sueldo" in question_lower:
            ingreso_match = re.search(r'\b(\d+[\d,]*\.?\d*)\b', answer.replace(',', ''))
            if ingreso_match:
                result["ingreso_mensual"] = float(ingreso_match.group(1).replace(',', ''))
        
        return result
    
    def save_to_profile(self, answers: Dict[str, Any]):
        """
        Guarda las respuestas en el perfil del usuario
        """
        profile = UserProfile()
        
        # Mapear campos conocidos
        field_mapping = {
            'edad': 'edad',
            'sexo': 'sexo',
            'estado_civil': 'estado_civil',
            'numero_hijos': 'numero_hijos',
            'ocupacion': 'ocupacion',
            'ingreso_mensual': 'ingreso_mensual',
            'anos_experiencia': 'anos_experiencia',
            'peso': 'peso',
            'altura': 'altura',
            'padres_vivos': 'padres_vivos'
        }
        
        for answer_key, profile_key in field_mapping.items():
            if answer_key in answers:
                setattr(profile, profile_key, answers[answer_key])
        
        # Campos especiales (listas)
        if 'enfermedades' in answers:
            profile.enfermedades = answers['enfermedades'] if isinstance(answers['enfermedades'], list) else [answers['enfermedades']]
        
        if 'preferencias_alimentacion' in answers:
            profile.preferencias_alimentacion = answers['preferencias_alimentacion'] if isinstance(answers['preferencias_alimentacion'], list) else [answers['preferencias_alimentacion']]
        
        # Todo lo demás va a additional_context
        for key, value in answers.items():
            if key not in field_mapping and key not in ['enfermedades', 'preferencias_alimentacion']:
                profile.additional_context[key] = value
        
        storage.save_profile(profile)

# Instancia global
questionnaire = AdaptiveQuestionnaire()