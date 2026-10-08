from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.app.infrastructure.database.session import get_db
from apps.api.app.domain.models import Project, TestSuite, TestCase, TestVector, FunctionModel
from apps.api.app.schemas.sentinel_api import (
    TestSuiteCreate,
    TestSuiteResponse,
    TestCaseCreate,
    TestCaseResponse,
)

router = APIRouter(prefix="/projects/{project_id}", tags=["Test Authoring"])


@router.post("/test-suites", response_model=TestSuiteResponse, status_code=status.HTTP_201_CREATED)
def create_test_suite(project_id: str, payload: TestSuiteCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    suite = TestSuite(project_id=project_id, name=payload.name, description=payload.description)
    db.add(suite)
    db.commit()
    db.refresh(suite)
    return suite


@router.post("/test-cases", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
def create_test_case(project_id: str, payload: TestCaseCreate, db: Session = Depends(get_db)):
    fn = db.query(FunctionModel).filter_by(id=payload.target_function_id, project_id=project_id).first()
    if not fn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "FUNCTION_NOT_FOUND", "message": f"Function {payload.target_function_id} not found"},
        )

    tc = TestCase(
        project_id=project_id,
        name=payload.name,
        target_function_id=payload.target_function_id,
        requirement_id=payload.requirement_id,
        test_suite_id=payload.test_suite_id,
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)

    for vec in payload.vectors:
        tv = TestVector(
            test_case_id=tc.id,
            vector_index=vec.vector_index,
            inputs=vec.inputs,
            expected_outputs=vec.expected_outputs,
        )
        db.add(tv)

    db.commit()
    db.refresh(tc)

    return TestCaseResponse(
        id=tc.id,
        project_id=tc.project_id,
        name=tc.name,
        target_function_id=tc.target_function_id,
        requirement_id=tc.requirement_id,
        vectors_count=len(tc.test_vectors),
        created_at=tc.created_at,
    )


@router.get("/test-cases", response_model=List[TestCaseResponse])
def list_test_cases(project_id: str, db: Session = Depends(get_db)):
    tcs = db.query(TestCase).filter_by(project_id=project_id).all()
    return [
        TestCaseResponse(
            id=tc.id,
            project_id=tc.project_id,
            name=tc.name,
            target_function_id=tc.target_function_id,
            requirement_id=tc.requirement_id,
            vectors_count=len(tc.test_vectors),
            created_at=tc.created_at,
        )
        for tc in tcs
    ]

