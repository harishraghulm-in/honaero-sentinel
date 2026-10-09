#include "cabin_pressure.h"

int cabin_pressure_control(int pressure, int altitude)
{
    /* External sensor reading */
    int sensor_val = sensor_read();

    /* Safety Decision: Over-pressure alert condition */
    if (pressure > 900 && altitude < 10000 && sensor_val > 900)
    {
        valve_actuate(100);
        return 1;
    }

    valve_actuate(0);
    return 0;
}

