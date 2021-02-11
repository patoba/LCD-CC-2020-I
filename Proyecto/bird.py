import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from itertools import islice
from operator import itemgetter

import random
import numpy as np
import os
import multiprocessing as mp

def intersects(center, radius,
               xy, width, height):
    """
    Determina si un rectángulo y un círculo se intersectan.
    
    Parámetros
    ----------
    center : float
        Centro del círculo.
        
    radius : float
        Radio del círculo.
        
    xy : list-like
        Lista de la forma [x,y], siendo las coordenadas del centro del rectángulo.
    
    width : float
        Ancho del rectángulo.
        
    height : float
        Alto del rectángulo
        
    Salida
    ------
    intersects : bool
        Si el círculo y rectángulo se intersectan o no.
    """
    cdistx, cdisty = np.abs(center[0] - xy[0]), np.abs(center[1] - xy[1])
    
    if cdistx > width/2 + radius:
        return False
    if cdisty > height/2 + radius:
        return False
    
    if cdistx <= width/2:
        return True
    if cdisty <= height/2:
        return True
    
    corner = (cdistx - width/2)**2 + (cdisty - height/2)**2
    return corner <= radius**2
    
class Bird:
    """
    Clase que representa un pájaro.
    
    Atributos
    ---------
    BIRD_RADIUS : float
        Radio del pájaro.
        
    MIN_VELOCITY : float
        Velocidad mínima de caída que puede tener. Cuando está cayendo la velocidad es negativa, así que esto es 
        en realidad una cota superior.
        
    GRAVITY : float
        Aceleración de la gravedad.
        
    DT : float
        Intervalo temporal.
        
    TOP: float
        Límite superior del mundo.
        
    FLAP_SPEED : float
        Velocidad que adquiere cuando aletea.
        
    y: float
        Posición vertical.
        
    vy: float
        Velocidad vertical.
        
    alive : bool
        Si está vivo o no.
        
    fitness: float
        Aptitud.
        
    network : NeuralNet
        Red neuronal con la que decide si aletear o no.
    """
    def __init__(self, network, settings):
        self.BIRD_RADIUS = settings['BIRD_RADIUS']
        self.MIN_VELOCITY = settings['MIN_VELOCITY']
        self.GRAVITY = settings['GRAVITY']
        self.DT = settings['DT']
        self.TOP = settings['TOP']
        self.FLAP_SPEED = settings['FLAP_SPEED']
        
        self.y = self.TOP/2
        self.vy = 0.
        self.alive = True
        self.fitness = 0
        self.network = network
        
    def __repr__(self): # Cómo imprimir el objeto
        return 'y: ' + str(self.y) + '\n' + \
               'vy: ' + str(self.vy) + '\n' + \
               'alive: ' + str(self.alive) + '\n' + \
               'fitness: ' + str(self.fitness)
                
    def move(self, flap):
        """
        Desplaza el pájaro una unidad de tiempo.
        
        Parámetros
        ----------
        flap : bool
            Si aletear o no.
        """
        if not self.alive:
            return
        self.y += 1/2 * self.GRAVITY * self.DT**2 + self.vy * self.DT
        if flap:
            self.vy = self.FLAP_SPEED
        else:
            if self.vy > self.MIN_VELOCITY:
                self.vy += self.GRAVITY * self.DT
        if self.y > self.TOP:
            self.y = self.TOP
    
    def step(self, pipe):
        choice = self.network([pipe.x, self.y-pipe.y])
        self.move(choice)
                
    def plot(self, ax, draw_dead=False, color=None):
        if not self.alive and not draw_dead:
            return
        c = Circle((0, self.y), self.BIRD_RADIUS, color=color)
        ax.add_patch(c)

        
class Pipe:
    """
    Clase que representa una tubería.
    
    Atributos
    ---------
    MINIMUM_HEIGHT: float
        Altura mínima que pueden tener las tuberías.
        
    PIPE_WIDTH : 
    """
    def __init__(self, x, settings):
        self.MINIMUM_HEIGHT = settings['MINIMUM_HEIGHT']
        self.PIPE_WIDTH = settings['PIPE_WIDTH']
        self.PIPE_GAP = settings['PIPE_GAP']
        self.TOP = settings['TOP']
        self.VX = settings['VX']
        self.DT = settings['DT']
        
        self.x = x
        self.y = self.MINIMUM_HEIGHT  + random.random() * (self.TOP - 2*self.MINIMUM_HEIGHT)
        
    def step(self):
        self.x += self.VX * self.DT
        
    def plot(self, ax):
        r1 = Rectangle((self.x, 0), self.PIPE_WIDTH, self.y - self.PIPE_GAP/2)
        r2 = Rectangle((self.x, self.y + self.PIPE_GAP/2), self.PIPE_WIDTH, self.TOP)
        ax.add_patch(r1)
        ax.add_patch(r2)
        ax.scatter([self.x], [self.y])
        
class World:
    def __init__(self, nets, settings):
        PIPE_WIDTH = settings['PIPE_WIDTH']
        RIGHT = settings['RIGHT']
        self.settings = settings

        self.birds = [Bird(n, settings) for n in nets]
        self.pipes = [Pipe((RIGHT - PIPE_WIDTH)/2, settings), Pipe(RIGHT, settings)]
        self.steps = 0
        self.alive = True
        
    def check_collision(self):
        BIRD_RADIUS = self.settings['BIRD_RADIUS']
        PIPE_WIDTH = self.settings['PIPE_WIDTH']
        PIPE_GAP = self.settings['PIPE_GAP']
        TOP = self.settings['TOP']
        
        i = 0
        while i < len(self.birds):
            b = self.birds[i]
            
            if not b.alive:
                i += 1
                continue
                
            if b.y - BIRD_RADIUS <= 0:
                b.alive = False
                i += 1
                continue
                
            for p in self.pipes:
                height_bot = p.y - PIPE_GAP/2
                height_top = TOP - p.y - PIPE_GAP/2
                cx = p.x + PIPE_WIDTH/2
                cy_bot = height_bot/2
                cy_top = p.y + PIPE_GAP/2 + height_top/2
                if intersects([0, b.y], BIRD_RADIUS, [cx, cy_bot], PIPE_WIDTH, height_bot) \
                or intersects([0, b.y], BIRD_RADIUS, [cx, cy_top], PIPE_WIDTH, height_top):
                    b.alive = False
                    break
            i += 1
            
    def step_pipes(self):
        BIRD_RADIUS = self.settings['BIRD_RADIUS']
        PIPE_WIDTH = self.settings['PIPE_WIDTH']
        RIGHT = self.settings['RIGHT']
        
        passed_pipe = False
        if not self.alive:
            return [0]*len(self.birds)
        for i,p in enumerate(self.pipes):
            p.step()
            if p.x + PIPE_WIDTH + BIRD_RADIUS < 0:
                self.pipes.pop(i)
                self.pipes.append(Pipe(RIGHT, self.settings))
                passed_pipe = True
        return passed_pipe
    
    def step_birds(self):
        for b in self.birds:
            b.step(self.pipes[0])
        
    def step(self):
        ALIVE_REWARD = self.settings['ALIVE_REWARD']
        PIPE_REWARD = self.settings['PIPE_REWARD']
        MAX_STEPS = self.settings['MAX_STEPS']
        
        passed_pipe = self.step_pipes()
        self.step_birds()

        self.check_collision()
        self.steps += 1
        if not any([b.alive for b in self.birds]) or self.steps > MAX_STEPS:
            self.alive = False
            
        for b in self.birds:
            b.fitness += b.alive*(ALIVE_REWARD + passed_pipe*PIPE_REWARD)
                
    def fitness(self):
        return [b.fitness for b in self.birds]
        
    def plot(self, ax, draw_dead=False):
        for p in self.pipes:
            p.plot(ax)
        if len(self.birds) == 2:
            self.birds[0].plot(ax, draw_dead=draw_dead, color='b')
            self.birds[1].plot(ax, draw_dead=draw_dead, color='orange')
        else:
            for b in self.birds:                
                b.plot(ax, draw_dead=draw_dead)

    def play(self, draw=False, path="./", max_steps=None):
        MAX_STEPS = self.settings['MAX_STEPS']
        RIGHT = self.settings['RIGHT']
        TOP = self.settings['TOP']
        
        i = 0
        if max_steps is None:
            max_steps = MAX_STEPS
        while self.alive and i < max_steps:
            self.step()
            if draw:
                fig, ax = plt.subplots(figsize=(10,10))
                ax.set_xlim(-1, RIGHT)
                ax.set_ylim(0, TOP)
                ax.set_aspect('equal')
                self.plot(ax)
                ax.tick_params(left=False,
                bottom=False,
                labelleft=False,
                labelbottom=False)
                name = str(i).rjust(5,'0') + ".png"
                fig.savefig(os.path.join(path, name), bbox_inches='tight', dpi=200)
                plt.close()
            i += 1
        return self.birds