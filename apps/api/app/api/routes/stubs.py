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

