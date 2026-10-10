import pytest
from apps.api.app.infrastructure.parsers.c_ast_parser import ClangAstSourceParser


def test_parse_cabin_pressure_control():
    parser = ClangAstSourceParser()
    c_code = """
    int cabin_pressure_control(int pressure, int altitude)
    {
        if (pressure > 900 && altitude < 10000)
            return 1;

        return 0;
    }
    """
    result = parser.parse_source("cabin_pressure.c", c_code)

    assert result.filename == "cabin_pressure.c"
    assert len(result.checksum_sha256) == 64
    assert len(result.functions) == 1

    fn = result.functions[0]
    assert fn.name == "cabin_pressure_control"
    assert fn.return_type == "int"
    assert len(fn.parameters) == 2
    assert fn.parameters[0].name == "pressure"
    assert fn.parameters[0].type == "int"
    assert fn.parameters[1].name == "altitude"
    assert fn.parameters[1].type == "int"

    # Decisions and atomic conditions
    assert len(fn.decisions) == 1
    decision = fn.decisions[0]
    assert decision.id == "D1"
    assert "pressure > 900" in decision.expression
    assert "altitude < 10000" in decision.expression

    assert len(decision.conditions) == 2
    c1, c2 = decision.conditions[0], decision.conditions[1]
    assert c1.id == "C1"
    assert "pressure > 900" in c1.expression
    assert "pressure" in c1.variable_references

    assert c2.id == "C2"
    assert "altitude < 10000" in c2.expression
    assert "altitude" in c2.variable_references


def test_parse_function_with_dependencies():
    parser = ClangAstSourceParser()
    c_code = """
    int sensor_read(void);
    void valve_write(int state);

    int cabin_pressure_system(int pressure, int altitude)
    {
        int sensor_val;
        sensor_val = sensor_read();
        if (sensor_val > 900 || altitude < 5000)
        {
            valve_write(1);
            return 1;
        }
        return 0;
    }
    """
    result = parser.parse_source("system.c", c_code)
    assert len(result.functions) == 1
    fn = result.functions[0]
    assert fn.name == "cabin_pressure_system"

    # Verify dependencies detected
    dep_names = [d.name for d in fn.dependencies]
    assert "sensor_read" in dep_names
    assert "valve_write" in dep_names

    # Verify decisions
    assert len(fn.decisions) == 1
    assert len(fn.decisions[0].conditions) == 2

