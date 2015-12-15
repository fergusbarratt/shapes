import pygame_sdl2 as pygame
import sys
from pygame_sdl2.locals import *
import pygame_sdl2.gfxdraw as pygamegfx
import numpy as np
pygame.init()

size = width, height = 320, 240
middleScreen = int(width/2), int(height/2)
velocity = [0, 0]
black = 0, 0, 0
red = 255, 0, 0
white = 255, 255, 255

# Models
class Shape(object):
    def __init__(self, location, colour, velocity, size):
        if pygame.display.get_surface():
            self.screen = pygame.display.get_surface()
        else:
            self.screen = pygame.display.set_mode(size)
        self.location = np.array(location)
        self.colour = np.array(colour)
        self.velocity = np.array(velocity)
        self.padding = np.array([2, 2])
        self.dead = False

    def speed(self):
        return np.sqrt(sum(x**2 for x in self.velocity))

    def move(self, velocity=None):
        if velocity is not None:
            self.velocity = velocity
        self.location += self.velocity
        if not self.dead:
            self.draw()

    def destroy(self):
        self.dead = True

class Ball(Shape):
    def __init__(self, radius, location,  colour, velocity, size=(640, 480)):
        Shape.__init__(self, location, colour, velocity, size)

        self.radius = np.asarray(radius)
        self.border = np.asarray([radius, radius]) + self.padding
        self.draw()

    def _build_params(self):
        return (self.screen, *self.location, self.radius,  list(self.colour))
    def draw(self):
        pygamegfx.aacircle(*self._build_params())

class Rectangle(Shape):
    def __init__(self, width, height, location, colour, velocity, size=(320, 240)):
        Shape.__init__(self, location, colour, velocity, size)

        self.width = np.asarray(width)
        self.height = np.asarray(height)
        self.border = np.asarray([width/2, height/2]) + self.padding

    def _build_params(self):
        '''self.location gets shifted because i chose center and pygame likes top right edge'''
        return (self.screen, pygame.Rect(*(np.array(self.location)-np.array([self.width/2, self.height/2])), self.width, self.height), list(self.colour))

    def draw(self):
        pygamegfx.rectangle(*self._build_params())

class Triangle(Shape):
    def __init__(self, top, left, right, location, colour, velocity, size=(680, 480)):
        Shape.__init__(self, location, colour, velocity, size)

        self.top = top
        self.left = left
        self.right = right
        self.border = np.array([abs(2 * left), abs(2 * top)])

    def _build_params(self):
        return (self.screen, *(self.location + self.top * np.array([0, 1])), *(self.location + self.left * np.array([-1, -1])), *(self.location + self.right * np.array([1, -1])), list(self.colour))

    def draw(self):
        pygamegfx.trigon(*self._build_params())

class Player(Triangle):
    def __init__(self, items, initial_position=middleScreen):
        Triangle.__init__(self, -7, -5, -5, initial_position, red, [0, 0], size=(680, 480))
        items.update({"player":self})
        self.bullet_speed = 2
        self.items = items
        self.bullets = []

    def fire_bullet(self):
        bullet = Bullet(self)
        if np.asarray(self.velocity).any():
            bullet.velocity = np.asarray(self.velocity) * self.bullet_speed
        else:
            bullet.velocity = self.bullet_speed * np.array([0, 1])
        self.bullets.append(bullet)
        return self.bullets

class Bullet(Ball):
    def __init__(self, player):
        Ball.__init__(self, 2, player.location-player.top+5, red, player.velocity)

# Controller
class FrameWatcher():
    def __init__(self):
        self._check_screen()
        self.collisions = 0

    def _check_screen(self):
        self.screen = pygame.display.get_surface()
        self.xlim, self.ylim = self.screen.get_size()
        self.xmin, self.ymin = 0, 0

    def _distance(self, item_1, item_2):
        return np.sqrt((item_1.location[0]-item_2.location[0])**2+(item_1.location[1]-item_2.location[1])**2)

    def _displacement(self, item_1, item_2):
        return item_1.location-item_2.location

    def _normalise(self, vector):
        return np.asarray(vector)/np.sqrt(sum([x**2 for x in vector]))

    def handle_collision(self, item_1, item_2):
        self.collisions += 1
        items_displacement = [d for d in self._displacement(item_1, item_2)]
        new_velocity_1 = item_1.speed() * self._normalise(np.asarray(item_1.velocity) + np.asarray(items_displacement))
        new_velocity_2 = item_2.speed() * self._normalise(np.asarray(item_2.velocity) - np.asarray(items_displacement))
            # very hacky things here
        item_1.velocity = [int(d) for d in 1 + (0.75 + np.random.random_sample() / 2) * new_velocity_1]
        item_2.velocity = [int(d) for d in 1 + (0.75 + np.random.random_sample() / 2) * new_velocity_2]

    # def handle_coincidence(self, item_1, item_2):
    #     pass

    def check(self, view, interactions=True, walls="hard", bullet=False):
        # Initialisations
        items = [item for item in view.data]
        locations = [item.location for item in items]
        # Check Boundaries
        if walls is "hard":
            for item in items:
                x, y = item.location
                xmin, ymin = np.array([self.xmin, self.ymin]) + item.border + item.padding
                xlim, ylim = np.array([self.xlim, self.ylim]) - item.border - item.padding
                if x > xlim or x < xmin:
                    item.velocity[0] = -item.velocity[0]
                if y > ylim or y < ymin:
                    item.velocity[1] = -item.velocity[1]
        elif walls is "soft":
            for item in items:
                x, y = item.location
                xmin, ymin = np.array([self.xmin, self.ymin]) + item.border + item.padding
                xlim, ylim = np.array([self.xlim, self.ylim]) - item.border - item.padding
                if x > xlim:
                    item.location = item.location - np.array([self.xlim, 0])
                if x < xmin:
                    item.location = item.location + np.array([self.xlim, 0])
                if y > ylim:
                    item.location = item.location - np.array([0, self.ylim])
                if y < ymin:
                    item.location = item.location + np.array([0, self.ylim])

        if interactions:
            # Check Collisions
            for current_location in enumerate(locations):
                current_item = items[current_location[0]]
                for other_location in enumerate(locations):
                    other_item = items[other_location[0]]
                    if not current_item == other_item:
                        if self._distance(current_item, other_item) < 2*max(current_item.border) and self._distance(current_item, other_item) > max(current_item.border):
                            self.handle_collision(current_item, other_item)
                        # elif self._distance(current_item, other_item) < max(current_item.border):
                        #     self.handle_coincidence(current_item, other_item)

# View
class ViewArray():
    def __init__(self, n_balls, n_rects, n_triangles):

        balls = [Ball(10, np.random.randint(10, 100, 2), white, [i, j]) for i,j in zip([np.random.randint(-5, 5) for _ in range (1, n_balls+1)], [np.random.randint(-5, 5) for _ in range(1, n_balls+1)])]

        rects = [Rectangle(20, 20, np.random.randint(10, 100, 2), white, [i, j]) for i,j in zip([np.random.randint(-5, 5) for _ in range (1, n_rects+1)], [np.random.randint(-5, 5) for _ in range(1, n_rects+1)])]

        tris = [Triangle(10, 10, 10, np.random.randint(10, 100, 2), white, [i, j]) for i,j in zip([np.random.randint(-5, 5) for _ in range (1, n_triangles+1)], [np.random.randint(-5, 5) for _ in range(1, n_triangles+1)])]

        self.dict = {"background": balls+rects+tris}
        self.data = [datum for row in self.dict.values() for datum in row]
        self.has_player = False
        self.n_bullets = 0

    def __iter__(self):
        return self.dict.__iter__()

    def __contains__(self, item):
        if item in self.dict:
            return True
        else:
            return False

    def __getitem__(self, key):
        '''assume key is a tuple of type, then number'''
        if key == "player":
            return self.dict["player"][0]
        return self.dict[key[0]][key[1]]

    def update(self, dict_items=None):
        '''called whenever draw data needs to be updated'''
        if dict_items:
            self.dict.update(dict_items)
            self.data = [datum for row in self.dict.values() for datum in row]


    def draw(self):
        '''executed on each game loop'''
        self.data[0].screen.fill(black)
        for object in self.data:
            object.move()

    def add_player(self):
        '''player is not in a list because there can be only one'''
        self.has_player = True
        self.player = Player(self.dict)
        self.update({"player":[self.player]})

# Initializations
view = ViewArray(2, 0, 0)
view.add_player()
b = FrameWatcher()
walls = False


# Game loop
while 1:
    for event in pygame.event.get():
        if event.type == QUIT:
            sys.exit()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            walls = walls is False
        elif event.type == pygame.KEYDOWN:
            if event.key == K_RIGHT:
                view["player"].velocity += np.array([1, 0])
            if event.key == K_LEFT:
                view["player"].velocity -= np.array([1, 0])
            if event.key == K_UP:
                view["player"].velocity -= np.array([0, 1])
            if event.key == K_DOWN:
                view["player"].velocity +=np.array([0, 1])
            if event.key == K_SPACE:
                view.update({"bullets": view["player"].fire_bullet()})

    view.draw()

    if walls:
        b.check(view, walls="soft")
    else:
        b.check(view, walls="hard")

    pygame.display.flip()

