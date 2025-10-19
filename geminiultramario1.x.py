import pygame
import sys
import math
import numpy
from enum import Enum

# --- Initialization ---
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# --- Constants ---
SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480
FPS = 60
GRAVITY = 0.85
MAX_FALL_SPEED = 10
JUMP_VELOCITY = -13
WALK_ACCEL = 0.3
RUN_ACCEL = 0.5
MAX_WALK_SPEED = 4.0
MAX_RUN_SPEED = 6.5
FRICTION = 0.88
AIR_FRICTION = 0.94

# --- Colors ---
SKY_BLUE = (100, 149, 237)
UNDERGROUND_BLACK = (20, 12, 28)
CASTLE_GRAY = (40, 40, 40)
MARIO_RED = (255, 0, 0)
MARIO_SKIN = (253, 221, 178)
MARIO_HAIR = (139, 69, 19)
FIRE_MARIO_WHITE = (255, 255, 255)
GROUND_BROWN = (139, 69, 19)
BRICK_ORANGE = (205, 102, 0)
PIPE_GREEN = (0, 128, 0)
CLOUD_WHITE = (240, 248, 255)
GOOMBA_BROWN = (160, 82, 45)
KOOPA_GREEN = (0, 180, 0)
QUESTION_BLOCK_YELLOW = (255, 165, 0)
COIN_YELLOW = (255, 215, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# --- Screen & Font ---
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF | pygame.HWSURFACE)
pygame.display.set_caption("Ultra Mario Forever - World Tour")
clock = pygame.time.Clock()
try:
    hud_font = pygame.font.Font('font/emulogic.ttf', 16)
except:
    hud_font = pygame.font.Font(None, 22)

# --- Sound Generation ---
def generate_sound(frequency, duration, volume=0.1):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    buf = numpy.zeros((n_samples, 2), dtype=numpy.int16)
    max_sample = 2**(16 - 1) - 1
    for i in range(n_samples):
        t = float(i) / sample_rate
        wave = math.sin(2 * math.pi * frequency * t)
        fade_out = max(0, 1 - (t / duration))
        buf[i][0] = buf[i][1] = int(max_sample * wave * volume * fade_out)
    return pygame.sndarray.make_sound(buf)

sounds = {
    'jump': generate_sound(440.0, 0.15), 'coin': generate_sound(1046.5, 0.1),
    'stomp': generate_sound(220.0, 0.2), 'powerup': generate_sound(523.25, 0.4),
    'powerdown': generate_sound(349.23, 0.3), 'die': generate_sound(110.0, 0.8),
    'break_block': generate_sound(180.0, 0.2), 'level_complete': generate_sound(880.0, 0.5)
}

# --- Enums for States ---
class GameState(Enum):
    OVERWORLD = 0
    LEVEL = 1
    GAME_OVER = 2
    GAME_COMPLETE = 3

class PlayerState(Enum):
    SMALL = 0
    SUPER = 1
    FIRE = 2

class BlockType(Enum):
    GROUND = 0
    BRICK = 1
    QUESTION = 2
    PIPE = 3
    CLOUD = 4
    USED = 5

# --- Game Object Classes ---
class Player:
    def __init__(self):
        self.state = PlayerState.SMALL
        self.set_size()
        self.rect = pygame.Rect(50, SCREEN_HEIGHT - 100, self.width, self.height)
        self.vel_x, self.vel_y, self.acc_x = 0, 0, 0
        self.on_ground = False
        self.facing_right = True
        self.running = False
        self.invincible_timer = 0
        self.jump_buffer, self.coyote_time = 0, 0
        self.lives, self.coins, self.score = 5, 0, 0
        self.fireball_cooldown = 0
        
    def set_size(self):
        if self.state == PlayerState.SMALL: self.width, self.height = 20, 20
        else: self.width, self.height = 20, 40

    def update(self, world_objects, enemies, coins, items, fireballs):
        if self.invincible_timer > 0: self.invincible_timer -= 1
        if self.fireball_cooldown > 0: self.fireball_cooldown -=1
        
        max_speed = MAX_RUN_SPEED if self.running else MAX_WALK_SPEED
        self.vel_x += self.acc_x
        self.vel_x *= FRICTION if self.on_ground else AIR_FRICTION
        self.vel_x = max(-max_speed, min(max_speed, self.vel_x))
        if abs(self.vel_x) < 0.1: self.vel_x = 0
        self.rect.x += self.vel_x
        self.check_collision_x(world_objects)
        
        self.vel_y = min(self.vel_y + GRAVITY, MAX_FALL_SPEED)
        self.rect.y += self.vel_y
        
        if self.on_ground: self.coyote_time = 6
        elif self.coyote_time > 0: self.coyote_time -= 1
        self.on_ground = False
        self.check_collision_y(world_objects)
        
        if self.jump_buffer > 0:
            self.jump_buffer -= 1
            if self.on_ground or self.coyote_time > 0:
                self.jump(); self.jump_buffer = 0
        
        if self.rect.top > SCREEN_HEIGHT + 100: self.die()
        self.handle_enemy_collisions(enemies)
        self.handle_item_collection(items, coins)

    def handle_enemy_collisions(self, enemies):
        for enemy in enemies[:]:
            if self.rect.colliderect(enemy.rect):
                if self.vel_y > 0 and self.rect.bottom < enemy.rect.centery:
                    sounds['stomp'].play()
                    self.vel_y = JUMP_VELOCITY * 0.6
                    enemy.is_stomped = True; self.score += 100
                elif self.invincible_timer == 0: self.hit()

    def handle_item_collection(self, items, coins):
        for coin in coins[:]:
            if self.rect.colliderect(coin.rect):
                sounds['coin'].play()
                self.coins += 1; self.score += 50
                if self.coins >= 100: self.coins = 0; self.lives += 1
                coins.remove(coin)
        for item in items[:]:
            if self.rect.colliderect(item.rect):
                if item.type == "mushroom" and self.state == PlayerState.SMALL:
                    self.power_up(PlayerState.SUPER); items.remove(item)
                elif item.type == "flower":
                    self.power_up(PlayerState.FIRE); items.remove(item)
    
    def check_collision_x(self, world_objects):
        for obj in world_objects:
            if self.rect.colliderect(obj.rect):
                if self.vel_x > 0: self.rect.right = obj.rect.left
                elif self.vel_x < 0: self.rect.left = obj.rect.right
                self.vel_x = 0

    def check_collision_y(self, world_objects):
        for obj in world_objects:
            if self.rect.colliderect(obj.rect):
                if self.vel_y > 0:
                    self.rect.bottom = obj.rect.top
                    self.on_ground, self.vel_y = True, 0
                elif self.vel_y < 0:
                    self.rect.top = obj.rect.bottom
                    self.vel_y = 0
                    if obj.type in [BlockType.BRICK, BlockType.QUESTION]:
                        obj.hit(self.state != PlayerState.SMALL)

    def jump(self):
        if self.on_ground or self.coyote_time > 0:
            sounds['jump'].play(); self.vel_y = JUMP_VELOCITY
    
    def shoot(self, fireballs):
        if self.state == PlayerState.FIRE and self.fireball_cooldown == 0:
            self.fireball_cooldown = 20
            fireballs.append(Fireball(self.rect.centerx, self.rect.centery, self.facing_right))

    def hit(self):
        if self.state == PlayerState.SMALL: self.die()
        else:
            sounds['powerdown'].play()
            self.state = PlayerState.SMALL; y_pos = self.rect.bottom
            self.set_size(); self.rect.height = self.height
            self.rect.bottom = y_pos; self.invincible_timer = 120

    def die(self):
        sounds['die'].play()
        self.lives -= 1; self.reset_position()
        self.state = PlayerState.SMALL; self.set_size()
        self.rect.height = self.height
    
    def power_up(self, new_state):
        if self.state.value < new_state.value:
            sounds['powerup'].play()
            y_pos = self.rect.bottom; self.state = new_state
            self.set_size(); self.rect.height = self.height
            self.rect.bottom = y_pos; self.score += 1000

    def reset_position(self):
        self.rect.x, self.rect.y = 100, SCREEN_HEIGHT - 150
        self.vel_x, self.vel_y = 0, 0

class Enemy: #... (rest of the classes are similar, abbreviated for brevity)
    def __init__(self, x, y, enemy_type="goomba"):
        self.type = enemy_type
        self.rect = pygame.Rect(x, y, 22, 22)
        self.vel_x, self.vel_y = -1.5, 0
        self.is_stomped = False
        self.stomp_timer = 20

    def update(self, world_objects):
        if self.is_stomped:
            self.stomp_timer -=1
            return
        self.vel_y = min(self.vel_y + GRAVITY, MAX_FALL_SPEED)
        self.rect.x += self.vel_x
        for obj in world_objects:
            if self.rect.colliderect(obj.rect):
                if self.vel_x > 0: self.rect.right = obj.rect.left
                else: self.rect.left = obj.rect.right
                self.vel_x *= -1
        self.rect.y += self.vel_y
        for obj in world_objects:
            if self.rect.colliderect(obj.rect) and self.vel_y > 0:
                self.rect.bottom = obj.rect.top; self.vel_y = 0

class Block:
    def __init__(self, x, y, block_type, item=None):
        self.rect = pygame.Rect(x, y, 24, 24)
        self.type = block_type
        self.original_y = y; self.is_hit = False
        self.hit_timer = 0; self.item = item

    def update(self):
        if self.is_hit:
            self.hit_timer -= 1
            self.rect.y = self.original_y - math.sin((self.hit_timer / 6) * math.pi) * 4
            if self.hit_timer <= 0:
                self.is_hit = False; self.rect.y = self.original_y

    def hit(self, is_super):
        if self.type == BlockType.USED: return
        if self.type == BlockType.BRICK:
            if is_super: sounds['break_block'].play(); self.type = BlockType.USED
            else: self.is_hit = True; self.hit_timer = 6
        elif self.type == BlockType.QUESTION:
            self.is_hit = True; self.hit_timer = 6
            self.type = BlockType.USED; sounds['powerup'].play()

class Item: # ...
    def __init__(self, x, y, item_type):
        self.type = item_type
        self.rect = pygame.Rect(x, y, 20, 20)
        self.vel_x, self.vel_y = 2, 0
    def update(self, world_objects):
        self.vel_y = min(self.vel_y + GRAVITY * 0.7, MAX_FALL_SPEED)
        self.rect.x += self.vel_x
        for obj in world_objects:
             if self.rect.colliderect(obj.rect): self.vel_x *= -1
        self.rect.y += self.vel_y
        for obj in world_objects:
            if self.rect.colliderect(obj.rect) and self.vel_y > 0:
                self.rect.bottom = obj.rect.top; self.vel_y = 0

class Fireball: # ...
    def __init__(self, x, y, facing_right):
        self.rect = pygame.Rect(x, y, 10, 10)
        self.vel_x = 8 if facing_right else -8
        self.vel_y = 3; self.bounces = 0
    def update(self, world_objects, enemies):
        self.vel_y = min(self.vel_y + GRAVITY, MAX_FALL_SPEED)
        self.rect.x += self.vel_x; self.rect.y += self.vel_y
        for obj in world_objects:
            if self.rect.colliderect(obj.rect):
                self.rect.bottom = obj.rect.top; self.vel_y = -6; self.bounces +=1
        for enemy in enemies:
             if self.rect.colliderect(enemy.rect):
                enemy.is_stomped = True; self.bounces = 10

class Coin: # ...
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 16, 20)
    def update(self): pass

class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def update(self, target):
        x = -target.rect.centerx + int(SCREEN_WIDTH / 2)
        y = -target.rect.centery + int(SCREEN_HEIGHT / 2)
        x = min(0, x) # stop scrolling at left edge
        x = max(-(self.width - SCREEN_WIDTH), x) # stop scrolling at right edge
        # Y-scrolling can be added here if needed
        self.camera = pygame.Rect(x, 0, self.width, self.height)

# --- Level and World Data ---
from level_data import worlds, overworld_nodes

# --- Game State Managers ---
class LevelManager:
    def __init__(self, player, world_num, level_num):
        self.player = player
        self.world_num = world_num
        self.level_num = level_num
        self.level_data = worlds[world_num][level_num]
        self.level_width = self.level_data["length"] * 24
        self.level_height = SCREEN_HEIGHT
        
        self.world_objects, self.enemies, self.coins, self.items, self.fireballs = self.load_level()
        self.camera = Camera(self.level_width, self.level_height)
        self.level_time = 400
        self.player.reset_position()

    def load_level(self):
        world_objects, enemies, coins, items, fireballs = [], [], [], [], []
        
        # Ground
        for i in range(self.level_data["length"]):
            world_objects.append(Block(i * 24, SCREEN_HEIGHT - 24, BlockType.GROUND))
            world_objects.append(Block(i * 24, SCREEN_HEIGHT - 48, BlockType.GROUND))

        # Layout objects
        for obj in self.level_data["objects"]:
            if obj["type"] == "block":
                world_objects.append(Block(obj["x"], obj["y"], obj["block_type"], obj.get("item")))
            elif obj["type"] == "enemy":
                enemies.append(Enemy(obj["x"], obj["y"]))
        
        return world_objects, enemies, coins, items, fireballs

    def update(self):
        self.level_time -= 1/FPS
        self.player.update(self.world_objects, self.enemies, self.coins, self.items, self.fireballs)
        
        # Spawn items from blocks
        for block in self.world_objects[:]:
            block.update()
            if block.type == BlockType.USED and block.item:
                if block.item == 'coin': self.coins.append(Coin(block.rect.x, block.rect.y - 30))
                else: self.items.append(Item(block.rect.x, block.rect.y - 25, block.item))
                block.item = None
            if block.type == BlockType.USED and block.original_y == block.rect.y and block.item is None and not any(c.rect.collidepoint(block.rect.topleft) for c in self.coins):
                 if any(item for item in self.items if item.rect.collidepoint(block.rect.topleft)): continue
                 # This logic for removing used blocks is simplified, could be improved
                 pass


        for enemy in self.enemies[:]:
            enemy.update(self.world_objects)
            if enemy.stomp_timer <= 0: self.enemies.remove(enemy)
        for item in self.items: item.update(self.world_objects)
        for coin in self.coins: coin.update()
        for fireball in self.fireballs[:]:
            fireball.update(self.world_objects, self.enemies)
            if fireball.bounces >= 3 or fireball.rect.x > self.level_width or fireball.rect.x < 0:
                self.fireballs.remove(fireball)
        
        self.camera.update(self.player)
        
        # Check for level complete
        if self.player.rect.x > self.level_width - 60:
            sounds['level_complete'].play()
            return GameState.OVERWORLD
        if self.player.lives <= 0 or self.level_time <= 0:
            return GameState.GAME_OVER
        return GameState.LEVEL

    def draw(self, screen):
        # Draw background based on world
        bg_color = [SKY_BLUE, UNDERGROUND_BLACK, SKY_BLUE, PIPE_GREEN, CASTLE_GRAY][self.world_num - 1]
        screen.fill(bg_color)
        
        # Draw all game objects with camera offset
        for obj in self.world_objects: draw_block(screen, obj, self.camera)
        for item in self.items: draw_item(screen, item, self.camera)
        for coin in self.coins: screen.blit(COIN_YELLOW_SURF, self.camera.apply(coin))
        for enemy in self.enemies: draw_enemy(screen, enemy, self.camera)
        for fireball in self.fireballs: draw_fireball(screen, fireball, self.camera)
        draw_mario(screen, self.player, self.camera)
        draw_hud(screen, self.player, self.level_time)

class OverworldManager:
    def __init__(self, player):
        self.player = player
        self.nodes = overworld_nodes
        self.current_node = 0
        self.player_icon_rect = pygame.Rect(0,0,20,20)
        self.move_timer = 0
    
    def update(self, events):
        if self.move_timer > 0:
            self.move_timer -=1
            return GameState.OVERWORLD, None
            
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_RIGHT, pygame.K_d] and self.nodes[self.current_node]["exits"]["right"] is not None:
                    self.current_node = self.nodes[self.current_node]["exits"]["right"]
                    self.move_timer = 15
                elif event.key in [pygame.K_LEFT, pygame.K_a] and self.nodes[self.current_node]["exits"]["left"] is not None:
                    self.current_node = self.nodes[self.current_node]["exits"]["left"]
                    self.move_timer = 15
                elif event.key in [pygame.K_SPACE, pygame.K_RETURN]:
                    return GameState.LEVEL, (self.nodes[self.current_node]["world"], self.nodes[self.current_node]["level"])
        return GameState.OVERWORLD, None

    def draw(self, screen):
        screen.fill(SKY_BLUE)
        # Draw paths
        for i, node in enumerate(self.nodes):
            if node["exits"]["right"] is not None:
                pygame.draw.line(screen, WHITE, (node["x"], node["y"]), (self.nodes[node["exits"]["right"]]["x"], self.nodes[node["exits"]["right"]]["y"]), 5)
        # Draw nodes
        for i, node in enumerate(self.nodes):
            color = (255,0,0) if i == self.current_node else WHITE
            pygame.draw.circle(screen, color, (node["x"], node["y"]), 15)
            level_text = hud_font.render(f'{node["world"]}-{node["level"]}', True, BLACK)
            screen.blit(level_text, (node["x"]-18, node["y"]-10))
        
        # Animate player icon
        player_node = self.nodes[self.current_node]
        self.player_icon_rect.center = (player_node["x"], player_node["y"] - 30 + math.sin(pygame.time.get_ticks()/200.0) * 4)
        draw_mario(screen, self.player, None, self.player_icon_rect) # Use mario draw for icon
        draw_hud(screen, self.player, 999) # Show persistent stats

# --- Drawing Functions (now take camera) ---
COIN_YELLOW_SURF = pygame.Surface((16,20)); COIN_YELLOW_SURF.fill(COIN_YELLOW)

def draw_mario(screen, player, camera, override_rect=None):
    rect_to_draw = override_rect if override_rect else camera.apply(player)
    if not override_rect and player.invincible_timer % 10 < 5 or override_rect:
        color = MARIO_RED
        if player.state == PlayerState.FIRE: color = FIRE_MARIO_WHITE
        body_h = rect_to_draw.height / 2
        head_h = rect_to_draw.height / 2
        body_rect = pygame.Rect(rect_to_draw.left, rect_to_draw.top + head_h, rect_to_draw.width, body_h)
        head_rect = pygame.Rect(rect_to_draw.left, rect_to_draw.top, rect_to_draw.width, head_h)
        pygame.draw.rect(screen, color, body_rect)
        pygame.draw.rect(screen, MARIO_SKIN, head_rect)
        hair_size = max(2, int(rect_to_draw.width * 0.2))
        if player.facing_right:
            pygame.draw.rect(screen, MARIO_HAIR, (rect_to_draw.left, rect_to_draw.top, hair_size * 2, hair_size))
        else:
            pygame.draw.rect(screen, MARIO_HAIR, (rect_to_draw.right - hair_size * 2, rect_to_draw.top, hair_size*2, hair_size))

def draw_enemy(screen, enemy, camera):
    if enemy.is_stomped:
        pygame.draw.rect(screen, GOOMBA_BROWN, (camera.apply(enemy).x, camera.apply(enemy).centery, 22, 11))
    else:
        pygame.draw.ellipse(screen, GOOMBA_BROWN, camera.apply(enemy))

def draw_block(screen, block, camera):
    if block.type == BlockType.GROUND: pygame.draw.rect(screen, GROUND_BROWN, camera.apply(block))
    elif block.type == BlockType.BRICK: pygame.draw.rect(screen, BRICK_ORANGE, camera.apply(block))
    elif block.type == BlockType.PIPE: pygame.draw.rect(screen, PIPE_GREEN, camera.apply(block))
    elif block.type == BlockType.CLOUD: pygame.draw.rect(screen, CLOUD_WHITE, camera.apply(block))
    elif block.type == BlockType.QUESTION: pygame.draw.rect(screen, QUESTION_BLOCK_YELLOW, camera.apply(block))
    elif block.type == BlockType.USED: pygame.draw.rect(screen, (80,80,80), camera.apply(block))

def draw_item(screen, item, camera): # ...
    if item.type == 'mushroom':
        pygame.draw.arc(screen, MARIO_RED, (camera.apply(item).x, camera.apply(item).y-5, 20, 20), 0, math.pi, 10)
        pygame.draw.rect(screen, MARIO_SKIN, (camera.apply(item).x + 5, camera.apply(item).y + 5, 10, 15))
    elif item.type == 'flower':
        pygame.draw.circle(screen, COIN_YELLOW, camera.apply(item).center, 8)

def draw_fireball(screen, fireball, camera): # ...
    pygame.draw.circle(screen, (255, 100, 0), camera.apply(fireball).center, 5)

def draw_hud(screen, player, time): # ...
    screen.blit(hud_font.render(f"SCORE {player.score:06}", True, WHITE), (20, 10))
    screen.blit(hud_font.render(f"COINS x{player.coins:02}", True, WHITE), (250, 10))
    screen.blit(hud_font.render(f"LIVES x{player.lives}", True, WHITE), (420, 10))
    if time < 999: screen.blit(hud_font.render(f"TIME {int(time):03}", True, WHITE), (550, 10))

# --- Main Game Loop ---
def main():
    player = Player()
    game_state = GameState.OVERWORLD
    current_level_manager = None
    overworld_manager = OverworldManager(player)
    
    while True:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
        
        if game_state == GameState.OVERWORLD:
            new_state, level_args = overworld_manager.update(events)
            if new_state == GameState.LEVEL:
                game_state = GameState.LEVEL
                current_level_manager = LevelManager(player, level_args[0], level_args[1])
            overworld_manager.draw(screen)

        elif game_state == GameState.LEVEL:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]: player.acc_x = -RUN_ACCEL if player.running else -WALK_ACCEL; player.facing_right = False
            elif keys[pygame.K_RIGHT] or keys[pygame.K_d]: player.acc_x = RUN_ACCEL if player.running else WALK_ACCEL; player.facing_right = True
            else: player.acc_x = 0
            
            for event in events:
                 if event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_UP, pygame.K_SPACE, pygame.K_w]: player.jump_buffer = 6
                    if event.key in [pygame.K_LSHIFT, pygame.K_z]: player.running = True
                    if event.key == pygame.K_x: player.shoot(current_level_manager.fireballs)
            
            game_state = current_level_manager.update()
            current_level_manager.draw(screen)

        elif game_state == GameState.GAME_OVER:
            screen.fill(BLACK)
            screen.blit(hud_font.render("GAME OVER", True, WHITE), (SCREEN_WIDTH//2-80, SCREEN_HEIGHT//2))
            screen.blit(hud_font.render("Press R to Restart", True, WHITE), (SCREEN_WIDTH//2-130, SCREEN_HEIGHT//2+30))
            for event in events:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    main() # Restart whole game

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    # Create a separate file named `level_data.py` with the world data
    try:
        f = open("level_data.py", "w")
        f.write("""
from enum import Enum

class BlockType(Enum):
    GROUND = 0; BRICK = 1; QUESTION = 2; PIPE = 3; CLOUD = 4; USED = 5

overworld_nodes = [
    # World 1
    {"x": 100, "y": 240, "world": 1, "level": 1, "exits": {"left": None, "right": 1}},
    {"x": 200, "y": 240, "world": 1, "level": 2, "exits": {"left": 0, "right": 2}},
    {"x": 300, "y": 240, "world": 1, "level": 3, "exits": {"left": 1, "right": 3}},
    {"x": 400, "y": 240, "world": 1, "level": 4, "exits": {"left": 2, "right": 4}}, # To World 2
    # World 2
    {"x": 500, "y": 180, "world": 2, "level": 1, "exits": {"left": 3, "right": 5}},
    {"x": 500, "y": 300, "world": 2, "level": 2, "exits": {"left": 4, "right": None}},
]

worlds = {
    1: { # World 1: Grasslands
        1: {"length": 100, "objects": [
            {"type": "block", "x": 150, "y": 350, "block_type": BlockType.QUESTION, "item": "mushroom"},
            {"type": "enemy", "x": 250, "y": 400},
        ]},
        2: {"length": 120, "objects": [
            {"type": "block", "x": 200, "y": 250, "block_type": BlockType.QUESTION, "item": "flower"},
            {"type": "enemy", "x": 300, "y": 400},
        ]},
        3: {"length": 100, "objects": []},
        4: {"length": 100, "objects": []},
    },
    2: { # World 2: Underground
        1: {"length": 150, "objects": []},
        2: {"length": 150, "objects": []},
    },
    3: { # World 3: Sky
        1: {"length": 200, "objects": []},
    },
    4: { # World 4: Pipe Maze
        1: {"length": 180, "objects": []},
    },
    5: { # World 5: Castle
        1: {"length": 220, "objects": []},
    }
}
""")
        f.close()
    except Exception as e:
        print("Could not write level_data.py:", e)
    main()

