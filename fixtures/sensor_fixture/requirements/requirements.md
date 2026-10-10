# Requirements Document: Pitot-Static Sensor Management Subsystem

## Project Scope
This document specifies high-level requirements (HLR) for the DO-178C Level A Pitot-Static Sensor Management Subsystem.

### HLR-SNS-001: Operational Pressure Range Verification
The system shall monitor pressure sensor telemetry and ensure that measured pressure remains strictly within the operational envelope of 10.0 PSI to 120.0 PSI inclusive. Any pressure telemetry below 10.0 PSI or exceeding 120.0 PSI shall be flagged as invalid.

### HLR-SNS-002: Calibrated Altitude Computation
The system shall compute calibrated barometric altitude using validated sensor pressure and reference ground datum. If pressure validation indicates an out-of-boundary reading, calibrated altitude computation shall be aborted and return an error sentinel of -1.0. Calibrated altitude shall never exceed the maximum service ceiling of 45,000 feet.
