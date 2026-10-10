from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.domain.models import Project, Dependency, StubConfiguration
from apps.api.app.domain.enums import DependencyMode
from apps.api.app.schemas.sentinel_api import (
    DependencyDTO,
    StubCreate,
    StubUpdate,
    StubResponse,
)

router = APIRouter(prefix="/projects/{project_id}", tags=["Dependencies & Stubs"])


@router.get("/dependencies", response_model=List[DependencyDTO])
def list_dependencies(project_id: str, db: Session = Depends(get_db)):
    deps = db.query(Dependency).filter_by(project_id=project_id).all()
    return [
        DependencyDTO(
            id=d.id,
            name=d.name,
            type=d.dep_type.value,
            return_type=d.return_type,
            mode=d.mode,
        )
        for d in deps
    ]


@router.post("/stubs", response_model=StubResponse, status_code=status.HTTP_201_CREATED)
def configure_stub(project_id: str, payload: StubCreate, db: Session = Depends(get_db)):
    dep = db.query(Dependency).filter_by(id=payload.dependency_id, project_id=project_id).first()
    if not dep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DEPENDENCY_NOT_FOUND", "message": f"Dependency {payload.dependency_id} not found"},
        )

    # Set dependency mode to STUB
    dep.mode = DependencyMode.STUB

    existing_stub = db.query(StubConfiguration).filter_by(dependency_id=dep.id).first()
    if existing_stub:
        existing_stub.return_values = payload.return_values
        existing_stub.output_params = payload.output_params
        existing_stub.expected_call_count = payload.expected_call_count
        existing_stub.call_order = payload.call_order
        existing_stub.custom_c_body = payload.custom_c_body
        stub_record = existing_stub
    else:
        stub_record = StubConfiguration(
            project_id=project_id,
            dependency_id=dep.id,
            function_name=payload.function_name,
            mode=DependencyMode.STUB,
            return_values=payload.return_values,
            output_params=payload.output_params,
            expected_call_count=payload.expected_call_count,
            call_order=payload.call_order,
            custom_c_body=payload.custom_c_body,
        )
        db.add(stub_record)

    db.commit()
    db.refresh(stub_record)
    return stub_record


@router.put("/stubs/{stub_id}", response_model=StubResponse)
def update_stub(project_id: str, stub_id: str, payload: StubUpdate, db: Session = Depends(get_db)):
    stub = db.query(StubConfiguration).filter_by(id=stub_id, project_id=project_id).first()
    if not stub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "STUB_NOT_FOUND", "message": f"Stub {stub_id} not found"},
        )

    if payload.mode is not None:
        stub.mode = payload.mode
        stub.dependency.mode = payload.mode
    if payload.return_values is not None:
        stub.return_values = payload.return_values
    if payload.output_params is not None:
        stub.output_params = payload.output_params
    if payload.expected_call_count is not None:
        stub.expected_call_count = payload.expected_call_count
    if payload.call_order is not None:
        stub.call_order = payload.call_order
    if payload.custom_c_body is not None:
        stub.custom_c_body = payload.custom_c_body

    db.commit()
    db.refresh(stub)
    return stub


@router.get("/stubs", response_model=List[StubResponse])
def list_stubs(project_id: str, db: Session = Depends(get_db)):
    return db.query(StubConfiguration).filter_by(project_id=project_id).all()


@router.delete("/stubs/{stub_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stub(project_id: str, stub_id: str, db: Session = Depends(get_db)):
    stub = db.query(StubConfiguration).filter_by(id=stub_id, project_id=project_id).first()
    if not stub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "STUB_NOT_FOUND", "message": f"Stub {stub_id} not found"},
        )
    if stub.dependency:
        stub.dependency.mode = DependencyMode.REAL
    db.delete(stub)
    db.commit()
    return None


@router.post("/dependencies", response_model=DependencyDTO, status_code=status.HTTP_201_CREATED)
def create_dependency(project_id: str, payload: dict, db: Session = Depends(get_db)):
    dep = Dependency(
        project_id=project_id,
        name=payload.get("name", "unnamed_dep"),
        return_type=payload.get("return_type") or payload.get("returnType") or "int",
        mode=DependencyMode.STUB if payload.get("isResolved") is False else DependencyMode.REAL,
    )
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return DependencyDTO(
        id=dep.id,
        name=dep.name,
        type=dep.dep_type.value if hasattr(dep.dep_type, "value") else str(dep.dep_type),
        return_type=dep.return_type,
        mode=dep.mode,
        file="",
        isResolved=True,
    )


@router.put("/dependencies/{dep_id}", response_model=DependencyDTO)
def update_dependency(project_id: str, dep_id: str, payload: dict, db: Session = Depends(get_db)):
    dep = db.query(Dependency).filter_by(id=dep_id, project_id=project_id).first()
    if not dep:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DEPENDENCY_NOT_FOUND", "message": f"Dependency {dep_id} not found"},
        )
    if "name" in payload:
        dep.name = payload["name"]
    if "mode" in payload:
        dep.mode = DependencyMode(payload["mode"])
    db.commit()
    db.refresh(dep)
    return DependencyDTO(
        id=dep.id,
        name=dep.name,
        type=dep.dep_type.value if hasattr(dep.dep_type, "value") else str(dep.dep_type),
        return_type=dep.return_type,
        mode=dep.mode,
        file="",
        isResolved=True,
    )

