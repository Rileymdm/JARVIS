def validate_float(value):
    try:
        return float(value)
    except ValueError:
        raise ValueError("Invalid input: must be a float.")

def format_simulation_results(results):
    formatted_results = []
    for result in results:
        formatted_results.append({
            "time": f"{result.get('time', 0):.1f}s",
            "altitude": f"{result.get('altitude', 0):.2f}m",
            "velocity": f"{result.get('velocity', 0):.2f}m/s",
            "acceleration": f"{result.get('acceleration', 0):.2f}m/s²",
            "thrust": f"{result.get('thrust', 0):.2f}N",
            "drag": f"{result.get('drag', 0):.2f}N"
        })
    return formatted_results

def prepare_data_for_visualization(simulation_data):
    times = [data['time'] for data in simulation_data]
    altitudes = [data['altitude'] for data in simulation_data]
    velocities = [data['velocity'] for data in simulation_data]
    return times, altitudes, velocities

import csv
import matplotlib.pyplot as plt

def plot_from_csv(csv_path="../simulation_results.csv"):
    times = []
    altitudes = []
    velocities = []
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                times.append(float(row['time']))
                altitudes.append(float(row['altitude']))
                velocities.append(float(row['velocity']))
            except Exception:
                continue
    if not times or not altitudes:
        print("No data to plot.")
        return
    plt.figure()
    plt.plot(times, altitudes, label='Altitude (m)')
    plt.plot(times, velocities, label='Velocity (m/s)')
    plt.xlabel('Time (s)')
    plt.legend()
    plt.tight_layout()
    plt.show()