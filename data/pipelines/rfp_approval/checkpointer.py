"""
Checkpointer Configuration - PostgreSQL/Supabase

Gestión de checkpoints para Human-in-the-Loop con LangGraph.
Permite pausar y reanudar grafos sin perder estado.
"""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


def get_checkpointer():
    """
    Factory para obtener checkpointer configurado.

    Priority:
    1. PostgresSaver con Supabase (PRODUCCIÓN)
    2. MemorySaver (DESARROLLO/TESTING)

    Returns:
        Checkpointer instance (PostgresSaver o MemorySaver)
    """
    database_url = os.getenv("SUPABASE_DATABASE_URL") or os.getenv("DATABASE_URL")

    if database_url and "postgresql" in database_url:
        # Producción: PostgreSQL/Supabase
        try:
            from langgraph.checkpoint.postgres import PostgresSaver
            from psycopg import Connection

            print("✅ Inicializando PostgresSaver con Supabase...")

            # Crear conexión persistente
            conn = Connection.connect(
                database_url,
                autocommit=True,
                prepare_threshold=0  # Desactiva prepared statements (compatibilidad Supabase)
            )

            # Crear tabla de checkpoints si no existe
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_ns TEXT NOT NULL DEFAULT '',
                    checkpoint_id TEXT NOT NULL,
                    parent_checkpoint_id TEXT,
                    type TEXT,
                    checkpoint JSONB NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{}',
                    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
                );

                CREATE INDEX IF NOT EXISTS checkpoints_thread_id_idx
                    ON checkpoints(thread_id);

                CREATE INDEX IF NOT EXISTS checkpoints_parent_id_idx
                    ON checkpoints(parent_checkpoint_id);
            """)

            checkpointer = PostgresSaver(conn)
            print("✅ PostgresSaver configurado correctamente")
            return checkpointer

        except ImportError:
            print("⚠️  langgraph[postgres] no instalado. Instalar con:")
            print("   pip install 'langgraph[postgres]'")
            print("   Fallback a MemorySaver...")
        except Exception as e:
            print(f"⚠️  Error conectando a PostgreSQL: {e}")
            print("   Fallback a MemorySaver...")

    # Fallback: MemorySaver (no persistente)
    from langgraph.checkpoint.memory import MemorySaver

    print("⚠️  Usando MemorySaver (checkpoints NO persisten entre reinicios)")
    return MemorySaver()


def get_thread_config(ticket_id: int, department: Optional[str] = None) -> dict:
    """
    Genera configuración de thread con namespacing correcto.

    Args:
        ticket_id: ID del ticket RFP
        department: Departamento específico (opcional)

    Returns:
        Config dict para LangGraph

    Examples:
        >>> get_thread_config(123)
        {"configurable": {"thread_id": "rfp-123"}}

        >>> get_thread_config(123, "operaciones")
        {"configurable": {"thread_id": "rfp-123:operaciones"}}
    """
    if department:
        thread_id = f"rfp-{ticket_id}:{department}"
    else:
        thread_id = f"rfp-{ticket_id}"

    return {
        "configurable": {
            "thread_id": thread_id
        }
    }


def clear_checkpoint(ticket_id: int, department: Optional[str] = None):
    """
    Limpia checkpoints de un ticket específico.

    USAR CON PRECAUCIÓN: Esto borra el estado guardado.
    Solo para testing o cleanup manual.
    """
    checkpointer = get_checkpointer()
    config = get_thread_config(ticket_id, department)

    # MemorySaver no tiene método clear, pero PostgresSaver sí
    if hasattr(checkpointer, 'delete'):
        checkpointer.delete(config)
        print(f"🗑️  Checkpoint eliminado: {config['configurable']['thread_id']}")
    else:
        print("⚠️  MemorySaver no soporta eliminación manual")


# ============================================================
# HELPER: Verificar estado de checkpoint
# ============================================================

def inspect_checkpoint(ticket_id: int, department: Optional[str] = None):
    """
    Inspecciona el estado actual de un checkpoint.

    Útil para debugging y monitoring.
    """
    from data.pipelines.rfp_approval.graph import build_rfp_approval_graph

    checkpointer = get_checkpointer()
    config = get_thread_config(ticket_id, department)
    graph = build_rfp_approval_graph(checkpointer=checkpointer)

    state = graph.get_state(config)

    if not state:
        print(f"❌ No se encontró checkpoint para: {config['configurable']['thread_id']}")
        return None

    print(f"\n📊 Checkpoint Info:")
    print(f"   Thread ID: {config['configurable']['thread_id']}")
    print(f"   Next Node: {state.next}")
    print(f"   Values Keys: {list(state.values.keys())}")
    print(f"   Waiting for Human: {state.values.get('waiting_for_human', False)}")
    print(f"   Waiting for Arbitration: {state.values.get('waiting_for_arbitration', False)}")

    return state.values


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    # Test checkpointer connection
    print("\n🧪 Testing Checkpointer Configuration\n")

    checkpointer = get_checkpointer()
    print(f"\nCheckpointer type: {type(checkpointer).__name__}")

    # Test thread config generation
    config1 = get_thread_config(123)
    print(f"\nConfig sin departamento: {config1}")

    config2 = get_thread_config(123, "operaciones")
    print(f"Config con departamento: {config2}")

    print("\n✅ Checkpointer test completado")
