"""
Evaluación de Sistema de Retrieval RAG

Evalúa la calidad del retrieval usando test-queries.json.

Métricas:
- Recall@3: % de queries donde el documento esperado está en top-3 resultados
- Average Similarity Score: Score promedio de retrieval
- Coverage: % de documentos cubiertos

Ejecutar:
    python data/eval/evaluate_retrieval.py
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.pipelines.rag_query import retrieve

# ============================================================
# CONFIGURACIÓN
# ============================================================

TEST_QUERIES_PATH = PROJECT_ROOT / "data" / "eval" / "test-queries.json"
K = 3  # Recall@3 (top-3 resultados)
MIN_SCORE = 0.5  # Score más bajo para no filtrar prematuramente

# ============================================================
# FUNCIONES DE EVALUACIÓN
# ============================================================

def load_test_queries() -> List[Dict[str, Any]]:
    """Carga test queries desde JSON."""
    with open(TEST_QUERIES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["queries"]


def evaluate_recall_at_k(queries: List[Dict[str, Any]], k: int = K) -> Dict[str, Any]:
    """
    Calcula Recall@K: % de queries donde el documento esperado está en top-K resultados.

    Args:
        queries: Lista de test queries con expected_documents
        k: Número de top resultados a considerar

    Returns:
        Dict con métricas de recall
    """
    total_queries = len(queries)
    successful_retrievals = 0
    all_scores = []

    results_detail = []

    print(f"\n🔍 Evaluando Recall@{k} con {total_queries} queries...\n")

    for query in queries:
        question = query["question"]
        expected_docs = query["expected_documents"]

        print(f"Q{query['id']}: {question}")
        print(f"  Documentos esperados: {expected_docs}")

        # Recuperar top-K chunks
        try:
            contexts = retrieve(question, k=k, min_score=MIN_SCORE)
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results_detail.append({
                "query_id": query["id"],
                "success": False,
                "error": str(e)
            })
            continue

        if not contexts:
            print(f"  ⚠️  Sin resultados (score < {MIN_SCORE})")
            results_detail.append({
                "query_id": query["id"],
                "success": False,
                "retrieved_docs": []
            })
            continue

        # Extraer documentos recuperados
        retrieved_docs = [ctx["source_document"] for ctx in contexts]
        retrieved_scores = [ctx["similarity_score"] for ctx in contexts]

        print(f"  Documentos recuperados: {retrieved_docs[:k]}")
        print(f"  Scores: {[f'{s:.3f}' for s in retrieved_scores[:k]]}")

        # Verificar si algún documento esperado está en top-K
        success = any(doc in retrieved_docs[:k] for doc in expected_docs)

        if success:
            successful_retrievals += 1
            print(f"  ✅ Éxito")
        else:
            print(f"  ❌ Fallo (documento esperado no en top-{k})")

        # Guardar scores
        all_scores.extend(retrieved_scores[:k])

        results_detail.append({
            "query_id": query["id"],
            "success": success,
            "retrieved_docs": retrieved_docs[:k],
            "scores": retrieved_scores[:k]
        })

        print()

    # Calcular métricas
    recall_at_k = successful_retrievals / total_queries if total_queries > 0 else 0
    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

    return {
        "recall_at_k": recall_at_k,
        "k": k,
        "successful_retrievals": successful_retrievals,
        "total_queries": total_queries,
        "average_similarity_score": avg_score,
        "results_detail": results_detail
    }


def calculate_document_coverage(results_detail: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calcula cobertura de documentos: % de documentos fuente recuperados al menos una vez.
    """
    all_retrieved_docs = set()

    for result in results_detail:
        if result.get("retrieved_docs"):
            all_retrieved_docs.update(result["retrieved_docs"])

    expected_docs = [
        "01-company-overview.md",
        "02-departments-operations.md",
        "03-technical-systems.md",
        "04-procedures-policies.md"
    ]

    coverage = len(all_retrieved_docs & set(expected_docs)) / len(expected_docs)

    return {
        "document_coverage": coverage,
        "retrieved_documents": sorted(all_retrieved_docs),
        "expected_documents": expected_docs
    }


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("🎯 Evaluación de Sistema de Retrieval - Brasaland RAG")
    print("=" * 70)

    # Cargar queries
    queries = load_test_queries()
    print(f"\n✅ Cargadas {len(queries)} test queries desde {TEST_QUERIES_PATH}")

    # Evaluar Recall@K
    recall_metrics = evaluate_recall_at_k(queries, k=K)

    # Evaluar cobertura de documentos
    coverage_metrics = calculate_document_coverage(recall_metrics["results_detail"])

    # Mostrar resultados consolidados
    print("=" * 70)
    print("📊 RESULTADOS DE EVALUACIÓN")
    print("=" * 70)

    print(f"\n🎯 Recall@{K}:")
    print(f"  - Recall: {recall_metrics['recall_at_k']:.2%}")
    print(f"  - Queries exitosas: {recall_metrics['successful_retrievals']}/{recall_metrics['total_queries']}")
    print(f"  - Similarity score promedio: {recall_metrics['average_similarity_score']:.3f}")

    print(f"\n📚 Cobertura de Documentos:")
    print(f"  - Cobertura: {coverage_metrics['document_coverage']:.2%}")
    print(f"  - Documentos recuperados: {len(coverage_metrics['retrieved_documents'])}/{len(coverage_metrics['expected_documents'])}")
    print(f"  - Documentos: {coverage_metrics['retrieved_documents']}")

    # Evaluación vs. target
    target_recall = 0.80
    print(f"\n🎖️  Evaluación vs. Target (Recall@{K} >= {target_recall:.0%}):")

    if recall_metrics['recall_at_k'] >= target_recall:
        print(f"  ✅ APROBADO ({recall_metrics['recall_at_k']:.2%} >= {target_recall:.0%})")
    else:
        print(f"  ❌ NO APROBADO ({recall_metrics['recall_at_k']:.2%} < {target_recall:.0%})")
        print(f"  Mejora requerida: +{(target_recall - recall_metrics['recall_at_k']):.2%}")

    print("\n" + "=" * 70)
    print("✅ Evaluación completada")
    print("=" * 70)

    # Guardar resultados
    output_path = PROJECT_ROOT / "data" / "eval" / "retrieval_eval_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "recall_metrics": {
                "recall_at_k": recall_metrics["recall_at_k"],
                "k": recall_metrics["k"],
                "successful_retrievals": recall_metrics["successful_retrievals"],
                "total_queries": recall_metrics["total_queries"],
                "average_similarity_score": recall_metrics["average_similarity_score"]
            },
            "coverage_metrics": coverage_metrics,
            "target_recall": target_recall,
            "approved": recall_metrics["recall_at_k"] >= target_recall
        }, f, indent=2, ensure_ascii=False)

    print(f"\n📝 Resultados guardados en: {output_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error durante evaluación: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
