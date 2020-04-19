import numpy as np
import numpy.random as npr
import random
import time

#Code pour convertir une couleur hex en couleur RGB
def hex_to_rgb(color):
    h = color.lstrip('#')
    return [int(h[i:i+2], 16) for i in (0, 2, 4)]


class Particle:
	def __init__(self, idx=0, x=0.5, y=0.5, state="S", move=0.1, colors={}):
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
	
	def update_grid_pos(self, country):
		self.grid_pos_x = int((self.coord[0] - country.x1) // country.x_lenght)
		self.grid_pos_y = int((self.coord[1] - country.y1) // country.y_lenght)
		
	#Update de la position de la particule
	def update_pos(self, country):
#         Trajectoire aléatoire de longueur self.move
#         v_x = npr.uniform(-self.move,self.move)
#         v_y_abs = np.sqrt(self.move**2 - v_x**2)
#         v_y = -v_y_abs if npr.randint(2) == 0 else v_y_abs
#         self.direction = np.array([v_x,v_y])
		coord_temp = self.coord + self.direction
		if coord_temp[0] < country.x1 or coord_temp[0] >= country.x2:
			self.direction[0] *= -1
		if coord_temp[1] < country.y1 or coord_temp[1] >= country.y2:
			self.direction[1] *= -1
		self.coord += self.direction
	
	def update_pos_q(self, country):
		coord_temp = self.coord + self.direction
		if coord_temp[0] < country.x1_q or coord_temp[0] >= country.x2_q:
			self.direction[0] *= -1
		if coord_temp[1] < country.y1_q or coord_temp[1] >= country.y2_q:
			self.direction[1] *= -1
		self.coord += self.direction
	
	#Chaque cas susceptible a une proba d'infection pour chaque cas infecté avec qui il est en contact "rapproché"
	def update_S(self, country):
		#On parcourt les rectangles "les plus proches" en premier, pour gagner en temps d'exécution moyen
		voisinage = (country.grid["[{},{}]".format(self.grid_pos_x, self.grid_pos_y)]
					+ country.grid["[{},{}]".format(self.grid_pos_x - 1, self.grid_pos_y)]
					+ country.grid["[{},{}]".format(self.grid_pos_x + 1, self.grid_pos_y)]
					+ country.grid["[{},{}]".format(self.grid_pos_x, self.grid_pos_y - 1)]
					+ country.grid["[{},{}]".format(self.grid_pos_x, self.grid_pos_y + 1)]
					+ country.grid["[{},{}]".format(self.grid_pos_x - 1, self.grid_pos_y - 1)]
					+ country.grid["[{},{}]".format(self.grid_pos_x + 1, self.grid_pos_y - 1)]
					+ country.grid["[{},{}]".format(self.grid_pos_x - 1, self.grid_pos_y + 1)]
					+ country.grid["[{},{}]".format(self.grid_pos_x + 1, self.grid_pos_y + 1)])
		for p_I in voisinage:
			if np.sqrt(((self.coord - p_I.coord)**2).sum()) < country.safe_zone:
				if npr.rand() < country.proba_I:
					country.S.remove(self)
					country.new_I_particles.append(self)
					self.set_state("I")
					break
		self.update_pos(country)
		self.update_grid_pos(country)
			
	#Chaque cas infecté finit par guérir ou mourir après une certaine période
	def update_I(self, country):
		self.time += country.time_period
		country.grid["[{},{}]".format(self.grid_pos_x, self.grid_pos_y)].remove(self)
		if country.quarantine:
			if self.time >= country.incubation_time:
				self.quarantine = True
				country.I.remove(self)
				country.I_q.append(self)
				self.coord = np.array([(country.x2_q-country.x1_q) / 2.0, (country.y2_q-country.y1_q) / 2.0])
				self.pos_canvas = [-1, -1]
			else:
				self.update_pos(country)
				self.update_grid_pos(country)
				country.grid["[{},{}]".format(self.grid_pos_x, self.grid_pos_y)].append(self)
		else:
			if self.time >= country.days_R:
				country.I.remove(self)
				if npr.rand() < country.proba_D:
					country.D.append(self)
					self.set_state("D")
				else:
					country.R.append(self)
					self.set_state("R")
					self.time = 0
				self.update_pos(country)
			else:
				self.update_pos(country)
				self.update_grid_pos(country)
				country.grid["[{},{}]".format(self.grid_pos_x, self.grid_pos_y)].append(self)

	def update_I_q(self, country):
		self.time += country.time_period
		if self.time >= country.days_R:
			country.I_q.remove(self)
			if npr.rand() < country.proba_D:
				country.D_q.append(self)
				self.set_state("D")
			else:
				country.R_q.append(self)
				self.set_state("R")
				self.time = 0
		self.update_pos_q(country)
	
	#Chaque cas guéri a une infime proba de redevenir un cas susceptible au bout d'une certaine période
	def update_R(self, country):              
		# self.time += country.time_period
		# if self.time == 7:
		# 	if npr.rand() < 0.00001:
		# 		country.R.remove(self)
		# 		country.S.append(self)
		# 		self.set_state("S")
		# 		self.time = 0
		self.update_pos(country)
	
	def update_R_q(self, country):
		# self.time += country.time_period
		# if self.time == 7:
		# 	if npr.rand() < 0.00001:
		# 		country.R_q.remove(self)
		# 		country.S_q.append(self)
		# 		self.set_state("S")
		# 		self.time = 0
		self.update_pos_q(country)


class Country:
	def __init__(self, idx=0, nb_S=200, nb_I=1, x1=0, x2=1, y1=0, y2=1, move=0.1, time_period=1/24.0,
				 colors={}, x1_q=0, x2_q=1, y1_q=0, y2_q=1):
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
		self.safe_zone = 0.0015
		self.incubation_time = 6
		self.days_R = 10
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
	
	def add_particles(self, nb_S=200, nb_I=1):
		for i in range(nb_S):
			self.add_rand_particle("S")
		for i in range(nb_I):
			self.add_rand_particle("I")
	
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

class World:
	def __init__(self, p_size=5, move=0.1, time_period=1/24.0, spread=0.4, eps=0.1,
				 colors={"S": hex_to_rgb("#10466a"), "I": hex_to_rgb("#bb0303"), "R": hex_to_rgb("#6AAB9C"), "D": hex_to_rgb("#0e2233")}):
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
		
		#Configuration du stackplot (ax1)
		self.labels = {'I': "Infected", 'S': "Susceptible", 'R': "Recovered", 'D': "Deceased"}
		self.l_I, self.l_S, self.l_R, self.l_D = [0], [0], [0], [0]
		self.res = [self.l_I, self.l_S, self.l_R, self.l_D]
		
		#Listes des coordonnées des particules, de leur couleur, et de leur position sur le canvas (pour la classe Visualizer)
		self.coord, self.p_colors, self.pos_canvas  = [], [], []
		
		#Coordonnées de la zone de promenade de chaque pays et de la zone quarantaine
		self.x1, self.x2, self.y1, self.y2 = 0, 1, 0, 1
		self.x1_q, self.x2_q, self.y1_q, self.y2_q = 0, 1, 0, 1
		
		#On initialise la figure
		self.nb_rows = 2
		self.nb_cols = self.nb_rows
		
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
	
	def random_tests(self, sample):
		for p,c in sample:
			if p.state == 'I':
				p.quarantine = True
				c.I.remove(p)
				c.I_q.append(p)
				p.coord = np.array([(self.x2_q-self.x1_q) / 4, 3 * (self.y2_q-self.y1_q) / 4])
				p.pos_canvas = [-1, -1]
				#Green color for better visualization
				p.color = hex_to_rgb('#51ff0d')

	def update(self, quarantine=False, nb_tests=0):
		#Update time
		self.time += self.time_period
		self.times.append(self.time)
		
		#Update quarantine system
		if not self.quarantine and quarantine:
			self.quarantine = True
			self.q_info += [[self.time]*2,[0,self.N],"black"]
		elif self.quarantine and not quarantine:
			self.quarantine = False
			self.q_info += [[self.time]*2,[0,self.N],"grey"]
		
		#Update for each country
		self.l_I.append(0)
		self.l_S.append(0)
		self.l_R.append(0)
		self.l_D.append(0)
		
		for c in self.countries.values():
			c.update(quarantine)
			self.update_lists(c)

		#Government does random tests on population. Infected people go to quarantine zone
		if nb_tests and abs(self.time-round(self.time)) < 1e-9:
			people_not_q = []
			for c in self.countries.values():
				people_not_q += [(p, c) for p in c.S + c.I + c.R]
			try:
				sample = random.sample(people_not_q, nb_tests)
				self.random_tests(sample)
			except ValueError:
				self.random_tests(people_not_q)

		#Update des coordonnées des particules, de leur couleur et de leur position sur le canvas
		self.coord = np.array([p.coord for c in self.countries.values() for p in c.particles.values()], dtype=np.float32)
		self.p_colors = np.array([p.color for c in self.countries.values() for p in c.particles.values()], dtype=np.float32) / 255
		self.pos_canvas = np.array([p.pos_canvas for c in self.countries.values() for p in c.particles.values()], dtype=np.float32)