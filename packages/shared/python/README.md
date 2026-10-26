# Brasaland Shared - Paquete Transversal

Paquete Python compartido para validaciones y lógica de dominio reutilizable entre servicios del monorepo.

## Estructura

```
brasaland_shared/
├── __init__.py       # Exports públicos
├── constants.py      # Constantes del dominio (categorías, estados, locales)
└── validators.py     # Validaciones de incidencias según BRIEFING.md
```

## Instalación

Desde la raíz del monorepo:

```bash
# Instalar como paquete editable (development)
pip install -e packages/shared/python
```

Para el backend FastAPI (ya incluido en `requirements.txt`):

```bash
cd services/api
source venv/bin/activate
pip install -r requirements.txt  # Instala -e ../../packages/shared/python
```

## Uso

### Script CLI (scripts/analyze.py, scripts/seed_incidents.py)

```python
from brasaland_shared import validar_registro, CATEGORIAS_PERMITIDAS

# Validar registro CSV
es_valido, razon = validar_registro(csv_row)

if not es_valido:
    print(f"Registro inválido: {razon}")
```

### API Backend (services/api)

```python
from brasaland_shared import (
    validar_registro,
    calcular_satisfaccion_promedio,
    ESTADOS_PERMITIDOS
)

# En service layer o routers
resultado = validar_registro(data_dict)
```

## Módulos

### `validators.py`

Funciones de validación:

- `validar_registro(registro: dict) -> Tuple[bool, str]`: Validación completa según BRIEFING
- `validar_fecha(fecha_str: str) -> bool`: Formato YYYY-MM-DD
- `validar_satisfaccion(satisfaccion_str: str) -> bool`: Rango 1-5
- `calcular_satisfaccion_promedio(registros: List[dict]) -> float`: Promedio de casos cerrados
- `obtener_evaluacion_satisfaccion(promedio: float) -> str`: Evaluación cualitativa

### `constants.py`

Constantes del dominio:

- `CATEGORIAS_PERMITIDAS`: 6 categorías de incidencias
- `ESTADOS_PERMITIDOS`: 4 estados (abierto, en_proceso, cerrado, descartado)
- `PAISES_PERMITIDOS`: CO, US
- `LOCALES_PERMITIDOS`: 14 sedes (10 Colombia + 4 Florida)
- `CAMPOS_OBLIGATORIOS`: 7 campos CSV requeridos

## Testing

```bash
cd packages/shared/python
python -m pytest tests/  # (cuando existan tests)
```

## Versionamiento

- **1.0.0**: Release inicial con validaciones de incidencias

## Contribuir

Al modificar este paquete:

1. Actualizar versión en `setup.py` y `__init__.py`
2. Ejecutar tests (cuando existan)
3. Reinstalar en servicios: `pip install -e packages/shared/python --force-reinstall`
4. Verificar que scripts CLI y API funcionan correctamente
