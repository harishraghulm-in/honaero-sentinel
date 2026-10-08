#ifndef CABIN_PRESSURE_H
#define CABIN_PRESSURE_H

#ifdef __cplusplus
extern "C" {
#endif

/* External sensor reading dependency */
int sensor_read(void);

/* Outflow valve actuation dependency */
void valve_actuate(int position_pct);

/* Target Unit Under Test */
int cabin_pressure_control(int pressure, int altitude);

#ifdef __cplusplus
}
#endif

#endif /* CABIN_PRESSURE_H */

