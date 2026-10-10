from pathlib import Path
from apps.api.app.infrastructure.coverage.gcov import GcovCoverageProvider


def test_gcov_provider_extract_from_json():
    provider = GcovCoverageProvider()
    mock_gcov_json = {
        "files": [
            {
                "file": "cabin_pressure.c",
                "functions": [{"name": "cabin_pressure_control", "execution_count": 2}],
                "lines": [
                    {"line_number": 2, "count": 2, "branches": []},
                    {
                        "line_number": 3,
                        "count": 2,
                        "branches": [
                            {"count": 1, "fallthrough": True, "throw": False},
                            {"count": 1, "fallthrough": False, "throw": False},
                        ],
                    },
                    {"line_number": 4, "count": 1, "branches": []},
                    {"line_number": 6, "count": 1, "branches": []},
                ],
            }
        ]
    }

    report = provider._extract_from_json(mock_gcov_json, "cabin_pressure.c", "/path/mock.gz")
    assert report.target_file == "cabin_pressure.c"
    assert report.total_lines == 4
    assert report.covered_lines == 4
    assert report.statement_coverage_pct == 100.0
    assert report.line_coverage_pct == 100.0
    assert report.total_branches == 2
    assert report.covered_branches == 2
    assert report.branch_coverage_pct == 100.0
    assert report.function_coverage_pct == 100.0

