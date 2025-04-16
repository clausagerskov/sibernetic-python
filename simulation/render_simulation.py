# render_simulation.py
import sys
import os
import time
import math
import numpy as np
import signal # For handling Ctrl+C

try:
    from OpenGL.GL import *
    from OpenGL.GLUT import *
    from OpenGL.GLU import * # For gluPerspective (alternative to glFrustum)
except ImportError:
    print("ERROR: PyOpenGL or PyOpenGL-accelerate not found.")
    print("Install with: pip install PyOpenGL PyOpenGL-accelerate")
    sys.exit(1)

# Import classes from previously created modules
from config_loader import ConfigLoader, SimConfig
from ow_opencl_solver import PyOpenCLSolver # Assuming owOpenCLSolver.py is accessible
from utils import Vector3D


# --- Global Variables (Mirroring C++ Globals) ---

# Configuration/Simulation State
config: SimConfig = None
solver: PyOpenCLSolver = None
load_from_file_mode = False # Set based on arguments or config
load_to_file_mode = False   # Set based on arguments or config
iteration_count = 0

# Rendering Flags (can be toggled via keyboard)
skip_display_particles = False
skip_display_membranes = False
skip_display_connections = False
show_info = True
s_pause = False

# Camera/View Control
camera_trans = np.array([0.0, 0.0, -8.0], dtype=np.float32) # X, Y, Z translation
camera_rot = np.array([60.0, -90.0, 0.0], dtype=np.float32) # X, Y, Z rotation
camera_trans_lag = np.array([0.0, 0.0, -8.0], dtype=np.float32)
camera_rot_lag = np.array([0.0, -0.0, 0.0], dtype=np.float32) # Using a lag for smoother movement (optional)
mouse_button_state = 0 # 0=None, 1=Left, 2=Middle/Ctrl+Left, 3=Right
mouse_old_x, mouse_old_y = 0, 0
view_scale = 0.025 # Initial zoom/scale factor (C++ sc)

# Timing/FPS
total_sim_time_ms = 0.0 # Accumulated simulation+render time
frames_counter = 0
fps = 0.0
last_fps_update_time = 0.0

# --- Constants ---
TIMER_INTERVAL = 16 # roughly 60 FPS if VSync allows

rho0 = 1000.0
mass = 100000.0e-13
simulation_scale = 0.0037 * (mass ** (1.0 / 3.0)) / (0.00025 ** (1.0 / 3.0))
sc = 0.0025

# --- Helper Functions ---

def calculate_fps():
    """Updates the global FPS counter."""
    global frames_counter, last_fps_update_time, fps, total_sim_time_ms
    frames_counter += 1
    current_time = time.time() # Use time.time() for wall clock time
    time_interval_sec = current_time - last_fps_update_time

    # Update FPS calculation every second
    if time_interval_sec >= 1.0:
        fps = frames_counter / time_interval_sec
        last_fps_update_time = current_time
        frames_counter = 0
        # print(f"FPS: {fps:.2f}") # Optional: print FPS to console

class Config:
    def __init__(self, xmin, xmax, ymin, ymax, zmin, zmax):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.zmin = zmin
        self.zmax = zmax

def draw_scene():
    """Draws the bounding box, axes, and scale indicator."""
    global config, view_scale, sc
    if config is None: 
        #print("no config!")
        pass
    config = Config(0, 100, 0, 100, 0, 100)
    # --- Calculate Box Vertices ---
    xmin, xmax = config.xmin, config.xmax
    ymin, ymax = config.ymin, config.ymax
    zmin, zmax = config.zmin, config.zmax

    vcenter = Vector3D(0, 0, 0)

    s_v = 1 / simulation_scale

    order = 0
    while s_v>= 1:
        s_v /= 10
        if s_v < 1:
            s_v *= 10
            break
        order += 1

    # --- Draw Axes ---
    glLineWidth(2.0)
    glBegin(GL_LINES)

    sc *= 10

    # X-axis (Red)
    glColor3f(1.0, 0.0, 0.0)
    glVertex3f(vcenter.x, vcenter.y, vcenter.z)
    glVertex3f(vcenter.x + sc, vcenter.y, vcenter.z)

    # Y-axis (Green)
    glColor3f(0.0, 1.0, 0.0)
    glVertex3d(vcenter.x, vcenter.y, vcenter.z)  # Vertex at vcenter
    glVertex3d(vcenter.x, vcenter.y + sc, vcenter.z)  # Vertex offset along Y-axis

    # Z-axis (Blue)
    glColor3f(0.0, 0.0, 1.0)
    glVertex3d(vcenter.x, vcenter.y, vcenter.z)  # Vertex at vcenter
    glVertex3d(vcenter.x, vcenter.y, vcenter.z + sc)  # Vertex offset along Z-axis
    glEnd()

    sc /= 10

    # Center the box at the origin for easier viewing
    vcenter = Vector3D(
        -(xmin + xmax)/2,
        -(ymin + ymax)/2,
        -(zmin + zmax)/2,
    )

    vcenter *= sc
    v1 = Vector3D(-xmax/2, -ymax/2, -zmax/2) * sc
    v2 = Vector3D(xmax/2, -ymax/2, -zmax/2) * sc
    v3 = Vector3D(xmax/2, ymax/2, -zmax/2) * sc
    v4 = Vector3D(-xmax/2, ymax/2, -zmax/2) * sc
    v5 = Vector3D(-xmax/2, -ymax/2, zmax/2) * sc
    v6 = Vector3D(xmax/2, -ymax/2, zmax/2) * sc
    v7 = Vector3D(xmax/2, ymax/2, zmax/2) * sc
    v8 = Vector3D(-xmax/2, ymax/2, zmax/2) * sc

    # --- Draw Bounding Box Lines ---

    glLineWidth(1.0)
    glBegin(GL_LINES)
    glColor3ub(255, 255, 255)
    glVertex3d(v1.x, v1.y, v1.z)
    glVertex3d(v2.x, v2.y, v2.z)

    glColor3ub(255, 255, 255)
    glVertex3d(v2.x, v2.y, v2.z)
    glVertex3d(v3.x, v3.y, v3.z)

    glVertex3d(v3.x, v3.y, v3.z)
    glVertex3d(v4.x, v4.y, v4.z)

    glVertex3d(v4.x, v4.y, v4.z)
    glVertex3d(v1.x, v1.y, v1.z)

    glVertex3d(v1.x, v1.y, v1.z)
    glVertex3d(v5.x, v5.y, v5.z)

    glVertex3d(v2.x, v2.y, v2.z)
    glVertex3d(v6.x, v6.y, v6.z)

    glVertex3d(v3.x, v3.y, v3.z)
    glVertex3d(v7.x, v7.y, v7.z)

    glVertex3d(v4.x, v4.y, v4.z)
    glVertex3d(v8.x, v8.y, v8.z)

    glVertex3d(v5.x, v5.y, v5.z)
    glVertex3d(v6.x, v6.y, v6.z)

    glVertex3d(v6.x, v6.y, v6.z)
    glVertex3d(v7.x, v7.y, v7.z)

    glVertex3d(v7.x, v7.y, v7.z)
    glVertex3d(v8.x + s_v * sc, v8.y, v8.z)

    glVertex3d(v8.x, v8.y, v8.z)
    glVertex3d(v5.x, v5.y, v5.z)
    glEnd()

    # --- Draw Scale Indicator (like C++) ---
    # Find a suitable scale length (e.g., 10^-order meters)
    sim_scale = simulation_scale
    box_size_sim_units = max(xmax-xmin, ymax-ymin, zmax-zmin)
    typical_size_meters = box_size_sim_units * sim_scale
    glLineWidth(2.0)
    glBegin(GL_LINES)
    glColor3ub(0, 0, 0)

    v_s = Vector3D(-xmax / 2 + s_v, ymax / 2,
                    zmax / 2) * sc

    glVertex3d(v_s.x, v_s.y, v_s.z)
    glVertex3d(v_s.x, v_s.y - 0.5 * sc, v_s.z)

    glVertex3d(v8.x, v8.y, v8.z)
    glVertex3d(v_s.x, v_s.y, v_s.z)

    glEnd()
#     # Find order of magnitude (e.g., 1e-3, 1e-4)
#     if typical_size_meters > 0:
#         order = math.floor(math.log10(typical_size_meters))
#         scale_length_meters = 10**order
#         scale_length_sim_units = scale_length_meters / sim_scale
#         scale_length_gl = scale_length_sim_units * view_scale

#         # Position the scale bar near a corner (e.g., top-back-left: v[7])
#         bar_start = np.array(v[7])
#         bar_end = bar_start + np.array([-scale_length_gl, 0, 0]) # Draw along negative X

#         glLineWidth(2.0)
#         glColor3f(0.0, 0.0, 0.0) # Black
#         glBegin(GL_LINES)
#         glVertex3fv(bar_start)
#         glVertex3fv(bar_end)
#         # Add small ticks at ends
#         tick_size = axis_length * 0.05
#         glVertex3fv(bar_start)
#         glVertex3fv(bar_start + np.array([0, -tick_size, 0]))
#         glVertex3fv(bar_end)
#         glVertex3fv(bar_end + np.array([0, -tick_size, 0]))
#         glEnd()

#         # Print the scale label
#         label_pos = bar_start + np.array([-scale_length_gl / 2, -tick_size * 2.5, 0])
#         if scale_length_meters >= 1:
#              label_text = f"{scale_length_meters:.0f} m"
#         elif scale_length_meters >= 0.001:
#              label_text = f"{scale_length_meters*1000:.0f} mm"
#         else:
#             label_text = f"{scale_length_meters:.1e} m"

# #        gl_print_3d(label_pos[0], label_pos[1], label_pos[2], label_text)

    glLineWidth(1.0) # Reset line width

def display():
    """Main display callback function."""
    global s_pause, load_from_file_mode, solver, iteration_count
    global positions_np, connections_np, membranes_np, muscle_signals_np, velocities_np
    global total_sim_time_ms

    step_start_time = time.perf_counter()
    # --- Rendering ---
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # Set up camera view
    #glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    # Apply camera transformations (translation and rotation)
    # Using lag adds smoothness but complicates direct mapping
    # Direct mapping:
    #glTranslatef(camera_trans[0], camera_trans[1], camera_trans[2])
    #glRotatef(camera_rot[0], 1.0, 0.0, 0.0) # Rotate around X
    #glRotatef(camera_rot[1], 0.0, 1.0, 0.0) # Rotate around Y
    #glRotatef(camera_rot[2], 0.0, 0.0, 1.0) # Rotate around Z (usually not needed)

    # Using lag (closer to C++):
    global camera_trans_lag, camera_rot_lag
    # Simple linear interpolation for lag effect
    lag_factor = 0.2
    camera_trans_lag += (camera_trans - camera_trans_lag) * lag_factor
    camera_rot_lag += (camera_rot - camera_rot_lag) * lag_factor
    glTranslatef(camera_trans_lag[0], camera_trans_lag[1], camera_trans_lag[2])
    glRotatef(camera_rot_lag[0], 1.0, 0.0, 0.0)
    glRotatef(camera_rot_lag[1], 0.0, 1.0, 0.0)


    # Draw fixed elements
    draw_scene()
    # Draw UI overlay
    window_width = glutGet(GLUT_WINDOW_WIDTH)
    window_height = glutGet(GLUT_WINDOW_HEIGHT)
    #render_info(window_width, window_height)

    glutSwapBuffers()

    step_end_time = time.perf_counter()
    total_sim_time_ms += (step_end_time - step_start_time) * 1000.0
    calculate_fps()

def resize(width, height):
    """GLUT reshape callback."""
    if height == 0: height = 1
    if width == 0: width = 1
    glViewport(0, 0, width, height)

    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    aspect_ratio = float(width) / float(height)
    # Use gluPerspective for a typical perspective projection
    # FOV (degrees), aspect ratio, near clip, far clip
    gluPerspective(45.0, aspect_ratio, 0.1, 100.0) # Adjust near/far as needed

    # Or use glFrustum (closer to C++ example if that's what it did)
    # near, far = 3.0, 45.0 # From C++ code
    # y_extent = near * math.tan(math.radians(45.0 / 2.0)) # Assuming 45 deg vertical FOV implicitely
    # x_extent = y_extent * aspect_ratio
    # glFrustum(-x_extent, x_extent, -y_extent, y_extent, near, far)


    glMatrixMode(GL_MODELVIEW)
    # Modelview matrix is reset in display() before applying camera transforms

def keyboard(key, x, y):
    """GLUT keyboard callback."""
    global s_pause, show_info, solver, config

    key_code = key.decode("utf-8").lower()

    if key == b'\x1b' or key_code == 'q': # Escape or Q/q
        cleanup_simulation()
        sys.exit(0)
    elif key_code == ' ':
        s_pause = not s_pause
        print(f"Simulation {'Paused' if s_pause else 'Resumed'}")
    elif key_code == 's':
        if solver and not load_from_file_mode:
            print("Saving snapshot...")
            # Implement snapshot saving if needed (get data, write to file)
            # solver.save_snapshot("snapshot.txt") # Needs implementation
            print("Snapshot feature not implemented.")
        else:
            print("Cannot save snapshot (no solver or in file loading mode).")
    elif key_code == 'r':
        if solver and not load_from_file_mode:
            print("Resetting simulation...")
            try:
                solver.reset_simulation() # Needs implementation in solver
                # Might need to reload initial data etc.
                print("Reset feature not fully implemented.")
            except Exception as e:
                print(f"Error resetting simulation: {e}")
        else:
            print("Cannot reset simulation (no solver or in file loading mode).")
    elif key_code == 'i':
        show_info = not show_info
        print(f"Info display {'ON' if show_info else 'OFF'}")

    glutPostRedisplay() # Request redraw after state change

def mouse(button, state, x, y):
    """GLUT mouse button callback."""
    global mouse_button_state, mouse_old_x, mouse_old_y, view_scale

    mouse_old_x, mouse_old_y = x, y

    if state == GLUT_DOWN:
        mods = glutGetModifiers()
        if button == GLUT_LEFT_BUTTON:
             # Check for Ctrl key (seems GLUT_ACTIVE_CTRL isn't always reliable?)
            # A common alternative is to check mods == GLUT_ACTIVE_CTRL but that might miss Shift etc.
            # Let's use Middle button for zoom or Ctrl+Left if Middle isn't available
            if mods & GLUT_ACTIVE_CTRL:
                 mouse_button_state = 2 # Zoom / Pan Y alternative
            else:
                 mouse_button_state = 1 # Rotate
        elif button == GLUT_RIGHT_BUTTON:
            mouse_button_state = 3 # Pan X/Y
        elif button == GLUT_MIDDLE_BUTTON:
             mouse_button_state = 2 # Zoom / Pan Y
        elif button == 3: # Mouse wheel up
            view_scale *= 1.15 # Zoom in
            glutPostRedisplay()
        elif button == 4: # Mouse wheel down
            view_scale /= 1.15 # Zoom out
            glutPostRedisplay()
    elif state == GLUT_UP:
        mouse_button_state = 0 # No button pressed

def motion(x, y):
    """GLUT mouse motion callback."""
    global mouse_button_state, mouse_old_x, mouse_old_y
    global camera_rot, camera_trans

    dx = x - mouse_old_x
    dy = y - mouse_old_y

    if mouse_button_state == 1: # Left button: Rotate
        # Sensitivity factors (adjust as needed)
        rot_factor = 0.2
        camera_rot[0] += dy * rot_factor # Pitch
        camera_rot[1] += dx * rot_factor # Yaw
    elif mouse_button_state == 3: # Right button: Pan X/Y
        # Sensitivity factors
        pan_factor = 0.01
        camera_trans[0] += dx * pan_factor
        camera_trans[1] -= dy * pan_factor # Invert Y for intuitive panning
    elif mouse_button_state == 2: # Middle / Ctrl+Left: Zoom (Pan Z) or Pan Y
        # Let's use it for Pan Z (like dolly zoom)
        zoom_factor = 0.02
        camera_trans[2] += dy * zoom_factor # Moving mouse up/down zooms in/out

    mouse_old_x, mouse_old_y = x, y
    glutPostRedisplay() # Request redraw after camera change

def idle():
    """GLUT idle callback. Requests redraw."""
    glutPostRedisplay()

def timer(value):
     """GLUT timer callback (alternative to idle for fixed frame rate)."""
     glutPostRedisplay()
     glutTimerFunc(TIMER_INTERVAL, timer, 0)

def init_gl(width, height):
    """Initialize OpenGL settings."""
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glClearColor(0.7, 0.7, 0.7, 1.0) # Grey background
    glShadeModel(GL_SMOOTH)

    # Blending for transparency
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Enable line/point smoothing
    glEnable(GL_LINE_SMOOTH)
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
    glEnable(GL_POINT_SMOOTH)
    glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)

    # Basic lighting (optional, makes points/lines visible without normals)
    #glEnable(GL_COLOR_MATERIAL) # Use glColor values for material properties
    #glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    # Simple white light
    # glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
    # glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
    # glLightfv(GL_LIGHT0, GL_POSITION, [5.0, 5.0, 10.0, 0.0]) # Directional light from above right
    # glEnable(GL_LIGHTING)
    # glEnable(GL_LIGHT0)

    # Set initial projection and modelview matrices
    resize(width, height)



def cleanup_simulation():
    """Release resources."""
    global solver
    print("\nCleaning up simulation...")
    if solver:
        solver.release()
        solver = None
        print("Solver resources released.")
    # Other cleanup if needed (e.g., closing log files)
    print("Cleanup complete.")

def signal_handler(sig, frame):
    """Handles Ctrl+C."""
    print("\nCtrl+C detected. Exiting gracefully...")
    cleanup_simulation()
    sys.exit(0)

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting Simulation Renderer...")
    signal.signal(signal.SIGINT, signal_handler) # Register Ctrl+C handler

    # --- Argument Parsing (Basic Example) ---
    # You might use argparse for more complex argument handling
    config_dir = "configuration"
    config_file = "demo1"
    cl_source_file = "kernels/sphFluid.cl" # <--- MUST BE SET CORRECTLY

    #print(f"Loading config: {os.path.join(config_dir, config_file)}")
    #loader = ConfigLoader(config_path=config_dir, config_filename=config_file)
    glutInit()

    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
    glutInitWindowSize(1200, 800)
    glutInitWindowPosition(100, 100)
    window_title = f"SIBERNETIC (Python Port) - {config_file}".encode("utf-8")
    glutCreateWindow(window_title)

    init_gl(1200, 800)

    # --- Register Callbacks ---
    glutDisplayFunc(display)
    #glutReshapeFunc(resize)
    glutKeyboardFunc(keyboard)
    glutMouseFunc(mouse)
    glutMotionFunc(motion)
    glutIdleFunc(idle) # Use idle for max speed rendering
    glutTimerFunc(TIMER_INTERVAL, timer, 0) # Use timer for fixed FPS attempt

    # Register cleanup function to be called on exit
    import atexit
    atexit.register(cleanup_simulation)


    # --- Start GLUT Main Loop ---
    print("Starting GLUT main loop...")
    last_fps_update_time = time.time() # Initialize FPS timer start


    config_loader = ConfigLoader()
    config_loader.config_path = "./configuration"
    config_loader.config_filename = "demo1"

    sim = config_loader.preload_config()

    glutMainLoop()
