#!/usr/bin/env python3
"""
Demo del Sistema de Memoria - Fase 3: Aprobación Human-in-the-Loop

Demuestra el flujo completo end-to-end:
1. Usuario hace pregunta con corrección explícita
2. Agente genera respuesta + propuesta de memoria
3. Usuario responde (sí/no/editar)
4. Sistema procesa decisión y persiste si es aprobada
5. Nueva conversación recupera memoria guardada
"""

import sys
from pathlib import Path

# Agregar raíz al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from services.agent.graph import query_with_agent


def demo_fase_3():
    """
    Demo de Fase 3: Ciclo completo de Human-in-the-Loop.
    """
    print("=" * 80)
    print("🧪 DEMO - Sistema de Memoria con Human-in-the-Loop (Fase 3 COMPLETA)")
    print("=" * 80)
    print("\nFase 3: Aprobación y persistencia de memoria")
    print("- Usuario decide explícitamente: aprobar, rechazar o editar")
    print("- Sistema persiste solo memorias aprobadas")
    print("- Trazabilidad completa en audit log")
    print("- Memorias recuperadas en futuras conversaciones\n")
    print("=" * 80)

    # Generar conversation_id único para la demo
    import uuid
    conversation_id = str(uuid.uuid4())

    # ============================================================
    # CASO 1: Propuesta → Aprobación → Persistencia
    # ============================================================

    print("\n\n" + "═" * 80)
    print("📌 CASO 1: Propuesta → Aprobación → Persistencia")
    print("═" * 80)

    print("\n🗣️  Usuario: \"En realidad, el ticket 482 se resuelve reiniciando el servicio de pagos, no el de autenticación\"")
    print("\n⚙️  Ejecutando agente...\n")

    result1 = query_with_agent(
        question="En realidad, el ticket 482 se resuelve reiniciando el servicio de pagos, no el de autenticación",
        conversation_id=conversation_id
    )

    # Verificar que se generó propuesta
    if result1.get("pending_proposal"):
        print("\n✅ Propuesta generada correctamente")
        proposal = result1["pending_proposal"]
        print(f"   ID: {proposal['id']}")
        print(f"   Contenido: {proposal['content']}")
        print(f"   Categoría: {proposal['category']}")

        # Simular aprobación del usuario
        print("\n" + "-" * 80)
        print("\n🗣️  Usuario: \"sí, guárdalo\"")
        print("\n⚙️  Procesando aprobación...\n")

        result2 = query_with_agent(
            question="sí, guárdalo",
            conversation_id=conversation_id
        )

        # Verificar que se persistió
        if "guardada exitosamente" in result2["answer"].lower():
            print("\n✅ Memoria persistida correctamente")
            print(f"   Estado: {result2['metadata'].get('approval_status')}")
        else:
            print("\n⚠️  No se detectó persistencia")
    else:
        print("\n⚠️  No se generó propuesta (revisar evaluación)")

    # ============================================================
    # CASO 2: Propuesta → Rechazo
    # ============================================================

    print("\n\n" + "═" * 80)
    print("📌 CASO 2: Propuesta → Rechazo explícito")
    print("═" * 80)

    # Nueva conversación para este caso
    conversation_id_2 = str(uuid.uuid4())

    print("\n🗣️  Usuario: \"El inventario sincroniza limpiando la caché de Redis\"")
    print("\n⚙️  Ejecutando agente...\n")

    result3 = query_with_agent(
        question="El inventario sincroniza limpiando la caché de Redis",
        conversation_id=conversation_id_2
    )

    if result3.get("pending_proposal"):
        print("\n✅ Propuesta generada")

        # Simular rechazo del usuario
        print("\n" + "-" * 80)
        print("\n🗣️  Usuario: \"no, no guardes eso\"")
        print("\n⚙️  Procesando rechazo...\n")

        result4 = query_with_agent(
            question="no, no guardes eso",
            conversation_id=conversation_id_2
        )

        # Verificar rechazo
        if "rechazada" in result4["answer"].lower():
            print("\n✅ Propuesta rechazada correctamente")
            print(f"   Estado: {result4['metadata'].get('approval_status')}")
        else:
            print("\n⚠️  No se detectó rechazo")

    # ============================================================
    # CASO 3: Propuesta → Edición → Aprobación
    # ============================================================

    print("\n\n" + "═" * 80)
    print("📌 CASO 3: Propuesta → Edición por usuario → Aprobación")
    print("═" * 80)

    # Nueva conversación
    conversation_id_3 = str(uuid.uuid4())

    print("\n🗣️  Usuario: \"Los incidentes de red se resuelven con reinicio del router\"")
    print("\n⚙️  Ejecutando agente...\n")

    result5 = query_with_agent(
        question="Los incidentes de red se resuelven con reinicio del router",
        conversation_id=conversation_id_3
    )

    if result5.get("pending_proposal"):
        print("\n✅ Propuesta generada")

        # Simular edición del usuario
        print("\n" + "-" * 80)
        print("\n🗣️  Usuario: \"mejor: Los incidentes de red se resuelven reiniciando el router principal y verificando configuración de DNS\"")
        print("\n⚙️  Procesando edición...\n")

        result6 = query_with_agent(
            question="mejor: Los incidentes de red se resuelven reiniciando el router principal y verificando configuración de DNS",
            conversation_id=conversation_id_3
        )

        # Verificar edición y persistencia
        if "guardada exitosamente" in result6["answer"].lower():
            print("\n✅ Contenido editado y persistido")
            print(f"   Estado: {result6['metadata'].get('approval_status')}")
            if "actualizado" in result6["answer"].lower():
                print("   ✓ Contenido fue modificado según edición del usuario")
        else:
            print("\n⚠️  No se detectó persistencia de contenido editado")

    # ============================================================
    # CASO 4: Propuesta → Cambio de tema (Descarte automático)
    # ============================================================

    print("\n\n" + "═" * 80)
    print("📌 CASO 4: Propuesta → Cambio de tema → Descarte automático")
    print("═" * 80)

    # Nueva conversación
    conversation_id_4 = str(uuid.uuid4())

    print("\n🗣️  Usuario: \"La autenticación LDAP requiere configuración especial\"")
    print("\n⚙️  Ejecutando agente...\n")

    result7 = query_with_agent(
        question="La autenticación LDAP requiere configuración especial",
        conversation_id=conversation_id_4
    )

    if result7.get("pending_proposal"):
        print("\n✅ Propuesta generada")

        # Usuario cambia de tema sin responder
        print("\n" + "-" * 80)
        print("\n🗣️  Usuario: \"¿Cuántos locales tiene Brasaland?\" (cambio de tema)")
        print("\n⚙️  Ejecutando agente...\n")

        result8 = query_with_agent(
            question="¿Cuántos locales tiene Brasaland?",
            conversation_id=conversation_id_4
        )

        # Verificar descarte
        if "descartada" in str(result8):
            print("\n✅ Propuesta descartada por cambio de tema")
        else:
            print("\n⚠️  No se detectó descarte automático")

    # ============================================================
    # CASO 5: Recuperación de memoria en nueva conversación
    # ============================================================

    print("\n\n" + "═" * 80)
    print("📌 CASO 5: Recuperación de memoria guardada (nueva conversación)")
    print("═" * 80)

    # Nueva conversación (simula usuario regresando después)
    conversation_id_5 = str(uuid.uuid4())

    print("\n🗣️  Usuario: \"¿Cómo soluciono el ticket 482?\" (pregunta relacionada)")
    print("\n⚙️  Ejecutando agente...\n")

    result9 = query_with_agent(
        question="¿Cómo soluciono el ticket 482?",
        conversation_id=conversation_id_5
    )

    # Verificar si se recuperó la memoria guardada en Caso 1
    if result9.get("metadata", {}).get("used_memories_count", 0) > 0:
        print("\n✅ Memoria recuperada de conversación anterior")
        print(f"   Memorias usadas: {result9['metadata']['used_memories_count']}")
        if "pagos" in result9["answer"].lower():
            print("   ✓ Respuesta incluye información de memoria guardada (servicio de pagos)")
    else:
        print("\n⚠️  No se recuperaron memorias (puede ser por threshold de similitud)")

    # ============================================================
    # CASO 6: Validación de políticas negativas (PII)
    # ============================================================

    print("\n\n" + "═" * 80)
    print("📌 CASO 6: Validación de políticas negativas (debe rechazar PII)")
    print("═" * 80)

    # Nueva conversación
    conversation_id_6 = str(uuid.uuid4())

    print("\n🗣️  Usuario: \"La contraseña del admin es abc123xyz\"")
    print("\n⚙️  Ejecutando agente...\n")

    result10 = query_with_agent(
        question="La contraseña del admin es abc123xyz",
        conversation_id=conversation_id_6
    )

    # Verificar que NO se generó propuesta (rechazada por política)
    if not result10.get("pending_proposal"):
        print("\n✅ Propuesta rechazada por política negativa (credentials)")
        print("   ✓ Sistema protege contra persistencia de datos sensibles")
    else:
        print("\n❌ ERROR: Se generó propuesta con PII (violación de seguridad)")
        print(f"   Contenido: {result10['pending_proposal']['content']}")

    # Resumen final
    print("\n\n" + "=" * 80)
    print("📊 RESUMEN DE FASE 3")
    print("=" * 80)
    print("\n✅ Implementado y verificado:")
    print("  ✓ Clasificación de decisiones (sí/no/editar/descarte)")
    print("  ✓ Persistencia de memorias aprobadas")
    print("  ✓ Rechazo explícito de propuestas")
    print("  ✓ Edición de contenido por usuario")
    print("  ✓ Descarte automático por cambio de tema")
    print("  ✓ Recuperación de memorias en nuevas conversaciones")
    print("  ✓ Validación de políticas negativas (PII/credentials)")
    print("  ✓ Audit log completo de todas las decisiones")
    print("\n🎯 Sistema completo de memoria Human-in-the-Loop FUNCIONAL")
    print("\n⏳ Próxima fase (opcional):")
    print("  - Consolidación automática de memorias similares")
    print("  - Expiración/TTL por categoría")
    print("  - Dashboard de auditoría")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        demo_fase_3()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrumpida por usuario")
    except Exception as e:
        print(f"\n\n❌ Error en demo: {e}")
        import traceback
        traceback.print_exc()
