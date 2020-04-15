
from Pandemic import *
from vispy import app, gloo
import numpy as np
import math

#Code pour convertir une couleur hex en couleur RGB
def hex_to_rgb(color):
    h = color.lstrip('#')
    return [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]


VERT_SHADER = """
#version 120

// y coordinate of the position.
attribute vec2 a_position;

// Color.
attribute vec3 a_color;
varying vec4 v_color;

void main() {

    // Position
    gl_Position = vec4(a_position, 0.0, 1.0);

    // Taille des points
    gl_PointSize = 10;

    // Color
    v_color = vec4(a_color, 1.);
}
"""

FRAG_SHADER = """
#version 120

varying vec4 v_color;

void main() {
    gl_FragColor = v_color;

    // Draw circle points
    vec2 coord = gl_PointCoord - vec2(0.5);  //from [0,1] to [-0.5,0.5]
    if(length(coord) > 0.5)                  //outside of circle radius?
        discard;
}
"""


class Visualizer(app.Canvas):
    def __init__(self, world):
        app.Canvas.__init__(self, title='Pandemic simulation', keys='interactive')
        self.world = world
        self.program = gloo.Program(VERT_SHADER, FRAG_SHADER)

        #Une country pour l'instant
        c = world.countries[0]

        self.program['a_position'] = np.c_[c.x_coord, c.y_coord].astype(np.float32)
        self.program['a_color'] = np.array([hex_to_rgb(color) for color in c.p_colors], dtype=np.float32)
        gloo.set_viewport(0, 0, *self.physical_size)
        self._timer = app.Timer(0, connect=self.on_timer, start=True)
        gloo.set_state(clear_color='white', blend=True, blend_func=('src_alpha', 'one_minus_src_alpha'))
        self.show()

    def on_resize(self, event):
        gloo.set_viewport(0, 0, *event.physical_size)

    def on_timer(self, event):
        self.world.update()
        c = self.world.countries[0]

        self.program['a_position'].set_data(np.c_[c.x_coord, c.y_coord].astype(np.float32))
        self.program['a_color'].set_data(np.array([hex_to_rgb(color) for color in c.p_colors], dtype=np.float32))
        self.update()

    def on_draw(self, event):
        gloo.clear()
        self.program.draw('points')

if __name__ == '__main__':
    w = World(move=0.01)
    for i in range(8):
        w.add_country(nb_S=500)
    v = Visualizer(w)
    app.run()

