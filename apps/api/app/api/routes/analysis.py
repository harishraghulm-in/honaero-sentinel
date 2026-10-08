from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.infrastructure.parsers.c_ast_parser import ClangAstSourceParser
from apps.api.app.domain.models import Project, SourceFile, FunctionModel, Dependency
from apps.api.app.domain.enums import DependencyMode, DependencyType
from apps.api.app.schemas.sentinel_api import (
    AnalysisResponse,
    FunctionDTO,
    ParameterDTO,
    DecisionDTO,
    ConditionDTO,
    DependencyDTO,
)

router = APIRouter(prefix="/projects/{project_id}", tags=["Analysis"])
parser = ClangAstSourceParser()


@router.post("/analyze", response_model=AnalysisResponse)
def run_source_analysis(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} does not exist"},
        )

    sources = db.query(SourceFile).filter_by(project_id=project_id).all()
    if not sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "NO_SOURCES", "message": "No source files imported to analyze"},
        )

    # Clear existing analyzed functions & dependencies for fresh run
    db.query(FunctionModel).filter_by(project_id=project_id).delete()
    db.query(Dependency).filter_by(project_id=project_id).delete()
    db.commit()

    all_fn_dtos = []
    all_dep_dtos = []

    for src in sources:
        parsed_result = parser.parse_source(src.filename, src.content)

        for fn in parsed_result.functions:
            fn_model = FunctionModel(
                project_id=project_id,
                source_file_id=src.id,
                name=fn.name,
                return_type=fn.return_type,
                parameters=[p.model_dump() for p in fn.parameters],
                local_variables=fn.local_variables,
                decisions=[d.model_dump() for d in fn.decisions],
                is_target_under_test=src.is_target,
            )
            db.add(fn_model)
            db.commit()
            db.refresh(fn_model)

            fn_dto = FunctionDTO(
                id=fn_model.id,
                name=fn.name,
                return_type=fn.return_type,
                parameters=[ParameterDTO(**p.model_dump()) for p in fn.parameters],
                decisions=[DecisionDTO(**d.model_dump()) for d in fn.decisions],
                is_target_under_test=src.is_target,
            )
            all_fn_dtos.append(fn_dto)

            # Store dependencies
            for dep in fn.dependencies:
                dep_model = Dependency(
                    project_id=project_id,
                    caller_function_id=fn_model.id,
                    name=dep.name,
                    dep_type=DependencyType.EXTERNAL_FUNCTION,
                    return_type=dep.return_type,
                    parameters=[p.model_dump() for p in dep.parameters],
                    mode=DependencyMode.REAL,
                )
                db.add(dep_model)
                db.commit()
                db.refresh(dep_model)

                all_dep_dtos.append(DependencyDTO(
                    id=dep_model.id,
                    name=dep.name,
                    type=dep_model.dep_type.value,
                    return_type=dep_model.return_type,
                    mode=dep_model.mode,
                ))

    return AnalysisResponse(
        project_id=project_id,
        total_sources=len(sources),
        functions=all_fn_dtos,
        dependencies=all_dep_dtos,
    )


@router.get("/analysis", response_model=AnalysisResponse)
def get_source_analysis(project_id: str, db: Session = Depends(get_db)):
    funcs = db.query(FunctionModel).filter_by(project_id=project_id).all()
    deps = db.query(Dependency).filter_by(project_id=project_id).all()
    sources_count = db.query(SourceFile).filter_by(project_id=project_id).count()

    fn_dtos = [
        FunctionDTO(
            id=f.id,
            name=f.name,
            return_type=f.return_type,
            parameters=[ParameterDTO(**p) for p in f.parameters],
            decisions=[DecisionDTO(**d) for d in f.decisions],
            is_target_under_test=f.is_target_under_test,
        )
        for f in funcs
    ]
    dep_dtos = [
        DependencyDTO(
            id=d.id,
            name=d.name,
            type=d.dep_type.value,
            return_type=d.return_type,
            mode=d.mode,
        )
        for d in deps
    ]

    return AnalysisResponse(
        project_id=project_id,
        total_sources=sources_count,
        functions=fn_dtos,
        dependencies=dep_dtos,
    )

