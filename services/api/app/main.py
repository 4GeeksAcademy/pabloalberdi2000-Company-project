from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import engine, Base
from .routers import candidates, incidents, auth, users, profiles, inventory, telemetry, telemetry_report, tasks, knowledge, knowledge_graph, chat_ws  # Inventory + Telemetry + Async Tasks + RAG + LangGraph + WebSocket Chat
from .middleware import TimingMiddleware  # Performance monitoring
from .cache import cache  # Cache manager

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize Inventory Database (Supabase or SQLite fallback)
print("🔄 Initializing Inventory Database...")
try:
    from .database_supabase import init_db as init_inventory_db, check_db_connection, engine as supabase_engine
    if supabase_engine and check_db_connection():
        init_inventory_db()
        print("✅ Inventory Database: Supabase")
    else:
        raise ImportError("Supabase not configured")
except (ImportError, Exception) as e:
    print(f"⚠️  Supabase not available, using SQLite for inventory")
    from .database_inventory_sqlite import init_inventory_db as init_sqlite_inventory
    init_sqlite_inventory()
    print("✅ Inventory Database: SQLite")

# Create FastAPI app
app = FastAPI(
    title="Brasaland API",
    description="Applicant Tracking System + Incidents Analysis for Brasaland",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Timing Middleware for performance monitoring
app.add_middleware(TimingMiddleware)


# ============================================================
# GLOBAL EXCEPTION HANDLER (Fase 4 - Incident Management)
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Manejador global de excepciones no controladas.

    Captura excepciones no manejadas y retorna error genérico sin exponer
    stack traces ni detalles internos de implementación.

    HTTPExceptions (400, 404, etc.) NO son capturadas aquí - FastAPI las maneja.
    """
    # Log para debugging (en producción usar logging.error)
    print(f"❌ Unhandled exception: {type(exc).__name__}: {str(exc)}")

    # Retornar error genérico 500
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."}
    )

# Include routers
app.include_router(candidates.router)
app.include_router(incidents.router)

# Hito 4: Authentication routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(profiles.router)

# Inventory System (Dual Database Architecture: TinyDB + Supabase)
app.include_router(inventory.router)

# Telemetry System (Event Ingestion + Analytics Report)
app.include_router(telemetry.router)
app.include_router(telemetry_report.router)

# Async Tasks System (Celery + Redis)
app.include_router(tasks.router)

# RAG Knowledge Base System
app.include_router(knowledge.router)

# RAG with LangGraph State Machine
app.include_router(knowledge_graph.router)

# WebSocket Chat with Token Streaming
app.include_router(chat_ws.router)


@app.get("/")
async def root():
    """Root endpoint - API health check"""
    return {
        "message": "Brasaland API",
        "version": "3.0.0",
        "status": "operational",
        "features": ["ats", "incidents-crud", "auth", "inventory", "telemetry", "telemetry-analytics", "async-tasks", "rag-knowledge-base", "rag-langgraph-state-machine"],
        "docs": "/docs",
        "architecture": "Dual Database (TinyDB: Auth | Supabase: Inventory)"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/cache/stats")
async def cache_stats():
    """
    Cache statistics endpoint.

    Returns:
        - hits: Número de aciertos de caché
        - misses: Número de fallos de caché
        - hit_rate: Porcentaje de aciertos
        - entries: Número de entradas en caché
        - total_requests: Total de requests a caché
    """
    return cache.stats()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
