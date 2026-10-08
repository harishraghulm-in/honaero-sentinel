import enum


class DependencyMode(str, enum.Enum):
    REAL = "REAL"
    STUB = "STUB"


class DependencyType(str, enum.Enum):
    EXTERNAL_FUNCTION = "external_function"
    GLOBAL_VARIABLE = "global_variable"
    SYSTEM_HEADER = "system_header"


class HookStage(str, enum.Enum):
    SETUP = "setup"
    BEFORE_TEST = "before_test"
    AFTER_TEST = "after_test"
    TEARDOWN = "teardown"


class ExecutionStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    BUILDING = "BUILDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    BUILD_FAILED = "BUILD_FAILED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class ComparisonStatus(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    MISMATCH = "MISMATCH"


class EvidenceFreshness(str, enum.Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"


class RequirementType(str, enum.Enum):
    HLR = "HLR"  # High-Level Requirement
    LLR = "LLR"  # Low-Level Requirement
    DERIVED = "DERIVED"


class MCDCConditionStatus(str, enum.Enum):
    PROVEN = "PROVEN"
    NOT_PROVEN = "NOT_PROVEN"
    UNTESTED = "UNTESTED"

