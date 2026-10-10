#ifndef SENSOR_H
#define SENSOR_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Sensor operational limits per DO-178C Level A specification */
#define MIN_ALLOWABLE_PRESSURE_PSI  10.0f
#define MAX_ALLOWABLE_PRESSURE_PSI  120.0f
#define MAX_ALTITUDE_FEET           45000.0f

typedef struct {
    float pressure_psi;
    float altitude_ft;
    bool valid;
    uint32_t status_flags;
} SensorData;

/**
 * Validate pressure sensor reading within DO-178C DAL-A boundaries.
 * Returns 1 (VALID) if within [10.0, 120.0], 0 (INVALID) if outside limits.
 */
int validate_pressure_reading(float pressure_psi);

/**
 * Compute calibrated altitude based on pressure and reference datum.
 * Returns calibrated altitude in feet, or -1.0f on invalid sensor pressure.
 */
float compute_calibrated_altitude(float pressure_psi, float ref_datum);

#ifdef __cplusplus
}
#endif

#endif /* SENSOR_H */
