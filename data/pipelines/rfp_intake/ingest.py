"""
RFP Ingest - PDF to Markdown Conversion & Readability Metrics

RESPONSABILIDADES:
1. Conversión PDF → Markdown con MarkItDown
2. Cálculo de métricas de legibilidad con py-readability-metrics
3. Estimación de tokens y costo de procesamiento

CRÍTICO:
- Conversión ANTES de enviar a agentes (optimización de tokens)
- Métricas persisten en RFPMetadata para trazabilidad
"""

import os
from pathlib import Path
from typing import Dict, Any, Tuple
import tiktoken
from datetime import datetime

# MarkItDown para conversión PDF → Markdown
try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False
    print("⚠️  MarkItDown no disponible. Instalar: pip install markitdown")

# py-readability-metrics para análisis de legibilidad
try:
    from readability import Readability
    READABILITY_AVAILABLE = True
except ImportError:
    READABILITY_AVAILABLE = False
    print("⚠️  py-readability-metrics no disponible. Instalar: pip install py-readability-metrics")


# ============================================================
# PDF → MARKDOWN CONVERSION
# ============================================================

def convert_pdf_to_markdown(pdf_path: str, output_dir: str = "data/processed/rfp_markdown") -> Tuple[str, str]:
    """
    Convierte PDF a Markdown usando MarkItDown.

    Args:
        pdf_path: Ruta del PDF original
        output_dir: Directorio de salida para Markdown

    Returns:
        (markdown_path, markdown_content)

    Raises:
        FileNotFoundError: Si PDF no existe
        RuntimeError: Si MarkItDown falla
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

    if not MARKITDOWN_AVAILABLE:
        # Fallback: leer como texto plano (subóptimo)
        print("⚠️  MarkItDown no disponible, fallback a extracción básica")
        return _fallback_pdf_extraction(pdf_path, output_dir)

    # Crear directorio de salida
    os.makedirs(output_dir, exist_ok=True)

    # Convertir con MarkItDown
    md = MarkItDown()
    result = md.convert(pdf_path)

    markdown_content = result.text_content

    # Guardar Markdown
    pdf_name = Path(pdf_path).stem
    markdown_filename = f"{pdf_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    markdown_path = os.path.join(output_dir, markdown_filename)

    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"✅ PDF convertido a Markdown: {markdown_path}")
    print(f"   Longitud: {len(markdown_content)} caracteres")

    return markdown_path, markdown_content


def _fallback_pdf_extraction(pdf_path: str, output_dir: str) -> Tuple[str, str]:
    """
    Fallback: Extracción básica de PDF sin MarkItDown.

    Usa PyPDF2 como alternativa (menos óptimo que MarkItDown).
    """
    try:
        import PyPDF2
    except ImportError:
        raise RuntimeError("Ni MarkItDown ni PyPDF2 disponibles. Instalar: pip install PyPDF2")

    os.makedirs(output_dir, exist_ok=True)

    # Extraer texto con PyPDF2
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text_content = ""
        for page in reader.pages:
            text_content += page.extract_text() + "\n\n"

    # Guardar como Markdown simple
    pdf_name = Path(pdf_path).stem
    markdown_filename = f"{pdf_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    markdown_path = os.path.join(output_dir, markdown_filename)

    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(f"# {pdf_name}\n\n")
        f.write(text_content)

    print(f"⚠️  Fallback: PDF extraído con PyPDF2: {markdown_path}")

    return markdown_path, text_content


# ============================================================
# READABILITY METRICS
# ============================================================

def calculate_readability_metrics(text: str) -> Dict[str, float]:
    """
    Calcula métricas de legibilidad con py-readability-metrics.

    Args:
        text: Texto del documento (Markdown)

    Returns:
        Dict con métricas:
        - flesch_reading_ease: 0-100 (más alto = más fácil)
        - flesch_kincaid_grade: Nivel de grado escolar
        - gunning_fog: Años de educación necesarios
        - smog_index: Simple Measure of Gobbledygook
    """
    if not READABILITY_AVAILABLE:
        print("⚠️  py-readability-metrics no disponible, retornando métricas dummy")
        return {
            "flesch_reading_ease": 50.0,
            "flesch_kincaid_grade": 12.0,
            "gunning_fog": 14.0,
            "smog_index": 12.0
        }

    try:
        r = Readability(text)

        flesch = r.flesch()
        fk_grade = r.flesch_kincaid()
        gunning = r.gunning_fog()
        smog = r.smog()

        metrics = {
            "flesch_reading_ease": round(flesch.score, 2),
            "flesch_kincaid_grade": round(fk_grade.score, 2),
            "gunning_fog": round(gunning.score, 2),
            "smog_index": round(smog.score, 2)
        }

        print(f"📊 Métricas de legibilidad calculadas:")
        print(f"   Flesch Reading Ease: {metrics['flesch_reading_ease']}")
        print(f"   Flesch-Kincaid Grade: {metrics['flesch_kincaid_grade']}")
        print(f"   Gunning Fog: {metrics['gunning_fog']}")

        return metrics

    except Exception as e:
        print(f"⚠️  Error calculando métricas: {e}")
        return {
            "flesch_reading_ease": 0.0,
            "flesch_kincaid_grade": 0.0,
            "gunning_fog": 0.0,
            "smog_index": 0.0
        }


# ============================================================
# TOKEN & COST ESTIMATION
# ============================================================

def estimate_tokens_and_cost(text: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """
    Estima tokens y costo de procesamiento.

    Args:
        text: Texto del documento
        model: Modelo a usar (para cálculo de tokens)

    Returns:
        Dict con estimaciones:
        - estimated_tokens: Tokens estimados
        - estimated_cost_usd: Costo estimado en USD
        - model: Modelo usado para estimación
    """
    try:
        # Usar tiktoken para contar tokens
        encoding = tiktoken.encoding_for_model("gpt-4")
        tokens = len(encoding.encode(text))

        # Costos aproximados por 1M tokens (gpt-4o-mini)
        # Input: $0.15 / 1M tokens
        # Output: $0.60 / 1M tokens
        # Estimamos 5x procesamiento (input+output en múltiples agentes)
        cost_per_million = 0.15 + 0.60  # $0.75 total
        estimated_cost = (tokens * 5 / 1_000_000) * cost_per_million

        estimation = {
            "estimated_tokens": tokens,
            "estimated_cost_usd": round(estimated_cost, 4),
            "model": model
        }

        print(f"💰 Estimación de costo:")
        print(f"   Tokens: {tokens:,}")
        print(f"   Costo estimado: ${estimated_cost:.4f} USD")

        return estimation

    except Exception as e:
        print(f"⚠️  Error estimando tokens: {e}")
        return {
            "estimated_tokens": len(text) // 4,  # Aproximación simple
            "estimated_cost_usd": 0.01,
            "model": model
        }


# ============================================================
# PIPELINE COMPLETO
# ============================================================

def process_rfp_document(pdf_path: str) -> Dict[str, Any]:
    """
    Pipeline completo de ingesta de RFP.

    Args:
        pdf_path: Ruta del PDF original

    Returns:
        Dict con:
        - markdown_path: Ruta del Markdown generado
        - markdown_content: Contenido del Markdown
        - readability_metrics: Métricas de legibilidad
        - token_estimation: Estimación de tokens y costo
    """
    print(f"\n{'='*70}")
    print(f"📄 Procesando RFP: {Path(pdf_path).name}")
    print(f"{'='*70}\n")

    # 1. Conversión PDF → Markdown
    print("🔄 Paso 1: Conversión PDF → Markdown...")
    markdown_path, markdown_content = convert_pdf_to_markdown(pdf_path)

    # 2. Métricas de legibilidad
    print("\n📊 Paso 2: Cálculo de métricas de legibilidad...")
    readability_metrics = calculate_readability_metrics(markdown_content)

    # 3. Estimación de tokens y costo
    print("\n💰 Paso 3: Estimación de tokens y costo...")
    token_estimation = estimate_tokens_and_cost(markdown_content)

    print(f"\n{'='*70}")
    print("✅ Procesamiento de ingesta completado")
    print(f"{'='*70}\n")

    return {
        "markdown_path": markdown_path,
        "markdown_content": markdown_content,
        "readability_metrics": readability_metrics,
        "token_estimation": token_estimation
    }
