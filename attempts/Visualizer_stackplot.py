from Pandemic import *
from vispy import app, gloo
from pyqtgraph.Qt import QtGui
import pyqtgraph as pg

#Code pour convertir une couleur hex en couleur RGB
def hex_to_rgb(color):
    h = color.lstrip('#')
    return [int(h[i:i+2], 16) for i in (0, 2, 4)]

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
// y coordinate of the position.
attribute vec2 a_position;

// Color
attribute vec3 a_color;
varying vec4 v_color;

void main() {

    // Position
    gl_Position = vec4(a_position, 0.0, 1.0);

    // Taille des points
    gl_PointSize = 5;

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
        self.graph = self.win.addPlot(title='Evolution of the Pandemic', row=0, col=0)
        self.graph.addLegend()
        self.traces = {}

        #SCATTER PLOT PART (VisPy)
        self.program = gloo.Program(VERT_SHADER, FRAG_SHADER)
        gloo.set_viewport(0, 0, *self.physical_size)
        #Black background
        gloo.set_state(clear_color='black', blend=True)
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

        #Convert scatter plot data for sending to gpu properly
        for c in self.world.countries.values():
            #On calcule les pos_x et pos_y de chaque pays sur le canvas (grâce à leur idx)
            pos_x = c.idx % self.world.nb_cols
            pos_y = c.idx // self.world.nb_cols
            #Plutôt de haut en bas
            pos_y = self.world.nb_rows-1-pos_y
            #On obtient les nouvelles coordonnées à partir de toutes les informations précédentes
            c.new_coord = [[-1 + self.margin_x + pos_x*(self.max_x_coord+self.delta_x) + self.max_x_coord*(x_coord-self.world.x1)/self.dist_x, 
                            -1 + self.margin_y + pos_y*(self.max_y_coord+self.delta_y) + self.max_y_coord*(y_coord-self.world.y1)/self.dist_y] for x_coord, y_coord in zip(c.x_coord, c.y_coord)]
        data = np.vstack([c.new_coord for c in self.world.countries.values()]).astype(np.float32)
        colors = np.array([hex_to_rgb(color) for c in self.world.countries.values() for color in c.p_colors], dtype=np.float32) / 255
        
        #Quarantine data
        if self.world.x_coord_q:
            new_coord_q = [[-self.max_x_coord/2 + self.max_x_coord * (x_coord_q-self.world.x1) / self.dist_x,
                            -1 + self.margin_y + self.max_y_coord * (y_coord_q-self.world.y1) / self.dist_y] for x_coord_q, y_coord_q in zip(self.world.x_coord_q, self.world.y_coord_q)]
            data = np.vstack([data, new_coord_q]).astype(np.float32)
            colors = np.vstack([colors, np.array([hex_to_rgb(color) for color in self.world.p_colors_q], dtype=np.float32) / 255])
        
        #Initialize or update plots
        if already_called:
            self.y_0.append(0)
            self.traces["0"].setData(self.world.times, self.y_0)
            self.traces["I"].setData(self.world.times, self.world.l_I)
            self.traces["S"].setData(self.world.times, self.world.l_S)
            self.traces["R"].setData(self.world.times, self.world.l_R)
            self.traces["D"].setData(self.world.times, self.world.l_D)

            self.program['a_position'].set_data(data)
            self.program['a_color'].set_data(colors)
        else:
            self.y_0 = [0]
            self.traces["0"] = self.graph.plot(self.world.times, self.y_0)
            self.traces["I"] = self.graph.plot(self.world.times, self.world.l_I, pen=self.world.colors_graph[0], name=self.world.labels[0])
            self.traces["S"] = self.graph.plot(self.world.times, self.world.l_S, pen=self.world.colors_graph[1], name=self.world.labels[1])
            self.traces["R"] = self.graph.plot(self.world.times, self.world.l_R, pen=self.world.colors_graph[2], name=self.world.labels[2])
            self.traces["D"] = self.graph.plot(self.world.times, self.world.l_D, pen=self.world.colors_graph[3], name=self.world.labels[3])

            self.program['a_position'] = data
            self.program['a_color'] = colors

        fills = [pg.FillBetweenItem(self.traces['0'], self.traces['I'], brush=hex_to_rgb(self.world.colors['I'])),
                pg.FillBetweenItem(self.traces['I'], self.traces['S'], brush=hex_to_rgb(self.world.colors['S'])),
                pg.FillBetweenItem(self.traces['S'], self.traces['R'], brush=hex_to_rgb(self.world.colors['R'])),
                pg.FillBetweenItem(self.traces['R'], self.traces['D'], brush=hex_to_rgb(self.world.colors['D']))]
        for f in fills:
            self.graph.addItem(f)
        
        #Note : Le temps d'envoi des données au GPU + le temps d'affichage à l'écran (self.update et self.on_draw) est négligeable !
        #Le seul moyen d'avoir une animation plus fluide est donc d'optimiser la façon de convertir les données. (et bien sûr aussi toute la partie Pandemic.py)

    def on_timer(self, event):
        beg = time.time()
        if self.world.time < 7:
            self.world.update()
        else:
            self.world.update(quarantine=True)
        interm = time.time()
        self.update_plots(already_called=True)
        end = time.time()
        print('time', interm-beg, '+', end-interm, '=', end-beg)
        #Display changes
        self.update()
        print('final :', time.time()-end, 'sec')

    def on_draw(self, event):
        gloo.clear()
        self.program.draw('points')


if __name__ == '__main__':
    w = World(move=0.01)
    for i in range(8):
        w.add_country(nb_S=500)
    v = Visualizer(w)
    app.run()