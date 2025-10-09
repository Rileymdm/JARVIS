def run_simulation(
    m,
    Cd,
    A,
    rho,
    thrust_curve_path=None,
    chute_height=None,
    chute_size=None,
    time_step=None,
    chute_deploy_start=None,
    chute_cd=None,
    chute_deploy_duration=3.0,
    atmosphere='constant',
    variable_cd_model=False,
    chute_target_descent_rate=None,
    rocket_ref_length=None,
    drag_cap=400.0,
    drag_cap_mode='soft',
    drag_cap_soft_threshold=0.85,
    propellant_mass=None,
    **kwargs
):
    """
    Rocket simulation with organized givens and constants.
    
    User Inputs (Givens):
        m: Initial mass of the rocket (kg)
        Cd: Drag coefficient (rocket body, typical 0.3–1.5)
        A: Cross-sectional area (m²)
        rho: Air density (kg/m³)
        thrust_curve_path: Path to thrust curve CSV file [optional]
        chute_cd: Parachute drag coefficient (typical 1.5–2.2, used as entered)
        chute_size: Parachute area (m²)

    Simulation Constants:
        g: Gravity acceleration (9.81 m/s²)
        g0: Standard gravity for Isp equation (9.80665 m/s²)
        TimeI: Simulation time increment (0.5 s)

    Derived/Calculated:
        thrust_data: List of (time, thrust) tuples (from file or default)
        times, thrusts: Arrays from thrust_data
        Isp: Specific impulse, estimated from total impulse and g0
        total_impulse:  from thrust curve

    Additional Optional Parameters:
        atmosphere: 'constant' or 'isa' for a simple International Standard Atmosphere density variation.
        variable_cd_model: If True, apply a simplistic Mach-dependent Cd bump near Mach 1 for the rocket body.
        chute_target_descent_rate: If provided (m/s) and chute_size is None, compute parachute area to target that terminal descent rate at deployment.
        rocket_ref_length: Optional reference length (m) for Reynolds/Mach related models (currently only Mach bump uses velocity & speed of sound).

    State Variables (updated during simulation):
        time, velocity, altitude, mass, chute_deployed

    Diagnostics Added:
        rho_local: Local air density (kg/m^3)
        q: Dynamic pressure (Pa)
        Mach: |v| / a (speed of sound)
        terminal_v_body: Instantaneous terminal velocity for body-only configuration
        terminal_v_chute: Instantaneous terminal velocity with current effective Cd*A (after chute deploy)
        Cd_body_eff: Body Cd after Mach adjustment (if enabled)
    """
    import numpy as np
    from scipy.interpolate import interp1d
    import csv
    if thrust_curve_path:
        thrust_data = []
        prop_mass_from_file = None
        import os
        _, ext = os.path.splitext(thrust_curve_path.lower())
        with open(thrust_curve_path, newline='') as csvfile:
            # Robust CSV scan: handle metadata rows above header containing 'thrust'
            if ext == '.csv':
                import re
                reader = csv.reader(csvfile)
                rows = []
                for row in reader:
                    if not row:
                        continue
                    cleaned = [ (c or '').strip() for c in row ]
                    if any(cleaned):
                        rows.append(cleaned)
                header_idx = None
                time_idx = None
                thrust_idx = None
                # Find header row containing 'thrust'
                for i, row in enumerate(rows):
                    lc = [c.lower() for c in row]
                    if any('thrust' in c for c in lc):
                        header_idx = i
                        # pick columns
                        # time column candidates
                        try:
                            time_idx = next(j for j,c in enumerate(lc) if any(k in c for k in ['time','sec','(s']))
                        except StopIteration:
                            time_idx = 0 if len(row) > 0 else None
                        try:
                            thrust_idx = next(j for j,c in enumerate(lc) if 'thrust' in c)
                        except StopIteration:
                            thrust_idx = 1 if len(row) > 1 else None
                        break
                # Extract propellant mass from lines above header
                if header_idx is not None and prop_mass_from_file is None:
                    for i in range(header_idx):
                        line = ','.join(rows[i]).lower()
                        if ('propellant' in line) or ('prop mass' in line) or ('propellant mass' in line):
                            # find first float
                            nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", line)
                            if nums:
                                try:
                                    val = float(nums[-1])
                                    # if ' g' present without 'kg', assume grams
                                    if ' g' in line and 'kg' not in line:
                                        val = val / 1000.0
                                    if val > 0:
                                        prop_mass_from_file = val
                                        break
                                except Exception:
                                    pass
                # Parse data rows
                if header_idx is not None and time_idx is not None and thrust_idx is not None:
                    for row in rows[header_idx+1:]:
                        if len(row) <= max(time_idx, thrust_idx):
                            continue
                        try:
                            t = float(row[time_idx])
                            F = float(row[thrust_idx])
                            thrust_data.append((t, F))
                        except Exception:
                            continue
                else:
                    # Fallback: simple two-column CSV
                    for row in rows:
                        if len(row) < 2:
                            continue
                        try:
                            t = float(row[0]); F = float(row[1])
                            thrust_data.append((t, F))
                        except Exception:
                            continue
            else:
                # Non-CSV file (e.g., .eng/.rasp). Keep legacy simple parse: two columns time, thrust
                reader = csv.reader(csvfile, delimiter=' ', skipinitialspace=True)
                for row in reader:
                    # skip comments and headers
                    if not row or row[0].startswith(('#',';')):
                        continue
                    if len(row) == 2:
                        try:
                            t = float(row[0]); F = float(row[1])
                            thrust_data.append((t, F))
                        except Exception:
                            continue
                    else:
                        # header-like ENG line has many tokens; skip
                        continue
        if not thrust_data:
            return {'error': "Thrust curve file is empty or invalid."}
        # Prefer propellant mass from file when not provided by caller
        if propellant_mass in (None, 0) and 'prop_mass_from_file' in locals() and prop_mass_from_file:
            propellant_mass = prop_mass_from_file
    else:
        thrust_data = [
            (0.124, 816.849), (0.375, 796.043), (0.626, 781.861), (0.877, 767.440),
            (1.129, 759.627), (1.380, 735.948), (1.631, 714.454), (1.883, 701.582),
            (2.134, 674.667), (2.385, 656.493), (2.637, 636.076), (2.889, 612.409),
            (3.140, 587.801), (3.391, 567.170), (3.642, 559.971), (3.894, 534.157),
            (4.145, 444.562), (4.396, 280.510), (4.648, 216.702), (4.899, 163.136),
            (5.150, 120.571), (5.402, 86.544), (5.653, 59.990), (5.904, 39.527),
            (6.156, 25.914), (6.408, 0.000),
        ]

    times, thrusts = zip(*thrust_data)
    # For times before thrust curve starts, use the first thrust value
    def thrust_func_fixed(t):
        if t < times[0]:
            return thrusts[0]
        return float(interp1d(times, thrusts, bounds_error=False, fill_value=0.0)(t))

    burn_time = times[-1]
    g = 9.81
    g0 = 9.80665  # Standard gravity for Isp equation
    # Use time_step from UI if provided, else default to 0.05
    TimeI = time_step if time_step is not None else 0.05
    time = 0.0
    velocity = 0.0
    altitude = 0.0
    results = []

    total_impulse = calculate_total_impulse(thrust_data)
    # Determine specific impulse. If propellant_mass is provided, compute Isp so that
    # integrated mass flow consumes exactly that propellant mass over the burn.
    if propellant_mass is not None and propellant_mass > 0:
        Isp = total_impulse / (propellant_mass * g0)  # seconds
    else:
        # Backward-compatibility fallback: assume an effective Isp from total impulse alone
        # (equivalent to assuming 1 kg propellant mass)
        Isp = total_impulse / g0  # seconds

    # --- Atmosphere / Aerodynamics Helpers ---
    rho0 = rho  # treat provided rho as sea-level density when atmosphere != constant
    T0 = 288.15  # K
    L = 0.0065   # K/m lapse (troposphere)
    R = 287.05287  # J/(kg*K)
    gamma = 1.4

    def isa_density(alt):
        """Very simple ISA up to 11 km; falls back to exponential beyond."""
        if alt < 0:
            alt = 0
        if alt <= 11000:  # troposphere
            T = T0 - L * alt
            p = 101325 * (T / T0) ** (g / (R * L))
            return p / (R * T)
        # Simple scale-height approximation above 11 km
        scale_height = 7000.0
        return rho0 * np.exp(-(alt - 11000) / scale_height) * (isa_density(11000) / rho0)

    def local_density(alt):
        if atmosphere == 'isa':
            return isa_density(alt)
        return rho0

    def speed_of_sound(alt):
        if atmosphere == 'isa':
            if alt < 0:
                alt = 0
            if alt <= 11000:
                T = T0 - L * alt
            else:
                # Hold temperature constant above tropopause for this simplified model
                T = T0 - L * 11000
        else:
            T = T0
        return (gamma * R * T) ** 0.5

    def adjust_body_cd_for_mach(cd_body, mach):
        """Simple Mach bump: +15% peak at Mach 1, taper from 0.8–1.2."""
        if not variable_cd_model:
            return cd_body
        if mach < 0.8 or mach > 1.2:
            return cd_body
        # triangular bump centered at 1.0
        if mach <= 1.0:
            factor = 1 + 0.15 * (mach - 0.8) / (0.2)
        else:
            factor = 1 + 0.15 * (1.2 - mach) / (0.2)
        return cd_body * factor

    chute_deployed = False
    # Fixed deployment duration (seconds) replacing previous random period
    deploy_period = chute_deploy_duration if chute_deploy_duration and chute_deploy_duration > 0 else 3.0
    deploy_start = None
    deploy_end = None
    # Initialize effective coefficients BEFORE first use
    current_Cd = Cd
    current_A = A
    # Separate smoothing states for body and chute drag components
    last_rocket_drag = 0.0
    last_chute_drag = 0.0
    drag_smoothing_alpha = 0.30
    sim_version = 2
    deployment_stats = None

    # Track masses for proper burn-down behavior
    initial_mass = m
    dry_mass = None
    if propellant_mass is not None:
        dry_mass = max(0.0, initial_mass - max(0.0, propellant_mass))

    try:
        while True:
            F = thrust_func_fixed(time) if time <= burn_time else 0.0

            # Local atmospheric properties
            rho_local = local_density(altitude)
            a_sound = speed_of_sound(altitude)
            speed = abs(velocity)
            Mach = speed / a_sound if a_sound > 0 else 0.0

            # Body Cd Mach adjustment (pre-chute or baseline portion)
            Cd_body_eff = adjust_body_cd_for_mach(Cd, Mach)

            # Deployment trigger (descending & below height)
            deploy_height = chute_height if chute_height is not None else 300
            if not chute_deployed and velocity < -0.5 and altitude < deploy_height:
                chute_deployed = True
                deploy_start = time
                deploy_end = deploy_start + deploy_period  # no rounding; allow smooth fraction
                deployment_stats = {
                    'deployment_time': time,
                    'force_at_deployment': 0.0
                }

            # Simple linear inflation (can be replaced with ODE model if desired)
            chute_fill = 0.0
            target_Cd = chute_cd if chute_cd is not None else (chute_cd or 1.8)
            target_A = chute_size if chute_size is not None else A
            if chute_deployed and deploy_start is not None:
                if time < deploy_end:
                    frac = (time - deploy_start) / max((deploy_end - deploy_start), 1e-9)
                else:
                    frac = 1.0
                frac = np.clip(frac, 0.0, 1.0)
                # If chute_size not provided but a target descent rate is, compute required area at deployment time
                if chute_size is None and chute_target_descent_rate and chute_target_descent_rate > 0:
                    target_A = (2 * m * g) / max(rho_local * target_Cd * chute_target_descent_rate**2, 1e-9)
                # Ease-in curve for softer onset (cubic with small bias)
                # Parabolic (quadratic) deployment curve: smooth increase over fixed duration
                # y = (t/T)^2 gives a parabolic ramp starting gently (lower initial opening shock)
                chute_fill = frac**2
                current_Cd = Cd_body_eff  # body Cd unaffected directly by chute
                current_A = A              # keep body reference area for legacy fields
            else:
                current_Cd = Cd_body_eff
                current_A = A

            # Signed drag force (opposes velocity)
            # --- Drag decomposition: body + (optional) parachute ---
            if velocity != 0:
                rocket_drag_signed_raw = -0.5 * rho_local * Cd_body_eff * A * velocity * abs(velocity)
                chute_drag_signed_raw = 0.0
                if chute_deployed:
                    chute_drag_signed_raw = -0.5 * rho_local * target_Cd * (target_A * chute_fill) * velocity * abs(velocity)
                raw_signed_drag = rocket_drag_signed_raw + chute_drag_signed_raw
            else:
                rocket_drag_signed_raw = 0.0
                chute_drag_signed_raw = 0.0
                raw_signed_drag = 0.0
            # Smooth body and chute drag separately
            rocket_drag_signed_smoothed = (1 - drag_smoothing_alpha) * last_rocket_drag + drag_smoothing_alpha * rocket_drag_signed_raw
            chute_drag_signed_smoothed_uncapped = (1 - drag_smoothing_alpha) * last_chute_drag + drag_smoothing_alpha * chute_drag_signed_raw

            # Apply limiter ONLY to the chute component (if deployed)
            drag_cap_applied = False
            drag_cap_method = None
            chute_drag_signed_smoothed = chute_drag_signed_smoothed_uncapped
            if drag_cap and drag_cap > 0 and chute_deployed:
                if drag_cap_mode == 'hard':
                    drag_cap_method = 'hard'
                    if abs(chute_drag_signed_smoothed) > drag_cap:
                        chute_drag_signed_smoothed = -drag_cap if chute_drag_signed_smoothed < 0 else drag_cap
                        drag_cap_applied = True
                else:
                    drag_cap_method = 'soft'
                    thr = max(0.0, min(0.9999, drag_cap_soft_threshold)) * drag_cap
                    mag = abs(chute_drag_signed_smoothed)
                    sign = 1 if chute_drag_signed_smoothed >= 0 else -1
                    if mag > thr:
                        span = drag_cap - thr if drag_cap > thr else max(1e-6, drag_cap * 1e-4)
                        r = (mag - thr) / span
                        if r > 0:
                            r_clamped = 1.0 if r >= 1 else (3*r*r - 2*r*r*r)
                            mag_new = thr + (drag_cap - thr) * r_clamped
                            if mag_new > drag_cap:
                                mag_new = drag_cap
                            if mag_new < mag:
                                drag_cap_applied = True
                                mag = mag_new
                        chute_drag_signed_smoothed = sign * mag

            # Combine components
            signed_drag_smoothed_uncapped = rocket_drag_signed_smoothed + chute_drag_signed_smoothed_uncapped
            signed_drag = rocket_drag_signed_smoothed + chute_drag_signed_smoothed

            # Update history
            last_rocket_drag = rocket_drag_signed_smoothed
            last_chute_drag = chute_drag_signed_smoothed

            # Net acceleration (positive upward)
            a = (F + signed_drag) / m - g
            mdot = F / (Isp * g0) if F > 0 else 0
            m -= mdot * TimeI
            # Prevent mass from dropping below dry mass due to integration error
            if dry_mass is not None and m < dry_mass:
                m = dry_mass
            velocity += a * TimeI
            altitude += velocity * TimeI
            time += TimeI
            if altitude < 0:
                altitude = 0
                velocity = 0
            # Dynamic pressure & terminal velocities
            q = 0.5 * rho_local * speed**2
            try:
                terminal_v_body = (2 * m * g / (rho_local * Cd_body_eff * A)) ** 0.5
            except Exception:
                terminal_v_body = None
            try:
                # Use combined effective drag area for current configuration (body + filled chute area * chute Cd)
                combined_CdA = (Cd_body_eff * A) + (target_Cd * target_A * chute_fill)
                terminal_v_current = (2 * m * g / max(rho_local * combined_CdA, 1e-9)) ** 0.5 if combined_CdA > 0 else None
            except Exception:
                terminal_v_current = None
            try:
                ballistic_coeff_body = m / (Cd_body_eff * A)
            except Exception:
                ballistic_coeff_body = None
            try:
                ballistic_coeff_current = m / max(combined_CdA, 1e-9)
            except Exception:
                ballistic_coeff_current = None
            results.append({
                'time': time,
                'altitude': altitude,
                'velocity': velocity,
                'acceleration': a,
                'thrust': F,
                'drag': abs(signed_drag),          # magnitude used in dynamics
                'drag_signed': signed_drag,        # signed used in dynamics
                'drag_raw_signed': raw_signed_drag,
                'drag_signed_uncapped': signed_drag_smoothed_uncapped,  # total smoothed before chute limit
                'drag_cap_applied': drag_cap_applied,
                'drag_cap_method': drag_cap_method,
                'Cd_eff': current_Cd,
                'A_eff': current_A,
                'chute_deployed': chute_deployed,
                'mass': m,
                'mdot': mdot,
                'sim_version': sim_version,
                'rho_local': rho_local,
                'q': q,
                'Mach': Mach,
                'Cd_body_eff': Cd_body_eff,
                'terminal_v_body': terminal_v_body,
                'terminal_v_current': terminal_v_current,
                'rocket_drag_signed_raw': rocket_drag_signed_raw,
                'chute_drag_signed_raw': chute_drag_signed_raw,
                'chute_fill': chute_fill,
                'rocket_drag_signed_smoothed': rocket_drag_signed_smoothed,
                'chute_drag_signed_smoothed_uncapped': chute_drag_signed_smoothed_uncapped,
                'chute_drag_signed_smoothed': chute_drag_signed_smoothed,
                'ballistic_coeff_body': ballistic_coeff_body,
                'ballistic_coeff_current': ballistic_coeff_current,
                'initial_mass': initial_mass,
                'propellant_mass': propellant_mass if propellant_mass is not None else None,
                'dry_mass': dry_mass
            })
            if altitude == 0 and velocity <= 0:
                break
        impulse = calculate_total_impulse(thrust_data)
        print("Total Impulse:", impulse, "N·s")
        # Attach deployment stats to results for UI display
        if deployment_stats:
            for r in results:
                r['deployment_time'] = deployment_stats['deployment_time']
                r['force_at_deployment'] = deployment_stats['force_at_deployment']
        return results
    except Exception as e:
        return {'error': str(e)}

def plot_results(results):
    print("Results length:", len(results))
    if not results:
        print("No results to plot.")
        return
    times = [r['time'] for r in results]
    altitudes = [r['altitude'] for r in results]
    velocities = [r['velocity'] for r in results]
    masses = [r['mass'] for r in results] if 'mass' in results[0] else None
    print("Sample times:", times[:5])
    print("Sample altitudes:", altitudes[:5])
    print("Sample velocities:", velocities[:5])
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10,6))
    plt.plot(times, altitudes, label='Altitude (m)')
    plt.plot(times, velocities, label='Velocity (m/s)')
    if masses:
        plt.plot(times, masses, label='Mass (kg)')
    plt.xlabel('Time (s)')
    plt.legend()
    plt.tight_layout()
    plt.show()

def plot_table_and_stats(results):
    import matplotlib.pyplot as plt
    import pandas as pd
    # Convert results to DataFrame for easy table and plotting
    df = pd.DataFrame(results)
    # Display table in console
    print(df[['time','altitude','velocity','acceleration','thrust','drag','mass','mdot']].head(20))

    # Plot all important stats
    fig, axs = plt.subplots(4, 2, figsize=(14, 12))
    axs = axs.flatten()
    columns = ['altitude','velocity','acceleration','thrust','drag','mass','mdot']
    for i, col in enumerate(columns):
        axs[i].plot(df['time'], df[col], label=col)
        axs[i].set_xlabel('Time (s)')
        axs[i].set_ylabel(col)
        axs[i].legend()
        axs[i].grid(True)
    axs[-1].axis('off')  # Hide unused subplot
    plt.tight_layout()
    plt.show()

# Function to calculate total impulse from thrust curve
def calculate_total_impulse(thrust_data):
    # thrust_data: list of (time, thrust) tuples
    total_impulse = 0.0
    for i in range(1, len(thrust_data)):
        t0, F0 = thrust_data[i-1]
        t1, F1 = thrust_data[i]
        # Trapezoidal integration
        dt = t1 - t0
        avg_thrust = (F0 + F1) / 2
        total_impulse += avg_thrust * dt
    return total_impulse