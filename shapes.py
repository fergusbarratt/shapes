import pygame_sdl2 as pygame
import sys
from pygame_sdl2.locals import *
import pygame_sdl2.gfxdraw as pygamegfx
import numpy as np
import copy
pygame.init()

size = width, height = 640, 480
middleScreen = int(width/2), int(height/2)
velocity = [0, 0]
black = 0, 0, 0
red = 255, 0, 0
green = 0, 255, 0
white = 255, 255, 255


# numpy additions
class Tools(object):
    def _normalise(self, vector):
        if np.linalg.norm(vector) != 0:
            return np.asarray(vector) / np.linalg.norm(vector)
        else:
            return vector

    def _flatten(self, vector):
        return [elem for sublist in [vector] for elem in sublist]

    def _check_screen(self):
        self.screen = pygame.display.get_surface()
        self.xlim, self.ylim = self.screen.get_size()
        self.xmin, self.ymin = 0, 0

# Models
# Base
class Shape(Tools):
    def __init__(self, location, colour, velocity, size):
        if pygame.display.get_surface():
            self.screen = pygame.display.get_surface()
        else:
            self.screen = pygame.display.set_mode(size)
        self.location = np.array(location)
        self.original_location = np.copy(location)
        self.colour = np.array(colour)
        self.velocity = np.array(velocity)
        self.original_velocity = np.copy(velocity)
        self.padding = np.array([2, 2])
        self.dead = False
        self.direction = np.array([1, 0])
        self.fix_orientation = False
        self.boundary_counter = 1
        self.mass = 100

    def _rotate(self, theta):
        return np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])

    def re_orient(self, draw_points):
        if np.asarray(self.velocity).any() and np.asarray(self.direction).any() and self.fix_orientation:
            angle = self._normalise(self.direction).dot(self._normalise(self.velocity))/(np.linalg.norm(self.direction) * np.linalg.norm(self.velocity))
            rotation_matrix = self._rotate(angle)
            self.direction = np.copy(self.velocity)
            return [rotation_matrix.dot(point) for point in draw_points]
        else:
            return draw_points

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

    def dead_action(self):
        return [  ]

    def reset(self):
        self.location = np.copy(self.original_location)
        self.velocity = np.copy(self.original_velocity)

class Ball(Shape):
    def __init__(self, radius, location,  colour, velocity, size=(640, 480)):
        Shape.__init__(self, location, colour, velocity, size)

        self.radius = np.asarray(radius)
        self.border = np.asarray([radius, radius]) + self.padding
        self.calculate_mass()
        self.re_born_counter = 0

    def calculate_mass(self):
        self.area = np.pi * self.radius ** 2
        self.density = 1
        self.mass = self.area * self.density

    def _build_params(self):
        return (self.screen, *self.location, self.radius,  list(self.colour))

    def dead_action(self, duplicate=False):
        self.radius = 0.5 * self.radius
        self.calculate_mass()
        if self.re_born_counter < 2:
            self.re_born_counter += 1
            if duplicate:
                copy1 = copy.copy(self)
                copy1.location = self.location+ np.array([10, 10])
                return [self, copy1]
            else:
                return [self]
        else:
            return None


    def draw(self):
        pygamegfx.aacircle(*self._build_params())

class Rectangle(Shape):
    def __init__(self, width, height, location, colour, velocity, size=(640, 480)):
        Shape.__init__(self, location, colour, velocity, size)

        self.width = np.array(width)
        self.height = np.array(height)
        self.border = np.array([width/2, height/2]) + self.padding
        self.calculate_mass()
        self.fix_orientation = True
        self.draw_points = [np.array([self.width/2, self.height/2]), np.array([self.width/2, -self.height/2]), np.array([-self.width/2, -self.height/2]), np.array([-self.width/2, self.height/2])]

    def calculate_mass(self):
        self.area = self.width * self.height
        self.density = 1
        self.mass = self.area * self.density

    def _build_params(self):
        self.draw_points = self.re_orient(self.draw_points)
        points = [self.location + point for point in self.draw_points]
        return (self.screen, points, list(self.colour))

    def draw(self):
        pygamegfx.aapolygon(*self._build_params())

class Triangle(Shape):
    def __init__(self, top, left, right, location, colour, velocity, size=(680, 480)):
        Shape.__init__(self, location, colour, velocity, size)

        self.top = top * np.array([0, 1])
        self.fix_orientation = True
        self.left = left * np.array([-1, -1])
        self.right = right * np.array([1, -1])
        self.draw_points = [self.top, self.left, self.right]
        self.border = np.array([abs(left), abs(top)])
        self.filled = False

    def calculate_mass(self):
        self.area = 0.5 * (self.right - self.left)[0] * (self.top + self.right)[1]
        self.density = 1
        self.mass = self.area * self.density

    def _build_params(self):
        self.draw_points = self.re_orient(self.draw_points)
        self.top = self.location + self.draw_points[0]
        self.left = self.location + self.draw_points[1]
        self.right = self.location + self.draw_points[2]
        return (self.screen, *self.top, *self.left, *self.right, list(self.colour))

    def draw(self):
        if self.filled:
            pygamegfx.filled_trigon(*self._build_params())
        else:
            pygamegfx.aatrigon(*self._build_params())


# Instantiations
class Player(Triangle):
    def __init__(self, items, initial_position=middleScreen):
        width = -10
        height = -10
        Triangle.__init__(self, height, width, width, initial_position, green, [0, 0], size=(680, 480))
        items.update({"player":self})
        self.direction = np.asarray([1, 0])
        self.has_fired = False
        self.bullet_speed = 2
        self.items = items
        self.bullets = []
        self.speed_tick = 3
        self.fix_orientation = True
        self.mass = 100
        self.filled = True

    def fire_bullet(self):
        self.has_fired = True
        if np.asarray(self.velocity).any():
            bullet_velocity = np.asarray(self.velocity) * self.bullet_speed
        else:
            bullet_velocity = -self.bullet_speed * np.array([0, 1])
        bullet = Bullet(self, bullet_velocity)
        self.bullets.append(bullet)
        return self.bullets

class Bullet(Ball):
    def __init__(self, player, bullet_velocity):
        if np.asarray(player.velocity).any():
            initial_location = np.asarray(player.location) + np.asarray(player.velocity) * 10
        else:
            initial_location = np.asarray(player.location) - np.array([0, 30])
        Ball.__init__(self, 2, initial_location, red, bullet_velocity)
        self.mass = 100


# Controller
class Frame(Tools):
    def __init__(self, view):
        self._check_screen()
        self.collisions = 0
        self.clock = pygame.time.Clock()
        self.view = view
        self.walls = False

    def _check_screen(self):
        self.screen = pygame.display.get_surface()
        self.xlim, self.ylim = self.screen.get_size()
        self.xmin, self.ymin = 0, 0

    def _distance(self, item_1, item_2):
        return np.sqrt((item_1.location[0] - item_2.location[0])**2 + (item_1.location[1]-item_2.location[1])**2)

    def _displacement(self, item_1, item_2):
        return item_1.location - item_2.location

    def _handle_collision(self, item_1, item_2, view):
        '''kill both items if either is a bullet (and neither is dead). Otherwise bounce'''
        self.collisions += 1
        if not (item_1.dead or item_2.dead):
            if view["player"].has_fired:
                if item_1 in view["bullets"] or item_2 in view["bullets"]:
                    if item_1 in view["background"] or item_2 in view["background"]:
                        item_1.dead = True
                        item_2.dead = True
            items_displacement = [d for d in self._displacement(item_1, item_2)]
            new_velocity_1 = item_2.speed()*(item_2.mass/item_1.mass) * self._normalise(np.asarray(item_1.velocity) + np.asarray(items_displacement))

            new_velocity_2 = item_1.speed()*(item_1.mass/item_2.mass) * self._normalise(np.asarray(item_2.velocity) - np.asarray(items_displacement))
                # very hacky things here
            item_1.velocity = [int(d) for d in 1 + (0.75 + np.random.random_sample() / 2) * new_velocity_1]
            item_2.velocity = [int(d) for d in 1 + (0.75 + np.random.random_sample() / 2) * new_velocity_2]

    def get_input(self):
        ''' input loop'''
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.walls = self.walls is False
            elif event.type == pygame.KEYDOWN:
                if event.key == K_RIGHT:
                    view["player"].velocity += np.array([view["player"].speed_tick, 0])
                if event.key == K_LEFT:
                    view["player"].velocity -= np.array([view["player"].speed_tick, 0])
                if event.key == K_UP:
                    view["player"].velocity -= np.array([0, view["player"].speed_tick])
                if event.key == K_DOWN:
                    view["player"].velocity +=np.array([0, view["player"].speed_tick])
                if event.key == K_SPACE:
                    view.update({"bullets": view["player"].fire_bullet()})

    def check(self, view, framerate=60, walls="hard", interactions=True):
        # Initialisations
        items = [item for item in view.data]
        locations = [item.location for item in items]

        # Check Boundaries
        if walls is "hard":
            for item in items:
                x, y = item.location
                xmin, ymin = np.array([self.xmin, self.ymin]) + item.border + item.padding
                xlim, ylim = np.array([self.xlim, self.ylim]) - item.border - item.padding
                item.bounced = True
                if x > xlim or x < xmin:
                    item.velocity[0] = -item.velocity[0]
                    item.location += np.asarray(item.velocity)
                    if x > xlim or x < xmin:
                        item.boundary_counter += 1
                        if item.boundary_counter > 100:
                            item.boundary_counter = 0
                            item.reset()
                elif y > ylim or y < ymin:
                    item.velocity[1] = -item.velocity[1]
                    item.location += np.asarray(item.velocity)
                    if y > ylim or y < ymin:
                        item.boundary_counter += 1
                        if item.boundary_counter > 100:
                            item.boundary_counter = 0
                            item.reset()
                else:
                    item.bounced = False

        elif walls is "soft":
            for item in items:
                x, y = item.location
                xmin, ymin = np.array([self.xmin, self.ymin]) + item.border + item.padding
                xlim, ylim = np.array([self.xlim, self.ylim]) - item.border - item.padding
                item.bounced = True
                if x > xlim:
                    item.location = item.location - np.array([self.xlim, 0])
                elif x < xmin:
                    item.location = item.location + np.array([self.xlim, 0])
                elif y > ylim:
                    item.location = item.location - np.array([0, self.ylim])
                elif y < ymin:
                    item.location = item.location + np.array([0, self.ylim])
                else:
                    item.bounced = False

        if interactions:
            # Detect Collisions
            for current_location in enumerate(locations):
                current_item = items[current_location[0]]
                for other_location in enumerate(locations):
                    other_item = items[other_location[0]]
                    if not current_item == other_item:
                        if self._distance(current_item, other_item) < 2 * max(current_item.border) and self._distance(current_item, other_item) > max(current_item.border):
                            self._handle_collision(current_item, other_item, view)
        self.clock.tick(framerate)


# View
class View(Tools):
    def __init__(self, n_balls, n_rects, n_triangles):

        balls = [Ball(10, np.random.randint(10, 100, 2), white, [i, j]) for i,j in zip([np.random.randint(-5, 5) for _ in range (1, n_balls+1)], [np.random.randint(-5, 5) for _ in range(1, n_balls+1)])]
        # width, height, location, colour, velocity
        rects = [Rectangle(13, 13, np.random.randint(10, 100, 2), white, [i, j]) for i,j in zip([np.random.randint(-5, 5) for _ in range (1, n_rects+1)], [np.random.randint(-5, 5) for _ in range(1, n_rects+1)])]
        print(rects[0].velocity)

        tris = [Triangle(10, 10, 10, np.random.randint(10, 100, 2), white, [i, j]) for i,j in zip([np.random.randint(-5, 5) for _ in range (1, n_triangles+1)], [np.random.randint(-5, 5) for _ in range(1, n_triangles+1)])]

        self.dict = {"background": balls+rects+tris}
        self.data = [datum for row in self.dict.values() for datum in row]
        self.has_player = False

    def __iter__(self):
        return self.dict.__iter__()

    def __contains__(self, item):
        if item in self.dict:
            return True
        else:
            return False

    def __getitem__(self, key):
        if key == "player":
            return self.dict["player"][0]
        return self.dict[key]

    def add_player(self):
        '''add player to list'''
        self.has_player = True
        self.player = Player(self.dict)
        self.update({"player":[self.player]})


    def update(self, dict_items=None):
        '''called whenever draw data needs to be updated'''
        if dict_items:
            self.dict.update(dict_items)
        self.data = [datum for row in self.dict.values() for datum in row]
        self.dead_data = (elem for elem in self.data if elem.dead)
        self.data = [elem for elem in self.data if not elem.dead]
        for lazarus in self.dead_data:
            if not isinstance(lazarus, Bullet):
                lazarus.dead = False
                self.data.append(lazarus.dead_action())
                self.dict["background"]+=lazarus.dead_action()
        # flatten & filter data
        self.data = [elem for sublist in [np.atleast_1d(x) for x in list(filter(None,  self.data))] for elem in sublist]

    def draw(self):
        '''executed on each game loop'''
        self.data[0].screen.fill(black)
        for object in self.data:
            if object:
                if not object.dead:
                    object.move()
        pygame.display.flip()


# Build the View, start the controller
view = View(20, 20, 20)
view.add_player()
frame = Frame(view)

# Game loop
while 1:
    frame.get_input()

    view.draw()

    if frame.walls:
        frame.check(view, walls="soft")
    else:
        frame.check(view, walls="hard")


