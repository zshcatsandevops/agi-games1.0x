import pygame
import sys
import math
from enum import Enum

# ==============================================
# Ultra Mario Forever 1.0A  — Buziol-style Engine
# Adds:
#  - Main Menu
#  - Overworld Map (SMB Deluxe-inspired)
#  - Unique levels for each stage node (5 worlds × 3 stages)
#  - Map progression with unlocks + returns to map on death/clear
# Credits: [C] Catsan
# ==============================================

# Initialize Pygame with Windows-friendly settings
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# Constants
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 400
FPS = 60
GRAVITY = 0.98
MAX_FALL_SPEED = 12
JUMP_VELOCITY = -12.5
WALK_ACCEL = 0.35
RUN_ACCEL = 0.5
MAX_WALK_SPEED = 3.5
MAX_RUN_SPEED = 5.5
FRICTION = 0.89
AIR_FRICTION = 0.95

# Colors
BLACK = (0, 0, 0)
RED = (228, 59, 68)
BROWN = (148, 81, 40)
GREEN = (92, 148, 13)
YELLOW = (251, 208, 0)
WHITE = (255, 255, 255)
BLUE = (92, 148, 252)
ORANGE = (252, 152, 56)
DARK_GREEN = (0, 168, 0)
GRAY = (96, 96, 96)
LIGHT_GRAY = (160, 160, 160)

# Screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF | pygame.HWSURFACE)
pygame.display.set_caption("Ultra Mario Forever 1.0A — Buziol Engine")
clock = pygame.time.Clock()

# Fonts
try:
    hud_font = pygame.font.Font(pygame.font.match_font('arial'), 16)
    big_font = pygame.font.Font(pygame.font.match_font('arial'), 24)
    title_font = pygame.font.Font(pygame.font.match_font('arial'), 36)
except:
    hud_font = pygame.font.Font(None, 16)
    big_font = pygame.font.Font(None, 24)
    title_font = pygame.font.Font(None, 36)

class PlayerState(Enum):
    SMALL = 0
    SUPER = 1
    FIRE = 2

class GameMode(Enum):
    MENU = 0
    MAP = 1
    PLAYING = 2
    GAME_OVER = 3
    GAME_COMPLETE = 4

class Player:
    def __init__(self):
        self.rect = pygame.Rect(50, SCREEN_HEIGHT - 100, 16, 16)  # small
        self.vel_x = 0
        self.vel_y = 0
        self.acc_x = 0
        self.on_ground = False
        self.facing_right = True
        self.running = False
        self.state = PlayerState.SMALL
        self.invincible_timer = 0

        # Stats
        self.lives = 5
        self.coins = 0
        self.score = 0

        # Timers
        self.jump_buffer = 0
        self.coyote_time = 0
        self.p_meter = 0

    def update(self, platforms, enemies, coins, items):
        # Invincibility
        if self.invincible_timer > 0:
            self.invincible_timer -= 1

        # Horizontal
        if self.running:
            max_speed = MAX_RUN_SPEED
            self.p_meter = min(self.p_meter + 2, 100)
        else:
            max_speed = MAX_WALK_SPEED
            self.p_meter = max(self.p_meter - 1, 0)

        self.vel_x += self.acc_x
        if self.on_ground:
            self.vel_x *= FRICTION
        else:
            self.vel_x *= AIR_FRICTION
        self.vel_x = max(-max_speed, min(max_speed, self.vel_x))

        # Apply movement X
        self.rect.x += self.vel_x
        self.check_collision_x(platforms)

        # Vertical
        self.vel_y = min(self.vel_y + GRAVITY, MAX_FALL_SPEED)
        self.rect.y += self.vel_y

        # Coyote
        if self.on_ground:
            self.coyote_time = 6
        elif self.coyote_time > 0:
            self.coyote_time -= 1

        self.on_ground = False
        self.check_collision_y(platforms, enemies)

        # Jump buffer
        if self.jump_buffer > 0:
            self.jump_buffer -= 1
            if self.on_ground:
                self.jump()
                self.jump_buffer = 0

        # Fell off
        if self.rect.bottom > SCREEN_HEIGHT:
            self.die()

        # Enemy collisions
        for enemy in enemies[:]:
            if self.rect.colliderect(enemy.rect):
                if self.vel_y > 0 and self.rect.bottom - 10 < enemy.rect.top:
                    self.vel_y = -8
                    self.score += 100
                    enemies.remove(enemy)
                elif self.invincible_timer == 0:
                    self.hit()

        # Coins
        for coin in coins[:]:
            if self.rect.colliderect(coin.rect):
                self.coins += 1
                self.score += 50
                if self.coins >= 100:
                    self.coins = 0
                    self.lives += 1
                coins.remove(coin)

        # Items
        for item in items[:]:
            if self.rect.colliderect(item.rect):
                if item.type == "mushroom" and self.state == PlayerState.SMALL:
                    self.power_up()
                    items.remove(item)
                elif item.type == "flower" and self.state != PlayerState.FIRE:
                    self.state = PlayerState.FIRE
                    items.remove(item)

    def check_collision_x(self, platforms):
        for plat in platforms:
            if self.rect.colliderect(plat):
                if self.vel_x > 0:
                    self.rect.right = plat.left
                elif self.vel_x < 0:
                    self.rect.left = plat.right
                self.vel_x = 0

    def check_collision_y(self, platforms, enemies):
        for plat in platforms:
            if self.rect.colliderect(plat):
                if self.vel_y > 0:
                    self.rect.bottom = plat.top
                    self.on_ground = True
                    self.vel_y = 0
                elif self.vel_y < 0:
                    self.rect.top = plat.bottom
                    self.vel_y = 0

    def jump(self):
        if self.on_ground or self.coyote_time > 0:
            self.vel_y = JUMP_VELOCITY
            if self.p_meter >= 100:
                self.vel_y = JUMP_VELOCITY * 1.2

    def hit(self):
        if self.state == PlayerState.SMALL:
            self.die()
        else:
            self.state = PlayerState.SMALL
            self.rect.height = 16
            self.invincible_timer = 120

    def die(self):
        self.lives -= 1
        self.reset_position()
        self.state = PlayerState.SMALL
        self.rect.height = 16

    def power_up(self):
        self.state = PlayerState.SUPER
        self.rect.height = 32
        self.rect.y -= 16
        self.score += 1000

    def reset_position(self):
        self.rect.x = 50
        self.rect.y = SCREEN_HEIGHT - 100
        self.vel_x = 0
        self.vel_y = 0
        self.p_meter = 0

class Enemy:
    def __init__(self, x, y, enemy_type="goomba"):
        self.type = enemy_type
        if enemy_type == "goomba":
            self.rect = pygame.Rect(x, y, 16, 16)
            self.vel_x = -1
        elif enemy_type == "koopa":
            self.rect = pygame.Rect(x, y, 16, 24)
            self.vel_x = -0.8
        self.vel_y = 0
        self.on_ground = False

    def update(self, platforms):
        self.vel_y = min(self.vel_y + GRAVITY, MAX_FALL_SPEED)
        self.rect.x += self.vel_x
        for plat in platforms:
            if self.rect.colliderect(plat):
                if self.vel_x > 0:
                    self.rect.right = plat.left
                else:
                    self.rect.left = plat.right
                self.vel_x *= -1
        self.rect.y += self.vel_y
        self.on_ground = False
        for plat in platforms:
            if self.rect.colliderect(plat):
                if self.vel_y > 0:
                    self.rect.bottom = plat.top
                    self.on_ground = True
                    self.vel_y = 0

class Coin:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 12, 16)
        self.animation_timer = 0

    def update(self):
        self.animation_timer = (self.animation_timer + 1) % 30

class Item:
    def __init__(self, x, y, item_type="mushroom"):
        self.type = item_type
        self.rect = pygame.Rect(x, y, 16, 16)
        self.vel_x = 1
        self.vel_y = 0

    def update(self, platforms):
        if self.type == "mushroom":
            self.rect.x += self.vel_x
            self.vel_y = min(self.vel_y + GRAVITY, MAX_FALL_SPEED)
            self.rect.y += self.vel_y
            for plat in platforms:
                if self.rect.colliderect(plat):
                    if self.vel_y > 0:
                        self.rect.bottom = plat.top
                        self.vel_y = 0
                    if abs(self.vel_x) > 0:
                        self.vel_x *= -1

# ----------------- OVERWORLD MAP -----------------

class MapNode:
    def __init__(self, x, y, world, level, unlocked=False):
        self.x = x
        self.y = y
        self.world = world
        self.level = level
        self.unlocked = unlocked
        self.cleared = False

def build_overworld_map():
    """Build a simple zig-zag path across 3 rows. 5 worlds × 3 levels = 15 nodes."""
    world_level_pairs = []
    for w in range(1, 6):
        for l in range(1, 3+1):
            world_level_pairs.append((w, l))

    rows_y = [300, 240, 180]  # bottom to top
    cols_x = [80, 160, 240, 320, 400]  # left to right
    positions = []
    for i in range(15):
        row = i // 5
        col = i % 5
        # zig-zag layout to feel "map-like"
        if row % 2 == 0:
            x = cols_x[col]
        else:
            x = cols_x[::-1][col]
        y = rows_y[row]
        positions.append((x, y))

    nodes = []
    for idx, ((w, l), (x, y)) in enumerate(zip(world_level_pairs, positions)):
        nodes.append(MapNode(x, y, w, l, unlocked=(idx == 0)))
    return nodes

def draw_map(screen, nodes, selected_index, player):
    # Background
    screen.fill((64, 176, 248))
    # rolling hills
    pygame.draw.ellipse(screen, (24, 120, 40), (-100, 300, 300, 200))
    pygame.draw.ellipse(screen, (24, 140, 48), (200, 310, 300, 160))
    pygame.draw.ellipse(screen, (24, 120, 40), (420, 300, 250, 200))

    # Path lines
    for i in range(len(nodes) - 1):
        a = nodes[i]
        b = nodes[i + 1]
        pygame.draw.line(screen, LIGHT_GRAY, (a.x, a.y), (b.x, b.y), 3)

    # Nodes
    for i, n in enumerate(nodes):
        color = GRAY
        if n.unlocked:
            color = WHITE
        if n.cleared:
            color = YELLOW
        if i == selected_index:
            color = GREEN
        pygame.draw.circle(screen, BLACK, (n.x, n.y), 10)
        pygame.draw.circle(screen, color, (n.x, n.y), 8)
        # Label WORLD-LEVEL above node
        wl = hud_font.render(f"{n.world}-{n.level}", True, BLACK if color in (WHITE, YELLOW) else WHITE)
        screen.blit(wl, (n.x - 12, n.y - 24))

    # Selector sprite (mini "Mario head")
    sel = nodes[selected_index]
    pygame.draw.rect(screen, RED, pygame.Rect(sel.x - 6, sel.y - 20, 12, 8))
    pygame.draw.rect(screen, RED, pygame.Rect(sel.x - 5, sel.y - 12, 10, 10))

    # UI text
    title = big_font.render("OVERWORLD MAP — Select a Stage", True, WHITE)
    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 20))
    info = hud_font.render("Arrows to move • ENTER to Start • ESC for Menu", True, WHITE)
    screen.blit(info, (SCREEN_WIDTH // 2 - info.get_width() // 2, 50))

    # Player stats on map
    stats = hud_font.render(f"Lives: {player.lives}   Coins: {player.coins}   Score: {player.score}", True, WHITE)
    screen.blit(stats, (SCREEN_WIDTH // 2 - stats.get_width() // 2, 70))

# ----------------- LEVELS -----------------

def generate_level(world, level):
    """Generate unique platforms/enemies/coins/items per (world, level)."""
    platforms = []
    enemies = []
    coins = []
    items = []

    # Ground base
    ground_color = BROWN
    platforms.append(pygame.Rect(0, SCREEN_HEIGHT - 40, SCREEN_WIDTH, 40))

    if world == 1:  # Grassland
        if level == 1:
            platforms.extend([
                pygame.Rect(120, 280, 64, 16),
                pygame.Rect(220, 240, 96, 16),
                pygame.Rect(360, 200, 64, 16),
                pygame.Rect(450, 280, 80, 16),
            ])
            enemies.extend([
                Enemy(150, 264, "goomba"),
                Enemy(250, 224, "goomba"),
                Enemy(380, 184, "koopa"),
            ])
            coins.extend([Coin(130, 250), Coin(145, 250), Coin(230, 210), Coin(370, 170)])
            items.append(Item(240, 200, "mushroom"))
        elif level == 2:
            platforms.extend([
                pygame.Rect(80, 300, 48, 16),
                pygame.Rect(160, 260, 64, 16),
                pygame.Rect(260, 220, 80, 16),
                pygame.Rect(380, 260, 64, 16),
                pygame.Rect(500, 300, 48, 16),
            ])
            enemies.extend([
                Enemy(90, 284, "goomba"),
                Enemy(180, 244, "koopa"),
                Enemy(280, 204, "goomba"),
                Enemy(400, 244, "goomba"),
            ])
            coins.extend([Coin(165, 230), Coin(265, 190), Coin(385, 230)])
            items.append(Item(160, 244, "mushroom"))
        elif level == 3:
            for i in range(3):
                platforms.append(pygame.Rect(140 + i * 150, 320 - i * 40, 80, 16))
            enemies.extend([Enemy(170, 304, "koopa"), Enemy(320, 264, "koopa"), Enemy(470, 224, "koopa")])
            coins.extend([Coin(160, 290), Coin(310, 250), Coin(460, 210)])
            items.append(Item(300, 250, "flower"))

    elif world == 2:  # Underground
        if level == 1:
            platforms.extend([
                pygame.Rect(100, 320, 32, 80),
                pygame.Rect(200, 280, 32, 120),
                pygame.Rect(300, 300, 32, 100),
                pygame.Rect(400, 260, 32, 140),
                pygame.Rect(500, 320, 32, 80),
            ])
            enemies.extend([Enemy(210, 264, "goomba"), Enemy(410, 244, "goomba")])
            coins.extend([Coin(110, 290), Coin(210, 250), Coin(310, 270), Coin(410, 230), Coin(510, 290)])
            items.append(Item(300, 260, "mushroom"))
        elif level == 2:
            platforms.extend([
                pygame.Rect(80, 280, 60, 16),
                pygame.Rect(170, 240, 60, 16),
                pygame.Rect(260, 200, 60, 16),
                pygame.Rect(350, 240, 60, 16),
                pygame.Rect(440, 280, 60, 16),
            ])
            enemies.extend([Enemy(175, 224, "koopa"), Enemy(355, 224, "koopa")])
            coins.extend([Coin(90, 250), Coin(180, 210), Coin(270, 170), Coin(360, 210), Coin(450, 250)])
        elif level == 3:
            # Long pits and narrow ledges
            platforms.extend([
                pygame.Rect(60, 300, 50, 16),
                pygame.Rect(140, 270, 50, 16),
                pygame.Rect(240, 240, 50, 16),
                pygame.Rect(340, 270, 50, 16),
                pygame.Rect(440, 300, 50, 16),
            ])
            enemies.extend([Enemy(145, 254, "goomba"), Enemy(345, 254, "goomba")])
            items.append(Item(240, 224, "mushroom"))

    elif world == 3:  # Water/Bridge
        if level == 1:
            platforms.extend([
                pygame.Rect(60, 300, 80, 16),
                pygame.Rect(180, 280, 80, 16),
                pygame.Rect(300, 260, 80, 16),
                pygame.Rect(420, 280, 80, 16),
            ])
            enemies.extend([Enemy(200, 264, "goomba"), Enemy(440, 264, "goomba")])
            coins.extend([Coin(200, 250), Coin(320, 230)])
            items.append(Item(180, 264, "mushroom"))
        elif level == 2:
            platforms.extend([
                pygame.Rect(100, 320, 100, 16),
                pygame.Rect(250, 280, 100, 16),
                pygame.Rect(400, 240, 100, 16),
            ])
            enemies.extend([Enemy(270, 264, "koopa")])
            coins.extend([Coin(130, 290), Coin(280, 250), Coin(430, 210)])
        elif level == 3:
            platforms.extend([
                pygame.Rect(80, 280, 60, 16),
                pygame.Rect(160, 240, 60, 16),
                pygame.Rect(240, 200, 60, 16),
                pygame.Rect(320, 240, 60, 16),
                pygame.Rect(400, 280, 60, 16),
            ])
            enemies.extend([Enemy(165, 224, "goomba"), Enemy(325, 224, "goomba")])
            items.append(Item(240, 184, "flower"))

    elif world == 4:  # Castle
        if level == 1:
            platforms.extend([
                pygame.Rect(100, 300, 80, 16),
                pygame.Rect(200, 260, 80, 16),
                pygame.Rect(300, 220, 80, 16),
                pygame.Rect(400, 260, 80, 16),
            ])
            enemies.extend([Enemy(210, 244, "koopa"), Enemy(410, 244, "koopa")])
            coins.extend([Coin(120, 270), Coin(220, 230), Coin(320, 190), Coin(420, 230)])
        elif level == 2:
            platforms.extend([
                pygame.Rect(60, 300, 40, 16),
                pygame.Rect(140, 260, 40, 16),
                pygame.Rect(220, 220, 40, 16),
                pygame.Rect(300, 260, 40, 16),
                pygame.Rect(380, 300, 40, 16),
                pygame.Rect(460, 260, 40, 16),
            ])
            enemies.extend([Enemy(145, 244, "goomba"), Enemy(305, 244, "goomba"), Enemy(465, 244, "goomba")])
            items.append(Item(220, 204, "mushroom"))
        elif level == 3:
            for i in range(4):
                platforms.append(pygame.Rect(120 + i * 100, 320 - (i % 2) * 40, 80, 16))
            enemies.extend([Enemy(170, 304, "koopa"), Enemy(270, 264, "koopa"), Enemy(370, 304, "koopa"), Enemy(470, 264, "koopa")])
            coins.extend([Coin(140, 290), Coin(240, 250), Coin(340, 290), Coin(440, 250)])

    elif world == 5:  # Sky / Hard
        if level == 1:
            platforms.extend([
                pygame.Rect(80, 260, 60, 16),
                pygame.Rect(180, 230, 60, 16),
                pygame.Rect(280, 200, 60, 16),
                pygame.Rect(380, 230, 60, 16),
                pygame.Rect(480, 260, 60, 16),
            ])
            enemies.extend([Enemy(185, 214, "goomba"), Enemy(385, 214, "goomba")])
            items.append(Item(280, 184, "mushroom"))
        elif level == 2:
            platforms.extend([
                pygame.Rect(60, 300, 50, 16),
                pygame.Rect(140, 270, 50, 16),
                pygame.Rect(220, 240, 50, 16),
                pygame.Rect(300, 210, 50, 16),
                pygame.Rect(380, 240, 50, 16),
                pygame.Rect(460, 270, 50, 16),
                pygame.Rect(540, 300, 50, 16),
            ])
            enemies.extend([Enemy(225, 224, "koopa"), Enemy(385, 224, "koopa")])
            coins.extend([Coin(305, 180), Coin(465, 210)])
        elif level == 3:
            platforms.extend([
                pygame.Rect(120, 320, 80, 16),
                pygame.Rect(260, 280, 80, 16),
                pygame.Rect(400, 240, 80, 16),
            ])
            enemies.extend([Enemy(270, 264, "goomba"), Enemy(410, 224, "koopa")])
            coins.extend([Coin(140, 290), Coin(280, 250), Coin(420, 210)])
            items.append(Item(400, 224, "flower"))

    return platforms, enemies, coins, items

# ----------------- DRAWING -----------------

def draw_hud(screen, player, world, level, time_left):
    hud_surface = pygame.Surface((SCREEN_WIDTH, 50))
    hud_surface.fill((32, 32, 32))

    score_text = hud_font.render(f"SCORE", True, WHITE)
    score_num = hud_font.render(f"{player.score:08d}", True, WHITE)
    hud_surface.blit(score_text, (20, 5))
    hud_surface.blit(score_num, (20, 20))

    coin_icon = pygame.Surface((8, 8))
    coin_icon.fill(YELLOW)
    hud_surface.blit(coin_icon, (120, 20))
    coins_text = hud_font.render(f"x{player.coins:02d}", True, WHITE)
    hud_surface.blit(coins_text, (135, 18))

    world_text = hud_font.render(f"WORLD", True, WHITE)
    world_num = hud_font.render(f"{world}-{level}", True, WHITE)
    hud_surface.blit(world_text, (220, 5))
    hud_surface.blit(world_num, (220, 20))

    time_text = hud_font.render(f"TIME", True, WHITE)
    time_num = hud_font.render(f"{max(0, int(time_left)):03d}", True, WHITE)
    hud_surface.blit(time_text, (320, 5))
    hud_surface.blit(time_num, (320, 20))

    lives_text = hud_font.render(f"LIVES", True, WHITE)
    lives_num = hud_font.render(f"{player.lives}", True, WHITE)
    hud_surface.blit(lives_text, (420, 5))
    hud_surface.blit(lives_num, (420, 20))

    p_text = hud_font.render("P", True, WHITE)
    hud_surface.blit(p_text, (500, 18))
    pygame.draw.rect(hud_surface, WHITE, (515, 20, 60, 8), 1)
    if player.p_meter > 0:
        pygame.draw.rect(hud_surface, ORANGE, (517, 22, int(56 * player.p_meter / 100), 4))

    screen.blit(hud_surface, (0, 0))

def draw_player(screen, player):
    if player.state == PlayerState.SMALL:
        color = RED
    elif player.state == PlayerState.SUPER:
        color = RED
        pygame.draw.rect(screen, RED, pygame.Rect(player.rect.x, player.rect.y, player.rect.width, 8))
    else:
        color = WHITE

    if player.invincible_timer % 4 < 2:
        pygame.draw.rect(screen, color, player.rect)

def draw_background(screen, world):
    if world == 1:
        screen.fill(BLUE)
        for i in range(3):
            pygame.draw.ellipse(screen, WHITE, (100 + i * 200, 80, 60, 30))
            pygame.draw.ellipse(screen, WHITE, (120 + i * 200, 75, 50, 35))
    elif world == 2:
        screen.fill(BLACK)
    elif world == 3:
        screen.fill((0, 64, 128))
    elif world == 4:
        screen.fill((64, 32, 32))
    else:
        screen.fill(BLUE)

def draw_menu(screen):
    screen.fill((20, 20, 24))
    title = title_font.render("ULTRA MARIO FOREVER 1.0A", True, (255, 180, 64))
    subtitle = big_font.render("Agentic Buziol Engine • SMB Deluxe-style Map", True, WHITE)
    prompt = hud_font.render("Press ENTER to Start • F1 for Controls • ESC to Quit", True, LIGHT_GRAY)
    credit = hud_font.render("© [C] Catsan — Mario Forever homage", True, LIGHT_GRAY)

    # Simple "sparkle" banner
    pygame.draw.rect(screen, (40, 40, 48), pygame.Rect(40, 80, SCREEN_WIDTH - 80, 4))
    pygame.draw.rect(screen, (120, 120, 160), pygame.Rect(40, 84, SCREEN_WIDTH - 80, 2))

    screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 110))
    screen.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, 160))
    screen.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, 210))
    screen.blit(credit, (SCREEN_WIDTH // 2 - credit.get_width() // 2, 240))

    help_lines = [
        "Controls (in level):",
        "  ←/→ Move • Z or Left Shift = Run • Space/Up = Jump",
        "  Running fills the P-meter for longer jumps.",
        "Map: ←/→ to choose stage • ENTER to start • ESC for Menu",
    ]
    for i, line in enumerate(help_lines):
        t = hud_font.render(line, True, LIGHT_GRAY)
        screen.blit(t, (40, 280 + i * 18))

# ----------------- MAIN -----------------

def main():
    player = Player()

    # Build overworld
    nodes = build_overworld_map()
    selected_index = 0
    current_world = nodes[selected_index].world
    current_level = nodes[selected_index].level

    # Game state
    mode = GameMode.MENU
    running = True
    level_time = 400
    time_counter = 0.0

    # Entities (only valid during PLAYING)
    platforms, enemies, coins, items = [], [], [], []

    while running:
        dt = clock.tick(FPS) / 1000.0

        # ---------- Events ----------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if mode == GameMode.MENU:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        mode = GameMode.MAP
                    elif event.key == pygame.K_ESCAPE:
                        running = False

            elif mode == GameMode.MAP:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RIGHT:
                        # Move to next unlocked node (linear path)
                        # Find farthest unlocked ahead
                        ahead = selected_index
                        for i in range(selected_index + 1, len(nodes)):
                            if nodes[i].unlocked:
                                ahead = i
                            else:
                                break
                        if ahead != selected_index:
                            selected_index = min(ahead, selected_index + 1)
                    elif event.key == pygame.K_LEFT:
                        if selected_index > 0:
                            selected_index -= 1
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        # Start the selected level if unlocked
                        node = nodes[selected_index]
                        if node.unlocked:
                            current_world = node.world
                            current_level = node.level
                            platforms, enemies, coins, items = generate_level(current_world, current_level)
                            player.reset_position()
                            level_time = 400
                            time_counter = 0.0
                            mode = GameMode.PLAYING
                    elif event.key == pygame.K_ESCAPE:
                        mode = GameMode.MENU

            elif mode == GameMode.PLAYING:
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP, pygame.K_SPACE):
                        player.jump_buffer = 6
                    if event.key in (pygame.K_LSHIFT, pygame.K_z):
                        player.running = True
                if event.type == pygame.KEYUP:
                    if event.key in (pygame.K_LSHIFT, pygame.K_z):
                        player.running = False

            elif mode in (GameMode.GAME_OVER, GameMode.GAME_COMPLETE):
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        # Reset everything back to fresh game
                        player = Player()
                        nodes = build_overworld_map()
                        selected_index = 0
                        current_world = nodes[selected_index].world
                        current_level = nodes[selected_index].level
                        level_time = 400
                        time_counter = 0.0
                        mode = GameMode.MENU

        # ---------- Update ----------
        if mode == GameMode.PLAYING:
            # Time update
            time_counter += dt
            if time_counter >= 1.0:
                time_counter = 0.0
                level_time -= 1
                if level_time <= 0:
                    # Time up counts as death
                    pre = player.lives
                    player.die()
                    if player.lives <= 0:
                        mode = GameMode.GAME_OVER
                    else:
                        # Back to map
                        level_time = 400
                        mode = GameMode.MAP

            # Input for movement
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                player.acc_x = -WALK_ACCEL if not player.running else -RUN_ACCEL
                player.facing_right = False
            elif keys[pygame.K_RIGHT]:
                player.acc_x = WALK_ACCEL if not player.running else RUN_ACCEL
                player.facing_right = True
            else:
                player.acc_x = 0

            # Track lives to detect death this frame
            lives_before = player.lives

            # Update entities
            player.update(platforms, enemies, coins, items)
            for enemy in enemies:
                enemy.update(platforms)
            for coin in coins:
                coin.update()
            for item in items:
                item.update(platforms)

            # Level complete check (reach flag area)
            if player.rect.right >= SCREEN_WIDTH - 50:
                # Mark node cleared, unlock next
                nodes[selected_index].cleared = True
                if selected_index + 1 < len(nodes):
                    nodes[selected_index + 1].unlocked = True
                    selected_index += 1
                    current_world = nodes[selected_index].world
                    current_level = nodes[selected_index].level
                    mode = GameMode.MAP
                else:
                    mode = GameMode.GAME_COMPLETE
                player.reset_position()
                level_time = 400

            # Death handling
            if player.lives < lives_before:
                if player.lives <= 0:
                    mode = GameMode.GAME_OVER
                else:
                    # Back to map (stage remains uncleared)
                    player.reset_position()
                    level_time = 400
                    mode = GameMode.MAP

        # ---------- Draw ----------
        if mode == GameMode.MENU:
            draw_menu(screen)

        elif mode == GameMode.MAP:
            draw_map(screen, nodes, selected_index, player)

        elif mode == GameMode.PLAYING:
            draw_background(screen, current_world)

            # Platforms
            for plat in platforms:
                if current_world == 1:
                    pygame.draw.rect(screen, BROWN, plat)
                elif current_world == 2:
                    pygame.draw.rect(screen, (64, 64, 64), plat)
                elif current_world == 3:
                    pygame.draw.rect(screen, (120, 140, 200), plat)
                elif current_world == 4:
                    pygame.draw.rect(screen, (90, 50, 50), plat)
                else:
                    pygame.draw.rect(screen, BROWN, plat)

            # Items
            for item in items:
                if item.type == "mushroom":
                    pygame.draw.rect(screen, RED, item.rect)
                    pygame.draw.rect(screen, WHITE, pygame.Rect(item.rect.x, item.rect.y, item.rect.width, 6))
                elif item.type == "flower":
                    pygame.draw.rect(screen, RED, item.rect)

            # Enemies
            for enemy in enemies:
                if enemy.type == "goomba":
                    pygame.draw.rect(screen, (139, 90, 43), enemy.rect)
                elif enemy.type == "koopa":
                    pygame.draw.rect(screen, GREEN, enemy.rect)

            # Coins
            for coin in coins:
                if coin.animation_timer < 15:
                    pygame.draw.rect(screen, YELLOW, coin.rect)
                else:
                    pygame.draw.rect(screen, ORANGE, pygame.Rect(coin.rect.x + 2, coin.rect.y, 8, 16))

            # Player
            draw_player(screen, player)

            # Flag/goal
            pygame.draw.rect(screen, (0, 255, 0), pygame.Rect(SCREEN_WIDTH - 40, SCREEN_HEIGHT - 140, 4, 100))
            pygame.draw.polygon(screen, RED, [
                (SCREEN_WIDTH - 36, SCREEN_HEIGHT - 140),
                (SCREEN_WIDTH - 36, SCREEN_HEIGHT - 120),
                (SCREEN_WIDTH - 20, SCREEN_HEIGHT - 130)
            ])

            draw_hud(screen, player, current_world, current_level, level_time)

        elif mode == GameMode.GAME_COMPLETE:
            screen.fill((10, 10, 16))
            complete_text = big_font.render("GAME COMPLETE!", True, WHITE)
            score_text = big_font.render(f"Final Score: {player.score}", True, WHITE)
            restart_text = hud_font.render("Press R to return to Menu", True, LIGHT_GRAY)
            screen.blit(complete_text, (SCREEN_WIDTH // 2 - complete_text.get_width() // 2, SCREEN_HEIGHT // 2 - 40))
            screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, SCREEN_HEIGHT // 2))
            screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, SCREEN_HEIGHT // 2 + 30))

        elif mode == GameMode.GAME_OVER:
            screen.fill((0, 0, 0))
            over_text = big_font.render("GAME OVER", True, WHITE)
            restart_text = hud_font.render("Press R to return to Menu", True, WHITE)
            screen.blit(over_text, (SCREEN_WIDTH // 2 - over_text.get_width() // 2, SCREEN_HEIGHT // 2 - 20))
            screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, SCREEN_HEIGHT // 2 + 10))

        # Present (HUD drawn in PLAYING branch; map/menu have their own UI)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    # Windows optimization — set process priority if possible
    try:
        import psutil
        import os
        p = psutil.Process(os.getpid())
        p.nice(psutil.HIGH_PRIORITY_CLASS)
    except Exception:
        pass

    main()
