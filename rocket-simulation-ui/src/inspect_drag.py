import sys
sys.path.append('c:/Users/wickerrd/Documents/GitHub/JARVIS/rocket-simulation-ui/src')
from simulation import run_simulation

results = run_simulation(5,0.6,0.02,1.225,time_step=0.05,chute_height=300,chute_size=0.8,chute_cd=1.8)
# Collect window
window = [x for x in results if 57.3 <= x['time'] <= 58.2]
print(f"{len(window)} records in 57.3-58.2s window")
for x in window:
    drag_raw = x.get('drag_raw')
    Cd_eff = x.get('Cd_eff')
    A_eff = x.get('A_eff')
    fill = x.get('chute_fill')
    print("t={:.2f} drag={:.2f} raw={} v={:.2f} alt={:.2f} Cd={} A={} fill={} limited={}".format(
        x['time'], x['drag'],
        f"{drag_raw:.2f}" if isinstance(drag_raw,(int,float)) else 'NA',
        x['velocity'], x['altitude'],
        f"{Cd_eff:.3f}" if isinstance(Cd_eff,(int,float)) else 'NA',
        f"{A_eff:.4f}" if isinstance(A_eff,(int,float)) else 'NA',
        f"{fill:.3f}" if isinstance(fill,(int,float)) else 'NA',
        x.get('drag_limit_applied')
    ))

print('Check for any sudden ratio jumps:')
for i in range(1, len(window)):
    prev = window[i-1]
    cur = window[i]
    if prev['drag'] > 0:
        ratio = cur['drag']/prev['drag']
        if ratio > 1.5:
            print(f"Jump at {cur['time']:.2f}s ratio {ratio:.2f}")
