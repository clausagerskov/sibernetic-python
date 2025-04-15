import math
import numpy as np
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *


class SimpleRenderer:
    def __init__(self):
        self.window_width = 800
        self.window_height = 600
        self.angle = 0.0
        self.radius = 5.0
        self.min_radius = 1.0
        self.max_radius = 200.0
        self.paused = False

    def init_gl(self):
        # Set up the clear color (background) to gray
        glClearColor(0.5, 0.5, 0.5, 1.0)  # Gray background
        glEnable(GL_DEPTH_TEST)  # Enable depth testing for 3D scenes

    def draw_grid(self):
        # Assuming localConfig is a dictionary-like object containing xmin, xmax, ymin, ymax, zmin, zmax values
        localConfig = {
            "xmin": -1.0,
            "xmax": 1.0,
            "ymin": -1.0,
            "ymax": 1.0,
            "zmin": -1.0,
            "zmax": 1.0,
        }

        # Define the 8 corners of the bounding box using numpy arrays for Vector3D-like behavior
        vbox = np.array([
            [localConfig['xmin'], localConfig['ymin'], localConfig['zmin']],
            [localConfig['xmax'], localConfig['ymin'], localConfig['zmin']],
            [localConfig['xmax'], localConfig['ymax'], localConfig['zmin']],
            [localConfig['xmin'], localConfig['ymax'], localConfig['zmin']],
            [localConfig['xmin'], localConfig['ymin'], localConfig['zmax']],
            [localConfig['xmax'], localConfig['ymin'], localConfig['zmax']],
            [localConfig['xmax'], localConfig['ymax'], localConfig['zmax']],
            [localConfig['xmin'], localConfig['ymax'], localConfig['zmax']]
        ])

        # Center of the box (vcenter)
        vcenter = np.array([0.0, 0.0, 0.0])

        # Scaling factor (sc) and initial scaling (sc * 10)
        sc = 1.0  # Define your scale factor as needed
        sc *= 10  # Apply scaling

        # Begin OpenGL lines for drawing
        glBegin(GL_LINES)

        # Red line (X-axis)
        glColor3ub(255, 0, 0)  # Set color to red
        glVertex3d(vcenter[0], vcenter[1], vcenter[2])  # Vertex at vcenter
        glVertex3d(vcenter[0] + sc, vcenter[1], vcenter[2])  # Vertex offset along X-axis

        # Green line (Y-axis)
        glColor3ub(0, 255, 0)  # Set color to green
        glVertex3d(vcenter[0], vcenter[1], vcenter[2])  # Vertex at vcenter
        glVertex3d(vcenter[0], vcenter[1] + sc, vcenter[2])  # Vertex offset along Y-axis

        # Blue line (Z-axis)
        glColor3ub(0, 0, 255)  # Set color to blue
        glVertex3d(vcenter[0], vcenter[1], vcenter[2])  # Vertex at vcenter
        glVertex3d(vcenter[0], vcenter[1], vcenter[2] + sc)  # Vertex offset along Z-axis

        # End the OpenGL lines drawing
        glEnd()

        # Reset the scale (sc /= 10) after the drawing
        sc /= 10

    def render_scene(self):
        # Clear the color and depth buffers
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glLoadIdentity()  # Reset transformations

        # Compute camera position in a circle
        cam_x = self.radius * math.sin(math.radians(self.angle))
        cam_z = self.radius * math.cos(math.radians(self.angle))
        cam_y = 2.0  # Slightly elevated view

        # Camera looking at origin (0, 0, 0)
        gluLookAt(cam_x, cam_y, cam_z,  # Eye/camera position
                  0.0, 0.0, 0.0,        # Look-at point
                  0.0, 1.0, 0.0)        # Up direction

        # Optional: Draw something (e.g., simple objects or a grid), but for now, nothing.
        self.draw_grid()

        glutSwapBuffers()  # Swap buffers to display the scene

    def display(self):
        # Clear the screen and set up the scene rendering
        self.render_scene()

    def update(self, _=None):
        if not self.paused:
            self.angle += 0.5
            if self.angle >= 360.0:
                self.angle -= 360.0
        glutPostRedisplay()
        glutTimerFunc(16, self.update, 0)  # ~60 FPS

    def mouse_wheel(self, wheel, direction, x, y):
        zoom_speed = 0.5
        self.radius -= direction * zoom_speed
        self.radius = max(self.min_radius, min(self.max_radius, self.radius))
        glutPostRedisplay()

    def keyboard(self, key, x, y):
        if key == b'p':
            self.paused = not self.paused

    def reshape(self, w, h):
        glViewport(0, 0, w, h)  # Adjust the viewport
        glMatrixMode(GL_PROJECTION)  # Set the projection matrix mode
        glLoadIdentity()  # Reset projection matrix
        gluPerspective(45, float(w) / float(h), 0.1, 100.0)  # Set perspective projection
        glMatrixMode(GL_MODELVIEW)  # Switch back to model view matrix

def main():
    # Initialize GLUT
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(800, 600)
    window = glutCreateWindow(b"Simple Renderer")

    # Create the renderer instance
    renderer = SimpleRenderer()

    # Initialize OpenGL settings
    renderer.init_gl()

    # Set GLUT callbacks
    glutDisplayFunc(renderer.display)
    glutReshapeFunc(renderer.reshape)
    glutKeyboardFunc(renderer.keyboard)
    glutMouseWheelFunc(renderer.mouse_wheel)
    glutTimerFunc(0, renderer.update, 0)

    # Start the main loop
    glutMainLoop()

if __name__ == "__main__":
    main()
