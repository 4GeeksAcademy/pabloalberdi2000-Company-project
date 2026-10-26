from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import engine, Base
from .routers import candidates, incidents, auth, users, profiles  # Hito 4: Nuevos routers

# Create database tables
Base.metadata.create_all(bind=engine)

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


@app.get("/")
async def root():
    """Root endpoint - API health check"""
    return {
        "message": "Brasaland API",
        "version": "2.0.0",
        "status": "operational",
        "features": ["ats", "incidents-crud", "auth"],
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
