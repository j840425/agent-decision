# 🧠 Agente de Decisiones Inteligentes

Sistema de análisis de decisiones basado en IA que utiliza el patrón **ReAct** (Reasoning + Acting) con LLMs de Google Vertex AI para ayudar a usuarios a tomar decisiones informadas mediante búsquedas web en tiempo real, cálculos cuantitativos y visualización de árboles de decisión.

## ✨ Características Principales

- **Cuestionario Adaptativo Inicial**: Construye un perfil personalizado del usuario una sola vez
- **Agente ReAct Robusto**: Razonamiento iterativo que combina pensamiento y acción usando herramientas externas
- **Búsquedas Web en Tiempo Real**: Integración con Tavily API para obtener datos actuales del mercado peruano
- **Análisis Cuantitativo**: Calculadora matemática y probabilística integrada
- **Visualización Interactiva**: Árboles de decisión con Plotly mostrando escenarios, probabilidades, costos y beneficios
- **Proceso Transparente**: Visualización en tiempo real del razonamiento del agente
- **Contextualización Geográfica**: Optimizado para Perú con moneda en PEN

## 🏗️ Arquitectura

El sistema está organizado en capas modulares:

- **Interfaz**: Streamlit para UI web reactiva
- **Agente IA**: LangChain + Vertex AI implementando patrón ReAct
- **Herramientas**: Web search (Tavily), calculator, probability calculator
- **Datos**: Pydantic models con 30+ tipos de recursos
- **Persistencia**: JSON local o Google Cloud Storage
- **Visualización**: Plotly para gráficos interactivos

## 🚀 Instalación

### Requisitos

- Python 3.12
- Cuenta de Google Cloud con Vertex AI habilitado
- API Key de Tavily (obtener en [tavily.com](https://tavily.com))

### Pasos

1. **Clonar el repositorio**
```bash
git clone https://github.com/tu-usuario/decision-agent.git
cd decision-agent
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Configurar Google Cloud**
```bash
gcloud auth application-default login
gcloud config set project TU-PROJECT-ID
```

4. **Configurar variables de entorno**

Crear archivo `.env`:
```env
GOOGLE_CLOUD_PROJECT=tu-proyecto-id
GOOGLE_CLOUD_REGION=us-central1
VERTEX_AI_MODEL=gemini (que soporte ReAct)
TAVILY_API_KEY=tvly-xxxxx
```

5. **Ejecutar la aplicación**
```bash
streamlit run app.py
```

La aplicación se abrirá automáticamente en `http://localhost:8501`

## 📖 Uso

### Primera Vez (Cuestionario)

1. Al iniciar, el sistema presenta un cuestionario adaptativo
2. Responde una serie de preguntas sobre tu perfil (edad, ocupación, situación económica, etc.)
3. El perfil se guarda automáticamente en un json y no se vuelve a solicitar

### Análisis de Decisiones

1. Escribe tu decisión en lenguaje natural
   - Ejemplo: *"¿Em conviene hacer una maestría en IA ahora?"*
2. El agente ReAct ejecuta un análisis profundo:
   - Busca costos y salarios actuales en Perú
   - Calcula ROI y tiempos de recuperación
   - Identifica riesgos y beneficios
   - Genera recomendación fundamentada
3. Visualiza:
   - Análisis textual completo (3-4 párrafos)
   - Árbol de decisión interactivo
   - Gráfico resumen de probabilidades
   - Detalles de cada escenario

## 🛠️ Tecnologías

| Componente | Tecnología | Versión |
|------------|-----------|---------|
| Framework Web | Streamlit | 1.39.0 |
| LLM Framework | LangChain | 0.3.7 |
| LLM Engine | Google Vertex AI | Gemini 1.5 Flash |
| Web Search | Tavily API | 0.3.3 |
| Visualización | Plotly | 5.24.1 |
| Validación | Pydantic | 2.9.2 |
| Storage | Google Cloud Storage | 2.18.2 |

## 📂 Estructura del Proyecto
```
decision-agent/
├── app.py                    # Aplicación Streamlit principal
├── agent.py                  # Agente ReAct con manejo de errores
├── tools.py                  # Herramientas (web_search, calculator)
├── questionnaire.py          # Cuestionario adaptativo con LLM
├── models.py                 # Modelos Pydantic (UserProfile, DecisionNode)
├── storage.py                # Persistencia (local/cloud)
├── visualizer.py             # Visualizaciones Plotly
├── custom_callback.py        # Callbacks para debugging
├── config.py                 # Configuración centralizada
├── requirements.txt          # Dependencias Python
├── .env                      # Variables de entorno
└── README.md                 # Este archivo
```

## 🔑 Características Técnicas Destacadas

### Patrón ReAct

El agente implementa el patrón **Reasoning + Acting**:
```
Thought → Action → Observation → Thought → ... → Final Answer
```

- Manejo robusto de errores de parseo
- Máximo 12 iteraciones con timeout de 600s
- Sistema de reintentos inteligentes (3 intentos)

### Prompt Engineering

- Prompts altamente estructurados con ejemplos explícitos
- Instrucciones específicas según tipo de decisión (financiera, laboral, educativa, personal, tecnológica)
- Prevención de errores comunes (mezcla de Action + Final Answer)
- Feedback dirigido según tipo de error

### Manejo de Errores

- `handle_parsing_errors()`: Detecta y corrige 5+ tipos de errores
- Contador de errores consecutivos con forzado de respuesta
- Construcción de análisis desde pasos intermedios si falla output
- Mensajes específicos con sugerencias de reformulación

## 🌐 Deployment en Cloud Run
```bash
# Build imagen
gcloud builds submit --tag gcr.io/PROJECT-ID/decision-agent

# Deploy
gcloud run deploy decision-agent \
  --image gcr.io/PROJECT-ID/decision-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

El sistema detecta automáticamente el entorno y usa Cloud Storage en producción.

## 🔒 Seguridad

- **NUNCA subas archivos `.env` o service account keys a Git**
- Usa `gcloud auth application-default login` para desarrollo local
- En Cloud Run, usa Service Accounts sin claves JSON
- Agrega al `.gitignore`:
```
.env
*.json
data/
__pycache__/
```

## 📝 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 👤 Autoría y Desarrollo

**Diseño y Arquitectura:** Jean Carlo Gómez Ponce
- Conceptualización del sistema
- Decisiones de arquitectura y flujo
- Dirección del desarrollo
- Correcciones y ajustes
  
**Implementación:** Código generado con Claude AI (Anthropic) bajo supervisión y especificaciones del autor

**Nota sobre el uso de IA:** Este proyecto fue desarrollado mediante pair programming con IA. El diseño, la arquitectura y las decisiones técnicas son del autor humano. La implementación del código fue asistida por Claude AI siguiendo las especificaciones proporcionadas.

Proyecto: [https://github.com/j840425/decision-agent](https://github.com/j840425/decision-agent)

## 🙏 Agradecimientos

- [Anthropic](https://anthropic.com) por Claude AI, asistente en el desarrollo del código
- [LangChain](https://langchain.com) por el framework de LLMs
- [Google Cloud](https://cloud.google.com) por Vertex AI
- [Tavily](https://tavily.com) por la API de búsqueda
- [Streamlit](https://streamlit.io) por el framework web

---

⭐ Si este proyecto te fue útil, considera darle una estrella en GitHub
