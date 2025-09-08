def run_simulation(m, Cd, A, rho, thrust_curve_path=None, chute_height=None, chute_size=None, time_step=None, chute_deploy_start=None, chute_cd=None, **kwargs):
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

    State Variables (updated during simulation):
        time: Current simulation time
        velocity: Current velocity
        altitude: Current altitude
        mass: Current mass (decreases with fuel burn)
        chute_deployed: Boolean for parachute deployment
    """
    import numpy as np
    from scipy.interpolate import interp1d
    import csv
    if thrust_curve_path:
        thrust_data = []
        with open(thrust_curve_path, newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                # Skip empty or header rows
                if not row or len(row) < 2:
                    continue
                try:
                    t = float(row[0])
                    thrust = float(row[1])
                    thrust_data.append((t, thrust))
                except Exception:
                    continue
        if not thrust_data:
            return {'error': "Thrust curve file is empty or invalid."}
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
    Isp = total_impulse/g0  # Estimate Isp from total impulse and g0

    def drag_force(v, Cd_val, A_val):
        return 0.5 * rho * v**2 * Cd_val * A_val

    try:
        import random
        chute_deployed = False
        deploy_period = random.uniform(0.5, 2.5)  # random deployment period in seconds
        deploy_start = None
        deploy_end = None

        deployment_stats = None
        while True:
            F = thrust_func_fixed(time) if time <= burn_time else 0.0
            # Deploy parachute if falling and below chute_height (if provided), else default to 300m
            deploy_height = chute_height if chute_height is not None else 300
            if not chute_deployed and velocity < 0 and altitude < deploy_height:
                chute_deployed = True
                deploy_start = time
                deploy_end = time + deploy_period
                # Record deployment stats
                deployment_stats = {
                    'deployment_time': time,
                    'force_at_deployment': drag_force(velocity, current_Cd, current_A)
                }
            # Gradually change Cd and area from normal to parachute values over random deployment period
            if chute_deployed and deploy_start is not None and deploy_start <= time < deploy_end:
                deploy_fraction = (time - deploy_start) / (deploy_end - deploy_start)
                target_Cd = chute_cd if chute_cd is not None else Cd
                target_A = chute_size if chute_size is not None else A
                current_Cd = Cd + deploy_fraction * (target_Cd - Cd)
                current_A = A + deploy_fraction * (target_A - A)
            elif chute_deployed and deploy_end is not None and time >= deploy_end:
                current_Cd = chute_cd if chute_cd is not None else Cd
                current_A = chute_size if chute_size is not None else A
            else:
                current_Cd = Cd
                current_A = A
            # Always use current_Cd and current_A for drag, smooth transition
            F_drag = drag_force(velocity, current_Cd, current_A)
            a = (F - np.sign(velocity) * F_drag) / m - g
            # Calculate mdot (mass flow rate) using proper specific impulse equation
            mdot = F / (Isp * g0) if F > 0 else 0
            m -= mdot * TimeI  # Update mass
            velocity += a * TimeI
            altitude += velocity * TimeI
            time += TimeI
            if altitude < 0:
                altitude = 0
                velocity = 0  # Reset velocity to zero when hitting ground to avoid infinite loop
            results.append({
                'time': time,
                'altitude': altitude,
                'velocity': velocity,
                'acceleration': a,
                'thrust': F,
                'drag': F_drag,
                'chute_deployed': chute_deployed,
                'mass': m,
                'mdot': mdot
            })
            # Use a small epsilon to avoid floating point issues
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