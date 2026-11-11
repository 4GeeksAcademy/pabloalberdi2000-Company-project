"""
Mock RAG Query - Sistema RAG sin dependencias externas

Proporciona respuestas predefinidas sobre Brasaland basadas en el conocimiento
del projectbrief.md sin necesitar Qdrant ni OpenAI.

Para desarrollo/testing.
"""

from typing import Dict, Any
import re


# Base de conocimiento en memoria (extraído de projectbrief.md)
KNOWLEDGE_BASE = {
    "locales": {
        "keywords": ["locales", "restaurantes", "sedes", "ubicaciones", "dónde", "cuántos"],
        "answer": """Brasaland opera **14 restaurantes propios** en dos países:

**Colombia (10 locales):**
- Medellín: Centro, Poblado, Envigado
- Bogotá: Zona Rosa, Usaquén, Suba
- Cali: Norte, Sur
- Cartagena: Centro
- Barranquilla: Norte

**Florida, USA (4 locales):**
- Miami Beach
- Miami Downtown
- Orlando
- Tampa"""
    },
    "ceo": {
        "keywords": ["ceo", "director", "mariana", "restrepo", "jefe", "líder"],
        "answer": "El CEO de Brasaland es **Mariana Restrepo**, hija del fundador. Asumió el cargo en 2019 y lidera la transformación digital de la empresa."
    },
    "empleados": {
        "keywords": ["empleados", "personal", "trabajadores", "cuántas personas", "equipo"],
        "answer": "Brasaland tiene **115 empleados** distribuidos en los 14 locales entre Colombia y Florida."
    },
    "facturacion": {
        "keywords": ["facturación", "ventas", "ingresos", "ganancias", "cuánto vende"],
        "answer": "Brasaland tiene una facturación anual de **$6 millones USD** en sus 14 locales."
    },
    "fundacion": {
        "keywords": ["fundación", "cuándo", "inicio", "creación", "fundada", "antigüedad"],
        "answer": "Brasaland fue fundada en **2008** en Medellín, Colombia. Tiene más de 15 años de trayectoria."
    },
    "cto": {
        "keywords": ["cto", "nicolás", "park", "tecnología", "técnico"],
        "answer": "El CTO (Chief Technology Officer) es **Nicolás Park**, basado en Medellín, quien lidera el equipo de Brasaland Digital."
    },
    "sistemas": {
        "keywords": ["sistemas", "software", "tecnología", "digital", "ats", "inventario"],
        "answer": """Brasaland Digital ha implementado los siguientes sistemas:

1. **ATS (Applicant Tracking System)** - 100% completado
   - Gestión de candidaturas para RRHH
   - Usuario: Ashley Turner (Personas y Cultura)

2. **Sistema de Análisis de Incidencias** - 100% completado
   - Análisis de incidencias postventa
   - 500 incidencias históricas

3. **Sistema de Inventario**
   - Gestión de ingredientes y materia prima
   - 11 ingredientes base
   - Stock por almacén en 14 locales

4. **RAG/Knowledge Base** (este sistema)
   - Consultas sobre conocimiento de Brasaland"""
    },
    "valores": {
        "keywords": ["valores", "misión", "visión", "cultura", "principios"],
        "answer": """Los valores de marca de Brasaland son:

1. **Consistencia**: La comida sabe igual en Medellín o Miami
2. **Experiencia cálida**: Servicio consistente y amigable
3. **Velocidad**: Cocina rápida y eficiente"""
    },
    "departamentos": {
        "keywords": ["departamentos", "áreas", "equipos", "divisiones", "organización"],
        "answer": """Brasaland tiene las siguientes áreas:

- **Operaciones** (Felipe Guerrero)
- **Compras** (Lucía Fernández) - ~20 proveedores
- **Marketing** (Camila Ospina)
- **RRHH** (Ashley Turner, Miami)
- **Formación** (Jake Morrison, Miami)
- **Tecnología** (Nicolás Park, Medellín)
- **Dirección** (Mariana Restrepo, CEO)"""
    },
}


def find_best_match(question: str) -> str:
    """
    Encuentra la mejor respuesta basada en keywords.

    Args:
        question: Pregunta del usuario

    Returns:
        Respuesta encontrada o mensaje por defecto
    """
    question_lower = question.lower()

    # Buscar coincidencias
    matches = []
    for topic, data in KNOWLEDGE_BASE.items():
        score = sum(1 for keyword in data["keywords"] if keyword in question_lower)
        if score > 0:
            matches.append((score, data["answer"]))

    # Retornar mejor match
    if matches:
        matches.sort(reverse=True, key=lambda x: x[0])
        return matches[0][1]

    # Respuesta por defecto
    return """Lo siento, no tengo información específica sobre esa pregunta en mi base de conocimiento actual.

**Puedo responder sobre:**
- Locales y ubicaciones de Brasaland
- Equipo directivo (CEO, CTO)
- Empleados y facturación
- Sistemas implementados (ATS, Inventario, Incidencias)
- Valores de marca
- Departamentos y organización

Intenta reformular tu pregunta usando esas palabras clave."""


def query(question: str) -> str:
    """
    Consulta RAG mock (sin dependencias externas).

    Args:
        question: Pregunta del usuario

    Returns:
        Respuesta generada
    """
    if not question or len(question.strip()) < 3:
        raise ValueError("La pregunta debe tener al menos 3 caracteres")

    answer = find_best_match(question)
    return answer


def main():
    """CLI para testing"""
    import sys

    if len(sys.argv) < 2:
        print("Uso: python rag_query_mock.py '<pregunta>'")
        print("\nEjemplos:")
        print('  python rag_query_mock.py "¿Cuántos locales tiene Brasaland?"')
        print('  python rag_query_mock.py "¿Quién es el CEO?"')
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    answer = query(question)

    print(f"\n{'='*70}")
    print(f"Pregunta: {question}")
    print(f"{'='*70}")
    print(f"\n{answer}\n")
    print(f"{'='*70}")
    print("💡 Sistema RAG Mock - Sin OpenAI/Qdrant\n")


if __name__ == "__main__":
    main()
