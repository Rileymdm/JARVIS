# 🚀 JARVIS Live Code Viewer - Presentation Guide

## Overview
The Live Code Viewer is a powerful presentation tool that shows executing code in real-time as the rocket simulation runs. Perfect for demonstrations, teaching, and technical presentations.

## How to Use

### 1. Opening the Live Code Viewer
- Click the **🔴 Live Code Viewer** button in the main simulation interface
- The viewer window will open to the right of the main application
- Position the windows side-by-side for best presentation effect

### 2. Demo Mode (Recommended for Presentations)
- Click **🎯 Demo Mode** to run a pre-built demonstration
- This will automatically:
  - Start code monitoring
  - Run physics calculations
  - Parse thrust curves
  - Simulate flight dynamics
  - Show all code execution in real-time

### 3. Live Simulation Monitoring
- Click **▶️ Start Monitoring** to track real simulation code
- Run any simulation from the main interface
- Watch as the code executes live in the viewer
- Functions from `simulation.py` and `main.py` will be tracked

### 4. Features

#### Function Call Stack
- Left panel shows the sequence of function calls
- Each call is timestamped and shows the file and line number
- Click on any function to see its details

#### Live Code Display
- Right panel shows the actual executing code
- Current line is highlighted with `>>> EXECUTING <<<`
- Syntax highlighting and function context provided

#### Performance Metrics
- Total function calls counter
- Average execution time
- Real-time execution timing

## Presentation Tips

### For Technical Audiences
1. **Show the Physics**: Run Demo Mode to highlight the physics calculations
2. **Explain the Flow**: Point out how functions call each other in the call stack
3. **Highlight Performance**: Use the metrics to discuss optimization

### For Educational Purposes
1. **Step-by-Step**: Use the function list to explain program flow
2. **Code Walkthrough**: Show how mathematical formulas become code
3. **Interactive Learning**: Let students see code execute as simulations run

### For Live Demonstrations
1. **Side-by-Side Setup**: Main app on left, code viewer on right
2. **Demo First**: Run Demo Mode to warm up the audience
3. **Real Simulation**: Then run actual simulations to show real code execution
4. **Interactive**: Encourage questions about specific functions

## Keyboard Shortcuts
- **Clear Display**: Clear button or restart monitoring
- **Stop/Start**: Toggle monitoring on/off
- **Window Management**: Standard Windows controls for positioning

## Technical Details

### What Code is Tracked
- All functions in `simulation.py` (physics calculations)
- Main UI functions in `main.py` (user interactions)
- Demo functions (for presentation mode)
- Custom rocket-related modules

### Performance Impact
- Minimal impact on simulation accuracy
- Slight delay when monitoring is active
- No impact when monitoring is off

### Compatibility
- Works with all simulation modes
- Compatible with both UI themes
- Supports all rocket configurations

## Troubleshooting

### Code Not Showing
- Ensure monitoring is active (red recording indicator)
- Check that simulation is actually running
- Try Demo Mode to verify functionality

### Window Positioning
- Manually drag windows to desired positions
- Viewer automatically positions to the right of main window
- Use Windows snap features for perfect alignment

### Performance Issues
- Stop monitoring when not presenting
- Use Demo Mode for consistent performance
- Clear display periodically during long presentations

## Best Practices for Presentations

1. **Prepare**: Test Demo Mode before your presentation
2. **Explain**: Tell your audience what they're seeing
3. **Interact**: Use the live code to answer "how does it work?" questions
4. **Focus**: Point out key algorithms and calculations
5. **Engage**: Show different simulation parameters and their code impact

---

**Pro Tip**: For maximum impact, run the demo in full-screen mode with the main application and code viewer side-by-side. This creates an impressive "mission control" atmosphere perfect for technical presentations!