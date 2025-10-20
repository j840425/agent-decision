# app.py
import streamlit as st
from storage import storage
from questionnaire import questionnaire
from agent import decision_agent
from visualizer import visualizer
from config import config
import traceback

# Configuración de la página
st.set_page_config(
    page_title="Agente de Decisiones Inteligentes",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        border-radius: 5px;
        height: 3em;
        background-color: #3498db;
        color: white;
    }
    .stButton>button:hover {
        background-color: #2980b9;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Inicializa el estado de la sesión"""
    if 'questionnaire_active' not in st.session_state:
        st.session_state.questionnaire_active = False
    if 'questionnaire_answers' not in st.session_state:
        st.session_state.questionnaire_answers = {}
    if 'current_question' not in st.session_state:
        st.session_state.current_question = None
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    if 'questionnaire_completed' not in st.session_state:
        st.session_state.questionnaire_completed = False

def questionnaire_page():
    """Página del cuestionario inicial"""
    st.title("🎯 Cuestionario Inicial")
    st.markdown("### Cuéntame sobre ti para poder ayudarte mejor")
    
    # Si no hay pregunta actual, generar la primera
    if st.session_state.current_question is None:
        with st.spinner("Generando pregunta..."):
            st.session_state.current_question = questionnaire.generate_next_question(
                st.session_state.questionnaire_answers
            )
    
    # Si el cuestionario está completo
    if st.session_state.current_question is None:
        st.success("✅ Cuestionario completado! Ya tengo suficiente información para ayudarte.")
        
        # Guardar perfil
        with st.spinner("Guardando tu perfil..."):
            questionnaire.save_to_profile(st.session_state.questionnaire_answers)
        
        # AGREGAR ESTO: Mostrar lo que se guardó
        with st.expander("📋 Información guardada:", expanded=True):
            for key, value in st.session_state.questionnaire_answers.items():
                st.write(f"**{key}:** {value}")
        
        if st.button("Ir al Análisis de Decisiones", type="primary"):
            # NUEVO: Marcar cuestionario como completado
            st.session_state.questionnaire_completed = True
            st.session_state.questionnaire_active = False
            st.session_state.current_question = None
            st.session_state.questionnaire_answers = {}
            st.rerun()
        return
    
    # Mostrar pregunta actual - VERSIÓN QUE MUESTRA TODO EL TEXTO
    # Mostrar pregunta actual - MÉTODO INFALIBLE
    st.markdown("---")
    st.markdown("#### ❓ Pregunta:")
    
    # Usar st.markdown sin HTML, solo texto plano
    st.markdown(st.session_state.current_question)
    
    st.markdown("---")
    
    # Input para respuesta
    with st.form(key='answer_form', clear_on_submit=True):
        answer = st.text_input(
            "Tu respuesta:", 
            key='user_answer',
            placeholder="Escribe aquí...",
            label_visibility="visible"
        )
        
        # Botón más pequeño - solo ocupa 30% del ancho
        col1, col2, col3 = st.columns([1, 1, 3])
        with col1:
            submit = st.form_submit_button("➡️ Enviar", type="primary")
        
        if submit and answer.strip():
            with st.spinner("Procesando..."):
                st.session_state.questionnaire_answers = questionnaire.process_answer(
                    st.session_state.current_question,
                    answer,
                    st.session_state.questionnaire_answers
                )
                
                # RESTAURAR: Guardar después de cada respuesta
                questionnaire.save_to_profile(st.session_state.questionnaire_answers)
                
                st.session_state.current_question = questionnaire.generate_next_question(
                    st.session_state.questionnaire_answers
                )
            
            st.rerun()

    # Mostrar respuestas anteriores (sin progreso)
    if st.session_state.questionnaire_answers:
        st.write("")
        st.divider()
        with st.expander("📋 Ver respuestas anteriores", expanded=False):
            for key, value in st.session_state.questionnaire_answers.items():
                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
    

def decision_analysis_page():
    """Página principal de análisis de decisiones"""
    st.title("🧠 Agente de Decisiones Inteligentes")
    
    # Sidebar con información del perfil
    with st.sidebar:
        st.header("👤 Tu Perfil")
        
        profile = storage.load_profile()
        
        if profile.edad:
            st.markdown(f"**Edad:** {profile.edad}")
        if profile.ocupacion:
            st.markdown(f"**Ocupación:** {profile.ocupacion}")
        if profile.estado_civil:
            st.markdown(f"**Estado civil:** {profile.estado_civil}")
        if profile.numero_hijos:
            st.markdown(f"**Hijos:** {profile.numero_hijos}")
        
        st.divider()
        
        if st.button("🔄 Reiniciar Perfil"):
            if st.session_state.get('confirm_reset', False):
                storage.clear_profile()
                st.session_state.questionnaire_active = True
                st.session_state.questionnaire_completed = False  # NUEVO
                st.session_state.questionnaire_answers = {}
                st.session_state.current_question = None
                st.session_state.confirm_reset = False
                st.rerun()
            else:
                st.session_state.confirm_reset = True
                st.warning("⚠️ Haz clic nuevamente para confirmar")
        
        st.divider()
        st.markdown("### ⚙️ Configuración")
        max_depth = st.slider(
            "Profundidad del árbol",
            min_value=1,
            max_value=4,
            value=config.MAX_TREE_DEPTH,
            help="Niveles de profundidad del árbol de decisión"
        )
    
    # Área principal
    st.markdown("""
    ### 💡 Plantéame tu decisión
    Describe la decisión que necesitas tomar y te ayudaré a analizarla racionalmente.
    """)
    
    # Input de la decisión
    col1, col2 = st.columns([4, 1])
    
    with col1:
        decision_question = st.text_area(
            "¿Qué decisión necesitas tomar?",
            placeholder="Ejemplo: ¿Debo cambiar de trabajo a una empresa que me ofrece 20% más de salario pero requiere mudarme a otra ciudad?",
            height=100
        )
    
    with col2:
        st.write("")  # Espaciado
        st.write("")  # Espaciado
        analyze_button = st.button("🔍 Analizar", type="primary")
    
    # Analizar decisión
    if analyze_button and decision_question.strip():
        try:
            # Crear container para mostrar el proceso de pensamiento
            thinking_container = st.container()
            
            with thinking_container:
                st.markdown("## 🤔 Analizando tu decisión...")
                st.markdown("---")
            
            # CAMBIO: Usar el método mejorado con reintentos
            result = decision_agent.analyze_decision_with_retry(
                decision_question,
                max_depth=max_depth,
                thinking_container=thinking_container
            )
            
            st.session_state.analysis_result = result
            
            # Mostrar mensaje de éxito
            if result and 'analysis' in result:
                st.success("✅ Análisis completado exitosamente")
            
        except Exception as e:
            st.error(f"⌛ Error durante el análisis: {str(e)}")
            
            # Ofrecer análisis alternativo
            if st.button("🔄 Intentar análisis simplificado"):
                try:
                    result = decision_agent._fallback_analysis(
                        decision_question, 
                        storage.load_profile().to_context_string(),
                        max_depth,
                        thinking_container
                    )
                    st.session_state.analysis_result = result
                except:
                    st.error("No se pudo completar el análisis. Por favor, intenta reformular tu pregunta.")
            
            with st.expander("Ver detalles del error"):
                st.code(traceback.format_exc())
    
    # Mostrar resultados
    if st.session_state.analysis_result:
        result = st.session_state.analysis_result
        
        st.divider()
        
        # Análisis textual
        st.markdown("### 📊 Análisis")
        with st.expander("Ver análisis completo", expanded=True):
            st.markdown(result['analysis'])
        
        st.divider()
        
        # Visualizaciones
        st.markdown("### 🌳 Árbol de Decisión")
        
        tab1, tab2 = st.tabs(["Árbol Completo", "Resumen"])
        
        with tab1:
            try:
                tree_fig = visualizer.create_tree_visualization(result['decision_tree'])
                st.plotly_chart(tree_fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error al visualizar árbol: {str(e)}")
        
        with tab2:
            try:
                summary_fig = visualizer.create_summary_chart(result['decision_tree'])
                st.plotly_chart(summary_fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error al visualizar resumen: {str(e)}")
        
        # Información detallada de nodos
        st.divider()
        st.markdown("### 📋 Detalles de Escenarios")
        
        def show_node_details(node, level=0):
            """Muestra detalles de un nodo recursivamente"""
            indent = "　" * level
            
            with st.expander(f"{indent}{'📍' if level == 0 else '↳'} {node.description} ({node.probability:.1f}%)"):
                if node.reasoning:
                    st.markdown(f"**Razonamiento:** {node.reasoning}")
                
                if node.costs:
                    st.markdown("**Costos:**")
                    for cost in node.costs:
                        icon = visualizer._get_resource_icon(cost.resource_type)
                        st.write(f"{icon} {cost.amount} {cost.unit} - {cost.description or cost.resource_type.value}")
                
                if node.benefits:
                    st.markdown("**Beneficios:**")
                    for benefit in node.benefits:
                        icon = visualizer._get_resource_icon(benefit.resource_type)
                        st.write(f"✅ {benefit.amount} {benefit.unit} - {benefit.description or benefit.resource_type.value}")
            
            # Recursión para hijos
            for child in node.children:
                show_node_details(child, level + 1)
        
        show_node_details(result['decision_tree'])

def main():
    """Función principal"""
    initialize_session_state()
    
    # Verificar configuración
    try:
        config.validate()
    except ValueError as e:
        st.error(f"❌ Error de configuración: {str(e)}")
        st.info("Por favor, configura tu archivo .env con GOOGLE_CLOUD_PROJECT")
        st.stop()
    
    # Determinar qué página mostrar usando la bandera
    if not st.session_state.questionnaire_completed or st.session_state.questionnaire_active:
        questionnaire_page()
    else:
        decision_analysis_page()

if __name__ == "__main__":
    main()