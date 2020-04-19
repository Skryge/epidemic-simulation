from Pandemic_opti import *
from vispy import app, gloo
import pyqtgraph as pg

#Profiling decorator
def profiling(function):
    def new_function(*args, **kwargs):
        beg = time.time()
        ret = function(*args, **kwargs)
        end = time.time()
        print('Executing time of {} function : {} seconds'.format(function.__name__, end-beg))
        return ret
    return new_function


VERT_SHADER = """
// coordinate of the position.
attribute vec2 a_coord;

// Color
attribute vec3 a_color;
varying vec4 v_color;

// Data for adjusting position (transformations, margin, etc)
uniform float a_world_x;
uniform float a_world_y;
uniform float a_dist_x;
uniform float a_dist_y;
uniform float a_delta_x;
uniform float a_delta_y;
uniform float a_margin_x;
uniform float a_margin_y;
uniform float a_max_x_coord;
uniform float a_max_y_coord;
attribute vec2 a_pos;

void main() {

    // Position
    if(a_pos[0] != -1) {gl_Position = vec4(-1 + a_margin_x + a_pos[0]*(a_max_x_coord+a_delta_x) + a_max_x_coord*(a_coord[0]-a_world_x)/a_dist_x, -1 + a_margin_y + a_pos[1]*(a_max_y_coord+a_delta_y) + a_max_y_coord*(a_coord[1]-a_world_y)/a_dist_y, 0.0, 1.0);}
    else {gl_Position = vec4(-a_max_x_coord/2 + a_max_x_coord*(a_coord[0]-a_world_x)/a_dist_x, -1 + a_margin_y + a_max_y_coord*(a_coord[1]-a_world_y)/a_dist_y, 0.0, 1.0);}


    // Taille des points
    gl_PointSize = 4;

    // Couleur
    v_color = vec4(a_color, 1.);
}
"""

FRAG_SHADER = """
varying vec4 v_color;

void main() {
    gl_FragColor = v_color;

    // Pour dessiner des disques (et non des carres)
    vec2 coord = gl_PointCoord - vec2(0.5);  //from [0,1] to [-0.5,0.5]
    if(length(coord) > 0.5)                  //outside of circle radius?
        discard;
}
"""

#Our Visualizer inherits app.Canvas but also manages another window for displaying the Pandemic evolution graph
#-> It allows for updating both windows easily, i.e. with only one timer (check if there is another way)
class Visualizer(app.Canvas):
    def __init__(self, world):
        app.Canvas.__init__(self, title='Pandemic simulation', keys='interactive', position=(952,0), size=(960, 1010))
        self.world = world
        
        #GRAPH PART (PyQtGraph)
        #Black background
        pg.setConfigOption('background', 'k')
        self.win = pg.GraphicsWindow(title='Evolution of the Pandemic', size=(960, 1010))
        self.win.move(-8,0)
        self.graph = self.win.addPlot(row=0, col=0)
        self.graph.setTitle('Evolution of the Pandemic', size='17px')
        labelStyle = {'color': '#7e7e7e', 'font-size': '15px'}
        self.graph.setLabel('left', 'Number of people', **labelStyle)
        self.graph.setLabel('bottom', 'Time (days)', **labelStyle)
        self.graph.addLegend(size=(100,150))
        self.traces = {}

        #SCATTER PLOT PART (VisPy)
        self.program = gloo.Program(VERT_SHADER, FRAG_SHADER)
        gloo.set_viewport(0, 0, *self.physical_size)
        #Black background
        gloo.set_state(clear_color='black', blend=True)

        #Initialize particle positions on canvas
        for c in self.world.countries.values():
            for p in c.particles.values():
                p.pos_canvas = [-1, -1] if p.quarantine else [c.idx % self.world.nb_cols, self.world.nb_rows-1-(c.idx // self.world.nb_cols)]

        #Prepare data for sending to GPU (through self.program)
        self.world.coord = np.array([p.coord for c in self.world.countries.values() for p in c.particles.values()], dtype=np.float32)
        self.world.p_colors = np.array([p.color for c in self.world.countries.values() for p in c.particles.values()], dtype=np.float32)
        self.world.pos_canvas = np.array([p.pos_canvas for c in self.world.countries.values() for p in c.particles.values()], dtype=np.float32) / 255
        #Distance max entre les coordonnées max et coordonnées min
        self.dist_x = self.world.x2-self.world.x1
        self.dist_y = self.world.y2-self.world.y1
        #On définit un delta permettant de séparer les scatter plots entre eux (et aussi de les séparer du graphe d'évolution)
        self.delta_x = self.dist_x / 8
        self.delta_y = self.dist_y / 8
        #On définit une marge permettant de voir les particules entièrement, même lorsqu'elles sont aux bords
        self.margin_x = self.dist_x / 8
        self.margin_y = self.dist_y / 8
        #Les coordonnées du canvas vont de -1 à 1 en x et en y (la longueur de chaque axe est donc de 1-(-1) = 2)
        #On normalise les coordonnées à partir des informations précédentes -> (0, max_x_coord) et (0, max_y_coord) :
        self.max_x_coord = (2 - 2*self.margin_x - (self.world.nb_cols-1)*self.delta_x) / self.world.nb_cols
        self.max_y_coord = (2 - 2*self.margin_y - (self.world.nb_rows-1)*self.delta_y) / self.world.nb_rows

        #COMMON PART (except self.show)
        #Initialize plots
        self.update_plots()
        #Show scatter plot canvas (graph windows is already showed through pg.GraphicsWindow function)
        self.show()
        #Set Timer (note that this one comes from VisPy library)
        self.timer = app.Timer(0, connect=self.on_timer, start=True)

    def on_resize(self, event):
        gloo.set_viewport(0, 0, *event.physical_size)

    #@profiling
    def update_plots(self, already_called=False):
        #Clear graph before redrawing it
        self.graph.clear()
        #Change values for building a stackplot
        nb_I = self.world.l_I[-1]
        nb_S = self.world.l_S[-1]
        nb_R = self.world.l_R[-1]
        self.world.l_S[-1] += nb_I
        self.world.l_R[-1] += nb_S + nb_I
        self.world.l_D[-1] += nb_S + nb_I + nb_R #I know it is equal to self.world.N
        
        #Initialize or update plots
        if already_called:
            self.y_0.append(0)
            self.traces["0"].setData(self.world.times, self.y_0)
            self.traces["I"].setData(self.world.times, self.world.l_I)
            self.traces["S"].setData(self.world.times, self.world.l_S)
            self.traces["R"].setData(self.world.times, self.world.l_R)
            self.traces["D"].setData(self.world.times, self.world.l_D)

            self.program['a_coord'].set_data(self.world.coord)
            self.program['a_color'].set_data(self.world.p_colors)
            self.program['a_pos'].set_data(self.world.pos_canvas)
        else:
            self.y_0 = [0]
            self.traces["0"] = self.graph.plot(self.world.times, self.y_0)
            self.traces["I"] = self.graph.plot(self.world.times, self.world.l_I, pen=self.world.colors['I'], name=self.world.labels['I'])
            self.traces["S"] = self.graph.plot(self.world.times, self.world.l_S, pen=self.world.colors['S'], name=self.world.labels['S'])
            self.traces["R"] = self.graph.plot(self.world.times, self.world.l_R, pen=self.world.colors['R'], name=self.world.labels['R'])
            self.traces["D"] = self.graph.plot(self.world.times, self.world.l_D, pen=self.world.colors['D'], name=self.world.labels['D'])

            self.program['a_world_x'] = self.world.x1
            self.program['a_world_y'] = self.world.y1
            self.program['a_dist_x'] = self.dist_x
            self.program['a_dist_y'] = self.dist_y
            self.program['a_delta_x'] = self.delta_x
            self.program['a_delta_y'] = self.delta_y
            self.program['a_margin_x'] = self.margin_x
            self.program['a_margin_y'] = self.margin_y
            self.program['a_max_x_coord'] = self.max_x_coord
            self.program['a_max_y_coord'] = self.max_y_coord
            self.program['a_coord'] = self.world.coord
            self.program['a_color'] = self.world.p_colors
            self.program['a_pos'] = self.world.pos_canvas

        fills = [pg.FillBetweenItem(self.traces['0'], self.traces['I'], brush=self.world.colors['I']),
                pg.FillBetweenItem(self.traces['I'], self.traces['S'], brush=self.world.colors['S']),
                pg.FillBetweenItem(self.traces['S'], self.traces['R'], brush=self.world.colors['R']),
                pg.FillBetweenItem(self.traces['R'], self.traces['D'], brush=self.world.colors['D'])]
        for f in fills:
            self.graph.addItem(f)
        
        #Note : Le temps d'envoi des données au GPU + le temps d'affichage à l'écran (self.update et self.on_draw) est négligeable !
        #Le seul moyen d'avoir une animation plus fluide est donc d'optimiser la façon de convertir les données. (et bien sûr aussi toute la partie Pandemic.py)

    def on_timer(self, event):
        self.world.update(quarantine=True, nb_tests=0)
        self.update_plots(already_called=True)
        #Display changes
        self.update()

    def on_draw(self, event):
        gloo.clear()
        self.program.draw('points')


if __name__ == '__main__':
    w = World(move=0.01, time_period=1/300)
    w.add_country(nb_S=500)
    w.add_country(nb_S=400)
    w.add_country(nb_S=300)
    v = Visualizer(w)
    app.run()