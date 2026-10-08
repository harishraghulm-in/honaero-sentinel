import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String, Text, Boolean, Integer, Float, ForeignKey, DateTime, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apps.api.app.infrastructure.database.base import Base
from apps.api.app.domain.enums import (
    DependencyMode,
    DependencyType,
    HookStage,
    ExecutionStatus,
    EvidenceFreshness,
    RequirementType,
)


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    source_files: Mapped[List["SourceFile"]] = relationship("SourceFile", back_populates="project", cascade="all, delete-orphan")
    build_configurations: Mapped[List["BuildConfiguration"]] = relationship("BuildConfiguration", back_populates="project", cascade="all, delete-orphan")
    requirements: Mapped[List["Requirement"]] = relationship("Requirement", back_populates="project", cascade="all, delete-orphan")
    functions: Mapped[List["FunctionModel"]] = relationship("FunctionModel", back_populates="project", cascade="all, delete-orphan")
    dependencies: Mapped[List["Dependency"]] = relationship("Dependency", back_populates="project", cascade="all, delete-orphan")
    stubs: Mapped[List["StubConfiguration"]] = relationship("StubConfiguration", back_populates="project", cascade="all, delete-orphan")
    user_hooks: Mapped[List["UserHook"]] = relationship("UserHook", back_populates="project", cascade="all, delete-orphan")
    test_suites: Mapped[List["TestSuite"]] = relationship("TestSuite", back_populates="project", cascade="all, delete-orphan")
    test_cases: Mapped[List["TestCase"]] = relationship("TestCase", back_populates="project", cascade="all, delete-orphan")
    executions: Mapped[List["Execution"]] = relationship("Execution", back_populates="project", cascade="all, delete-orphan")
    evidence_records: Mapped[List["EvidenceRecord"]] = relationship("EvidenceRecord", back_populates="project", cascade="all, delete-orphan")


class SourceFile(Base):
    __tablename__ = "source_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    filepath: Mapped[str] = mapped_column(String(1024), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    is_target: Mapped[bool] = mapped_column(Boolean, default=False)
    is_environment: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    project: Mapped["Project"] = relationship("Project", back_populates="source_files")
    functions: Mapped[List["FunctionModel"]] = relationship("FunctionModel", back_populates="source_file", cascade="all, delete-orphan")


class BuildConfiguration(Base):
    __tablename__ = "build_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    compiler: Mapped[str] = mapped_column(String(50), default="gcc")
    compiler_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    compiler_flags: Mapped[Optional[str]] = mapped_column(Text, default="-O0 -g --coverage -fprofile-arcs -ftest-coverage")
    include_dirs: Mapped[Optional[str]] = mapped_column(Text, default=".")
    defines: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    project: Mapped["Project"] = relationship("Project", back_populates="build_configurations")


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    identifier: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., HLR-001
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Text] = mapped_column(Text, nullable=False)
    req_type: Mapped[RequirementType] = mapped_column(SQLEnum(RequirementType), default=RequirementType.HLR)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    project: Mapped["Project"] = relationship("Project", back_populates="requirements")
    test_cases: Mapped[List["TestCase"]] = relationship("TestCase", back_populates="requirement")


class FunctionModel(Base):
    __tablename__ = "functions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    source_file_id: Mapped[str] = mapped_column(String(36), ForeignKey("source_files.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    return_type: Mapped[str] = mapped_column(String(100), default="void")
    parameters: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    local_variables: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    decisions: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    is_target_under_test: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    project: Mapped["Project"] = relationship("Project", back_populates="functions")
    source_file: Mapped["SourceFile"] = relationship("SourceFile", back_populates="functions")
    dependencies: Mapped[List["Dependency"]] = relationship("Dependency", back_populates="caller_function")
    test_cases: Mapped[List["TestCase"]] = relationship("TestCase", back_populates="target_function")


class Dependency(Base):
    __tablename__ = "dependencies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    caller_function_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("functions.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dep_type: Mapped[DependencyType] = mapped_column(SQLEnum(DependencyType), default=DependencyType.EXTERNAL_FUNCTION)
    return_type: Mapped[str] = mapped_column(String(100), default="void")
    parameters: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    mode: Mapped[DependencyMode] = mapped_column(SQLEnum(DependencyMode), default=DependencyMode.REAL)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    project: Mapped["Project"] = relationship("Project", back_populates="dependencies")
    caller_function: Mapped[Optional["FunctionModel"]] = relationship("FunctionModel", back_populates="dependencies")
    stub_config: Mapped[Optional["StubConfiguration"]] = relationship("StubConfiguration", back_populates="dependency", uselist=False)


class StubConfiguration(Base):
    __tablename__ = "stub_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    dependency_id: Mapped[str] = mapped_column(String(36), ForeignKey("dependencies.id", ondelete="CASCADE"), nullable=False, unique=True)
    function_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mode: Mapped[DependencyMode] = mapped_column(SQLEnum(DependencyMode), default=DependencyMode.STUB)
    return_values: Mapped[List[Any]] = mapped_column(JSON, default=list)
    output_params: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    expected_call_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    call_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    custom_c_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    project: Mapped["Project"] = relationship("Project", back_populates="stubs")
    dependency: Mapped["Dependency"] = relationship("Dependency", back_populates="stub_config")


class UserHook(Base):
    __tablename__ = "user_hooks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    stage: Mapped[HookStage] = mapped_column(SQLEnum(HookStage), nullable=False)
    code_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    project: Mapped["Project"] = relationship("Project", back_populates="user_hooks")


class TestSuite(Base):
    __tablename__ = "test_suites"
    __test__ = False

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    project: Mapped["Project"] = relationship("Project", back_populates="test_suites")
    test_cases: Mapped[List["TestCase"]] = relationship("TestCase", back_populates="test_suite", cascade="all, delete-orphan")


class TestCase(Base):
    __tablename__ = "test_cases"
    __test__ = False

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    test_suite_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("test_suites.id", ondelete="SET NULL"), nullable=True)
    target_function_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("functions.id", ondelete="SET NULL"), nullable=True)
    requirement_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("requirements.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    project: Mapped["Project"] = relationship("Project", back_populates="test_cases")
    test_suite: Mapped[Optional["TestSuite"]] = relationship("TestSuite", back_populates="test_cases")
    target_function: Mapped[Optional["FunctionModel"]] = relationship("FunctionModel", back_populates="test_cases")
    requirement: Mapped[Optional["Requirement"]] = relationship("Requirement", back_populates="test_cases")
    test_vectors: Mapped[List["TestVector"]] = relationship("TestVector", back_populates="test_case", cascade="all, delete-orphan")
    executions: Mapped[List["Execution"]] = relationship("Execution", back_populates="test_case")


class TestVector(Base):
    __tablename__ = "test_vectors"
    __test__ = False

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    test_case_id: Mapped[str] = mapped_column(String(36), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    vector_index: Mapped[int] = mapped_column(Integer, default=0)
    inputs: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    expected_outputs: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    test_case: Mapped["TestCase"] = relationship("TestCase", back_populates="test_vectors")


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    test_case_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[ExecutionStatus] = mapped_column(SQLEnum(ExecutionStatus), default=ExecutionStatus.QUEUED)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    source_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    stub_checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    vector_checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    results_summary: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    project: Mapped["Project"] = relationship("Project", back_populates="executions")
    test_case: Mapped[Optional["TestCase"]] = relationship("TestCase", back_populates="executions")
    artifacts: Mapped[List["ExecutionArtifact"]] = relationship("ExecutionArtifact", back_populates="execution", cascade="all, delete-orphan")
    coverage: Mapped[Optional["CoverageResult"]] = relationship("CoverageResult", back_populates="execution", uselist=False, cascade="all, delete-orphan")
    mcdc: Mapped[Optional["MCDCResult"]] = relationship("MCDCResult", back_populates="execution", uselist=False, cascade="all, delete-orphan")
    evidence: Mapped[Optional["EvidenceRecord"]] = relationship("EvidenceRecord", back_populates="execution", uselist=False)


class ExecutionArtifact(Base):
    __tablename__ = "execution_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("executions.id", ondelete="CASCADE"), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False)  # binary, gcda, gcno, stdout, stderr
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    execution: Mapped["Execution"] = relationship("Execution", back_populates="artifacts")


class CoverageResult(Base):
    __tablename__ = "coverage_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, unique=True)
    statement_coverage_pct: Mapped[float] = mapped_column(Float, default=0.0)
    branch_coverage_pct: Mapped[float] = mapped_column(Float, default=0.0)
    function_coverage_pct: Mapped[float] = mapped_column(Float, default=0.0)
    line_coverage_pct: Mapped[float] = mapped_column(Float, default=0.0)
    raw_coverage_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    execution: Mapped["Execution"] = relationship("Execution", back_populates="coverage")


class MCDCResult(Base):
    __tablename__ = "mcdc_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, unique=True)
    coverage_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    decisions: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    gap_analysis: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    execution: Mapped["Execution"] = relationship("Execution", back_populates="mcdc")


class TraceabilityLink(Base):
    __tablename__ = "traceability_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    requirement_id: Mapped[str] = mapped_column(String(36), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False)
    function_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("functions.id", ondelete="SET NULL"), nullable=True)
    test_case_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True)
    execution_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("executions.id", ondelete="SET NULL"), nullable=True)
    evidence_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("evidence_records.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("executions.id", ondelete="CASCADE"), nullable=False, unique=True)
    freshness: Mapped[EvidenceFreshness] = mapped_column(SQLEnum(EvidenceFreshness), default=EvidenceFreshness.CURRENT)
    source_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    stub_checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    vector_checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tool_version: Mapped[str] = mapped_column(String(50), default="HonAero Sentinel 1.0.0")
    evidence_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    pdf_artifact_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=get_utc_now)

    project: Mapped["Project"] = relationship("Project", back_populates="evidence_records")
    execution: Mapped["Execution"] = relationship("Execution", back_populates="evidence")
