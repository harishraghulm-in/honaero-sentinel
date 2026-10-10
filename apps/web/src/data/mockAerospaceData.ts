import type { Project, ProjectFile, Requirement, TestCase, Diagnostic  } from '../types';

export const MOCK_PROJECTS: Project[] = [
  {
    id: 'proj-x35-fcc',
    name: 'X-35 Fly-By-Wire Flight Control Computer',
    codeName: 'X35_FBW_FCC_V4',
    description: 'DO-178C Level A Primary Flight Control Computer core actuation and sensor stabilization loop.',
    dalLevel: 'DAL-A',
    branch: 'release/v4.2-cert',
    toolchain: 'Clang-12-Aero-Embedded (Target: PowerPC e500v2)',
    isBackendConnected: false,
    indexedTimestamp: '2026-10-09 14:15:00 UTC',
    stats: {
      discoveredFiles: 42,
      totalFunctions: 184,
      requirementCount: 68,
      testCaseCount: 142,
      passRate: 94.3,
      mcDcCoverage: 88.6,
      compilationErrors: 0,
      runtimeErrors: 1,
    },
  },
  {
    id: 'proj-apu-controller',
    name: 'APU-90 Auxiliary Power Unit Controller',
    codeName: 'APU_FADEC_SEC',
    description: 'Turbine starter governor and thermal emergency shutdown sequencing logic.',
    dalLevel: 'DAL-B',
    branch: 'main',
    toolchain: 'GCC-10-ARM-none-eabi (Target: Cortex-R5F)',
    isBackendConnected: false,
    indexedTimestamp: '2026-10-08 09:30:00 UTC',
    stats: {
      discoveredFiles: 28,
      totalFunctions: 96,
      requirementCount: 44,
      testCaseCount: 88,
      passRate: 98.8,
      mcDcCoverage: 92.1,
      compilationErrors: 0,
      runtimeErrors: 0,
    },
  },
];

export const MOCK_FILES: ProjectFile[] = [
  {
    id: 'fcc_pitch_ctrl',
    name: 'fcc_pitch_ctrl.c',
    path: 'src/actuation/fcc_pitch_ctrl.c',
    directory: 'src/actuation',
    language: 'C',
    linesCount: 84,
    functionsCount: 4,
    priorityScore: 0.98,
    criticality: 'DAL-A',
    cyclomaticComplexity: 16,
    coveragePercent: 91.2,
    status: 'passed',
    priorityRationale: {
      summary: 'Critical Pitch Axis Actuator: DAL-A flight safety envelope boundary.',
      determinismType: 'hybrid',
      factors: [
        'DO-178C DAL-A safety envelope protection',
        'Complex multi-branch MC/DC conditions',
        'Recent commit modified rate limiter constants',
      ],
    },
    content: `/*
 * HONAERO AVIONICS - FLIGHT CONTROL COMPUTER (FCC)
 * Module: fcc_pitch_ctrl.c
 * Target: DO-178C DAL-A Flight-Critical Flight Control Surface
 */

#include "fcc_types.h"
#include "actuator_io.h"

#define PITCH_LIMIT_POSITIVE_DEG   25.0f
#define PITCH_LIMIT_NEGATIVE_DEG  -15.0f
#define RATE_LIMIT_DEG_PER_SEC     12.5f

static float g_last_demanded_pitch = 0.0f;

ActuatorStatus_t update_pitch_actuation(
    float pilot_command_deg,
    float current_inertial_pitch,
    float q_bar_dynamic_pressure,
    bool autopilot_disengage_switch,
    float delta_time_sec)
{
    /* REQ-FCC-014: Disengage autopilot if pilot override exceeds 2.0g force */
    if (autopilot_disengage_switch) {
        actuator_set_manual_override(PITCH_AXIS);
        return ACT_STATUS_PILOT_OVERRIDE;
    }

    /* REQ-FCC-015: Structural Q-bar envelope protection */
    float effective_max_pitch = PITCH_LIMIT_POSITIVE_DEG;
    if (q_bar_dynamic_pressure > 450.0f) {
        effective_max_pitch = 18.0f; /* High-speed limit */
    }

    /* Envelope limiting clamp */
    float clamped_target = pilot_command_deg;
    if (clamped_target > effective_max_pitch) {
        clamped_target = effective_max_pitch;
    } else if (clamped_target < PITCH_LIMIT_NEGATIVE_DEG) {
        clamped_target = PITCH_LIMIT_NEGATIVE_DEG;
    }

    /* Slew rate limiter to prevent hydraulic hammer */
    float max_delta = RATE_LIMIT_DEG_PER_SEC * delta_time_sec;
    float demanded_delta = clamped_target - g_last_demanded_pitch;

    if (demanded_delta > max_delta) {
        demanded_delta = max_delta;
    } else if (demanded_delta < -max_delta) {
        demanded_delta = -max_delta;
    }

    g_last_demanded_pitch += demanded_delta;
    actuator_write_analog_dac(PITCH_AXIS, g_last_demanded_pitch);

    return ACT_STATUS_NOMINAL;
}
`,
  },
  {
    id: 'fuel_mgmt_system',
    name: 'fuel_mgmt_system.c',
    path: 'src/systems/fuel_mgmt_system.c',
    directory: 'src/systems',
    language: 'C',
    linesCount: 72,
    functionsCount: 3,
    priorityScore: 0.94,
    criticality: 'DAL-A',
    cyclomaticComplexity: 14,
    coveragePercent: 64.5,
    status: 'failed',
    priorityRationale: {
      summary: 'Verified Runtime Division-by-Zero Risk: Tank crossfeed transfer logic.',
      determinismType: 'deterministic',
      factors: [
        'Confirmed assertion fault in test vector TC-FMS-042-02',
        'Unchecked zero sum denominator in fuel balance ratio calculation',
        'Branch coverage gap on dual-empty tank emergency flag',
      ],
    },
    content: `/*
 * HONAERO AVIONICS - FUEL TRANSFER & CENTER OF GRAVITY (FMS)
 * Module: fuel_mgmt_system.c
 * DO-178C Criticality: DAL-A Dual-Engine Feed System
 */

#include "fuel_mgmt.h"

#define MAX_ALLOWABLE_IMBALANCE_LBS  450.0f
#define EMERGENCY_JETTISON_RATE_GPM  280.0f

FuelTransferResult_t balance_fuel_tanks(
    float tank_left_lbs,
    float tank_right_lbs,
    bool crossfeed_valve_open,
    FuelValveState_t* out_valve_command)
{
    /*
     * DIAGNOSTIC LOC: LINE 23
     * BUG: When both tanks report near zero during fuel starvation test,
     * total_fuel becomes 0.0f, inducing floating-point zero divide!
     */
    float total_fuel = tank_left_lbs + tank_right_lbs;
    float left_ratio = tank_left_lbs / total_fuel;

    if (!out_valve_command) {
        return FUEL_ERR_NULL_POINTER;
    }

    float delta = tank_left_lbs - tank_right_lbs;
    if (delta > MAX_ALLOWABLE_IMBALANCE_LBS) {
        /* Left heavier -> Feed engines from left tank */
        *out_valve_command = VALVE_FEED_LEFT_ONLY;
        return FUEL_TRANSFER_REBALANCING;
    } else if (delta < -MAX_ALLOWABLE_IMBALANCE_LBS) {
        /* Right heavier -> Feed engines from right tank */
        *out_valve_command = VALVE_FEED_RIGHT_ONLY;
        return FUEL_TRANSFER_REBALANCING;
    }

    *out_valve_command = VALVE_CROSSFEED_BALANCED;
    return FUEL_TRANSFER_NOMINAL;
}
`,
  },
  {
    id: 'pressure_sensor_driver',
    name: 'pressure_sensor_driver.h',
    path: 'src/drivers/pressure_sensor_driver.h',
    directory: 'src/drivers',
    language: 'Header',
    linesCount: 52,
    functionsCount: 2,
    priorityScore: 0.88,
    criticality: 'DAL-B',
    cyclomaticComplexity: 7,
    coveragePercent: 100.0,
    status: 'passed',
    priorityRationale: {
      summary: 'Pitot-Static Pitot Transducer Interface: Complete 100% MC/DC coverage.',
      determinismType: 'deterministic',
      factors: [
        'Hardware abstraction layer interface',
        'Triple-redundant pressure transducer voting driver',
        'Clean boundaries validated',
      ],
    },
    content: `/*
 * HONAERO AVIONICS - PITOT-STATIC SENSOR DRIVER
 * Header: pressure_sensor_driver.h
 */

#ifndef PRESSURE_SENSOR_DRIVER_H
#define PRESSURE_SENSOR_DRIVER_H

#include <stdint.h>
#include <stdbool.h>

#define PITOT_MIN_VALID_PSI   2.15f
#define PITOT_MAX_VALID_PSI  48.50f
#define SENSOR_FAULT_MASK    0xE000

typedef struct {
    float raw_voltage;
    float calibrated_psi;
    uint16_t status_word;
    bool is_stale;
} PitotSensorReading_t;

bool validate_pitot_reading(const PitotSensorReading_t* reading);
float vote_triple_redundant_pressure(
    PitotSensorReading_t a,
    PitotSensorReading_t b,
    PitotSensorReading_t c);

#endif /* PRESSURE_SENSOR_DRIVER_H */
`,
  },
  {
    id: 'sensor_fusion_bus',
    name: 'sensor_fusion_bus.c',
    path: 'src/drivers/sensor_fusion_bus.c',
    directory: 'src/drivers',
    language: 'C',
    linesCount: 98,
    functionsCount: 5,
    priorityScore: 0.82,
    criticality: 'DAL-A',
    cyclomaticComplexity: 11,
    coveragePercent: 78.0,
    status: 'idle',
    priorityRationale: {
      summary: 'ARINC 429 Bus Serializer & Checksum Validator.',
      determinismType: 'ai_heuristic',
      factors: [
        'Inter-system bus communication',
        'Checksum verification bitmask logic',
        'Potential timeout loop on frame misalignment',
      ],
    },
    content: `/*
 * HONAERO AVIONICS - ARINC 429 SERIAL BUS DESERIALIZER
 * Module: sensor_fusion_bus.c
 */

#include "arinc429.h"
#include <string.h>

#define ARINC_LABEL_ALTITUDE_BARO  0204
#define ARINC_LABEL_AIRSPEED_TRUE  0210
#define BUS_TIMEOUT_TICKS           50

BusStatus_t decode_arinc_word(
    uint32_t raw_word,
    uint8_t expected_label,
    float* out_engineering_value)
{
    uint8_t rx_label = (uint8_t)(raw_word & 0xFF);
    if (rx_label != expected_label) {
        return BUS_LABEL_MISMATCH;
    }

    /* Parity validation: Odd parity in bit 32 */
    uint32_t parity_accum = raw_word;
    parity_accum ^= parity_accum >> 16;
    parity_accum ^= parity_accum >> 8;
    parity_accum ^= parity_accum >> 4;
    parity_accum ^= parity_accum >> 2;
    parity_accum ^= parity_accum >> 1;

    if ((parity_accum & 1) == 0) {
        return BUS_PARITY_FAULT;
    }

    /* 19-bit BNR data payload extraction */
    int32_t payload = (int32_t)((raw_word >> 11) & 0x7FFFF);
    if (raw_word & (1U << 29)) {
        payload -= (1 << 19); /* Sign extend */
    }

    *out_engineering_value = (float)payload * 0.0625f;
    return BUS_OK;
}
`,
  },
  {
    id: 'nav_attitude_estimator',
    name: 'nav_attitude_estimator.c',
    path: 'src/navigation/nav_attitude_estimator.c',
    directory: 'src/navigation',
    language: 'C',
    linesCount: 110,
    functionsCount: 6,
    priorityScore: 0.76,
    criticality: 'DAL-B',
    cyclomaticComplexity: 9,
    coveragePercent: 88.0,
    status: 'passed',
    priorityRationale: {
      summary: 'Extended Kalman Filter Quaternion Estimator.',
      determinismType: 'deterministic',
      factors: [
        'High mathematical matrix operations',
        'Singularity protection around pitch ±90 deg',
      ],
    },
    content: `/*
 * HONAERO AVIONICS - ATTITUDE & HEADING REFERENCE SYSTEM (AHRS)
 * Module: nav_attitude_estimator.c
 */

#include "matrix_math.h"
#include <math.h>

void propagate_quaternion(
    float q[4],
    float gx_rad_s,
    float gy_rad_s,
    float gz_rad_s,
    float dt)
{
    float half_dt = 0.5f * dt;
    float q0 = q[0], q1 = q[1], q2 = q[2], q3 = q[3];

    q[0] += (-q1 * gx_rad_s - q2 * gy_rad_s - q3 * gz_rad_s) * half_dt;
    q[1] += ( q0 * gx_rad_s + q2 * gz_rad_s - q3 * gy_rad_s) * half_dt;
    q[2] += ( q0 * gy_rad_s - q1 * gz_rad_s + q3 * gx_rad_s) * half_dt;
    q[3] += ( q0 * gz_rad_s + q1 * gy_rad_s - q2 * gx_rad_s) * half_dt;

    /* Renormalize to prevent numerical drift */
    float norm = sqrtf(q[0]*q[0] + q[1]*q[1] + q[2]*q[2] + q[3]*q[3]);
    if (norm > 0.0001f) {
        float inv = 1.0f / norm;
        q[0] *= inv; q[1] *= inv; q[2] *= inv; q[3] *= inv;
    }
}
`,
  },
];

export const MOCK_REQUIREMENTS: Requirement[] = [
  {
    id: 'REQ-FCC-014',
    title: 'Pilot Override Disengage Threshold',
    standard: 'DO-178C',
    criticality: 'DAL-A',
    description: 'The Flight Control Computer shall immediately relinquish automatic pitch actuation to manual mode within 20 milliseconds if the pilot force override switch is asserted or stick force exceeds 15.0 daN.',
    documentSource: 'SysReq_DO178C_X35_Flight_Envelope.pdf',
    page: 42,
    linkedFileIds: ['fcc_pitch_ctrl'],
    linkedTestIds: ['TC-FCC-014-01', 'TC-FCC-014-02'],
    reviewStatus: 'Approved',
    coverageStatus: 'Fully Covered',
  },
  {
    id: 'REQ-FCC-015',
    title: 'High-Speed Q-Bar Dynamic Pressure Limiter',
    standard: 'DO-178C',
    criticality: 'DAL-A',
    description: 'When dynamic pressure (q_bar) exceeds 450.0 lb/ft², maximum positive pitch actuation command shall be clamped to 18.0 degrees to prevent aeroelastic flutter overstress.',
    documentSource: 'SysReq_DO178C_X35_Flight_Envelope.pdf',
    page: 44,
    linkedFileIds: ['fcc_pitch_ctrl'],
    linkedTestIds: ['TC-FCC-015-01'],
    reviewStatus: 'Approved',
    coverageStatus: 'Fully Covered',
  },
  {
    id: 'REQ-FMS-042',
    title: 'Fuel Tank Imbalance Rebalancing Protection',
    standard: 'DO-178C',
    criticality: 'DAL-A',
    description: 'The Fuel Management System shall maintain left/right wing tank fuel mass differential within 450.0 lbs and must handle zero-quantity emergency scenarios without inducing division-by-zero or processor exception.',
    documentSource: 'DO178C_FMS_Systems_Spec_RevC.docx',
    page: 88,
    linkedFileIds: ['fuel_mgmt_system'],
    linkedTestIds: ['TC-FMS-042-01', 'TC-FMS-042-02'],
    reviewStatus: 'Approved',
    coverageStatus: 'Partially Covered',
  },
  {
    id: 'REQ-DRV-007',
    title: 'Pitot Transducer Valid Boundary Acceptance',
    standard: 'DO-178C',
    criticality: 'DAL-B',
    description: 'The pressure transducer driver shall reject any sensor input under 2.15 PSI or over 48.50 PSI as SENSOR_STALE / OUT_OF_BOUNDS and flag the voting register.',
    documentSource: 'Pitot_AirData_ICD_v3.pdf',
    page: 16,
    linkedFileIds: ['pressure_sensor_driver'],
    linkedTestIds: ['TC-DRV-007-01'],
    reviewStatus: 'Approved',
    coverageStatus: 'Fully Covered',
  },
  {
    id: 'REQ-BUS-033',
    title: 'ARINC 429 Odd Parity Bit & Label Validation',
    standard: 'DO-178C',
    criticality: 'DAL-A',
    description: 'All 32-bit ARINC words arriving on the navigation bus shall undergo hardware odd parity validation. If parity fails, the word shall be dropped and BUS_PARITY_FAULT emitted within the frame cycle.',
    documentSource: 'Avionics_Bus_Architecture_Spec.pdf',
    page: 63,
    linkedFileIds: ['sensor_fusion_bus'],
    linkedTestIds: ['TC-BUS-033-01'],
    reviewStatus: 'Under Review',
    coverageStatus: 'Partially Covered',
  },
];

export const MOCK_TEST_CASES: TestCase[] = [
  {
    id: 'TC-FCC-014-01',
    title: 'Autopilot Disengage on Pilot Switch Assertion',
    requirementId: 'REQ-FCC-014',
    fileId: 'fcc_pitch_ctrl',
    sourceFunction: 'update_pitch_actuation',
    objective: 'Verify actuation state transitions to ACT_STATUS_PILOT_OVERRIDE when override switch is true.',
    preconditions: 'Pitch trim in nominal cruise, autopilot engaged, delta_time = 0.02s.',
    vectorSchema: [
      {
        name: 'pilot_command_deg',
        label: 'Pilot Stick Command',
        type: 'float',
        currentValue: 12.0,
        unit: 'deg',
        min: -15.0,
        max: 25.0,
        description: 'Demanded pitch attitude angle',
      },
      {
        name: 'current_inertial_pitch',
        label: 'Current Inertial Pitch',
        type: 'float',
        currentValue: 3.5,
        unit: 'deg',
        min: -30.0,
        max: 30.0,
        description: 'AHRS measured pitch angle',
      },
      {
        name: 'q_bar_dynamic_pressure',
        label: 'Dynamic Pressure (Q_bar)',
        type: 'float',
        currentValue: 280.0,
        unit: 'lb/ft²',
        min: 0.0,
        max: 800.0,
        description: 'Pitot dynamic aerodynamic loading',
      },
      {
        name: 'autopilot_disengage_switch',
        label: 'Pilot Override Disengage Switch',
        type: 'boolean',
        currentValue: true,
        description: 'Tactile stick paddle override switch assertion',
      },
      {
        name: 'delta_time_sec',
        label: 'Frame Loop Delta Time',
        type: 'float',
        currentValue: 0.02,
        unit: 's',
        min: 0.005,
        max: 0.1,
        description: 'Loop execution period',
      },
    ],
    expectedResult: 'Return: ACT_STATUS_PILOT_OVERRIDE (1), actuator_set_manual_override() invoked.',
    boundaryCases: ['Switch true at pitch limit', 'Switch false during high-g pull'],
    isNegativeTest: false,
    status: 'approved',
    lastRunStatus: 'passed',
    observedResult: 'ACT_STATUS_PILOT_OVERRIDE returned. Manual override latch set in 0.4ms.',
    executionDurationMs: 1.2,
  },
  {
    id: 'TC-FCC-015-01',
    title: 'Q-Bar Structural Limiter Clamping at 520 lb/ft²',
    requirementId: 'REQ-FCC-015',
    fileId: 'fcc_pitch_ctrl',
    sourceFunction: 'update_pitch_actuation',
    objective: 'Ensure positive pitch demand of 24.0 deg is clamped to 18.0 deg when Q_bar > 450 lb/ft².',
    preconditions: 'High-speed dive regime, Q_bar = 520 lb/ft², autopilot switch = false.',
    vectorSchema: [
      {
        name: 'pilot_command_deg',
        label: 'Pilot Stick Command',
        type: 'float',
        currentValue: 24.0,
        unit: 'deg',
        min: -15.0,
        max: 25.0,
        description: 'Demanded pitch attitude angle exceeds high-speed envelope',
        isBoundaryCase: true,
      },
      {
        name: 'current_inertial_pitch',
        label: 'Current Inertial Pitch',
        type: 'float',
        currentValue: 8.0,
        unit: 'deg',
        min: -30.0,
        max: 30.0,
        description: 'AHRS measured pitch angle',
      },
      {
        name: 'q_bar_dynamic_pressure',
        label: 'Dynamic Pressure (Q_bar)',
        type: 'float',
        currentValue: 520.0,
        unit: 'lb/ft²',
        min: 0.0,
        max: 800.0,
        description: 'High-speed aerodynamic pressure trigger (> 450)',
      },
      {
        name: 'autopilot_disengage_switch',
        label: 'Pilot Override Disengage Switch',
        type: 'boolean',
        currentValue: false,
        description: 'Override switch inactive',
      },
      {
        name: 'delta_time_sec',
        label: 'Frame Loop Delta Time',
        type: 'float',
        currentValue: 0.02,
        unit: 's',
        min: 0.005,
        max: 0.1,
        description: 'Loop execution period',
      },
    ],
    expectedResult: 'Actuation target clamped at 18.0 deg. Return: ACT_STATUS_NOMINAL.',
    boundaryCases: ['Q_bar = 450.00 exact threshold', 'Q_bar = 450.01 threshold crossover'],
    isNegativeTest: false,
    status: 'approved',
    lastRunStatus: 'passed',
    observedResult: 'Effective max pitch clamped to 18.0 deg as verified by DAC telemetry trace.',
    executionDurationMs: 0.8,
  },
  {
    id: 'TC-FMS-042-01',
    title: 'Nominal Fuel Balancing with 600 lbs Left Imbalance',
    requirementId: 'REQ-FMS-042',
    fileId: 'fuel_mgmt_system',
    sourceFunction: 'balance_fuel_tanks',
    objective: 'Verify valve commands VALVE_FEED_LEFT_ONLY when left tank exceeds right by > 450 lbs.',
    preconditions: 'Tank Left: 4200 lbs, Tank Right: 3400 lbs (delta = 800 lbs).',
    vectorSchema: [
      {
        name: 'tank_left_lbs',
        label: 'Tank Left Quantity',
        type: 'float',
        currentValue: 4200.0,
        unit: 'lbs',
        min: 0.0,
        max: 12000.0,
        description: 'Left wing tank capacitive fuel probe reading',
      },
      {
        name: 'tank_right_lbs',
        label: 'Tank Right Quantity',
        type: 'float',
        currentValue: 3400.0,
        unit: 'lbs',
        min: 0.0,
        max: 12000.0,
        description: 'Right wing tank capacitive fuel probe reading',
      },
      {
        name: 'crossfeed_valve_open',
        label: 'Crossfeed Valve Solenoid State',
        type: 'boolean',
        currentValue: true,
        description: 'Hardware solenoid status feedback',
      },
    ],
    expectedResult: 'Return: FUEL_TRANSFER_REBALANCING, *out_valve_command = VALVE_FEED_LEFT_ONLY.',
    boundaryCases: ['Delta = 450.0 lbs boundary test', 'Delta = 450.1 lbs crossover'],
    isNegativeTest: false,
    status: 'approved',
    lastRunStatus: 'passed',
    observedResult: 'Valve commanded to FEED_LEFT_ONLY; rebalance timer started.',
    executionDurationMs: 0.6,
  },
  {
    id: 'TC-FMS-042-02',
    title: 'Dual Empty Tank Starvation Edge Case (Divide by Zero)',
    requirementId: 'REQ-FMS-042',
    fileId: 'fuel_mgmt_system',
    sourceFunction: 'balance_fuel_tanks',
    objective: 'Evaluate fuel balance routine under extreme zero-fuel exhaustion condition (Tank L: 0, Tank R: 0).',
    preconditions: 'Extreme flameout test simulation, tanks depleted.',
    vectorSchema: [
      {
        name: 'tank_left_lbs',
        label: 'Tank Left Quantity',
        type: 'float',
        currentValue: 0.0,
        unit: 'lbs',
        min: 0.0,
        max: 12000.0,
        description: 'Starvation zero fuel boundary',
        isBoundaryCase: true,
      },
      {
        name: 'tank_right_lbs',
        label: 'Tank Right Quantity',
        type: 'float',
        currentValue: 0.0,
        unit: 'lbs',
        min: 0.0,
        max: 12000.0,
        description: 'Starvation zero fuel boundary',
        isBoundaryCase: true,
      },
      {
        name: 'crossfeed_valve_open',
        label: 'Crossfeed Valve Solenoid State',
        type: 'boolean',
        currentValue: true,
        description: 'Hardware solenoid status feedback',
      },
    ],
    expectedResult: 'Graceful handling without floating point exception or NaN propagation.',
    boundaryCases: ['Zero denominator check', 'Sub-normal float < 1e-6'],
    isNegativeTest: true,
    status: 'approved',
    lastRunStatus: 'failed',
    observedResult: 'ASSERTION FAILED: Division by zero at fuel_mgmt_system.c:23 (total_fuel == 0.0f).',
    executionDurationMs: 1.4,
  },
  {
    id: 'TC-DRV-007-01',
    title: 'Pitot Transducer Out of Bounds Underflow Rejection',
    requirementId: 'REQ-DRV-007',
    fileId: 'pressure_sensor_driver',
    sourceFunction: 'validate_pitot_reading',
    objective: 'Verify reading under 2.15 PSI is rejected and flagged as invalid.',
    preconditions: 'Air data computer powered on, pitot probe unheated/obstructed.',
    vectorSchema: [
      {
        name: 'raw_voltage',
        label: 'Raw ADC Voltage',
        type: 'float',
        currentValue: 0.12,
        unit: 'V',
        min: 0.0,
        max: 5.0,
        description: 'Transducer analog input channel',
      },
      {
        name: 'calibrated_psi',
        label: 'Calibrated PSI Value',
        type: 'float',
        currentValue: 1.45,
        unit: 'PSI',
        min: 0.0,
        max: 60.0,
        description: 'Underflow test vector below 2.15 PSI boundary',
        isBoundaryCase: true,
      },
      {
        name: 'status_word',
        label: 'Sensor Hardware Status Word',
        type: 'string',
        currentValue: '0x0000',
        description: 'Status bitmask flags',
      },
    ],
    expectedResult: 'validate_pitot_reading() returns false; status word tagged SENSOR_FAULT_MASK.',
    boundaryCases: ['2.149 PSI (rejected)', '2.150 PSI (accepted)'],
    isNegativeTest: true,
    status: 'approved',
    lastRunStatus: 'passed',
    observedResult: 'Rejected as SENSOR_OUT_OF_BOUNDS (calibrated_psi = 1.45 < 2.15).',
    executionDurationMs: 0.5,
  },
];

export const MOCK_DIAGNOSTICS: Diagnostic[] = [
  {
    id: 'diag-001',
    severity: 'error',
    category: 'assertion_failure',
    filePath: 'src/systems/fuel_mgmt_system.c',
    line: 23,
    column: 38,
    functionName: 'balance_fuel_tanks',
    testId: 'TC-FMS-042-02',
    requirementId: 'REQ-FMS-042',
    message: 'Floating-Point Division by Zero: Variable "total_fuel" evaluated to 0.000000f in left_ratio calculation.',
    rawTrace: 'AssertionFailedError: DivisionByZero at fuel_mgmt_system.c:23:38\n  in balance_fuel_tanks(tank_left=0.0, tank_right=0.0)\n  called by harness_runner_fms::run_vector(TC-FMS-042-02)\n  FPE Signal: SIGFPE [Floating point exception]',
    timestamp: '2026-10-09 14:18:22 UTC',
  },
  {
    id: 'diag-002',
    severity: 'warning',
    category: 'coverage_gap',
    filePath: 'src/systems/fuel_mgmt_system.c',
    line: 36,
    column: 12,
    functionName: 'balance_fuel_tanks',
    testId: 'TC-FMS-042-01',
    requirementId: 'REQ-FMS-042',
    message: 'Branch Coverage Gap: Condition "delta < -MAX_ALLOWABLE_IMBALANCE_LBS" evaluated False but never True in suite.',
    rawTrace: 'GcovReport: Branch 2 in balance_fuel_tanks() executed 0 times.\n  Decision "delta < -450.0f" never exercised True branch.\n  MC/DC requirement for DAL-A not satisfied.',
    timestamp: '2026-10-09 14:18:24 UTC',
  },
  {
    id: 'diag-003',
    severity: 'info',
    category: 'compiler_error',
    filePath: 'src/actuation/fcc_pitch_ctrl.c',
    line: 32,
    column: 9,
    functionName: 'update_pitch_actuation',
    testId: 'TC-FCC-015-01',
    requirementId: 'REQ-FCC-015',
    message: 'MISRA C:2012 Rule 10.4: Implicit float-to-double promotion in comparison "q_bar_dynamic_pressure > 450.0f".',
    rawTrace: 'MISRA-Checker: Rule 10.4 (Required)\n  Both operands shall have essentially the same type category.\n  Suggest suffixing literals with explicit "f" type.',
    timestamp: '2026-10-09 14:18:20 UTC',
  },
];
