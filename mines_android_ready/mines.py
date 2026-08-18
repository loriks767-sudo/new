import pygame
import random
import math
import json
import sys
import os
from decimal import Decimal

# ================== NUSTATYMAI ==================
FPS = 60
MIN_BET = 1.0
BG = (15, 18, 35)
PANEL_BG = (22, 26, 48)
PANEL_BORDER = (40, 48, 80)
TILE_HIDDEN = (35, 42, 75)
TILE_HOVER = (55, 70, 120)
TILE_GEM = (20, 180, 160)
TILE_GEM_GLOW = (40, 230, 200)
TILE_BOMB = (180, 40, 55)
TILE_BOMB_GLOW = (255, 80, 90)
ACCENT = (0, 220, 180)
ACCENT_DIM = (0, 160, 130)
GOLD = (255, 215, 80)
WHITE = (240, 245, 255)
MUTED = (120, 130, 160)
RED = (255, 90, 100)
BUTTON_HOVER = (50, 65, 110)

GRID_OPTIONS = {
    "3x3": 3,
    "5x5": 5,
    "7x7": 7,
}

# House edge ~1% (kaip realiuose casino, pvz. Stake)
HOUSE_EDGE = 0.01


# ================== STORAGE ==================
# Android: use Kivy's writable app-data directory when available.
# PC: keep the original local balances.json behavior.
try:
    from kivy.utils import platform
except Exception:
    platform = "win"

if platform == "android":
    try:
        from android.storage import app_storage_path
        DATA_DIR = app_storage_path()
    except Exception:
        DATA_DIR = "."
else:
    DATA_DIR = "."

BALANCE_FILE = os.path.join(DATA_DIR, "balances.json")


def load_balances():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(BALANCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_balances(balances):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(BALANCE_FILE, "w", encoding="utf-8") as f:
        json.dump(balances, f, indent=4)


if len(sys.argv) > 1:
    CURRENT_USER = sys.argv[1]
else:
    CURRENT_USER = "player1"


def ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def ease_out_elastic(t):
    if t == 0 or t == 1:
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1


class Particle:
    def __init__(self, x, y, color, kind="spark"):
        self.x = x
        self.y = y
        self.kind = kind
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(80, 280) if kind == "spark" else random.uniform(40, 120)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - random.uniform(50, 150)
        self.life = random.uniform(0.4, 0.9)
        self.max_life = self.life
        self.color = color
        self.size = random.uniform(3, 8) if kind == "spark" else random.uniform(4, 10)
        self.gravity = 400

    def update(self, dt):
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.vx *= 0.98

    def draw(self, screen):
        if self.life <= 0:
            return
        a = max(0, self.life / self.max_life)
        s = max(1, int(self.size * a))
        surf = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
        c = (*self.color[:3], int(220 * a))
        pygame.draw.circle(surf, c, (s, s), s)
        screen.blit(surf, (int(self.x - s), int(self.y - s)))


class Tile:
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.is_mine = False
        self.revealed = False
        self.anim = 0.0          # 0..1 reveal progress
        self.hover_t = 0.0
        self.pulse = random.uniform(0, math.pi * 2)
        self.shake = 0.0
        self.scale_pop = 0.0     # extra scale on reveal

    def reset(self):
        self.is_mine = False
        self.revealed = False
        self.anim = 0.0
        self.shake = 0.0
        self.scale_pop = 0.0


class MinesGame:
    def __init__(self, username):
        global CURRENT_USER
        pygame.init()

        self.current_user = username
        CURRENT_USER = username
        info = pygame.display.Info()
        self.W = info.current_w or 1080
        self.H = info.current_h or 1920

        # Android/mobile: fullscreen with the actual display size.
        # PC keeps the same fullscreen behavior.
        self.screen = pygame.display.set_mode((self.W, self.H), pygame.FULLSCREEN)
        pygame.display.set_caption("Mines • Casino")
        self.clock = pygame.time.Clock()

        # Scale typography for phones/tablets while preserving the PC look.
        scale = max(0.75, min(2.0, min(self.W / 1280.0, self.H / 720.0)))
        self.font_title = pygame.font.SysFont("arial", max(42, int(56 * scale)), bold=True)
        self.font_big = pygame.font.SysFont("arial", max(25, int(32 * scale)), bold=True)
        self.font_med = pygame.font.SysFont("arial", max(18, int(22 * scale)), bold=True)
        self.font_small = pygame.font.SysFont("arial", max(15, int(18 * scale)))
        self.font_tiny = pygame.font.SysFont("arial", max(13, int(15 * scale)))

        balances = load_balances()
        if CURRENT_USER not in balances:
            balances[CURRENT_USER] = "1000.0"
            save_balances(balances)
        self.credits = Decimal(str(balances[CURRENT_USER]))
        self.bet = 5.0

        self.grid_size = 5
        self.mine_count = 3
        self.tiles = []
        self.particles = []

        self.state = "betting"  # betting, playing, won, lost
        self.revealed_count = 0
        self.current_mult = 1.0
        self.mult_history = []
        self.message = ""
        self.msg_timer = 0.0
        self.win_amount = 0.0

        # UI anim
        self.bg_phase = 0.0
        self.btn_hover = {}
        self.cashout_pulse = 0.0
        self.lose_flash = 0.0
        self.win_burst = 0.0

        self._build_grid()
        self._layout()

    def save_balance(self):
        balances = load_balances()
        balances[CURRENT_USER] = float(self.credits)
        save_balances(balances)

    def _build_grid(self):
        self.tiles = [[Tile(r, c) for c in range(self.grid_size)] for r in range(self.grid_size)]

    def _layout(self):
        # Left panel
        self.panel_w = 280
        self.panel_rect = pygame.Rect(20, 20, self.panel_w, self.H - 40)

        # Grid area – centre-right
        max_grid = min(self.W - self.panel_w - 100, self.H - 160)
        self.tile_gap = 8
        n = self.grid_size
        self.tile_size = int((max_grid - (n - 1) * self.tile_gap) / n)
        self.tile_size = max(36, min(self.tile_size, 92))
        grid_w = n * self.tile_size + (n - 1) * self.tile_gap
        grid_h = grid_w
        self.grid_x = self.panel_w + 40 + (self.W - self.panel_w - 60 - grid_w) // 2
        # šiek tiek žemiau – vietos MINES antraštei ir mult juostai
        self.grid_y = (self.H - grid_h) // 2 + 10

        # Multiplier strip above grid
        self.mult_y = self.grid_y - 48

    def _tile_rect(self, r, c):
        x = self.grid_x + c * (self.tile_size + self.tile_gap)
        y = self.grid_y + r * (self.tile_size + self.tile_gap)
        return pygame.Rect(x, y, self.tile_size, self.tile_size)

    def max_mines(self):
        return self.grid_size * self.grid_size - 1

    # ----- odds (kaip real casino Mines) -----
    def _calc_mult(self, gems_found):
        """
        Stake / Shuffle stilius:
        mult = 0.99 * Π (total - i) / (safe - i)  i=0..gems-1
        """
        total = self.grid_size * self.grid_size
        mines = self.mine_count
        safe = total - mines
        if gems_found <= 0 or gems_found > safe or safe <= 0:
            return 1.0
        mult = 1.0 - HOUSE_EDGE
        for i in range(gems_found):
            mult *= (total - i) / float(safe - i)
        # apvalinimas kaip casino UI (2 skaitmenys)
        return max(1.01, round(mult, 2))

    def _next_mults(self, count=5):
        out = []
        for i in range(1, count + 1):
            m = self._calc_mult(self.revealed_count + i)
            out.append(m)
        return out

    # ----- game flow -----
    def start_round(self):
        if self.state == "playing":
            return
        if Decimal(str(self.bet)) > self.credits or self.bet < MIN_BET:
            self._toast("Nepakanka kreditų!")
            return

        total = self.grid_size * self.grid_size
        if self.mine_count >= total:
            self.mine_count = max(1, total - 1)

        self.credits -= Decimal(str(self.bet))
        self.save_balance()

        self._build_grid()
        # place mines
        positions = [(r, c) for r in range(self.grid_size) for c in range(self.grid_size)]
        random.shuffle(positions)
        for i in range(self.mine_count):
            r, c = positions[i]
            self.tiles[r][c].is_mine = True

        self.revealed_count = 0
        self.current_mult = 1.0
        self.mult_history = []
        self.state = "playing"
        self.message = ""
        self.win_amount = 0.0
        self.lose_flash = 0.0
        self.win_burst = 0.0
        self.particles.clear()

    def reveal(self, r, c):
        if self.state != "playing":
            return
        tile = self.tiles[r][c]
        if tile.revealed:
            return

        tile.revealed = True
        tile.anim = 0.01
        tile.scale_pop = 1.0

        cx = self.grid_x + c * (self.tile_size + self.tile_gap) + self.tile_size / 2
        cy = self.grid_y + r * (self.tile_size + self.tile_gap) + self.tile_size / 2

        if tile.is_mine:
            # LOSE
            tile.shake = 1.0
            self.state = "lost"
            self.lose_flash = 1.0
            self._toast("Looseris")
            for _ in range(28):
                self.particles.append(Particle(cx, cy, (255, 80, 60), "spark"))
            for _ in range(12):
                self.particles.append(Particle(cx, cy, (255, 180, 40), "spark"))
            # reveal all mines with delay feel
            for row in self.tiles:
                for t in row:
                    if t.is_mine and not t.revealed:
                        t.revealed = True
                        t.anim = 0.01
        else:
            # GEM
            self.revealed_count += 1
            self.current_mult = self._calc_mult(self.revealed_count)
            self.mult_history.append(self.current_mult)
            for _ in range(14):
                self.particles.append(Particle(cx, cy, (40, 230, 200), "spark"))
            for _ in range(6):
                self.particles.append(Particle(cx, cy, (180, 255, 240), "spark"))

            # auto-win if all safe revealed
            safe_total = self.grid_size * self.grid_size - self.mine_count
            if self.revealed_count >= safe_total:
                self.cash_out()

    def cash_out(self):
        if self.state != "playing" or self.revealed_count == 0:
            return
        win = round(self.bet * self.current_mult, 2)
        self.win_amount = win
        self.credits += Decimal(str(win))
        self.save_balance()
        self.state = "won"
        self.win_burst = 1.0
        self._toast(f"+{win:.2f}$")
        # sparkle on grid centre
        cx = self.grid_x + (self.grid_size * (self.tile_size + self.tile_gap) - self.tile_gap) / 2
        cy = self.grid_y + (self.grid_size * (self.tile_size + self.tile_gap) - self.tile_gap) / 2
        for _ in range(40):
            self.particles.append(Particle(cx, cy, (255, 220, 80), "spark"))

    def _toast(self, text):
        self.message = text
        self.msg_timer = 2.2

    # ----- input -----
    def change_bet(self, delta):
        if self.state == "playing":
            return
        self.bet = round(self.bet + delta, 2)
        self.bet = max(MIN_BET, min(self.bet, float(self.credits)))

    def set_grid(self, size):
        if self.state == "playing":
            return
        self.grid_size = size
        self.mine_count = min(self.mine_count, self.max_mines())
        self.mine_count = max(1, self.mine_count)
        self._build_grid()
        self._layout()

    def set_mines(self, n):
        if self.state == "playing":
            return
        self.mine_count = max(1, min(int(n), self.max_mines()))

    def change_mines(self, delta):
        if self.state == "playing":
            return
        self.set_mines(self.mine_count + delta)

    # ----- update -----
    def update(self, dt):
        self.bg_phase += dt
        self.cashout_pulse += dt * 3

        if self.msg_timer > 0:
            self.msg_timer -= dt
            if self.msg_timer <= 0:
                self.message = ""

        if self.lose_flash > 0:
            self.lose_flash = max(0, self.lose_flash - dt * 1.2)
        if self.win_burst > 0:
            self.win_burst = max(0, self.win_burst - dt * 0.9)

        # tiles
        for row in self.tiles:
            for t in row:
                if t.revealed and t.anim < 1.0:
                    t.anim = min(1.0, t.anim + dt * 3.5)
                if t.scale_pop > 0:
                    t.scale_pop = max(0, t.scale_pop - dt * 4)
                if t.shake > 0:
                    t.shake = max(0, t.shake - dt * 3)
                t.pulse += dt * 2.5
                # hover
                rect = self._tile_rect(t.row, t.col)
                mouse = pygame.mouse.get_pos()
                target = 1.0 if rect.collidepoint(mouse) and self.state == "playing" and not t.revealed else 0.0
                t.hover_t += (target - t.hover_t) * min(1.0, dt * 12)

        # particles
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.update(dt)

    # ----- draw helpers -----
    def _draw_rounded(self, rect, color, radius=12, border=None, border_w=2):
        pygame.draw.rect(self.screen, color, rect, border_radius=radius)
        if border:
            pygame.draw.rect(self.screen, border, rect, border_w, border_radius=radius)

    def _draw_gem(self, cx, cy, size, alpha=255):
        """Faceted gem diamond shape with 3D feel."""
        s = size
        a = max(0, min(255, int(alpha))) / 255.0

        def fade(rgb):
            # blend toward dark so fade-in looks soft without RGBA polygons
            return (
                int(rgb[0] * a + 20 * (1 - a)),
                int(rgb[1] * a + 180 * (1 - a)),
                int(rgb[2] * a + 160 * (1 - a)),
            )

        top = (cx, cy - s * 0.55)
        right = (cx + s * 0.5, cy - s * 0.05)
        bottom = (cx, cy + s * 0.55)
        left = (cx - s * 0.5, cy - s * 0.05)
        mid_t = (cx, cy - s * 0.15)

        cols = [
            ((60, 255, 220), [top, right, mid_t]),
            ((20, 200, 180), [top, left, mid_t]),
            ((0, 160, 150), [mid_t, right, bottom]),
            ((0, 130, 130), [mid_t, left, bottom]),
        ]
        for col, pts in cols:
            pygame.draw.polygon(self.screen, fade(col), pts)
        # highlight
        hi = fade((180, 255, 240))
        pygame.draw.line(self.screen, hi, (cx - s * 0.12, cy - s * 0.35),
                         (cx + s * 0.08, cy - s * 0.15), 2)

    def _draw_bomb(self, cx, cy, size, alpha=255, shake=0):
        ox = random.uniform(-3, 3) * shake
        oy = random.uniform(-3, 3) * shake
        cx, cy = cx + ox, cy + oy
        r = size * 0.38
        # body
        body = (40, 40, 50) if alpha > 200 else (40, 40, 50)
        pygame.draw.circle(self.screen, (30, 30, 40), (int(cx + 2), int(cy + 3)), int(r))
        pygame.draw.circle(self.screen, (55, 55, 70), (int(cx), int(cy)), int(r))
        # shine
        pygame.draw.circle(self.screen, (90, 95, 110), (int(cx - r * 0.3), int(cy - r * 0.3)), int(r * 0.25))
        # fuse
        pygame.draw.line(self.screen, (180, 140, 60), (cx, cy - r), (cx + r * 0.35, cy - r * 1.5), 3)
        # spark
        sx, sy = cx + r * 0.35, cy - r * 1.5
        for i in range(5):
            a = self.bg_phase * 8 + i * 1.2
            px = sx + math.cos(a) * 6
            py = sy + math.sin(a) * 6
            pygame.draw.circle(self.screen, (255, 180, 40), (int(px), int(py)), 3)
        pygame.draw.circle(self.screen, (255, 80, 40), (int(sx), int(sy)), 4)

    def _draw_tile(self, tile):
        rect = self._tile_rect(tile.row, tile.col)
        cx = rect.centerx
        cy = rect.centery

        # hover lift
        lift = tile.hover_t * 4
        scale = 1.0 + tile.hover_t * 0.06 + tile.scale_pop * 0.15 * (1 - tile.anim if tile.revealed else 1)

        if tile.revealed:
            t = ease_out_back(min(1.0, tile.anim))
            scale *= 0.85 + 0.15 * t
            # background
            if tile.is_mine:
                # bomb tile
                glow = int(80 * t)
                base = (
                    min(255, TILE_BOMB[0] + glow),
                    min(255, TILE_BOMB[1] + glow // 2),
                    min(255, TILE_BOMB[2] + glow // 2),
                )
                # radial glow
                glow_s = pygame.Surface((rect.w + 20, rect.h + 20), pygame.SRCALPHA)
                pygame.draw.rect(glow_s, (*TILE_BOMB_GLOW, int(60 * t)), (0, 0, rect.w + 20, rect.h + 20), border_radius=16)
                self.screen.blit(glow_s, (rect.x - 10, rect.y - 10 - lift))
                r2 = rect.inflate(-2, -2).move(0, -lift)
                self._draw_rounded(r2, base, radius=14)
                # inner
                inner = r2.inflate(-8, -8)
                pygame.draw.rect(self.screen, (120, 25, 40), inner, border_radius=10)
                if t > 0.3:
                    self._draw_bomb(cx, cy - lift, self.tile_size * 0.7 * t, alpha=int(255 * t), shake=tile.shake)
            else:
                # gem tile
                glow_s = pygame.Surface((rect.w + 20, rect.h + 20), pygame.SRCALPHA)
                pygame.draw.rect(glow_s, (*TILE_GEM_GLOW, int(50 * t)), (0, 0, rect.w + 20, rect.h + 20), border_radius=16)
                self.screen.blit(glow_s, (rect.x - 10, rect.y - 10 - lift))
                r2 = rect.inflate(-2, -2).move(0, -lift)
                # gradient-ish
                self._draw_rounded(r2, TILE_GEM, radius=14)
                inner = r2.inflate(-6, -6)
                pygame.draw.rect(self.screen, (30, 210, 185), inner, border_radius=10)
                # top highlight
                hi = pygame.Surface((inner.w, inner.h // 2), pygame.SRCALPHA)
                pygame.draw.rect(hi, (255, 255, 255, 30), (0, 0, inner.w, inner.h // 2), border_radius=10)
                self.screen.blit(hi, inner.topleft)
                if t > 0.25:
                    self._draw_gem(cx, cy - lift, self.tile_size * 0.42 * t, alpha=int(255 * t))
        else:
            # hidden tile – 3D raised look
            r = rect.move(0, -lift)
            # depth shadow
            sh = r.move(0, 4)
            pygame.draw.rect(self.screen, (10, 12, 25), sh, border_radius=14)
            # body
            col = (
                int(TILE_HIDDEN[0] + (TILE_HOVER[0] - TILE_HIDDEN[0]) * tile.hover_t),
                int(TILE_HIDDEN[1] + (TILE_HOVER[1] - TILE_HIDDEN[1]) * tile.hover_t),
                int(TILE_HIDDEN[2] + (TILE_HOVER[2] - TILE_HIDDEN[2]) * tile.hover_t),
            )
            self._draw_rounded(r, col, radius=14)
            # top edge highlight
            pygame.draw.line(self.screen, (70, 85, 130), (r.x + 10, r.y + 3), (r.right - 10, r.y + 3), 2)
            # subtle inner
            inner = r.inflate(-10, -10)
            pulse = 0.5 + 0.5 * math.sin(tile.pulse)
            ic = (45 + int(15 * pulse), 55 + int(15 * pulse), 95 + int(20 * pulse))
            pygame.draw.rect(self.screen, ic, inner, border_radius=10)
            # mini diamond hint
            s = self.tile_size * 0.12
            pts = [(cx, cy - s - lift), (cx + s, cy - lift), (cx, cy + s - lift), (cx - s, cy - lift)]
            pygame.draw.polygon(self.screen, (55, 70, 120), pts)

    def _draw_panel(self):
        p = self.panel_rect
        self._draw_rounded(p, PANEL_BG, radius=18, border=PANEL_BORDER, border_w=2)

        y = p.y + 24
        # Title
        title = self.font_big.render("MINES", True, WHITE)
        self.screen.blit(title, (p.centerx - title.get_width() // 2, y))
        y += 50

        mouse = pygame.mouse.get_pos()
        gap = 8

        # Number of mines – nuo 1 iki (n*n - 1)
        lbl = self.font_tiny.render("MINES", True, MUTED)
        self.screen.blit(lbl, (p.x + 20, y))
        y += 22

        mine_rect = pygame.Rect(p.x + 20, y, p.w - 40, 44)
        self._draw_rounded(mine_rect, (30, 38, 70), radius=12, border=(50, 60, 100), border_w=2)
        mine_str = f"{self.mine_count}  /  {self.max_mines()}"
        mt = self.font_med.render(mine_str, True, WHITE)
        self.screen.blit(mt, (mine_rect.centerx - mt.get_width() // 2, mine_rect.centery - mt.get_height() // 2))

        self._mine_btns = []  # (rect, delta)
        for label, dx, delta in [("-", -1, -1), ("+", 1, 1)]:
            br = pygame.Rect(mine_rect.x + (0 if dx < 0 else mine_rect.w - 40), mine_rect.y + 2, 38, 40)
            self._mine_btns.append((br, delta))
            hov = br.collidepoint(mouse) and self.state != "playing"
            self._draw_rounded(br, (55, 70, 120) if hov else (40, 50, 90), radius=10)
            t = self.font_med.render(label, True, WHITE)
            self.screen.blit(t, (br.centerx - t.get_width() // 2, br.centery - t.get_height() // 2))
        y += 55

        # Grid size – be 9x9
        lbl = self.font_tiny.render("GRID", True, MUTED)
        self.screen.blit(lbl, (p.x + 20, y))
        y += 22
        grids = [("3x3", 3), ("5x5", 5), ("7x7", 7)]
        bw = 70
        total_w = len(grids) * bw + (len(grids) - 1) * gap
        bx = p.centerx - total_w // 2
        self._grid_btns = []
        for i, (name, sz) in enumerate(grids):
            r = pygame.Rect(bx + i * (bw + gap), y, bw, 36)
            self._grid_btns.append((r, sz))
            active = self.grid_size == sz
            hovered = r.collidepoint(mouse) and self.state != "playing"
            col = ACCENT if active else ((50, 65, 110) if hovered else (40, 50, 85))
            self._draw_rounded(r, col, radius=10)
            t = self.font_small.render(name, True, (15, 20, 30) if active else WHITE)
            self.screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
        y += 55

        # Bet
        lbl = self.font_tiny.render("BET", True, MUTED)
        self.screen.blit(lbl, (p.x + 20, y))
        y += 22
        bet_rect = pygame.Rect(p.x + 20, y, p.w - 40, 44)
        self._draw_rounded(bet_rect, (30, 38, 70), radius=12, border=(50, 60, 100), border_w=2)
        bet_str = f"{self.bet:.2f}$"
        bt = self.font_med.render(bet_str, True, WHITE)
        self.screen.blit(bt, (bet_rect.centerx - bt.get_width() // 2, bet_rect.centery - bt.get_height() // 2))

        # +/- bet
        self._bet_btns = []
        for label, dx, delta in [("-", -1, -1), ("+", 1, 1)]:
            br = pygame.Rect(bet_rect.x + (0 if dx < 0 else bet_rect.w - 40), bet_rect.y + 2, 38, 40)
            self._bet_btns.append((br, delta))
            hov = br.collidepoint(mouse) and self.state != "playing"
            self._draw_rounded(br, (55, 70, 120) if hov else (40, 50, 90), radius=10)
            t = self.font_med.render(label, True, WHITE)
            self.screen.blit(t, (br.centerx - t.get_width() // 2, br.centery - t.get_height() // 2))
        y += 60

        # Quick bet chips
        chips = [1, 5, 10, 25]
        cw = 50
        total_w = len(chips) * cw + (len(chips) - 1) * 8
        bx = p.centerx - total_w // 2
        self._chip_btns = []
        for i, ch in enumerate(chips):
            r = pygame.Rect(bx + i * (cw + 8), y, cw, 32)
            self._chip_btns.append((r, ch))
            hov = r.collidepoint(mouse) and self.state != "playing"
            self._draw_rounded(r, (55, 70, 120) if hov else (40, 50, 90), radius=8)
            t = self.font_small.render(str(ch), True, WHITE)
            self.screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))
        y += 50

        # Main action button
        btn_h = 52
        btn = pygame.Rect(p.x + 20, y, p.w - 40, btn_h)
        self._main_btn = btn
        hov = btn.collidepoint(mouse)

        if self.state == "playing":
            if self.revealed_count > 0:
                # CASHOUT
                pulse = 0.5 + 0.5 * math.sin(self.cashout_pulse)
                col = (0, int(180 + 40 * pulse), int(140 + 30 * pulse))
                if hov:
                    col = (0, 230, 180)
                self._draw_rounded(btn, col, radius=14)
                win_preview = round(self.bet * self.current_mult, 2)
                t1 = self.font_med.render("CASHOUT", True, (10, 25, 20))
                t2 = self.font_small.render(f"{win_preview:.2f}$", True, (10, 30, 25))
                self.screen.blit(t1, (btn.centerx - t1.get_width() // 2, btn.y + 6))
                self.screen.blit(t2, (btn.centerx - t2.get_width() // 2, btn.y + 28))
            else:
                self._draw_rounded(btn, (40, 50, 80), radius=14)
                t = self.font_med.render("Rink gem...", True, MUTED)
                self.screen.blit(t, (btn.centerx - t.get_width() // 2, btn.centery - t.get_height() // 2))
        else:
            col = ACCENT if not hov else (40, 255, 210)
            self._draw_rounded(btn, col, radius=14)
            t = self.font_med.render("BET", True, (10, 25, 20))
            self.screen.blit(t, (btn.centerx - t.get_width() // 2, btn.centery - t.get_height() // 2))

        y += 70

        # Stats
        if self.state == "playing" and self.revealed_count > 0:
            mult_s = self.font_big.render(f"{self.current_mult:.2f}x", True, GOLD)
            self.screen.blit(mult_s, (p.centerx - mult_s.get_width() // 2, y))
            y += 36
            gems_s = self.font_small.render(f"Gems: {self.revealed_count}", True, ACCENT)
            self.screen.blit(gems_s, (p.centerx - gems_s.get_width() // 2, y))
            y += 28

        # Balance
        y = p.bottom - 90
        bal_lbl = self.font_tiny.render("BALANCE", True, MUTED)
        self.screen.blit(bal_lbl, (p.centerx - bal_lbl.get_width() // 2, y))
        y += 20
        cred = f"{float(self.credits):,.2f}$".replace(",", " ")
        bal_s = self.font_big.render(cred, True, GOLD)
        self.screen.blit(bal_s, (p.centerx - bal_s.get_width() // 2, y))

        # ESC
        esc = self.font_tiny.render("ESC – išeiti", True, MUTED)
        self.screen.blit(esc, (p.centerx - esc.get_width() // 2, p.bottom - 28))

    def _draw_multipliers(self):
        if self.state not in ("playing", "won") and self.revealed_count == 0:
            # show preview chain
            mults = [self._calc_mult(i) for i in range(1, min(6, self.grid_size * self.grid_size - self.mine_count + 1))]
        else:
            mults = self._next_mults(5)

        if not mults:
            return

        # current highlight
        box_w, box_h = 72, 34
        gap = 8
        total = len(mults) * box_w + (len(mults) - 1) * gap
        x0 = self.grid_x + (self.grid_size * (self.tile_size + self.tile_gap) - self.tile_gap) // 2 - total // 2
        y = self.mult_y

        for i, m in enumerate(mults):
            r = pygame.Rect(x0 + i * (box_w + gap), y, box_w, box_h)
            is_next = (i == 0 and self.state == "playing")
            col = (0, 100, 90) if is_next else (30, 38, 70)
            border = ACCENT if is_next else (50, 60, 100)
            self._draw_rounded(r, col, radius=8, border=border, border_w=2)
            t = self.font_small.render(f"{m:.2f}x", True, GOLD if is_next else MUTED)
            self.screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))

        # current mult big
        if self.revealed_count > 0:
            cur = self.font_title.render(f"{self.current_mult:.2f}x", True, GOLD)
            gx = self.grid_x + (self.grid_size * (self.tile_size + self.tile_gap) - self.tile_gap) // 2
            self.screen.blit(cur, (gx - cur.get_width() // 2, y - 50))

    def _draw_bg(self):
        self.screen.fill(BG)
        # subtle animated orbs
        for i, (ox, oy, rad, col) in enumerate([
            (0.2, 0.3, 180, (30, 40, 90)),
            (0.8, 0.6, 220, (25, 50, 70)),
            (0.5, 0.8, 150, (40, 30, 80)),
        ]):
            px = self.W * ox + math.sin(self.bg_phase * 0.3 + i) * 40
            py = self.H * oy + math.cos(self.bg_phase * 0.25 + i) * 30
            s = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, 40), (rad, rad), rad)
            self.screen.blit(s, (px - rad, py - rad))

        # lose flash
        if self.lose_flash > 0:
            ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            ov.fill((180, 20, 40, int(80 * self.lose_flash)))
            self.screen.blit(ov, (0, 0))

        # win glow
        if self.win_burst > 0:
            ov = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            ov.fill((0, 180, 140, int(40 * self.win_burst)))
            self.screen.blit(ov, (0, 0))

    def draw(self):
        self._draw_bg()
        self._draw_panel()

        # Title above grid – aukščiau, kad nesidengtų
        title = self.font_title.render("MINES", True, WHITE)
        gx = self.grid_x + (self.grid_size * (self.tile_size + self.tile_gap) - self.tile_gap) // 2
        title_y = max(12, self.grid_y - 140)
        for i in range(3):
            g = self.font_title.render("MINES", True, (0, 200, 180))
            g.set_alpha(30 - i * 8)
            self.screen.blit(g, (gx - g.get_width() // 2 + i, title_y + i))
        self.screen.blit(title, (gx - title.get_width() // 2, title_y))

        self._draw_multipliers()

        # tiles
        for row in self.tiles:
            for t in row:
                self._draw_tile(t)

        # particles
        for p in self.particles:
            p.draw(self.screen)

        # toast message
        if self.message and self.msg_timer > 0:
            a = min(1.0, self.msg_timer * 2) if self.msg_timer < 0.5 else 1.0
            if self.msg_timer < 0.4:
                a = self.msg_timer / 0.4
            col = RED if "Looseris" in self.message else GOLD
            t = self.font_big.render(self.message, True, col)
            # backdrop
            pad = 20
            br = pygame.Rect(0, 0, t.get_width() + pad * 2, t.get_height() + pad)
            br.center = (gx, self.grid_y + self.grid_size * (self.tile_size + self.tile_gap) // 2)
            s = pygame.Surface((br.w, br.h), pygame.SRCALPHA)
            pygame.draw.rect(s, (10, 12, 25, int(200 * a)), (0, 0, br.w, br.h), border_radius=14)
            self.screen.blit(s, br.topleft)
            t.set_alpha(int(255 * a))
            self.screen.blit(t, (br.centerx - t.get_width() // 2, br.centery - t.get_height() // 2))

    def handle_click(self, pos):
        # panel buttons
        if self.state != "playing":
            for r, delta in getattr(self, "_mine_btns", []):
                if r.collidepoint(pos):
                    self.change_mines(delta)
                    return
            for r, sz in getattr(self, "_grid_btns", []):
                if r.collidepoint(pos):
                    self.set_grid(sz)
                    return
            for r, delta in getattr(self, "_bet_btns", []):
                if r.collidepoint(pos):
                    self.change_bet(delta)
                    return
            for r, ch in getattr(self, "_chip_btns", []):
                if r.collidepoint(pos):
                    self.bet = min(float(self.credits), float(ch))
                    return

        # main button
        if hasattr(self, "_main_btn") and self._main_btn.collidepoint(pos):
            if self.state == "playing":
                if self.revealed_count > 0:
                    self.cash_out()
            else:
                self.start_round()
            return

        # grid
        if self.state == "playing":
            for r in range(self.grid_size):
                for c in range(self.grid_size):
                    if self._tile_rect(r, c).collidepoint(pos):
                        self.reveal(r, c)
                        return

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                elif event.type == pygame.FINGERDOWN:
                    # Convert normalized Android touch coordinates to pixels.
                    self.handle_click((int(event.x * self.W), int(event.y * self.H)))

            self.update(dt)
            self.draw()
            pygame.display.flip()

        pygame.quit()
def start(username):
    game = MinesGame(username)
    game.run()

if __name__ == "__main__":
    
    username = sys.argv[1] if len(sys.argv) > 1 else "player1"
    start(username)
