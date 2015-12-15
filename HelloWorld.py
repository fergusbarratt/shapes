import pygame
import numpy as np
pygame.init()

y = 0
x = 0
ydir = 1
xdir = 1
width = 800
height = 600
screen = pygame.display.set_mode((width, height))
linecolor = 255, 255, 255
bg_color = 0, 0, 0
running = 1

while running:
    event = pygame.event.poll()
    if event.type == pygame.QUIT:
        running = 0
    elif event.type == pygame.MOUSEMOTION:
        print("mouse at ({a} {b})".format(a=event.pos[0], b=event.pos[1]))
    screen.fill(bg_color)
    pygame.display.flip()
