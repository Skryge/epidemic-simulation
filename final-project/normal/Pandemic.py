import numpy as np
import numpy.random as npr
import time


class Particle:
	def __init__(self, idx=0, x=0.5, y=0.5, state="S", move=0.1,
				 colors={"S": "#10466a", "I": "#bb0303", "R": "#6AAB9C", "D": "#0e2233"}):
		self.idx = idx
		self.colors = colors
		self.coord = np.array([x, y])
		self.set_state(state)
		self.move = move
		self.quarantine = False
		self.time = 0
		
		#Vecteur direction (à ne plus modifier ensuite si l'on souhaite des déplacements linéaires)
		v_x = npr.uniform(-self.move, self.move)
		v_y_abs = np.sqrt(self.move**2 - v_x**2)
		v_y = -v_y_abs if npr.randint(2) == 0 else v_y_abs
		self.direction = np.array([v_x, v_y])
		
	def set_state(self, state="S"):
		self.state = state
		self.color = self.colors[state]
	
	def update_grid_pos(self, world):
		self.grid_pos_x = int((self.coord[0] - world.x1) // world.x_lenght)
		self.grid_pos_y = int((self.coord[1] - world.y1) // world.y_lenght)
		
	#Update de la position de la particule
	def update_pos(self, world):
#         Trajectoire aléatoire de longueur self.move
#         v_x = npr.uniform(-self.move,self.move)
#         v_y_abs = np.sqrt(self.move**2 - v_x**2)
#         v_y = -v_y_abs if npr.randint(2) == 0 else v_y_abs
#         self.direction = np.array([v_x,v_y])
		coord_temp = self.coord + self.direction
		if coord_temp[0] < world.x1 or coord_temp[0] >= world.x2:
			self.direction[0] *= -1
		if coord_temp[1] < world.y1 or coord_temp[1] >= world.y2:
			self.direction[1] *= -1
		self.coord += self.direction
	
	def update_pos_q(self, world):
		coord_temp = self.coord + self.direction
		if coord_temp[0] < world.x1_q or coord_temp[0] >= world.x2_q:
			self.direction[0] *= -1
		if coord_temp[1] < world.y1_q or coord_temp[1] >= world.y2_q:
			self.direction[1] *= -1
		self.coord += self.direction
	
	#Chaque cas susceptible a une proba d'infection pour chaque cas infecté avec qui il est en contact "rapproché"
	def update_S(self, world):
		#On parcourt les rectangles "les plus proches" en premier, pour gagner en temps d'exécution moyen
		voisinage = (world.grid["[{},{}]".format(self.grid_pos_x, self.grid_pos_y)]
					+ world.grid["[{},{}]".format(self.grid_pos_x - 1, self.grid_pos_y)]
					+ world.grid["[{},{}]".format(self.grid_pos_x + 1, self.grid_pos_y)]
					+ world.grid["[{},{}]".format(self.grid_pos_x, self.grid_pos_y - 1)]
					+ world.grid["[{},{}]".format(self.grid_pos_x, self.grid_pos_y + 1)]
					+ world.grid["[{},{}]".format(self.grid_pos_x - 1, self.grid_pos_y - 1)]
					+ world.grid["[{},{}]".format(self.grid_pos_x + 1, self.grid_pos_y - 1)]
					+ world.grid["[{},{}]".format(self.grid_pos_x - 1, self.grid_pos_y + 1)]
					+ world.grid["[{},{}]".format(self.grid_pos_x + 1, self.grid_pos_y + 1)])
		for p_I in voisinage:
			if np.sqrt(((self.coord - p_I.coord)**2).sum()) < world.safe_zone:
				if npr.rand() < world.proba_I:
					world.S.remove(self)
					world.new_I_particles.append(self)
					self.set_state("I")
					break
		self.update_pos(world)
		self.update_grid_pos(world)
			
	#Chaque cas infecté finit par guérir ou mourir après une certaine période
	def update_I(self, world):
		self.time += world.time_period
		world.grid["[{},{}]".format(self.grid_pos_x, self.grid_pos_y)].remove(self)
		if world.quarantine:
			if self.time >= world.incubation_time:
				self.quarantine = True
				world.I.remove(self)
				world.I_q.append(self)
				self.coord = np.array([(world.x2_q-world.x1_q) / 2.0, (world.y2_q-world.y1_q) / 2.0])
			else:
				self.update_pos(world)
				self.update_grid_pos(world)
				world.grid["[{},{}]".format(self.grid_pos_x, self.grid_pos_y)].append(self)
		else:
			if self.time >= world.days_R:
				world.I.remove(self)
				if npr.rand() < world.proba_D:
					world.D.append(self)
					self.set_state("D")
				else:
					world.R.append(self)
					self.set_state("R")
					self.time = 0
				self.update_pos(world)
			else:
				self.update_pos(world)
				self.update_grid_pos(world)
				world.grid["[{},{}]".format(self.grid_pos_x, self.grid_pos_y)].append(self)

	def update_I_q(self, world):
		self.time += world.time_period
		if self.time >= world.days_R:
			world.I_q.remove(self)
			if npr.rand() < world.proba_D:
				world.D_q.append(self)
				self.set_state("D")
			else:
				world.R_q.append(self)
				self.set_state("R")
				self.time = 0
		self.update_pos_q(world)
	
	#Chaque cas guéri a une infime proba de redevenir un cas susceptible au bout d'une certaine période
	def update_R(self, world):              
		self.time += world.time_period
		if self.time == 7:
			if npr.rand() < 0.00001:
				world.R.remove(self)
				world.S.append(self)
				self.set_state("S")
				self.time = 0
		self.update_pos(world)
	
	def update_R_q(self, world):
		self.time += world.time_period
		if self.time == 7:
			if npr.rand() < 0.00001:
				world.R_q.remove(self)
				world.S_q.append(self)
				self.set_state("S")
				self.time = 0
		self.update_pos_q(world)


class Country:
	def __init__(self, idx=0, nb_S=200, nb_I=1, x1=0, x2=1, y1=0, y2=1, move=0.1, time_period=1/24.0,
				 colors={"S": "#10466a", "I": "#bb0303", "R": "#6AAB9C", "D": "#0e2233"}, x1_q=0, x2_q=1, y1_q=0, y2_q=1):
		self.idx = idx
		self.x1, self.x2, self.y1, self.y2 = x1, x2, y1, y2
		self.x1_q, self.x2_q, self.y1_q, self.y2_q = x1_q, x2_q, y1_q, y2_q
		self.limits = [x1, x2, y1, y2]
		self.particles = {}
		self.N = 0
		self.quarantine = False
		self.colors = colors
		
		#Prise en compte du temps (exprimé en jours)
		self.time = 0
		
		#Probabilités et mesures remarquables
		self.proba_I = 0.2
		self.proba_D = 0.03
		self.safe_zone = 0.01
		self.incubation_time = 2
		self.days_R = 7
		self.move = move
		self.time_period = time_period
		
		#On quadrille la zone plus ou moins finement, selon la valeur de self.safe_zone
		#On placera à chaque tour les cas infectées dans le set correspondant à leur position sur le quadrillage
		#Cela permet pour chaque cas susceptible de ne le comparer qu'aux particules infectées de son voisinage
		#et donc de gagner en temps d'exécution, en particulier quand il y a à peu près autant de cas S que de cas I
		nb_rectangles_x = int((self.x2 - self.x1) // self.safe_zone)
		nb_rectangles_y = int((self.y2 - self.y1) // self.safe_zone)
		#On calcule les longueurs des côtés des rectangles, servant au calcul de la position des particules sur le quadrillage
		self.x_lenght = (self.x2 - self.x1) / nb_rectangles_x
		self.y_lenght = (self.y2 - self.y1) / nb_rectangles_y
		#On compte également une couronne de rectangles entourant la zone quadrillée, afin d'éviter les problèmes au bourd
		#(et de devoir ajouter plein de conditions) au moment de la construction du voisinage de chaque cas susceptible
		self.grid = {"[{},{}]".format(pos_x,pos_y): [] for pos_x in range(-1, nb_rectangles_x + 1) 
					 for pos_y in range(-1, nb_rectangles_y + 1)}
		
		#On distinguera les particules selon leur état
		self.S, self.I, self.R, self.D = [], [], [], []
		self.S_q, self.I_q, self.R_q, self.D_q = [], [], [], []
		
		#Listes des coordonnées des particules et de leur couleur (permet de ne faire qu'un seul plot par update)
		self.x_coord, self.y_coord, self.p_colors  = [], [], []
		
		#Listes des coordonnées des particules en quarantaine et de leur couleur
		self.x_coord_q, self.y_coord_q, self.p_colors_q  = [], [], []
		
		#Pourcentage d'infectés
		pct_I = 0
		
		#Ajout des particules au sein du pays
		self.add_particles(nb_S,nb_I)
			
	def add_rand_particle(self, state="S"):
		p = Particle(self.N, npr.uniform(self.x1, self.x2), npr.uniform(self.y1, self.y2), state, self.move, self.colors)
		self.particles[self.N] = p
		self.N += 1
		if p.state == "S":
			self.S.append(p)
			p.update_grid_pos(self)
		elif p.state == "I":
			self.I.append(p)
			p.update_grid_pos(self)
			self.grid["[{},{}]".format(p.grid_pos_x, p.grid_pos_y)].append(p)
		elif p.state == "R":
			self.R.append(p)
		else:
			self.D.append(p)
		self.x_coord.append(p.coord[0])
		self.y_coord.append(p.coord[1])
		self.p_colors.append(p.color)
		
		self.pct_I = round(len(self.I)/len(self.S+self.I+self.R+self.D)*100, 1)
	
	def add_particles(self, nb_S=200, nb_I=1):
		for i in range(nb_S):
			self.add_rand_particle("S")
		for i in range(nb_I):
			self.add_rand_particle("I")
	
	#Update des listes des coordonnées des particules et de leur couleur
	def update_lists(self):
		l = self.S + self.I + self.R + self.D
		l_q = self.S_q + self.I_q + self.R_q + self.D_q
		self.x_coord = [p.coord[0] for p in l]
		self.y_coord = [p.coord[1] for p in l]
		self.p_colors = [p.color for p in l]
		self.x_coord_q = [p.coord[0] for p in l_q]
		self.y_coord_q = [p.coord[1] for p in l_q]
		self.p_colors_q = [p.color for p in l_q]
	
	def update(self, quarantine=False):
		#Update du temps
		self.time += self.time_period
		
		#Mise en place ou non du système de quarantaine
		self.quarantine = quarantine

		#Update de l'état et de la position des particules
		self.new_I_particles = []
		
		#Suivre un ordre bien précis pour ne pas mettre à jour des particules plusieurs fois
		"Veut-on inclure la fonction update_lists dans les fonctions update_{} ?"
		for p_S in self.S:
			p_S.update_S(self)
		for p_S_q in self.S_q:
			p_S_q.update_pos_q(self)
		for p_R in self.R:
			p_R.update_R(self)
		for p_R_q in self.R_q:
			p_R_q.update_R_q(self)
		for p_I_q in self.I_q:
			p_I_q.update_I_q(self)
		for p_I in self.I:
			p_I.update_I(self)
		
		#Ajout des particules susceptibles devenues infectées (dans self.grid et self.I)
		for p in self.new_I_particles:
			self.grid["[{},{}]".format(p.grid_pos_x, p.grid_pos_y)].append(p)
		self.I += self.new_I_particles
		
		self.update_lists()
		self.pct_I = round(len(self.I)/len(self.S+self.I+self.R+self.D)*100, 1)


class World:
	def __init__(self, p_size=5, move=0.1, time_period=1/24.0, spread=0.4, eps=0.1,
				 colors={"S": "#10466a", "I": "#bb0303", "R": "#6AAB9C", "D": "#0e2233"}):
		self.nb_countries = 0
		self.countries = {}
		self.colors = colors
		self.p_size = p_size
		self.N = 0
		self.quarantine = False
		self.q_info = []
		
		#Prise en compte du temps (exprimé en jours)
		self.time = 0
		self.times = [self.time]
		self.move = move
		self.time_period = time_period
		self.daily_distance = self.move / self.time_period
		
		#Gestion des déplacements des particules entre pays
		self.chrono_travel = 0
		
		#Configuration du stackplot (ax1)
		self.labels = ("Infected", "Susceptible", "Recovered", "Deceased")
		self.colors_graph = (self.colors["I"], self.colors["S"], self.colors["R"], self.colors["D"])
		self.l_I, self.l_S, self.l_R, self.l_D = [0], [0], [0], [0]
		self.res = [self.l_I, self.l_S, self.l_R, self.l_D]
		
		#Listes des coordonnées des particules en quarantaine et de leur couleur (à regrouper en une zone commune)
		self.x_coord_q, self.y_coord_q, self.p_colors_q  = [], [], []
		
		#Coordonnées de la zone de promenade de chaque pays et de la zone quarantaine
		self.x1, self.x2, self.y1, self.y2 = 0, 1, 0, 1
		self.x1_q, self.x2_q, self.y1_q, self.y2_q = 0, 1, 0, 1
		
		#On initialise la figure
		self.nb_rows = 2
		self.nb_cols = self.nb_rows
		
		#Gestion du tracé des populations de chaque pays au sein d'un unique subplot
		self.spread = (self.x2-self.x1) / 2
		self.eps = (self.x2-self.x1) / 16
		
	#On souhaite que la zone de promenade de chaque pays se rapproche le plus possible d'un carré : hauteur ~= largeur
	def find_grid_dim(self):
		#Cela revient à minimiser nb_rows tel que nb_cols = nb_rows et nb_cols * (nb_rows-2) >= nb_countries
		while self.nb_cols * (self.nb_cols-2) < self.nb_countries:
			self.nb_rows += 1
			self.nb_cols = self.nb_rows
			
	#Update des listes du nombre de cas susceptibles, infectés, guéris et morts
	def update_lists(self, c):
		self.l_S[-1] += len(c.S + c.S_q)
		self.l_I[-1] += len(c.I + c.I_q)
		self.l_R[-1] += len(c.R + c.R_q)
		self.l_D[-1] += len(c.D + c.D_q)
	
	def add_country(self, nb_S=200, nb_I=1):
		c = Country(idx=self.nb_countries, nb_S=nb_S, nb_I=nb_I, colors=self.colors, x1=self.x1, x2=self.x2, y1=self.y1, 
					y2=self.y2, move=self.move, time_period=self.time_period, x1_q=self.x1_q, x2_q=self.x2_q, y1_q=self.y1_q,
					y2_q=self.y2_q)
		self.countries[self.nb_countries] = c
		self.nb_countries += 1
		self.N += nb_S + nb_I
		self.update_lists(c)
		self.find_grid_dim()
	
	"A FAIRE !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
	def travels(self, frequency=0.5):
		pass
		
	def update(self, quarantine=False):
		
		#Update du temps
		self.time += self.time_period
		self.times.append(self.time)
		
		#Update du système de quarantaine
		if not self.quarantine and quarantine:
			self.quarantine = True
			self.q_info += [[self.time]*2,[0,self.N],"black"]
		elif self.quarantine and not quarantine:
			self.quarantine = False
			self.q_info += [[self.time]*2,[0,self.N],"grey"]
		
		#Update au sein de chaque pays
		self.l_I.append(0)
		self.l_S.append(0)
		self.l_R.append(0)
		self.l_D.append(0)

		self.x_coord_q, self.y_coord_q, self.p_colors_q  = [], [], []
		
		for c in self.countries.values():
			c.update(quarantine)
			self.update_lists(c)
		
			#Réunion des particules en quarantaine dans chaque pays au sein d'une zone commune
			self.x_coord_q += c.x_coord_q
			self.y_coord_q += c.y_coord_q
			self.p_colors_q += c.p_colors_q
