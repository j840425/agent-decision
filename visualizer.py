# visualizer.py
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from models import DecisionNode, ResourceType
from typing import List, Tuple, Dict
import math

class DecisionTreeVisualizer:
    """Visualiza árboles de decisión con Plotly"""
    
    def __init__(self):
        self.node_positions = {}
        self.edge_traces = []
        self.node_traces = []
    
    def create_tree_visualization(self, root: DecisionNode) -> go.Figure:
        """
        Crea una visualización interactiva del árbol de decisión
        """
        # Calcular posiciones de nodos
        self._calculate_positions(root, x=0, y=0, level=0, width=10)
        
        # Crear figura
        fig = go.Figure()
        
        # Agregar aristas (conexiones)
        self._add_edges(fig, root)
        
        # Agregar nodos
        self._add_nodes(fig, root)
        
        # Configurar layout
        fig.update_layout(
            title={
                'text': "Árbol de Decisión - Análisis de Escenarios",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'color': '#2c3e50'}
            },
            showlegend=False,
            hovermode='closest',
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='white',
            xaxis={
                'showgrid': False,
                'zeroline': False,
                'showticklabels': False,
                'title': ''
            },
            yaxis={
                'showgrid': False,
                'zeroline': False,
                'showticklabels': False,
                'title': '',
                'autorange': 'reversed'  # Niveles de arriba hacia abajo
            },
            height=800,
            margin=dict(l=20, r=20, t=80, b=20)
        )
        
        return fig
    
    def _calculate_positions(self, node: DecisionNode, x: float, y: float, 
                            level: int, width: float):
        """
        Calcula posiciones de nodos usando algoritmo de árbol balanceado
        """
        self.node_positions[node.id] = (x, y)
        
        if not node.children:
            return
        
        # Calcular ancho para distribuir hijos
        num_children = len(node.children)
        child_width = width / num_children
        
        # Posicionar hijos
        start_x = x - width / 2 + child_width / 2
        
        for i, child in enumerate(node.children):
            child_x = start_x + i * child_width
            child_y = y + 1  # Incrementar nivel
            self._calculate_positions(child, child_x, child_y, level + 1, child_width * 0.8)
    
    def _add_edges(self, fig: go.Figure, node: DecisionNode):
        """
        Agrega aristas (líneas de conexión) al gráfico
        """
        if node.id not in self.node_positions:
            return
        
        parent_pos = self.node_positions[node.id]
        
        for child in node.children:
            if child.id in self.node_positions:
                child_pos = self.node_positions[child.id]
                
                # Línea de conexión
                fig.add_trace(go.Scatter(
                    x=[parent_pos[0], child_pos[0]],
                    y=[parent_pos[1], child_pos[1]],
                    mode='lines',
                    line=dict(
                        color='#95a5a6',
                        width=2
                    ),
                    hoverinfo='skip',
                    showlegend=False
                ))
                
                # Etiqueta de probabilidad en la arista
                mid_x = (parent_pos[0] + child_pos[0]) / 2
                mid_y = (parent_pos[1] + child_pos[1]) / 2
                
                fig.add_trace(go.Scatter(
                    x=[mid_x],
                    y=[mid_y],
                    mode='text',
                    text=[f"{child.probability:.0f}%"],
                    textfont=dict(size=10, color='#e74c3c', family='Arial Black'),
                    hoverinfo='skip',
                    showlegend=False
                ))
                
                # Recursión para hijos
                self._add_edges(fig, child)
    
    def _add_nodes(self, fig: go.Figure, node: DecisionNode):
        """
        Agrega nodos al gráfico
        """
        if node.id not in self.node_positions:
            return
        
        pos = self.node_positions[node.id]
        
        is_leaf = len(node.children) == 0

        # Determinar color
        if is_leaf:
            # Todas las hojas del mismo color verde
            color = '#2ecc71'  # Verde para hojas
        else:
            # Nodos internos según nivel
            colors = ['#3498db', '#f39c12', '#e74c3c', '#9b59b6']
            color = colors[node.level % len(colors)]
        
        # Crear hover text con toda la información
        hover_text = self._create_hover_text(node)
        
        # Agregar nodo
        fig.add_trace(go.Scatter(
            x=[pos[0]],
            y=[pos[1]],
            mode='markers+text',
            marker=dict(
                size=40,
                color=color,
                line=dict(color='white', width=3),
                symbol='circle'
            ),
            text=[self._truncate_text(node.description, 20)],
            textposition='bottom center',
            textfont=dict(size=10, color='#2c3e50', family='Arial'),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=False
        ))
        
        # Recursión para hijos
        for child in node.children:
            self._add_nodes(fig, child)
    
    def _create_hover_text(self, node: DecisionNode) -> str:
        """
        Crea el texto de hover con información detallada del nodo
        """
        lines = [
            f"<b>{node.description}</b>",
            f"Probabilidad: {node.probability:.1f}%",
            ""
        ]
        
        if node.reasoning:
            lines.append(f"<i>Razonamiento:</i> {node.reasoning}")
            lines.append("")
        
        if node.costs:
            lines.append("<b>Costos:</b>")
            for cost in node.costs:
                icon = self._get_resource_icon(cost.resource_type)
                lines.append(f"{icon} {cost.amount} {cost.unit} - {cost.description or cost.resource_type.value}")
            lines.append("")
        
        if node.benefits:
            lines.append("<b>Beneficios:</b>")
            for benefit in node.benefits:
                icon = self._get_resource_icon(benefit.resource_type)
                lines.append(f"✅ {benefit.amount} {benefit.unit} - {benefit.description or benefit.resource_type.value}")
        
        return "<br>".join(lines)
    
    def _get_resource_icon(self, resource_type: ResourceType) -> str:
        """
        Retorna un emoji/icono según el tipo de recurso
        """
        icons = {
            # Tangibles
            ResourceType.DINERO: "💰",
            ResourceType.TIEMPO: "⏰",
            
            # Personales
            ResourceType.ENERGIA: "⚡",
            ResourceType.SALUD: "❤️",
            ResourceType.ESTRES: "😰",
            ResourceType.BIENESTAR: "😊",
            
            # Sociales
            ResourceType.REPUTACION: "⭐",
            ResourceType.RELACIONES: "👥",
            ResourceType.FAMILIA: "👨‍👩‍👧",
            ResourceType.RED_CONTACTOS: "🤝",
            
            # Profesionales
            ResourceType.CARRERA: "📈",
            ResourceType.EDUCACION: "🎓",
            ResourceType.EXPERIENCIA: "💼",
            ResourceType.HABILIDADES: "🛠️",
            ResourceType.CONOCIMIENTO: "📚",
            ResourceType.CREDENCIALES: "📜",
            
            # Estratégicos
            ResourceType.OPORTUNIDAD: "🚪",
            ResourceType.CALIDAD_VIDA: "🌟",
            ResourceType.LIBERTAD: "🕊️",
            ResourceType.FLEXIBILIDAD: "🤸",
            ResourceType.SEGURIDAD: "🛡️",
            ResourceType.ESTABILIDAD: "⚓",
            
            # Financieros
            ResourceType.AHORROS: "🏦",
            ResourceType.DEUDA: "💳",
            ResourceType.INVERSION: "📊",
            ResourceType.PATRIMONIO: "🏠",
            
            # Otros
            ResourceType.RIESGO: "⚠️",
            ResourceType.INCERTIDUMBRE: "❓",
            ResourceType.OTRO: "📌"
        }
        return icons.get(resource_type, "📌")
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """
        Trunca texto para mostrar en el nodo
        """
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def create_summary_chart(self, root: DecisionNode) -> go.Figure:
        """
        Crea un gráfico resumen con las probabilidades de escenarios principales
        """
        # Extraer escenarios de primer nivel
        scenarios = []
        probabilities = []
        
        for child in root.children:
            scenarios.append(self._truncate_text(child.description, 30))
            probabilities.append(child.probability)
        
        if not scenarios:
            # Si no hay hijos, mostrar el nodo raíz
            scenarios = [self._truncate_text(root.description, 30)]
            probabilities = [root.probability]
        
        # Crear gráfico de barras
        fig = go.Figure(data=[
            go.Bar(
                x=scenarios,
                y=probabilities,
                marker_color=['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6'][:len(scenarios)],
                text=[f"{p:.1f}%" for p in probabilities],
                textposition='outside'
            )
        ])
        
        fig.update_layout(
            title="Probabilidades de Escenarios Principales",
            xaxis_title="Escenario",
            yaxis_title="Probabilidad (%)",
            height=400,
            showlegend=False,
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='white'
        )
        
        return fig

# Instancia global
visualizer = DecisionTreeVisualizer()