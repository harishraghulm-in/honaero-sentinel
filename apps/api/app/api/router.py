from fastapi import APIRouter
from apps.api.app.api.routes import (
    health,
    projects,
    sources,
    analysis,
    scope,
    stubs,
    tests,
    executions,
    traceability,
    evidence,
    requirements,
    config,
    ai,
    prioritization,
    reports,
)

# Root probes
health_router = health.router

# Public Version 1 API router
api_v1_router = APIRouter()

api_v1_router.include_router(projects.router)
api_v1_router.include_router(sources.router)
api_v1_router.include_router(sources.file_tree_router)
api_v1_router.include_router(requirements.router)
api_v1_router.include_router(analysis.router)
api_v1_router.include_router(scope.router)
api_v1_router.include_router(stubs.router)
api_v1_router.include_router(tests.router)
api_v1_router.include_router(executions.router)
api_v1_router.include_router(traceability.router)
api_v1_router.include_router(evidence.router)
api_v1_router.include_router(evidence.project_evidence_router)
api_v1_router.include_router(config.router)
api_v1_router.include_router(ai.router)
api_v1_router.include_router(prioritization.router)
api_v1_router.include_router(reports.router)


