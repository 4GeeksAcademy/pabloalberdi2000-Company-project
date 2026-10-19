"""
Router de Incidencias Postventa
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.schemas.incident import AnalysisResponse
from app.services.incident_analyzer import analizar_csv


router = APIRouter(
    prefix="/incidents",
    tags=["incidents"]
)


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_incidents(
    file: UploadFile = File(...)
):
    """
    Analiza un archivo CSV de incidencias postventa.

    - **file**: Archivo CSV con incidencias (formato según BRIEFING_INCIDENCIAS.md)

    Retorna métricas completas:
    - Total de registros procesados
    - Registros válidos e inválidos
    - Métricas por categoría, estado y país
    - Índice de satisfacción promedio
    """
    # Validar tipo de archivo
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser un CSV (.csv)"
        )

    try:
        # Leer contenido del archivo
        contenido = await file.read()
        contenido_str = contenido.decode('utf-8')

        # Analizar CSV
        resultado = await analizar_csv(contenido_str)

        return resultado

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="El archivo debe estar codificado en UTF-8"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el archivo: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Endpoint de salud para verificar que el servicio está activo"""
    return {
        "status": "ok",
        "service": "Incidents Analysis API",
        "version": "1.0.0"
    }
