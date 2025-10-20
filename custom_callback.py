# custom_callback.py - VERSIÓN CORREGIDA SIN IMPORTACIÓN CIRCULAR
import streamlit as st
from langchain.callbacks.base import BaseCallbackHandler
from typing import Any, Dict, List
import re

class StreamlitAgentCallback(BaseCallbackHandler):
    """Callback mejorado para debugging del proceso del agente"""
    
    def __init__(self, container):
        self.container = container
        self.iteration = 0
        self.current_thought = ""
        self.error_count = 0
        self.successful_tools = 0
        
    def on_agent_action(self, action, **kwargs):
        """Se ejecuta cuando el agente decide una acción"""
        self.iteration += 1
        
        with self.container:
            # Crear columnas para mejor organización
            col1, col2 = st.columns([1, 3])
            
            with col1:
                st.markdown(f"### 🔄 Iteración {self.iteration}")
                
                # Mostrar estado
                if self.error_count > 0:
                    st.warning(f"⚠️ Errores: {self.error_count}")
                if self.successful_tools > 0:
                    st.success(f"✅ Éxitos: {self.successful_tools}")
            
            with col2:
                # Extraer y mostrar el pensamiento
                if hasattr(action, 'log') and action.log:
                    log_text = action.log.strip()
                    
                    # Extraer el Thought más limpiamente
                    thought_match = re.search(r'Thought:\s*(.*?)(?:\n|$)', log_text, re.IGNORECASE)
                    if thought_match:
                        thought = thought_match.group(1)
                        st.markdown(f"**💭 Pensamiento:**")
                        st.info(thought)
                    elif log_text and not log_text.startswith('Action'):
                        # Si no hay "Thought:" pero hay texto, mostrarlo
                        st.markdown(f"**💭 Procesando:**")
                        st.info(log_text[:200] + "..." if len(log_text) > 200 else log_text)
            
            # Mostrar la acción en una caja separada
            with st.container():
                st.markdown(f"**⚡ Herramienta:** `{action.tool}`")
                
                # Mostrar el input de forma más clara
                if isinstance(action.tool_input, dict):
                    st.markdown("**📥 Entrada:**")
                    for key, value in action.tool_input.items():
                        st.write(f"  • {key}: {value}")
                else:
                    st.markdown(f"**📥 Entrada:** `{action.tool_input}`")
            
            st.markdown("---")
    
    def on_tool_end(self, output: str, **kwargs):
        """Se ejecuta cuando una herramienta termina"""
        self.successful_tools += 1
        
        with self.container:
            # Limitar la longitud del output mostrado
            output_str = str(output)
            if len(output_str) > 500:
                output_display = output_str[:500] + "... [truncado]"
            else:
                output_display = output_str
            
            # Mostrar resultado con formato mejorado
            with st.expander("📊 Resultado", expanded=True):
                st.success(output_display)
            
            st.markdown("---")
    
    def on_tool_error(self, error: Exception, **kwargs):
        """Se ejecuta cuando una herramienta falla"""
        self.error_count += 1
        
        with self.container:
            st.error(f"❌ Error en herramienta: {str(error)[:200]}")
            st.markdown("---")
    
    def on_agent_finish(self, finish, **kwargs):
        """Se ejecuta cuando el agente termina"""
        with self.container:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Iteraciones", self.iteration)
            with col2:
                st.metric("Herramientas Exitosas", self.successful_tools)
            with col3:
                st.metric("Errores", self.error_count)
            
            st.markdown("### ✅ Análisis Completado")
            
            # Mostrar resumen del proceso
            if self.successful_tools > 0:
                st.success(f"Se ejecutaron {self.successful_tools} herramientas exitosamente")
            if self.error_count > 0:
                st.warning(f"Se encontraron {self.error_count} errores durante el proceso")
            
            st.markdown("---")
    
    def on_llm_error(self, error: Exception, **kwargs):
        """Se ejecuta cuando el LLM tiene un error"""
        error_str = str(error)
        
        # NUEVO: Filtrar errores de parseo - NO mostrarlos en interfaz
        parsing_errors = [
            "Could not parse",
            "both a final answer and a parse-able action",
            "Invalid or incomplete response",
            "Has mezclado formatos"
        ]
        
        # Si es un error de parseo, NO incrementar contador ni mostrar
        if any(err in error_str for err in parsing_errors):
            return  # Silenciosamente ignorar, el agente lo manejará internamente
        
        # Solo mostrar errores REALES (timeout, API, etc)
        self.error_count += 1
        
        with self.container:
            st.error(f"❌ Error del LLM: {str(error)[:200]}")
            
            if "timeout" in str(error).lower():
                st.warning("⏱️ Timeout - la consulta está tardando demasiado")
            
    def on_chain_error(self, error: Exception, **kwargs):
        """Se ejecuta cuando hay un error en la cadena"""
        error_str = str(error)
        
        # NUEVO: También filtrar errores de parseo aquí
        parsing_errors = [
            "Could not parse",
            "both a final answer and a parse-able action",
            "Invalid or incomplete response"
        ]
        
        if any(err in error_str for err in parsing_errors):
            return  # Ignorar silenciosamente
        
        self.error_count += 1
        
        #with self.container:
            #st.error(f"❌ Error en el proceso: {str(error)[:200]}")

# NO HAY IMPORTACIÓN AL FINAL - ESE ERA EL ERROR