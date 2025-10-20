#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ultra Mario Forever HDR v1.3 — Fixed Edition (Miyamoto Homage)
Pure Pygame, asset-free procedural Mario-like platformer.
(C) 2025 FlamesCo / Samsoft — GPL-3.0-or-later
"""

import sys, math, random, pygame
from enum import Enum

# ------------------------------------------------------------------
# Init
# ------------------------------------------------------------------
pygame.init()
pygame.mixer.quit()

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
SCREEN_W, SCREEN_H = 640, 480
FPS = 60
TILE = 16

# Colors
SKY_DAY = (120, 180, 255)
SKY_NIGHT = (40, 60, 120)
UNDERGROUND_SKY = (20, 20, 40)
CASTLE_SKY = (70, 70, 70)
GROUND_BROWN = (150, 90, 40)
BRICK = (180, 90, 30)
BLOCK_SOLID = (170, 100, 50)
PIPE_GREEN = (0, 170, 0)
MARIO_RED = (230, 40, 30)
WHITE = (255, 255, 255)
LAVA = (220, 50, 20)
FLAG = (240, 240, 240)
FLAG_POLE = (180, 180, 180)

# Physics
GRAVITY = 0.8
MAX_FALL = 12
JUMP = -11
ACCEL = 0.4
FRICTION = 0.85
MAX_SPEED = 3.5

class GameState(Enum):
    MENU=0; MAP=1; LEVEL=2; VICTORY=3; DEAD=4
class Theme(Enum):
    OVERWORLD=0; UNDERGROUND=1; NIGHT=2; CASTLE=3

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def clamp(v, lo, hi): return max(lo, min(v, hi))
def theme_colors(theme):
    return {
        Theme.OVERWORLD:(SKY_DAY,GROUND_BROWN),
        Theme.UNDERGROUND:(UNDERGROUND_SKY,(60,60,100)),
        Theme.NIGHT:(SKY_NIGHT,(110,70,30)),
        Theme.CASTLE:(CASTLE_SKY,(90,90,90))
    }[theme]

# ------------------------------------------------------------------
# Entities
# ------------------------------------------------------------------
class Mario(pygame.sprite.Sprite):
    def __init__(self,x,y):
        super().__init__()
        self.w,self.h=16,32
        self.image=pygame.Surface((self.w,self.h)); self.image.fill(MARIO_RED)
        self.rect=self.image.get_rect(topleft=(x,y))
        self.velx=self.vely=0; self.on_ground=False
    def update(self,keys,solids):
        # Horizontal input
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: self.velx-=ACCEL
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]: self.velx+=ACCEL
        else: self.velx*=FRICTION
        self.velx=clamp(self.velx,-MAX_SPEED,MAX_SPEED)
        # Jump
        if self.on_ground and (keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]):
            self.vely=JUMP; self.on_ground=False
        # Gravity
        self.vely=clamp(self.vely+GRAVITY,-999,MAX_FALL)
        # X move
        self.rect.x+=int(self.velx); self.collide(solids,self.velx,0)
        # Y move
        self.rect.y+=int(self.vely); self.on_ground=False; self.collide(solids,0,self.vely)
    def collide(self,solids,dx,dy):
        for b in solids:
            if self.rect.colliderect(b.rect):
                if dx>0: self.rect.right=b.rect.left; self.velx=0
                if dx<0: self.rect.left=b.rect.right; self.velx=0
                if dy>0: self.rect.bottom=b.rect.top; self.vely=0; self.on_ground=True
                if dy<0: self.rect.top=b.rect.bottom; self.vely=0

class Solid(pygame.sprite.Sprite):
    def __init__(self,x,y,w,h,color=BLOCK_SOLID):
        super().__init__()
        self.image=pygame.Surface((w,h)); self.image.fill(color)
        self.rect=self.image.get_rect(topleft=(x,y))

class Pipe(pygame.sprite.Sprite):
    def __init__(self,x,ground_top_y,height):
        super().__init__()
        self.image=pygame.Surface((TILE*2,height)); self.image.fill(PIPE_GREEN)
        self.rect=self.image.get_rect(bottomleft=(x,ground_top_y))

class FlagPole(pygame.sprite.Sprite):
    def __init__(self,x,ground_top_y,h=TILE*5):
        super().__init__()
        self.image=pygame.Surface((6,h)); self.image.fill(FLAG_POLE)
        self.rect=self.image.get_rect(bottomleft=(x,ground_top_y))
        self.flag=pygame.Rect(self.rect.left+4,self.rect.top+10,16,8)
    def draw(self,surf,camx):
        surf.blit(self.image,(self.rect.x-camx,self.rect.y))
        pygame.draw.rect(surf,FLAG,self.flag.move(-camx,0))

class Hazard(pygame.sprite.Sprite):
    def __init__(self,x,y,w,h,color=LAVA):
        super().__init__()
        self.image=pygame.Surface((w,h)); self.image.fill(color)
        self.rect=self.image.get_rect(topleft=(x,y))

# ------------------------------------------------------------------
# Level generation
# ------------------------------------------------------------------
class Level:
    def __init__(self,world,stage,theme,width_px,ground_top_y,solids,pipes,hazards,flagpole):
        self.world,self.stage,self.theme=world,stage,theme
        self.width_px,self.ground_top_y=width_px,ground_top_y
        self.solids,self.pipes,self.hazards,self.flagpole=solids,pipes,hazards,flagpole

def choose_theme(world,stage):
    return [Theme.OVERWORLD,Theme.UNDERGROUND,Theme.NIGHT,Theme.CASTLE][(stage-1)%4]

def build_level(world,stage,mario):
    random.seed(world*777+stage*19)
    theme=choose_theme(world,stage)
    sky,ground_color=theme_colors(theme)
    solids,pipes,hazards=pygame.sprite.Group(),pygame.sprite.Group(),pygame.sprite.Group()
    base_tiles=120; width_tiles=base_tiles+world*8+(stage-1)*4; width_px=width_tiles*TILE
    ground_top_y=SCREEN_H-TILE*3

    # Lava for castles
    if theme==Theme.CASTLE:
        hazards.add(Hazard(0,ground_top_y+TILE*2,width_px,TILE))

    phase_len=width_tiles//3
    x_tile=0
    for phase in range(3):
        gap_chance=0.07+0.02*phase
        pipe_spacing=max(5,12-world//2-phase)
        phase_end=x_tile+phase_len
        # Ground/gaps
        while x_tile<phase_end:
            if random.random()<gap_chance and x_tile>6:
                x_tile+=random.randint(1,2+phase)
            else:
                span=random.randint(4,9)
                for i in range(span):
                    gx=(x_tile+i)*TILE
                    solids.add(Solid(gx,ground_top_y,TILE,TILE,ground_color))
                    solids.add(Solid(gx,ground_top_y+TILE,TILE,TILE,ground_color))
                x_tile+=span
        # Pipes
        px=(phase_end-phase_len)*TILE+TILE*8
        while px<phase_end*TILE-10*TILE:
            pipe_h=mario.h+random.randint(0,TILE*(1+phase))
            pipes.add(Pipe(px,ground_top_y,pipe_h))
            px+=TILE*(pipe_spacing+random.randint(0,2))
        x_tile=phase_end

    # Pyramid
    base_x=random.randint(TILE*20,width_px-TILE*40)
    steps=random.randint(3,5)
    for h in range(steps):
        for i in range(steps-h):
            solids.add(Solid(base_x+i*TILE,ground_top_y-h*TILE,TILE,TILE,BLOCK_SOLID))

    flag_x=width_px-TILE*8
    flagpole=FlagPole(flag_x,ground_top_y,TILE*(4+world//2))
    solids.add(Solid(flag_x-TILE*3,ground_top_y,TILE*5,TILE,BRICK))
    return Level(world,stage,theme,width_px,ground_top_y,solids,pipes,hazards,flagpole)

# ------------------------------------------------------------------
# Camera
# ------------------------------------------------------------------
class Camera:
    def __init__(self,level_width_px):
        self.camx=0; self.level_width_px=level_width_px
    def update(self,focus_rect):
        target=focus_rect.centerx-int(SCREEN_W*0.4)
        self.camx=clamp(target,0,self.level_width_px-SCREEN_W)

# ------------------------------------------------------------------
# UI
# ------------------------------------------------------------------
def draw_text(surf,text,x,y,size=18,color=WHITE,center=False):
    font=pygame.font.SysFont("Arial",size,bold=True)
    img=font.render(text,True,color)
    rect=img.get_rect(center=(x,y) if center else (x,y))
    surf.blit(img,rect)

# ------------------------------------------------------------------
# Game
# ------------------------------------------------------------------
class Game:
    def __init__(self):
        self.screen=pygame.display.set_mode((SCREEN_W,SCREEN_H))
        pygame.display.set_caption("Ultra Mario Forever HDR — Fixed Edition")
        self.clock=pygame.time.Clock()
        self.state=GameState.MENU
        self.world=self.stage=1
        self.mario=Mario(50,SCREEN_H-100)
        self.level=None; self.camera=None
        self.sky_color,self.ground_color=SKY_DAY,GROUND_BROWN
        self.death_timer=self.victory_timer=0

    def start_level(self,world,stage):
        self.world,self.stage=world,stage
        self.mario=Mario(TILE*2,0)
        self.level=build_level(world,stage,self.mario)
        self.camera=Camera(self.level.width_px)
        self.sky_color,self.ground_color=theme_colors(self.level.theme)
        self.mario.rect.topleft=(TILE*2,self.level.ground_top_y-self.mario.h)
        self.state=GameState.LEVEL; self.death_timer=self.victory_timer=0

    # --- State Updates ---
    def update_menu(self,keys,events):
        self.screen.fill(SKY_DAY)
        draw_text(self.screen,"Ultra Mario Forever HDR",SCREEN_W//2,80,28,WHITE,True)
        draw_text(self.screen,"Press ENTER to select world/stage",SCREEN_W//2,150,18,WHITE,True)
        for e in events:
            if e.type==pygame.KEYDOWN and e.key==pygame.K_RETURN:
                self.state=GameState.MAP

    def update_map(self,keys,events):
        self.screen.fill(SKY_DAY)
        draw_text(self.screen,"SELECT WORLD / STAGE",SCREEN_W//2,60,22,WHITE,True)
        for e in events:
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_LEFT: self.world=max(1,self.world-1)
                if e.key==pygame.K_RIGHT: self.world=min(8,self.world+1)
                if e.key==pygame.K_UP: self.stage=min(4,self.stage+1)
                if e.key==pygame.K_DOWN: self.stage=max(1,self.stage-1)
                if e.key==pygame.K_RETURN: self.start_level(self.world,self.stage)
                if e.key==pygame.K_ESCAPE: self.state=GameState.MENU
        draw_text(self.screen,f"World {self.world}-{self.stage}",SCREEN_W//2,150,20,WHITE,True)

    def check_death(self):
        if self.mario.rect.top>SCREEN_H+50: return True
        return any(self.mario.rect.colliderect(hz.rect) for hz in self.level.hazards)

    def update_level(self,keys,events):
        for e in events:
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_r: self.start_level(self.world,self.stage); return
                if e.key==pygame.K_ESCAPE: self.state=GameState.MAP; return
        solids=self.level.solids.copy(); solids.add(*self.level.pipes)
        self.mario.update(keys,solids); self.camera.update(self.mario.rect)
        # Flag
        if self.mario.rect.colliderect(self.level.flagpole.rect.union(self.level.flagpole.flag)):
            self.victory_timer+=1
            if self.victory_timer>FPS*0.5: self.state=GameState.VICTORY; self.victory_timer=0
        else: self.victory_timer=0
        # Death
        if self.check_death():
            self.death_timer+=1
            if self.death_timer>FPS*0.3: self.state=GameState.DEAD; self.death_timer=0
        else: self.death_timer=0
        self.draw_level()

    def draw_level(self):
        self.screen.fill(self.sky_color); camx=self.camera.camx
        for grp in (self.level.solids,self.level.pipes,self.level.hazards):
            for s in grp: self.screen.blit(s.image,(s.rect.x-camx,s.rect.y))
        self.level.flagpole.draw(self.screen,camx)
        self.screen.blit(self.mario.image,(self.mario.rect.x-camx,self.mario.rect.y))
        draw_text(self.screen,f"W{self.world}-{self.stage}",12,8,18,WHITE)

    def update_victory(self,keys,events):
        self.screen.fill(SKY_DAY)
        draw_text(self.screen,f"Cleared W{self.world}-{self.stage}!",SCREEN_W//2,120,24,WHITE,True)
        draw_text(self.screen,"ENTER: Next   ESC: Select",SCREEN_W//2,170,18,WHITE,True)
        for e in events:
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_RETURN:
                    nw,ns=self.world,(self.stage%4)+1
                    if ns==1: nw=(self.world%8)+1
                    self.start_level(nw,ns)
                if e.key==pygame.K_ESCAPE: self.state=GameState.MAP

    def update_dead(self,keys,events):
        self.screen.fill((30,0,0))
        draw_text(self.screen,"Ouch! Try again.",SCREEN_W//2,120,24,WHITE,True)
        draw_text(self.screen,"ENTER: Retry   ESC: Select",SCREEN_W//2,170,18,WHITE,True)
        for e in events:
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_RETURN: self.start_level(self.world,self.stage)
                if e.key==pygame.K_ESCAPE: self.state=GameState.MAP

    def run(self):
        while True:
            keys=pygame.key.get_pressed()
            events=pygame.event.get()
            for e in events:
                if e.type==pygame.QUIT or (e.type==pygame.KEYDOWN and e.key==pygame.K_q):
                    pygame.quit(); sys.exit()
            if self.state==GameState.MENU: self.update_menu(keys,events)
            elif self.state==GameState.MAP: self.update_map(keys,events)
            elif self.state==GameState.LEVEL: self.update_level(keys,events)
            elif self.state==GameState.VICTORY: self.update_victory(keys,events)
            elif self.state==GameState.DEAD: self.update_dead(keys,events)
            pygame.display.flip(); self.clock.tick(FPS)

# ------------------------------------------------------------------
def main(): Game().run()
if __name__=="__main__": main()
