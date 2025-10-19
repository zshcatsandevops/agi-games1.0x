#!/usr/bin/env python3
"""
Ultra Mario Forever HDR v1.1
------------------------------------
Pure Pygame build — no assets, no wav.
Features:
 - Mario-height pipes (auto-sized)
 - Menu, simple overworld, level demo
 - SMB1-style physics
(C) 2025 FlamesCo / Samsoft
"""

import sys
import math
import pygame
from enum import Enum

pygame.init()
pygame.mixer.quit()  # disable audio for asset-free mode

# ---------------------------------------------------
# Constants
# ---------------------------------------------------
SCREEN_W, SCREEN_H = 640, 400
FPS = 60
TILE = 24

# Colors
SKY = (120, 180, 255)
GROUND = (150, 90, 40)
PIPE_GREEN = (0, 170, 0)
BRICK = (180, 90, 30)
MARIO_RED = (230, 40, 30)
WHITE = (255, 255, 255)

# ---------------------------------------------------
# Mario Physics
# ---------------------------------------------------
GRAVITY = 0.9
MAX_FALL = 10
JUMP = -12
ACCEL = 0.35
FRICTION = 0.86
MAX_SPEED = 4.2


class GameState(Enum):
    MENU = 0
    MAP = 1
    LEVEL = 2


# ---------------------------------------------------
# Entities
# ---------------------------------------------------
class Mario(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.w = 22
        self.h = 32
        self.image = pygame.Surface((self.w, self.h))
        self.image.fill(MARIO_RED)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.velx = 0
        self.vely = 0
        self.on_ground = False

    def update(self, keys, blocks):
        if keys[pygame.K_LEFT]:
            self.velx -= ACCEL
        elif keys[pygame.K_RIGHT]:
            self.velx += ACCEL
        else:
            self.velx *= FRICTION

        self.velx = max(-MAX_SPEED, min(MAX_SPEED, self.velx))
        if self.on_ground and keys[pygame.K_SPACE]:
            self.vely = JUMP
            self.on_ground = False

        self.vely += GRAVITY
        if self.vely > MAX_FALL:
            self.vely = MAX_FALL

        self.rect.x += int(self.velx)
        self.collide(blocks, self.velx, 0)
        self.rect.y += int(self.vely)
        self.on_ground = False
        self.collide(blocks, 0, self.vely)

    def collide(self, blocks, vx, vy):
        for b in blocks:
            if self.rect.colliderect(b.rect):
                if vx > 0:
                    self.rect.right = b.rect.left
                    self.velx = 0
                if vx < 0:
                    self.rect.left = b.rect.right
                    self.velx = 0
                if vy > 0:
                    self.rect.bottom = b.rect.top
                    self.vely = 0
                    self.on_ground = True
                if vy < 0:
                    self.rect.top = b.rect.bottom
                    self.vely = 0


class Block(pygame.sprite.Sprite):
    def __init__(self, x, y, w, h, color=BRICK):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill(color)
        self.rect = self.image.get_rect(topleft=(x, y))


class Pipe(pygame.sprite.Sprite):
    def __init__(self, x, y, mario_height):
        super().__init__()
        # height matches Mario's current sprite height
        h = mario_height
        self.image = pygame.Surface((TILE * 2, h))
        self.image.fill(PIPE_GREEN)
        self.rect = self.image.get_rect(bottomleft=(x, y))


# ---------------------------------------------------
# Level builder
# ---------------------------------------------------
def build_level(mario):
    blocks = pygame.sprite.Group()
    ground_y = SCREEN_H - TILE * 2
    for i in range(0, SCREEN_W, TILE):
        b = Block(i, ground_y, TILE, TILE * 2, GROUND)
        blocks.add(b)

    # Example pipes — all match Mario height dynamically
    pipe1 = Pipe(200, ground_y, mario.h)
    pipe2 = Pipe(400, ground_y, mario.h)
    blocks.add(pipe1)
    blocks.add(pipe2)
    return blocks


# ---------------------------------------------------
# Main game loop
# ---------------------------------------------------
def main():
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()
    state = GameState.LEVEL

    mario = Mario(50, SCREEN_H - 100)
    blocks = build_level(mario)
    all_sprites = pygame.sprite.Group(mario, *blocks)

    while True:
        keys = pygame.key.get_pressed()
        for e in pygame.event.get():
            if e.type == pygame.QUIT or keys[pygame.K_ESCAPE]:
                pygame.quit()
                sys.exit()

        if state == GameState.LEVEL:
            mario.update(keys, blocks)

        # Draw
        screen.fill(SKY)
        for b in blocks:
            screen.blit(b.image, b.rect)
        screen.blit(mario.image, mario.rect)

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
