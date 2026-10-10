import math
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from apps.api.app.domain.enums import ComparisonStatus


class ComparisonDetail(BaseModel):
    field: str
    expected: Any
    actual: Any
    status: ComparisonStatus
    message: str = ""


class ComparisonResult(BaseModel):
    status: ComparisonStatus
    all_passed: bool
    details: List[ComparisonDetail] = Field(default_factory=list)
    disclaimer: str = (
        "Non-qualified verification comparator. For evaluation and simulation verification only."
    )


class IResultComparator(ABC):
    @abstractmethod
    def compare(self, actual: Any, expected: Any) -> ComparisonResult:
        pass


class ScalarComparator(IResultComparator):
    def __init__(self, float_tolerance: float = 1e-6):
        self.tolerance = float_tolerance

    def compare(self, actual: Any, expected: Any) -> ComparisonResult:
        if actual is None and expected is None:
            return ComparisonResult(
                status=ComparisonStatus.PASS,
                all_passed=True,
                details=[ComparisonDetail(field="value", expected=expected, actual=actual, status=ComparisonStatus.PASS)]
            )

        if isinstance(expected, float) or isinstance(actual, float):
            try:
                diff = abs(float(actual) - float(expected))
                passed = diff <= self.tolerance
                st = ComparisonStatus.PASS if passed else ComparisonStatus.FAIL
                return ComparisonResult(
                    status=st,
                    all_passed=passed,
                    details=[ComparisonDetail(
                        field="scalar_float",
                        expected=expected,
                        actual=actual,
                        status=st,
                        message=f"Delta {diff} (tolerance {self.tolerance})" if not passed else "Within tolerance"
                    )]
                )
            except (ValueError, TypeError) as e:
                return ComparisonResult(
                    status=ComparisonStatus.MISMATCH,
                    all_passed=False,
                    details=[ComparisonDetail(field="scalar_float", expected=expected, actual=actual, status=ComparisonStatus.MISMATCH, message=str(e))]
                )

        # Integers, booleans, strings
        passed = (actual == expected)
        st = ComparisonStatus.PASS if passed else ComparisonStatus.FAIL
        return ComparisonResult(
            status=st,
            all_passed=passed,
            details=[ComparisonDetail(field="scalar", expected=expected, actual=actual, status=st)]
        )


class StructuredComparator(IResultComparator):
    def __init__(self, scalar_comparator: IResultComparator = ScalarComparator()):
        self.scalar_comp = scalar_comparator

    def compare(self, actual: Any, expected: Any) -> ComparisonResult:
        if isinstance(expected, dict) and isinstance(actual, dict):
            details: List[ComparisonDetail] = []
            all_pass = True

            for key, exp_val in expected.items():
                if key not in actual:
                    all_pass = False
                    details.append(ComparisonDetail(
                        field=key,
                        expected=exp_val,
                        actual=None,
                        status=ComparisonStatus.MISMATCH,
                        message=f"Missing key '{key}' in actual result"
                    ))
                else:
                    sub_res = self.compare(actual[key], exp_val)
                    if not sub_res.all_passed:
                        all_pass = False
                    details.extend(sub_res.details)

            final_st = ComparisonStatus.PASS if all_pass else ComparisonStatus.FAIL
            return ComparisonResult(status=final_st, all_passed=all_pass, details=details)

        elif isinstance(expected, list) and isinstance(actual, list):
            if len(expected) != len(actual):
                return ComparisonResult(
                    status=ComparisonStatus.MISMATCH,
                    all_passed=False,
                    details=[ComparisonDetail(
                        field="length",
                        expected=len(expected),
                        actual=len(actual),
                        status=ComparisonStatus.MISMATCH,
                        message="Array length mismatch"
                    )]
                )
            details = []
            all_pass = True
            for i, (act_elem, exp_elem) in enumerate(zip(actual, expected)):
                sub_res = self.compare(act_elem, exp_elem)
                if not sub_res.all_passed:
                    all_pass = False
                details.extend(sub_res.details)
            final_st = ComparisonStatus.PASS if all_pass else ComparisonStatus.FAIL
            return ComparisonResult(status=final_st, all_passed=all_pass, details=details)

        # Fallback to scalar
        return self.scalar_comp.compare(actual, expected)

