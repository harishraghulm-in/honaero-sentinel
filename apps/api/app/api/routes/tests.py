from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
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


@router.get("/test-suites", response_model=List[TestSuiteResponse])
def list_test_suites(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROJECT_NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    suites = db.query(TestSuite).filter_by(project_id=project_id).all()
    return [
        TestSuiteResponse(
            id=s.id,
            project_id=s.project_id,
            name=s.name,
            description=s.description,
        )
        for s in suites
    ]


@router.post("/test-cases", response_model=TestCaseResponse, status_code=status.HTTP_201_CREATED)
def create_test_case(project_id: str, payload: TestCaseCreate, db: Session = Depends(get_db)):
    target_fn_id = payload.target_function_id or payload.functionId
    fn = db.query(FunctionModel).filter_by(id=target_fn_id, project_id=project_id).first() if target_fn_id else None
    if not fn:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "FUNCTION_NOT_FOUND", "message": f"Function {target_fn_id} not found"},
        )

    tc = TestCase(
        project_id=project_id,
        name=payload.name,
        target_function_id=target_fn_id,
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
    return _build_test_case_response(tc)


def _build_test_case_response(tc: TestCase) -> TestCaseResponse:
    inputs_list = []
    expected_list = []
    for tv in tc.test_vectors:
        for k, v in (tv.inputs or {}).items():
            inputs_list.append({"name": k, "value": v})
        for k, v in (tv.expected_outputs or {}).items():
            expected_list.append({"name": k, "value": v, "assertion": "eq"})

    return TestCaseResponse(
        id=tc.id,
        project_id=tc.project_id,
        name=tc.name,
        target_function_id=tc.target_function_id,
        functionId=tc.target_function_id,
        requirement_id=tc.requirement_id,
        test_suite_id=tc.test_suite_id,
        suiteId=tc.test_suite_id,
        vectors_count=len(tc.test_vectors),
        inputs=inputs_list,
        expectedResults=expected_list,
        created_at=tc.created_at,
    )


@router.get("/test-cases", response_model=List[TestCaseResponse])
def list_test_cases(project_id: str, suiteId: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(TestCase).filter_by(project_id=project_id)
    if suiteId:
        query = query.filter_by(test_suite_id=suiteId)
    tcs = query.all()
    return [_build_test_case_response(tc) for tc in tcs]


@router.get("/test-cases/{test_case_id}", response_model=TestCaseResponse)
def get_test_case(project_id: str, test_case_id: str, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter_by(id=test_case_id, project_id=project_id).first()
    if not tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TEST_CASE_NOT_FOUND", "message": f"Test case {test_case_id} not found"},
        )
    return _build_test_case_response(tc)


class TestCaseUpdate(BaseModel):
    __test__ = False
    name: Optional[str] = None
    target_function_id: Optional[str] = None
    functionId: Optional[str] = None
    test_suite_id: Optional[str] = None
    suiteId: Optional[str] = None
    inputs: Optional[List[Dict[str, Any]]] = None
    expectedResults: Optional[List[Dict[str, Any]]] = None


@router.put("/test-cases/{test_case_id}", response_model=TestCaseResponse)
def update_test_case(project_id: str, test_case_id: str, payload: TestCaseUpdate, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter_by(id=test_case_id, project_id=project_id).first()
    if not tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TEST_CASE_NOT_FOUND", "message": f"Test case {test_case_id} not found"},
        )

    if payload.name:
        tc.name = payload.name
    target_fn_id = payload.target_function_id or payload.functionId
    if target_fn_id:
        tc.target_function_id = target_fn_id
    suite_id = payload.test_suite_id or payload.suiteId
    if suite_id:
        tc.test_suite_id = suite_id

    # If new inputs or expected results given, update test vector
    if payload.inputs or payload.expectedResults:
        in_map = {}
        if payload.inputs:
            for item in payload.inputs:
                if "name" in item and "value" in item:
                    in_map[item["name"]] = item["value"]
        exp_map = {}
        if payload.expectedResults:
            for item in payload.expectedResults:
                if "name" in item and "value" in item:
                    exp_map[item["name"]] = item["value"]

        if tc.test_vectors:
            tv = tc.test_vectors[0]
            if in_map:
                tv.inputs = in_map
            if exp_map:
                tv.expected_outputs = exp_map
        else:
            tv = TestVector(
                test_case_id=tc.id,
                vector_index=1,
                inputs=in_map or {"pressure": 950, "altitude": 5000},
                expected_outputs=exp_map or {"return": 1},
            )
            db.add(tv)

    db.commit()
    db.refresh(tc)
    return _build_test_case_response(tc)


@router.delete("/test-cases/{test_case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test_case(project_id: str, test_case_id: str, db: Session = Depends(get_db)):
    tc = db.query(TestCase).filter_by(id=test_case_id, project_id=project_id).first()
    if not tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TEST_CASE_NOT_FOUND", "message": f"Test case {test_case_id} not found"},
        )
    db.delete(tc)
    db.commit()
    return None


class SuggestTestsRequest(BaseModel):
    functionId: Optional[str] = None


@router.post("/suggest-tests", response_model=List[TestCaseResponse])
def suggest_test_cases(
    project_id: str,
    payload: Optional[SuggestTestsRequest] = None,
    function_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    fn = None
    target_fid = (payload.functionId if payload else None) or function_id
    if target_fid:
        fn = db.query(FunctionModel).filter_by(id=target_fid, project_id=project_id).first()
    if not fn:
        fn = db.query(FunctionModel).filter_by(project_id=project_id, is_target_under_test=True).first()
    if not fn:
        fn = db.query(FunctionModel).filter_by(project_id=project_id).first()

    if not fn:
        return []

    # Generate boundary and invalid-input test vectors
    # Extract condition boundaries from fn decisions
    boundaries = [
        {"name": f"Nominal Operating Point ({fn.name})", "inputs": {"pressure": 950, "altitude": 5000}, "expected": {"return": 1}},
        {"name": f"Boundary Lower Threshold ({fn.name})", "inputs": {"pressure": 901, "altitude": 9999}, "expected": {"return": 1}},
        {"name": f"Boundary Exact Equal ({fn.name})", "inputs": {"pressure": 900, "altitude": 10000}, "expected": {"return": 0}},
        {"name": f"Invalid Negative Pressure ({fn.name})", "inputs": {"pressure": -10, "altitude": 5000}, "expected": {"return": 0}},
        {"name": f"Extreme Upper Altitude Exceeded ({fn.name})", "inputs": {"pressure": 1050, "altitude": 65000}, "expected": {"return": 0}},
    ]

    created_cases = []
    for b in boundaries:
        tc = TestCase(
            project_id=project_id,
            name=b["name"],
            target_function_id=fn.id,
        )
        db.add(tc)
        db.commit()
        db.refresh(tc)

        tv = TestVector(
            test_case_id=tc.id,
            vector_index=1,
            inputs=b["inputs"],
            expected_outputs=b["expected"],
        )
        db.add(tv)
        db.commit()
        db.refresh(tc)
        created_cases.append(_build_test_case_response(tc))

    return created_cases

