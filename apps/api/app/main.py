from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from apps.api.app.core.config import get_settings
from apps.api.app.core.logging import setup_logging, get_logger
from apps.api.app.api.router import api_v1_router, health_router
from apps.api.app.infrastructure.database.base import Base
from apps.api.app.infrastructure.database.session import engine

settings = get_settings()
setup_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)
logger = get_logger("sentinel.main")


from sqlalchemy import inspect, text


def sync_sqlite_schema(db_engine):
    """
    Safely synchronizes the SQLite database schema by adding any missing columns
    defined on SQLAlchemy models to existing tables without data loss.
    """
    if db_engine.dialect.name != "sqlite":
        return
    with db_engine.connect() as conn:
        inspector = inspect(db_engine)
        for table_name in Base.metadata.tables.keys():
            if not inspector.has_table(table_name):
                continue
            existing_cols = {c["name"] for c in inspector.get_columns(table_name)}
            table = Base.metadata.tables[table_name]
            for col in table.columns:
                if col.name not in existing_cols:
                    col_type = col.type.compile(db_engine.dialect)
                    default_clause = ""
                    if col.server_default is not None and hasattr(col.server_default, "arg"):
                        default_clause = f" DEFAULT {col.server_default.arg.text}"
                    elif col.default is not None and getattr(col.default, "is_scalar", False):
                        val = col.default.arg
                        if hasattr(val, "value"):
                            val = val.value
                        if isinstance(val, bool):
                            default_clause = f" DEFAULT {1 if val else 0}"
                        elif isinstance(val, (int, float)):
                            default_clause = f" DEFAULT {val}"
                        elif isinstance(val, str):
                            escaped = val.replace("'", "''")
                            default_clause = f" DEFAULT '{escaped}'"
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}{default_clause}"))
                    logger.info("Synchronized SQLite column: %s.%s (%s%s)", table_name, col.name, col_type, default_clause)
        conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing HonAero Sentinel Verification Studio Backend...")
    # Initialize base tables if using local development
    Base.metadata.create_all(bind=engine)
    sync_sqlite_schema(engine)
    logger.info("Database schemas verified.")
    yield
    logger.info("HonAero Sentinel Backend shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="HonAero Sentinel — Smart Verification Studio (DO-178C Verification Pipeline Backend)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS configuration for subsequent React+TS integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        code = detail.get("code", "HTTP_ERROR")
        msg = detail.get("message", str(detail))
        details = detail.get("details", {})
    else:
        code = "HTTP_ERROR"
        msg = str(detail)
        details = {}

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": msg,
                "details": details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request payload validation failed",
                "details": {"errors": exc.errors()},
            }
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception during request {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred in the verification studio pipeline",
                "details": {},
            }
        },
    )


# Root health and readiness probes
app.include_router(health_router)

# Versioned API routes
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

