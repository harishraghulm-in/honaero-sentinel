#include "sensor.h"

int validate_pressure_reading(float pressure_psi) {
    if (pressure_psi >= MIN_ALLOWABLE_PRESSURE_PSI && pressure_psi <= MAX_ALLOWABLE_PRESSURE_PSI) {
        return 1;
    }
    return 0;
}

float compute_calibrated_altitude(float pressure_psi, float ref_datum) {
    if (validate_pressure_reading(pressure_psi) == 0) {
        return -1.0f;
    }
    float altitude = (101.325f - pressure_psi) * 100.0f + ref_datum;
    if (altitude < 0.0f) {
        return 0.0f;
    }
    if (altitude > MAX_ALTITUDE_FEET) {
        return MAX_ALTITUDE_FEET;
    }
    return altitude;
}
