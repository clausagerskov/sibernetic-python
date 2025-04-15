from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *

class Renderer:
    def __init__(self):
        self.window_width = 800
        self.window_height = 600

    def init_gl(self):
        glClearColor(0.7, 0.7, 0.7, 1.0)  # Set background to gray
        glEnable(GL_DEPTH_TEST)           # Enable depth testing for 3D rendering

    def resize(self, width, height):
        glViewport(0, 0, width, height)  # Set viewport to window size
        glMatrixMode(GL_PROJECTION)       # Switch to projection matrix
        glLoadIdentity()
        gluPerspective(45.0, width / height, 0.1, 50.0)  # Perspective projection
        glMatrixMode(GL_MODELVIEW)        # Switch back to modelview matrix

    def draw_grid(self):
        # No drawing here for now (just the background)
        pass

    def render_scene(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # Clear the screen and depth buffer
        glLoadIdentity()  # Reset transformations

        glTranslatef(0.0, 0.0, -5.0)  # Move the camera backward to see the scene

        self.draw_grid()  # Call drawing method (empty for now)

        # Now we swap the buffers to display the frame
        glutSwapBuffers()  # Swap the buffer to display the rendered image

    def display(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)  # Clear the screen and depth buffer
        self.render_scene()  # Call the scene rendering function
        glutSwapBuffers()  # Swap the buffer to display the rendered image


def main():
    # Initialize the library and create the window
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(800, 600)
    glutCreateWindow("OpenGL Renderer".encode("utf-8"))

    renderer = Renderer()
    renderer.init_gl()

    # Set the callback functions
    glutDisplayFunc(renderer.display)
    glutReshapeFunc(renderer.resize)

    # Start the main loop
    glutMainLoop()

if __name__ == "__main__":
    main()
