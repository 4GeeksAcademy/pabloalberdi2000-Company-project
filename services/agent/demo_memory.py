#!/usr/bin/env python3
"""
Demo del Sistema de Memoria con Human-in-the-Loop

Demuestra el flujo completo de Fase 2:
1. Usuario hace pregunta con corrección explícita
2. Agente genera respuesta + propuesta de memoria
3. Propuesta se muestra al usuario
4. (Fase 3 manejará la aprobación)
"""

import sys
from pathlib import Path

# Agregar raíz al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.agent.graph import query_with_agent


def demo_fase_2():
    """
    Demo de Fase 2: Auto-evaluación y propuesta de memoria.
    """
    print("=" * 80)
    print("🧪 DEMO - Sistema de Memoria con Human-in-the-Loop (Fase 2)")
    print("=" * 80)
    print("\nFase 2: Auto-evaluación y propuesta de memoria")
    print("- El agente detecta correcciones y soluciones memorables")
    print("- Propone recordarlo al usuario (sin persistir aún)")
    print("- Fase 3 manejará la aprobación/rechazo\n")
    print("=" * 80)

    # Caso 1: Corrección explícita del usuario
    print("\n\n📌 CASO 1: Corrección explícita del usuario")
    print("-" * 80)

    question1 = "En realidad, el ticket 482 se resuelve reiniciando el servicio de pagos, no el de autenticación"

    print(f"\n🗣️  Usuario: {question1}")
    print("\n⚙️  Ejecutando agente...\n")

    result1 = query_with_agent(question1)

    # Verificar que se generó propuesta
    if result1.get("pending_proposal"):
        print("\n✅ ÉXITO: Propuesta de memoria generada")
        print(f"   - Contenido: {result1['pending_proposal']['content']}")
        print(f"   - Categoría: {result1['pending_proposal']['category']}")
        print(f"   - ID: {result1['pending_proposal']['id']}")
    else:
        print("\n⚠️  No se generó propuesta (revisar threshold de evaluación)")

    # Caso 2: Pregunta sobre conocimiento existente (no memorable)
    print("\n\n📌 CASO 2: Pregunta sobre conocimiento existente (no debería generar propuesta)")
    print("-" * 80)

    question2 = "¿Cuántos locales tiene Brasaland?"

    print(f"\n🗣️  Usuario: {question2}")
    print("\n⚙️  Ejecutando agente...\n")

    result2 = query_with_agent(question2)

    # Verificar que NO se generó propuesta
    if not result2.get("pending_proposal"):
        print("\n✅ CORRECTO: No se generó propuesta (información ya está en RAG)")
    else:
        print("\n⚠️  Se generó propuesta cuando no debería (falso positivo)")
        print(f"   - Contenido: {result2['pending_proposal']['content']}")

    # Caso 3: Solución a problema no documentado
    print("\n\n📌 CASO 3: Solución a problema no documentado")
    print("-" * 80)

    question3 = "Descubrí que cuando el inventario no sincroniza, hay que limpiar la caché de Redis y reiniciar el worker de inventario"

    print(f"\n🗣️  Usuario: {question3}")
    print("\n⚙️  Ejecutando agente...\n")

    result3 = query_with_agent(question3)

    # Verificar propuesta
    if result3.get("pending_proposal"):
        print("\n✅ ÉXITO: Propuesta de memoria generada")
        print(f"   - Contenido: {result3['pending_proposal']['content']}")
        print(f"   - Categoría: {result3['pending_proposal']['category']}")
        print(f"   - Razón: {result3['pending_proposal']['reason']}")
    else:
        print("\n⚠️  No se generó propuesta (debería detectar solución nueva)")

    # Caso 4: Intento de guardar PII (debe ser rechazado)
    print("\n\n📌 CASO 4: Intento de guardar PII (debe ser rechazado por política negativa)")
    print("-" * 80)

    question4 = "La contraseña del admin es abc123xyz"

    print(f"\n🗣️  Usuario: {question4}")
    print("\n⚙️  Ejecutando agente...\n")

    result4 = query_with_agent(question4)

    # Verificar que NO se generó propuesta (rechazada por política)
    if not result4.get("pending_proposal"):
        print("\n✅ CORRECTO: Propuesta rechazada por política negativa (PII/credentials)")
    else:
        print("\n❌ ERROR: Se generó propuesta con PII (violación de seguridad)")
        print(f"   - Contenido: {result4['pending_proposal']['content']}")

    # Resumen final
    print("\n\n" + "=" * 80)
    print("📊 RESUMEN DE FASE 2")
    print("=" * 80)
    print("\n✅ Implementado:")
    print("  - Auto-evaluación con Structured Output")
    print("  - Propuestas de memoria con categorización")
    print("  - Validación de políticas negativas")
    print("  - Logging de propuestas en audit log")
    print("\n⏳ Pendiente (Fase 3):")
    print("  - Handler de aprobación/rechazo")
    print("  - Clasificación de respuestas del usuario")
    print("  - Persistencia de memorias aprobadas")
    print("  - Actualización de audit log con decisión")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        demo_fase_2()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrumpida por usuario")
    except Exception as e:
        print(f"\n\n❌ Error en demo: {e}")
        import traceback
        traceback.print_exc()
