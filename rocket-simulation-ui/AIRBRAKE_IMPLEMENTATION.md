# Airbrake Implementation Summary

## Overview
Added airbrake capability to the rocket simulation system. Airbrakes are simple aerodynamic surfaces that deploy at a specified altitude or time to increase drag and reduce apogee.

## Changes Made

### 1. Simulation Engine (`simulation.py`)

#### Function Parameters
Added three new optional parameters to `run_simulation()`:
- `airbrake_altitude`: Altitude (m) at which to deploy airbrakes
- `airbrake_time`: Time (s) at which to deploy airbrakes  
- `airbrake_area`: Additional surface area (m²) added by airbrakes when deployed

#### Deployment Logic
- Airbrakes deploy when **either** the altitude threshold OR time threshold is exceeded (whichever comes first)
- Deployment is tracked with `airbrake_deployed` flag and `airbrake_deploy_time` variable
- Once deployed, they remain deployed for the entire flight

#### Drag Calculation
- Airbrakes contribute drag using a fixed Cd of 1.3 (typical for bluff bodies)
- Airbrake drag is calculated as: `drag = -0.5 * rho * Cd * area * velocity^2`
- Airbrake drag is **added** to the total drag (body + parachute + airbrakes)

#### Results Output
Added to simulation results dictionary:
- `airbrake_deployed`: Boolean flag indicating deployment status
- `airbrake_drag_signed_raw`: Raw airbrake drag force at each time step

### 2. User Interface (`main.py`)

#### Input Fields
Added three new input fields in the form layout:
1. **Airbrake Deploy Altitude** 
   - Units: meters (m) or feet (ft)
   - Accepts value or leave blank (defaults to None)

2. **Airbrake Deploy Time**
   - Units: seconds (s) or milliseconds (ms)
   - Accepts value or leave blank (defaults to None)

3. **Airbrake Surface Area**
   - Units: square meters (m²) or square feet (ft²)
   - Accepts value or leave blank (defaults to None)

#### Input Processing
- `get_inputs_for_simulation()` updated to extract and convert airbrake parameters with proper unit conversion
- Conversion factors: altitude (1 m = 3.28084 ft), time (1 s = 0.001 ms), area (1 m² = 10.764 ft²)

#### Results Display
- Airbrake deployment time is detected from results and displayed in summary table
- Appears as "Airbrake Deploy: X.XX s" in the results summary

#### Settings Persistence
- Airbrake settings are saved/loaded with other user settings in `user_settings.json`
- Allows users to configure and save airbrake parameters for repeated simulations

### 3. Integration Points

#### Simulation Call
Updated `start_simulation()` to pass airbrake parameters:
```python
sim_kwargs = {
    ...
    'airbrake_altitude': airbrake_altitude,
    'airbrake_time': airbrake_time,
    'airbrake_area': airbrake_area
}
```

#### UI Styling
- Airbrake input fields use same styling as other inputs (consistent look & feel)
- Unit dropdowns styled to match existing UI theme

## Usage

### Example 1: Deploy airbrakes at 1000 meters altitude
1. Set **Airbrake Deploy Altitude** to 1000 (m)
2. Leave **Airbrake Deploy Time** empty
3. Set **Airbrake Surface Area** to 0.05 (m²)
4. Run simulation

### Example 2: Deploy airbrakes at 10 seconds into flight
1. Leave **Airbrake Deploy Altitude** empty
2. Set **Airbrake Deploy Time** to 10 (s)
3. Set **Airbrake Surface Area** to 0.05 (m²)
4. Run simulation

## Physics Notes

- **Drag Coefficient**: Airbrakes use Cd = 1.3 (typical for flat plates/bluff bodies perpendicular to flow)
- **Deployment**: Instantaneous (no inflation delay like parachute)
- **Area Interpretation**: The `airbrake_area` represents the equivalent flat-plate area exposed to the airflow
- **Effect on Trajectory**: Increases drag significantly, reducing maximum altitude and descent velocity

## Testing Recommendations

1. Verify airbrake deploys at correct altitude/time
2. Check drag spike in results when airbrake deploys
3. Confirm apogee is reduced compared to no-airbrake case
4. Test with both altitude and time triggers
5. Verify units convert correctly (metric/imperial)

## Future Enhancements

- Multiple airbrake deployment stages
- Gradual deployment over a time period
- Adjustable Cd for different airbrake designs
- Visual indicators showing airbrake status in plots
- Export airbrake event markers to CSV/telemetry data
