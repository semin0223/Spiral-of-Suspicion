import pygame, sys, random, math, array
from types import SimpleNamespace

# ================= 초기화 =================
pygame.init()
info = pygame.display.Info()
SCREEN_WIDTH, SCREEN_HEIGHT = info.current_w, info.current_h
MAP_WIDTH, MAP_HEIGHT = 7000, 5200  # 40개 방 기준으로 줄인 맵
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Spiral of Suspicion")
clock = pygame.time.Clock()

VENT_AUDIO_MAX_DIST = 275
vent_audio_channel = None
_vent_sound = None
_vent_audio_ok = False
_bomb_sound = None
_bomb_audio_ok = False

BOMB_AUDIO_MAX_DIST = 480


def _build_vent_ambience_sound(duration=2.0, sample_rate=22050):
    """Short loopable rumble + wobble (vent / duct air noise)."""
    n = int(sample_rate * duration)
    tau = math.tau
    buf = array.array("h")
    for i in range(n):
        t = i / sample_rate
        v = math.sin(tau * 46 * t) * 0.34
        v += math.sin(tau * (92 + 14 * math.sin(tau * 2.4 * t)) * t) * 0.2
        v += math.sin(tau * 165 * t) * 0.05 * math.sin(tau * 6.5 * t)
        v += (random.random() * 2 - 1) * 0.055
        buf.append(int(max(-1.0, min(1.0, v)) * 28000))
    return pygame.mixer.Sound(buffer=buf)


def _build_bomb_explosion_sound(duration=0.52, sample_rate=22050):
    """짧은 폭발: 저음 붐 + 감쇠 노이즈."""
    n = int(sample_rate * duration)
    tau = math.tau
    buf = array.array("h")
    for i in range(n):
        u = i / sample_rate
        env = math.exp(-u * 7.2)
        atk = min(1.0, u * 140.0)
        boom = math.sin(tau * 68.0 * u) * env * atk * 0.5
        noise = (random.random() * 2.0 - 1.0) * env * atk * 0.48
        crack = math.sin(tau * (180.0 + 320.0 * env) * u) * env * atk * 0.14
        v = boom + noise + crack
        buf.append(int(max(-1.0, min(1.0, v)) * 30000))
    return pygame.mixer.Sound(buffer=buf)


try:
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=1024)
    _vent_sound = _build_vent_ambience_sound()
    _vent_audio_ok = True
    _bomb_sound = _build_bomb_explosion_sound()
    _bomb_audio_ok = True
except Exception:
    _vent_audio_ok = False
    _bomb_audio_ok = False


def stop_vent_proximity_audio():
    global vent_audio_channel
    if vent_audio_channel is not None:
        try:
            if vent_audio_channel.get_busy():
                vent_audio_channel.stop()
        except Exception:
            pass
        vent_audio_channel = None


def update_vent_proximity_audio(round_playing, game_over_flag, game_started_flag):
    """Weird vent noise: only during random 'Vent noise detected!' event, near that vent."""
    global vent_audio_channel
    if not _vent_audio_ok or _vent_sound is None:
        return
    if not game_started_flag or not round_playing or game_over_flag:
        stop_vent_proximity_audio()
        return

    if vent_noise_timer <= 0 or vent_noise_vent is None:
        stop_vent_proximity_audio()
        return

    px = player.x + player.width / 2
    py = player.y + player.height / 2
    v = vent_noise_vent
    dist = math.hypot(px - v.x, py - v.y)

    if dist > VENT_AUDIO_MAX_DIST:
        stop_vent_proximity_audio()
        return

    t = dist / VENT_AUDIO_MAX_DIST
    vol = (1.0 - t) ** 1.4 * 0.42

    vol = max(0.0, min(1.0, vol))
    if vol < 0.02:
        stop_vent_proximity_audio()
        return

    if vent_audio_channel is None or not vent_audio_channel.get_busy():
        vent_audio_channel = _vent_sound.play(loops=-1, fade_ms=120)
    if vent_audio_channel is not None:
        vent_audio_channel.set_volume(vol)


def play_bomb_explosion_sound_near_player(world_x, world_y):
    """희생자 폭발 위치가 플레이어와 가까울 때만 폭발음(거리에 따라 볼륨)."""
    if not _bomb_audio_ok or _bomb_sound is None:
        return
    px = player.x + player.width / 2
    py = player.y + player.height / 2
    dist = math.hypot(px - world_x, py - world_y)
    if dist > BOMB_AUDIO_MAX_DIST:
        return
    t = dist / BOMB_AUDIO_MAX_DIST
    vol = (1.0 - t) ** 1.25 * 0.92
    vol = max(0.0, min(1.0, vol))
    if vol < 0.04:
        return
    ch = pygame.mixer.find_channel(True)
    if ch is None:
        return
    ch.play(_bomb_sound)
    ch.set_volume(vol)


def _make_ui_font(size):
    """Prefer a clear system UI font; fall back to default bitmap font."""
    for name in (
        "malgungothic", "Malgun Gothic",  # Windows Korean
        "nanumgothic", "NanumGothic",
        "gulim", "dotum",
        "segoeui", "Segoe UI", "arial", "helvetica", "calibri",
    ):
        try:
            f = pygame.font.SysFont(name, size)
            probe = f.render("My", True, (255, 255, 255))
            if probe.get_width() > 8:
                return f
        except Exception:
            continue
    return pygame.font.SysFont(None, size)


font = _make_ui_font(28)
nick_font = _make_ui_font(20)
title_font = _make_ui_font(64)
menu_font = _make_ui_font(36)

# ================= 색상 =================
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
RED, GREEN, BLUE, YELLOW = (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)
GRAY, DARK_GRAY, PURPLE, CYAN = (50, 50, 50), (30, 30, 30), (150, 0, 150), (0, 255, 255)
ROOM_FLOOR_A = (34, 42, 58)
ROOM_FLOOR_B = (42, 36, 64)
ROOM_FLOOR_C = (36, 56, 52)
CORRIDOR_FLOOR = (58, 58, 66)
ZONE_BORDER = (90, 90, 110)
NEON_LINE = (120, 190, 255)
ROOM_ACCENT = (90, 150, 210)
ORANGE = (255, 165, 0)
TROLL_COLOR = (128, 255, 0)
DOCTOR_COLOR = (0, 200, 200)
GUARD_COLOR = (100, 100, 255)
BOMBER_COLOR = (255, 90, 90)
MAD_SCIENTIST_COLOR = (90, 220, 130)
ENGINEER_COLOR = (120, 220, 255)
UNDERTAKER_COLOR = (180, 140, 220)
TASK_COLOR = YELLOW


def random_color(lo=60, hi=255):
    """Random RGB for player/AI body color."""
    return (random.randint(lo, hi), random.randint(lo, hi), random.randint(lo, hi))


NICKNAME_POOL = [
    "Apollo", "Nova", "Blaze", "Frost", "Echo", "Pixel", "Orbit", "Comet",
    "Mango", "Peach", "Kiwi", "Berry", "Cocoa", "Mocha", "Lunar", "Solar",
    "Mint", "Lilac", "Coral", "Jet", "Silver", "Gold", "Ruby", "Sapphire",
    "Crimson", "Azure", "Jade", "Amber", "Violet", "Sky", "Lime", "Grape",
    "Alpha", "Bravo", "Delta", "Omega", "Sigma", "Vega", "Lyra", "Draco",
    "Aiden", "Bella", "Chloe", "Dylan", "Ethan", "Fiona", "Grace", "Henry",
    "Iris", "Jack", "Kara", "Leo", "Mia", "Noah", "Olivia", "Parker",
    "Quinn", "Riley", "Sofia", "Theo", "Uma", "Victor", "Wendy", "Xander",
    "Yuna", "Zane", "Ariel", "Benny", "Celine", "Daisy", "Eli", "Felix",
    "Gina", "Harper", "Isaac", "Juno", "Kai", "Lena", "Milo", "Nora",
    "Owen", "Penny", "Reina", "Simon", "Tara", "Uri", "Vera", "Will",
    "Zoe", "Robin", "Sunny", "River", "Cloud", "Stone", "Flame", "Storm",
    "Shadow", "Spark", "Copper", "Indigo", "Marble", "Rocket", "Anchor", "Quest",
]


def assign_unique_nicknames():
    """Assign unique random nicknames from the pool to player and all AI."""
    pool = list(NICKNAME_POOL)
    random.shuffle(pool)
    everybody = [player] + AIs
    for i, p in enumerate(everybody):
        if i < len(pool):
            p.nickname = pool[i]
        else:
            p.nickname = f"Guest{i + 1}"


# ================= 클래스 =================
class Player:
    def __init__(self,x,y,color,role="crew",avoid_player=False):
        self.x,self.y,self.color=x,y,color
        self.width,self.height=25,25
        self.role=role
        self.nickname = ""
        self.alive=True
        self.ghost=False  # 유령 상태
        self.task_progress=0
        self.target_task=None
        self.venting=False
        self.vent_time=0
        self.avoid_player=avoid_player
        self.fleeing=False
        self.flee_timer=0
        self.flee_target=None
        self.suspect_player=None  # 의심하는 플레이어
        self.flee_weave_phase=0  # 도망 시 지그재그(속도 유지)
        self.wander_target=None  # 임포스터 돌아다니기 목표
        self.natural_action_timer = 0  # 크루 AI 자연 행동 지속 시간
        self.natural_action = None  # "wander", "buddy", "idle"
        self.hunt_target=None  # 임포스터 추적 대상 (고립된 크루)
        self.last_kill_vent=None  # 킬 후 환풍구 탈출 고려용
        self.stun_timer=0  # 트롤 공격 시 30초 정지
        self.revive_used=False  # 의사: 타인 부활 1회
        self.undertaker_revive_used=False  # 장의사: 타인 부활 1회
        self.doctor_self_revive_used=False  # 닥터: 첫 사망 시 즉시 자기 부활(1회)
        self.sheriff_bullets = 1  # Shooter: hit imposter to keep bullet
        self.bombs_remaining = 7  # 폭탄광: 한 판당 폭탄 7개
        self.last_bomb_target = None  # 붐버 AI: 방금 폭탄 준 대상 재추적 방지
        self.nav_door_target = None  # 벽에 막히면 우선 이동할 문 좌표
        self.stats_tasks_completed = 0
        self.stats_kills = 0
        self.stats_stuns = 0
        self.stats_revives = 0
        self.gas_kill_cooldown = 0  # 미친 과학자: 독가스 40s 쿨다운(프레임)
        # 벽 끼임 탈출 상태 (벽 탈출이 역할 행동보다 우선)
        self.stuck_frames = 0
        self.escape_timer = 0
        self.escape_dir = (0, 0)
        self.spin_angle = 0
        self.dance_offset_x = 0
        self.dance_offset_y = 0
        self.dance_note_style = 0
        self.fake_task_timer = 0
    def rect(self):
        return pygame.Rect(self.x,self.y,self.width,self.height)
    def draw(self, camera_x, camera_y):
        if self.alive and not self.venting:
            screen_x = self.x - camera_x + self.dance_offset_x
            screen_y = self.y - camera_y + self.dance_offset_y
            if -30 < screen_x < SCREEN_WIDTH and -30 < screen_y < SCREEN_HEIGHT:
                border_color = TROLL_COLOR if self.stun_timer > 0 else WHITE
                body_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                pygame.draw.rect(body_surface, self.color, (0, 0, self.width, self.height))
                pygame.draw.rect(body_surface, border_color, (0, 0, self.width, self.height), 2)
                pygame.draw.rect(body_surface, WHITE, (self.width // 2 - 3, 3, 6, 5), border_radius=2)
                if self.spin_angle % 360:
                    rotated = pygame.transform.rotate(body_surface, self.spin_angle)
                    rr = rotated.get_rect(center=(screen_x + self.width // 2, screen_y + self.height // 2))
                    screen.blit(rotated, rr)
                else:
                    screen.blit(body_surface, (screen_x, screen_y))
                if self.nickname:
                    nt = nick_font.render(self.nickname, True, WHITE)
                    screen.blit(nt, (screen_x + self.width // 2 - nt.get_width() // 2, screen_y - nt.get_height() - 2))
        elif self.ghost:
            # 살아 있을 때는 다른 사람 유령 안 보임; 본인이 유령일 때만 전원 표시
            if player.alive:
                return
            screen_x = self.x - camera_x + self.dance_offset_x
            screen_y = self.y - camera_y + self.dance_offset_y
            if -30 < screen_x < SCREEN_WIDTH and -30 < screen_y < SCREEN_HEIGHT:
                # 투명 Surface 생성
                ghost_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                ghost_surface.fill((*self.color, 150))  # 60% 투명
                # 테두리
                pygame.draw.rect(ghost_surface, (128, 128, 128), (0, 0, self.width, self.height), 1)
                pygame.draw.rect(ghost_surface, (230, 230, 255), (self.width // 2 - 3, 3, 6, 5), border_radius=2)
                if self.spin_angle % 360:
                    rotated = pygame.transform.rotate(ghost_surface, self.spin_angle)
                    rr = rotated.get_rect(center=(screen_x + self.width // 2, screen_y + self.height // 2))
                    screen.blit(rotated, rr)
                else:
                    screen.blit(ghost_surface, (screen_x, screen_y))
                if self.nickname:
                    nt = nick_font.render(self.nickname, True, (220, 220, 220))
                    screen.blit(nt, (screen_x + self.width // 2 - nt.get_width() // 2, screen_y - nt.get_height() - 2))

class Task:
    def __init__(self, x, y, task_type="normal"):
        self.x, self.y = x, y
        self.width, self.height = 25, 25
        self.completed = False
        self.task_type = task_type  # "normal", "fix", "upload"
        self.completion_time = 0  # 미션 완료를 위해 필요한 시간 (프레임)
        self.time_required = {"normal": 120, "fix": 180, "upload": 240}  # 각 타입별 소요 시간
        self.time_needed = self.time_required.get(task_type, 120)
    
    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)
    
    def draw(self, player, camera_x, camera_y):
        if math.hypot(self.x-player.x, self.y-player.y) < 250:
            screen_x = self.x - camera_x
            screen_y = self.y - camera_y
            if -20 < screen_x < SCREEN_WIDTH and -20 < screen_y < SCREEN_HEIGHT:
                color = TASK_COLOR if not self.completed else GREEN
                pygame.draw.rect(screen, color, (screen_x, screen_y, self.width, self.height))
                pygame.draw.rect(screen, WHITE, (screen_x, screen_y, self.width, self.height), 2)

class Wall:
    def __init__(self,x,y,w,h):
        self.rect=pygame.Rect(x,y,w,h)
    def draw(self, camera_x, camera_y):
        screen_x = self.rect.x - camera_x
        screen_y = self.rect.y - camera_y
        if -self.rect.w < screen_x < SCREEN_WIDTH and -self.rect.h < screen_y < SCREEN_HEIGHT:
            pygame.draw.rect(screen, DARK_GRAY, (screen_x, screen_y, self.rect.w, self.rect.h))

class Body:
    def __init__(self,x,y,dead_player=None):
        self.x,self.y=x,y
        self.width,self.height=25,25
        self.dead_player=dead_player  # 의사 부활용
    def rect(self):
        return pygame.Rect(self.x,self.y,self.width,self.height)
    def draw(self, player, camera_x, camera_y):
        if math.hypot(self.x-player.x,self.y-player.y)<300:
            screen_x = self.x - camera_x
            screen_y = self.y - camera_y
            if -30 < screen_x < SCREEN_WIDTH and -30 < screen_y < SCREEN_HEIGHT:
                pygame.draw.rect(screen, PURPLE, (screen_x, screen_y, self.width, self.height))

class Vent:
    def __init__(self,x,y,vent_id):
        self.x,self.y=x,y
        self.radius=15
        self.id=vent_id
        self.available_vents=[]
    def rect(self):
        return pygame.Rect(self.x-self.radius,self.y-self.radius,self.radius*2,self.radius*2)
    def draw(self, camera_x, camera_y):
        screen_x = self.x - camera_x
        screen_y = self.y - camera_y
        if -30 < screen_x < SCREEN_WIDTH and -30 < screen_y < SCREEN_HEIGHT:
            pygame.draw.circle(screen, CYAN, (screen_x, screen_y), self.radius)
            pygame.draw.circle(screen, WHITE, (screen_x, screen_y), self.radius, 2)

# ================= 변수 =================
# 고정 인원 구성:
# 크루9, 임포2, 의사1, 가드1, 엔지니어1, 장의사1, 셔리프1, 붐버1, 트롤1, 미친 과학자1 (총 18)
ROLE_QUOTA = {
    "crew": 9,
    "imposter": 2,
    "doctor": 1,
    "guard": 1,
    "engineer": 1,
    "undertaker": 1,
    "sheriff": 1,
    "bomber": 1,
    "troll": 1,
    "mad_scientist": 1,
}

# 플레이어 역할은 인원수와 상관없이 모든 직업이 같은 확률로 선택됨.
player_role = random.choice(list(ROLE_QUOTA.keys()))
player = Player(MAP_WIDTH // 2, MAP_HEIGHT // 2, random_color(60, 255), player_role)

CREW_ROLES = ("crew", "doctor", "guard", "engineer", "undertaker", "sheriff")
# 임포 판정·사보 태세 제외 등에 쓰는 중립/서브 진영 (크루 미션 없음)
NEUTRAL_SIDE_ROLES = ("troll", "bomber", "mad_scientist")
# 화면 표시용 직업명 (내부 role 문자열과 다를 수 있음)
ROLE_DISPLAY_NAME = {
    "crew": "Crew",
    "doctor": "Doctor",
    "guard": "Guard",
    "engineer": "Engineer",
    "undertaker": "Undertaker",
    "sheriff": "Shooter",
    "imposter": "Imposter",
    "troll": "Troll",
    "bomber": "Bomber",
    "mad_scientist": "Mad Scientist",
}


def get_role_display_name(role_key):
    return ROLE_DISPLAY_NAME.get(role_key, role_key.replace("_", " ").title())

# 관전 가능 역할 (죽은 임포 포함)
SPECTATE_DOCTOR_ROLES = (
    "crew",
    "doctor",
    "guard",
    "engineer",
    "undertaker",
    "troll",
    "bomber",
    "mad_scientist",
    "imposter",
)
# Role labels above heads in spectate overlay (임포는 숨김)
SPECTATE_ROLE_LABELS = {
    "doctor": ("Doctor", DOCTOR_COLOR),
    "guard": ("Guard", GUARD_COLOR),
    "engineer": ("Engineer", ENGINEER_COLOR),
    "undertaker": ("Undertaker", UNDERTAKER_COLOR),
    "sheriff": ("Shooter", GUARD_COLOR),
    "troll": ("Troll", TROLL_COLOR),
    "bomber": ("Bomber", BOMBER_COLOR),
    "mad_scientist": ("Mad Scientist", MAD_SCIENTIST_COLOR),
}
num_ai = sum(ROLE_QUOTA.values()) - 1  # 전체 인원 중 플레이어 1명 제외
ai_roles = []
for role_name, cnt in ROLE_QUOTA.items():
    remain = cnt - (1 if player_role == role_name else 0)
    ai_roles.extend([role_name] * max(0, remain))
random.shuffle(ai_roles)

positions = [(random.randint(100, MAP_WIDTH-100), random.randint(100, MAP_HEIGHT-100)) for _ in range(num_ai)]
AIs=[]
avoid_ai_idx = random.randint(0, num_ai-1)
for i in range(num_ai):
    avoid = (i == avoid_ai_idx)
    AIs.append(Player(positions[i][0], positions[i][1], random_color(60, 255), ai_roles[i], avoid_player=avoid))

assign_unique_nicknames()

# 다양한 미션 타입 생성
task_types = ["normal", "normal", "normal", "fix", "fix", "upload"]
tasks = []
for i in range(100):  # 큰 맵/다인원 기준 미션 수 증가
    task_type = random.choice(task_types)
    tasks.append(Task(random.randint(100, MAP_WIDTH-100), random.randint(100, MAP_HEIGHT-100), task_type))

# 환기 시스템 (큰 맵에 더 많은 환풍구)
vents = [
    Vent(600, 800, 0),
    Vent(MAP_WIDTH-600, 800, 1),
    Vent(600, MAP_HEIGHT-800, 2),
    Vent(MAP_WIDTH-600, MAP_HEIGHT-800, 3),
    Vent(MAP_WIDTH//2, MAP_HEIGHT//2, 4),
    Vent(1500, 1200, 5),
    Vent(MAP_WIDTH-1500, 1200, 6),
    Vent(1500, MAP_HEIGHT-1500, 7),
    Vent(MAP_WIDTH-1500, MAP_HEIGHT-1500, 8),
    Vent(MAP_WIDTH // 4, MAP_HEIGHT // 3, 9),
    Vent(MAP_WIDTH * 3 // 4, MAP_HEIGHT // 3, 10),
    Vent(MAP_WIDTH // 4, MAP_HEIGHT * 2 // 3, 11),
    Vent(MAP_WIDTH * 3 // 4, MAP_HEIGHT * 2 // 3, 12),
    Vent(2600, MAP_HEIGHT // 2, 13),
    Vent(MAP_WIDTH - 2600, MAP_HEIGHT // 2, 14),
]
for i, vent in enumerate(vents):
    vent.available_vents = [v for j, v in enumerate(vents) if i != j]

# ================= 방 / 벽 =================
# 구조물 대신 방 여러 개 + 방 사이 문(틈) 기반 레이아웃
walls = [
    Wall(0, 0, MAP_WIDTH, 50),
    Wall(0, 0, 50, MAP_HEIGHT),
    Wall(0, MAP_HEIGHT - 50, MAP_WIDTH, 50),
    Wall(MAP_WIDTH - 50, 0, 50, MAP_HEIGHT),
]

WALL_THICK = 46
ROOM_COLS = 8
ROOM_ROWS = 5
MARGIN_X = 220
MARGIN_Y = 180
MARGIN_X = 70
MARGIN_Y = 70
DOOR_SIZE = 170

cell_w = (MAP_WIDTH - (MARGIN_X * 2)) // ROOM_COLS
cell_h = (MAP_HEIGHT - (MARGIN_Y * 2)) // ROOM_ROWS

room_names = [
    "Cafeteria", "Admin", "Weapons", "Navigation", "Shields",
    "MedBay", "Storage", "Electrical", "Reactor", "Security",
    "Upper Engine", "Lower Engine", "Comms", "O2", "Specimen",
    "Laboratory", "Office", "Vitals", "Armory", "Vault",
]
# 40개 방 이름 보장
while len(room_names) < ROOM_COLS * ROOM_ROWS:
    room_names.append(f"Sector {len(room_names) + 1}")
room_palette = [ROOM_FLOOR_A, ROOM_FLOOR_B, ROOM_FLOOR_C]
room_zones = []
ROOM_ZONE_SCALE = 0.92  # 방들이 거의 붙어 보이도록 크게 표시

# 방 바닥 영역
idx = 0
for row in range(ROOM_ROWS):
    for col in range(ROOM_COLS):
        rx = MARGIN_X + col * cell_w + WALL_THICK // 2
        ry = MARGIN_Y + row * cell_h + WALL_THICK // 2
        base_rw = cell_w - WALL_THICK
        base_rh = cell_h - WALL_THICK
        rw = int(base_rw * ROOM_ZONE_SCALE)
        rh = int(base_rh * ROOM_ZONE_SCALE)
        rx += (base_rw - rw) // 2
        ry += (base_rh - rh) // 2
        room_zones.append({
            "num": idx + 1,
            "name": room_names[idx % len(room_names)],
            "rect": pygame.Rect(rx, ry, rw, rh),
            "color": room_palette[(row + col) % len(room_palette)],
        })
        idx += 1

# 세로 구분벽(문 포함)
for col in range(1, ROOM_COLS):
    x = MARGIN_X + col * cell_w - WALL_THICK // 2
    for row in range(ROOM_ROWS):
        y0 = MARGIN_Y + row * cell_h
        y1 = y0 + cell_h
        door_center = y0 + cell_h // 2
        top_h = max(0, door_center - DOOR_SIZE // 2 - y0)
        bot_y = door_center + DOOR_SIZE // 2
        bot_h = max(0, y1 - bot_y)
        if top_h > 0:
            walls.append(Wall(x, y0, WALL_THICK, top_h))
        if bot_h > 0:
            walls.append(Wall(x, bot_y, WALL_THICK, bot_h))

# 가로 구분벽(문 포함)
for row in range(1, ROOM_ROWS):
    y = MARGIN_Y + row * cell_h - WALL_THICK // 2
    for col in range(ROOM_COLS):
        x0 = MARGIN_X + col * cell_w
        x1 = x0 + cell_w
        door_center = x0 + cell_w // 2
        left_w = max(0, door_center - DOOR_SIZE // 2 - x0)
        right_x = door_center + DOOR_SIZE // 2
        right_w = max(0, x1 - right_x)
        if left_w > 0:
            walls.append(Wall(x0, y, left_w, WALL_THICK))
        if right_w > 0:
            walls.append(Wall(right_x, y, right_w, WALL_THICK))

# 복도 바닥은 벽 주변 띠 형태로 계산
corridor_zones = []
door_points = []
for col in range(1, ROOM_COLS):
    cx = MARGIN_X + col * cell_w - WALL_THICK
    corridor_zones.append(pygame.Rect(cx, MARGIN_Y, WALL_THICK * 2, ROOM_ROWS * cell_h))
for row in range(1, ROOM_ROWS):
    cy = MARGIN_Y + row * cell_h - WALL_THICK
    corridor_zones.append(pygame.Rect(MARGIN_X, cy, ROOM_COLS * cell_w, WALL_THICK * 2))

# 문 좌표(벽 막힘 시 AI 우회용)
for col in range(1, ROOM_COLS):
    x = MARGIN_X + col * cell_w
    for row in range(ROOM_ROWS):
        y = MARGIN_Y + row * cell_h + cell_h // 2
        door_points.append((x, y))
for row in range(1, ROOM_ROWS):
    y = MARGIN_Y + row * cell_h
    for col in range(ROOM_COLS):
        x = MARGIN_X + col * cell_w + cell_w // 2
        door_points.append((x, y))

# Door 클래스는 문은 벽의 일부를 파괴해서 자연스럽게 만들어지므로 불필요

bodies=[]
game_over=False
game_started=False
winner=None
dead_players=[]  # 죽은 플레이어 추적
last_body_count=0  # 시체 개수 변화 감지용

MOVE_SPEED = 5.2  # 플레이어·AI 전원 동일 이동 속도
SHIFT_SPEED_MULTIPLIER = 1.8  # Shift 누를 때 플레이어 가속 배율
SHIFT_MAX_DURATION_FRAMES = 5 * 60  # 5초
SHIFT_COOLDOWN_FRAMES = 30 * 60  # 30초
imposter_range=50
MAD_SCIENTIST_GAS_MAX_RANGE = 420  # 클릭 방향으로 살포 가능 최대 거리
MAD_SCIENTIST_GAS_CLOUD_RADIUS = 108  # 착탄 지점 초록 가스 구름 피해 반경
MAD_SCIENTIST_GAS_COOLDOWN_FRAMES = 40 * 60
task_range=40
vision_radius=int(min(MAP_WIDTH,MAP_HEIGHT)*0.15)
VISION_DARK_ALPHA = 225
VISION_EDGE_STEPS = ((1.00, 115), (0.96, 70), (0.91, 30), (0.86, 0))
VISION_RAY_STEP_DEG = 8
imposter_kill_cooldown=0
player_kill_cooldown=0
player_kill_count=0  # 플레이어가 킬한 수
STUN_DURATION = 30 * 60  # 30초 (60fps)
troll_stun_cooldown = 0  # 트롤 공격 쿨다운
shift_energy_frames = SHIFT_MAX_DURATION_FRAMES
shift_cooldown_frames = 0

# 폭탄 시스템
BOMB_FUSE_FRAMES = 15 * 60  # 반드시 15초 후 폭발
BOMB_PASS_RANGE = 65
active_bombs = []  # {"owner": Player, "holder": Player, "timer": int}
bomb_explosion_fx = []  # {"x","y","t","max_t","particles"} — 폭발 연출
gas_cloud_fx = []  # 독가스 구름 {"cx","cy","t","max_t"}
imposter_slice_fx = []  # 임포 킬: 네모 조각 {"cx","cy","color","t","max_t","fragments"}
bomb_kill_notice_text = ""
bomb_kill_notice_timer = 0

# 크루들이 가끔 4~5명씩 모여 노는 이벤트
crew_gather_timer = 0
crew_gather_cooldown = 60 * 8
crew_gather_target = None
crew_gather_members = []
crew_gather_notice_text = ""
crew_gather_notice_timer = 0

# 랜덤 이벤트 시스템 (짧은 쿨다운 = 이벤트가 더 자주)
event_cooldown = 60 * 7
event_notice_text = ""
event_notice_timer = 0
blackout_timer = 0
blackout_room = None
locked_room_timer = 0
locked_room = None
cleanup_timer = 0
cleanup_room = None
cleanup_progress = 0
vent_noise_timer = 0
vent_noise_vent = None
security_camera_timer = 0
security_camera_room = None
security_camera_view_index = 0
security_camera_mode = False
oxygen_timer = 0
oxygen_rooms = []
oxygen_fixed = []
oxygen_points = []
suspicion_event_timer = 0
dance_challenge_timer = 0
dance_challenge_room = None
dance_boost_timer = 0
ghost_prank_timer = 0
ghost_prank_pos = None
ghost_prank_cooldown = 0
sabotage_cooldown = 0
sabotage_select_mode = None
blackout_sabotage_owner = None
locked_room_sabotage_owner = None
oxygen_sabotage_owner = None

SECURITY_DESK_ROOM_NAME = "Security"


def player_in_security_room():
    """플레이어 중심이 Security 방에 있을 때만 보안 데스크 사용 가능."""
    if not player.alive:
        return False
    ri = get_room_index_at(player.x + player.width / 2, player.y + player.height / 2)
    if 0 <= ri < len(room_zones):
        return room_zones[ri]["name"] == SECURITY_DESK_ROOM_NAME
    return False


def security_camera_feed_active():
    """Security 방에서 B로 연 모니터일 때만 방 고정 시점."""
    return (
        player.alive
        and not player.venting
        and security_camera_mode
        and player_in_security_room()
    )


def reset_match_state():
    """새 판처럼 플레이어/AI/미션·이벤트 전역 상태를 초기화 (메인 메뉴로 나갈 때 등)."""
    global player, AIs, player_role
    global game_over, winner, bodies, dead_players, last_body_count
    global player_kill_count, imposter_kill_cooldown, player_kill_cooldown, troll_stun_cooldown
    global shift_energy_frames, shift_cooldown_frames
    global active_bombs, bomb_explosion_fx, gas_cloud_fx, imposter_slice_fx
    global bomb_kill_notice_text, bomb_kill_notice_timer
    global crew_gather_timer, crew_gather_cooldown, crew_gather_target, crew_gather_members
    global crew_gather_notice_text, crew_gather_notice_timer
    global event_cooldown, event_notice_text, event_notice_timer
    global blackout_timer, blackout_room, locked_room_timer, locked_room
    global cleanup_timer, cleanup_room, cleanup_progress
    global security_camera_timer, security_camera_room, security_camera_view_index, security_camera_mode
    global suspicion_event_timer, dance_challenge_timer, dance_challenge_room
    global dance_boost_timer, ghost_prank_timer, ghost_prank_pos, ghost_prank_cooldown
    global sabotage_cooldown, sabotage_select_mode
    global blackout_sabotage_owner, locked_room_sabotage_owner, oxygen_sabotage_owner
    global spectate_doctor_mode, spectate_follow_index

    stop_vent_proximity_audio()

    game_over = False
    winner = None
    bodies = []
    dead_players = []
    last_body_count = 0
    player_kill_count = 0
    imposter_kill_cooldown = 0
    player_kill_cooldown = 0
    troll_stun_cooldown = 0
    shift_energy_frames = SHIFT_MAX_DURATION_FRAMES
    shift_cooldown_frames = 0

    active_bombs = []
    bomb_explosion_fx = []
    gas_cloud_fx = []
    imposter_slice_fx = []
    bomb_kill_notice_text = ""
    bomb_kill_notice_timer = 0

    crew_gather_timer = 0
    crew_gather_cooldown = 60 * 8
    crew_gather_target = None
    crew_gather_members = []
    crew_gather_notice_text = ""
    crew_gather_notice_timer = 0

    event_cooldown = 60 * 7
    event_notice_text = ""
    event_notice_timer = 0
    blackout_timer = 0
    blackout_room = None
    locked_room_timer = 0
    locked_room = None
    cleanup_timer = 0
    cleanup_room = None
    cleanup_progress = 0
    vent_noise_timer = 0
    vent_noise_vent = None
    security_camera_timer = 0
    security_camera_room = None
    security_camera_view_index = 0
    security_camera_mode = False
    oxygen_timer = 0
    oxygen_rooms = []
    oxygen_fixed = []
    oxygen_points = []
    suspicion_event_timer = 0
    dance_challenge_timer = 0
    dance_challenge_room = None
    dance_boost_timer = 0
    ghost_prank_timer = 0
    ghost_prank_pos = None
    ghost_prank_cooldown = 0
    sabotage_cooldown = 0
    sabotage_select_mode = None
    blackout_sabotage_owner = None
    locked_room_sabotage_owner = None
    oxygen_sabotage_owner = None
    spectate_doctor_mode = False
    spectate_follow_index = 0

    player_role = random.choice(list(ROLE_QUOTA.keys()))
    player = Player(MAP_WIDTH // 2, MAP_HEIGHT // 2, random_color(60, 255), player_role)

    n_ai = sum(ROLE_QUOTA.values()) - 1
    new_ai_roles = []
    for role_name, cnt in ROLE_QUOTA.items():
        remain = cnt - (1 if player_role == role_name else 0)
        new_ai_roles.extend([role_name] * max(0, remain))
    random.shuffle(new_ai_roles)
    positions = [(random.randint(100, MAP_WIDTH - 100), random.randint(100, MAP_HEIGHT - 100)) for _ in range(n_ai)]
    AIs = []
    avoid_idx = random.randint(0, n_ai - 1) if n_ai > 0 else 0
    for i in range(n_ai):
        avoid = i == avoid_idx
        AIs.append(
            Player(positions[i][0], positions[i][1], random_color(60, 255), new_ai_roles[i], avoid_player=avoid)
        )

    assign_unique_nicknames()

    for task in tasks:
        task.completed = False
        task.completion_time = 0
        task.time_needed = task.time_required.get(task.task_type, 120)
        task.x, task.y = find_safe_position()

    player.x, player.y = find_safe_position()
    for ai in AIs:
        ai.x, ai.y = find_safe_position()


# ================= 함수 =================
def get_room_door_blocks(room_index):
    row = room_index // ROOM_COLS
    col = room_index % ROOM_COLS
    blocks = []
    block_w = WALL_THICK + 10
    block_h = DOOR_SIZE + 20
    if col > 0:
        x = MARGIN_X + col * cell_w - block_w // 2
        y = MARGIN_Y + row * cell_h + cell_h // 2 - block_h // 2
        blocks.append(pygame.Rect(x, y, block_w, block_h))
    if col < ROOM_COLS - 1:
        x = MARGIN_X + (col + 1) * cell_w - block_w // 2
        y = MARGIN_Y + row * cell_h + cell_h // 2 - block_h // 2
        blocks.append(pygame.Rect(x, y, block_w, block_h))
    if row > 0:
        x = MARGIN_X + col * cell_w + cell_w // 2 - block_h // 2
        y = MARGIN_Y + row * cell_h - block_w // 2
        blocks.append(pygame.Rect(x, y, block_h, block_w))
    if row < ROOM_ROWS - 1:
        x = MARGIN_X + col * cell_w + cell_w // 2 - block_h // 2
        y = MARGIN_Y + (row + 1) * cell_h - block_w // 2
        blocks.append(pygame.Rect(x, y, block_h, block_w))
    return blocks


def get_active_door_blocks():
    blocks = []
    if locked_room_timer > 0 and locked_room is not None:
        blocks.extend(get_room_door_blocks(locked_room))
    return blocks


def event_doors_block_entity(ent):
    return ent is not None and getattr(ent, "role", None) != "imposter"


def check_collision(rect, ent=None):
    """벽 충돌 감지"""
    for w in walls:
        if rect.colliderect(w.rect):
            return True
    if event_doors_block_entity(ent):
        for block in get_active_door_blocks():
            if rect.colliderect(block):
                return True
    return False


def _wall_overlap_area(rect, wall):
    c = rect.clip(wall.rect)
    return max(0, c.width) * max(0, c.height)


def slide_offset_candidates(blocked_rect, mx, my, spd):
    """Vertical wall (tall): slide up/down first. Horizontal wall (wide): slide left/right first."""
    hitting = [w for w in walls if blocked_rect.colliderect(w.rect)]
    if not hitting:
        return [(spd, 0), (-spd, 0), (0, spd), (0, -spd)]

    v_score = sum(_wall_overlap_area(blocked_rect, w) for w in hitting if w.rect.h > w.rect.w)
    h_score = sum(_wall_overlap_area(blocked_rect, w) for w in hitting if w.rect.w >= w.rect.h)

    cand = []
    if v_score > h_score:
        if my != 0:
            cand.append((0, my))
        cand.extend([(0, spd), (0, -spd)])
        if mx != 0:
            cand.append((mx, 0))
        cand.extend([(spd, 0), (-spd, 0)])
    elif h_score > v_score:
        if mx != 0:
            cand.append((mx, 0))
        cand.extend([(spd, 0), (-spd, 0)])
        if my != 0:
            cand.append((0, my))
        cand.extend([(0, spd), (0, -spd)])
    else:
        if abs(mx) >= abs(my):
            if my != 0:
                cand.append((0, my))
            cand.extend([(0, spd), (0, -spd), (mx, 0), (spd, 0), (-spd, 0)])
        else:
            if mx != 0:
                cand.append((mx, 0))
            cand.extend([(spd, 0), (-spd, 0), (0, my), (0, spd), (0, -spd)])

    out, seen = [], set()
    for t in cand:
        if t == (0, 0):
            continue
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def try_wall_slide_delta(x, y, w, h, mx, my, spd, ent=None):
    """Intended step (mx,my). Returns one applied (ox,oy) from current pos, or (0,0) if blocked."""
    nr = pygame.Rect(x + mx, y + my, w, h)
    if not check_collision(nr, ent):
        return mx, my
    for ox, oy in slide_offset_candidates(nr, mx, my, spd):
        ar = pygame.Rect(x + ox, y + oy, w, h)
        if not check_collision(ar, ent):
            return ox, oy
    return 0, 0


def choose_escape_direction(x, y, w, h, mx, my, spd, ent=None):
    """막힘 유형 기반 탈출 방향 선택.
    - 세로벽에 막힘: 상/하
    - 가로벽에 막힘: 좌/우
    - 코너(혼합): 방향 선택 대신 순간이동 처리로 넘김
    """
    blocked_rect = pygame.Rect(x + mx, y + my, w, h)
    hitting = [wobj for wobj in walls if blocked_rect.colliderect(wobj.rect)]
    if not hitting:
        for ox, oy in ((0, -spd), (0, spd), (spd, 0), (-spd, 0)):
            ar = pygame.Rect(x + ox, y + oy, w, h)
            if not check_collision(ar, ent):
                return ox, oy
        return 0, 0

    v_score = sum(_wall_overlap_area(blocked_rect, wobj) for wobj in hitting if wobj.rect.h > wobj.rect.w)
    h_score = sum(_wall_overlap_area(blocked_rect, wobj) for wobj in hitting if wobj.rect.w >= wobj.rect.h)

    # 코너/복합 충돌: 순간이동 처리
    if v_score > 0 and h_score > 0:
        return 0, 0

    # 세로벽 -> 상하
    if v_score > h_score:
        for ox, oy in ((0, -spd), (0, spd)):
            ar = pygame.Rect(x + ox, y + oy, w, h)
            if not check_collision(ar, ent):
                return ox, oy
        return 0, 0

    # 가로벽 -> 좌우
    for ox, oy in ((-spd, 0), (spd, 0)):
        ar = pygame.Rect(x + ox, y + oy, w, h)
        if not check_collision(ar, ent):
            return ox, oy
    return 0, 0


def force_unstuck_position(ent, max_radius=140):
    """현재 벽에 겹친 상태면 주변에서 가장 가까운 비충돌 위치로 강제 탈출."""
    base_x, base_y = ent.x, ent.y
    test_rect = pygame.Rect(base_x, base_y, ent.width, ent.height)
    if not check_collision(test_rect, ent):
        return False

    # 가까운 원형 탐색으로 벽 밖 좌표 찾기
    for r in range(10, max_radius + 1, 10):
        for ang in range(0, 360, 15):
            rad = math.radians(ang)
            nx = base_x + math.cos(rad) * r
            ny = base_y + math.sin(rad) * r
            nx = max(0, min(nx, MAP_WIDTH - ent.width))
            ny = max(0, min(ny, MAP_HEIGHT - ent.height))
            nr = pygame.Rect(nx, ny, ent.width, ent.height)
            if not check_collision(nr, ent):
                ent.x, ent.y = nx, ny
                ent.stuck_frames = 0
                ent.escape_timer = 0
                ent.escape_dir = (0, 0)
                return True
    return False


def apply_move_with_escape_priority(ent, mx, my, spd):
    """벽 탈출이 최우선인 이동 적용. 반환값: (moved, adx, ady)."""
    # 벽에 파묻힌 상태면 강제 탈출 먼저 수행
    force_unstuck_position(ent)

    # 이미 탈출 중이면 목적 행동보다 탈출 이동 먼저 수행
    if ent.escape_timer > 0 and ent.escape_dir != (0, 0):
        ex, ey = ent.escape_dir
        adx, ady = try_wall_slide_delta(ent.x, ent.y, ent.width, ent.height, ex, ey, spd, ent)
        if adx != 0 or ady != 0:
            ent.x = max(0, min(ent.x + adx, MAP_WIDTH - ent.width))
            ent.y = max(0, min(ent.y + ady, MAP_HEIGHT - ent.height))
            ent.escape_timer -= 1
            ent.stuck_frames = 0
            return True, adx, ady
        # 기존 탈출 방향이 막히면 방향을 다시 선택
        ndx, ndy = choose_escape_direction(ent.x, ent.y, ent.width, ent.height, ex, ey, spd * 1.35, ent)
        if (ndx, ndy) != (0, 0):
            ent.escape_dir = (ndx, ndy)
        else:
            # 코너/복합 막힘은 가까운 위치로 순간이동
            force_unstuck_position(ent)
            ent.escape_timer = max(0, ent.escape_timer - 1)

    adx, ady = try_wall_slide_delta(ent.x, ent.y, ent.width, ent.height, mx, my, spd, ent)
    if adx != 0 or ady != 0:
        ent.x = max(0, min(ent.x + adx, MAP_WIDTH - ent.width))
        ent.y = max(0, min(ent.y + ady, MAP_HEIGHT - ent.height))
        ent.stuck_frames = 0
        return True, adx, ady

    # 이동 의도는 있는데 실제 이동 0 -> 막힘 누적
    if abs(mx) > 0.01 or abs(my) > 0.01:
        ent.stuck_frames += 1
        if ent.stuck_frames >= 8:
            ent.escape_dir = choose_escape_direction(ent.x, ent.y, ent.width, ent.height, mx, my, spd, ent)
            if ent.escape_dir == (0, 0):
                # 코너 막힘 판단: 즉시 가까운 안전 위치로 이동
                force_unstuck_position(ent)
                ent.escape_timer = 0
            else:
                ent.escape_timer = 16
            ent.stuck_frames = 0
    else:
        ent.stuck_frames = 0
    return False, 0, 0


def find_safe_position():
    """벽과 겹치지 않는 안전한 위치 찾기"""
    while True:
        x = random.randint(50, MAP_WIDTH-50)
        y = random.randint(50, MAP_HEIGHT-50)
        test_rect = pygame.Rect(x, y, 25, 25)
        if not check_collision(test_rect):
            return x, y

def find_safe_position_near(cx, cy, radius=80):
    """지정 좌표 근처에서 벽에 끼지 않는 안전한 위치 찾기 (환풍구 포탈용)"""
    test_rect = pygame.Rect(cx, cy, 25, 25)
    if not check_collision(test_rect):
        return cx, cy
    for r in range(30, radius, 15):
        for angle in range(0, 360, 20):
            rad = math.radians(angle)
            x = int(cx + r * math.cos(rad))
            y = int(cy + r * math.sin(rad))
            x = max(50, min(x, MAP_WIDTH-50))
            y = max(50, min(y, MAP_HEIGHT-50))
            test_rect = pygame.Rect(x, y, 25, 25)
            if not check_collision(test_rect):
                return x, y
    return find_safe_position()

def can_see_player(observer, target):
    """시야 범위 내에 있는지 확인"""
    return math.hypot(observer.x-target.x, observer.y-target.y) <= get_effective_vision_radius()


def get_player_name(p):
    if p is player:
        return "Player"
    return p.nickname if p.nickname else get_role_display_name(p.role)


def attach_bomb(owner, target):
    """폭탄광이 타겟에게 15초 폭탄 부착."""
    if owner is None or target is None:
        return False
    if not owner.alive or not target.alive:
        return False
    if owner.role != "bomber":
        return False
    if owner.bombs_remaining <= 0:
        return False
    # 한 사람당 동시에 폭탄 1개만 허용
    for b in active_bombs:
        if b.get("holder") is target:
            return False
    owner.bombs_remaining -= 1
    active_bombs.append({"owner": owner, "holder": target, "timer": BOMB_FUSE_FRAMES})
    return True


def transfer_bomb(bomb, new_holder):
    if bomb is None or new_holder is None or not new_holder.alive:
        return False
    bomb["holder"] = new_holder
    return True


def start_fake_task(actor):
    if actor is None or actor.role != "imposter" or not actor.alive:
        return False
    near_task = next((t for t in tasks if math.hypot(actor.x - t.x, actor.y - t.y) < task_range + 25), None)
    if near_task is None:
        return False
    actor.fake_task_timer = 60 * 4
    for crew in [player] + AIs:
        if crew.alive and crew.role in CREW_ROLES and getattr(crew, "suspect_player", None) is actor:
            if math.hypot(crew.x - actor.x, crew.y - actor.y) < get_effective_vision_radius():
                crew.suspect_player = None
                crew.flee_timer = 0
    if actor is player:
        set_event_notice("Faking task...")
    return True


def spawn_bomb_explosion(world_x, world_y, burst_color=(255, 180, 90)):
    """폭탄 사망 시 연출. burst_color는 희생자 몸 색(그 자리에서 터지는 느낌)."""
    particles = []
    for _ in range(44):
        particles.append(
            (random.random() * math.tau, random.uniform(65, 280), random.uniform(0.25, 1.1))
        )
    bc = burst_color[:3] if burst_color else (255, 180, 90)
    bomb_explosion_fx.append(
        {
            "x": float(world_x),
            "y": float(world_y),
            "burst": (int(bc[0]), int(bc[1]), int(bc[2])),
            "t": 0,
            "max_t": 60,
            "particles": particles,
        }
    )
    play_bomb_explosion_sound_near_player(world_x, world_y)


def update_bomb_explosion_fx():
    global bomb_explosion_fx
    for fx in bomb_explosion_fx:
        fx["t"] += 1
    bomb_explosion_fx = [fx for fx in bomb_explosion_fx if fx["t"] < fx["max_t"]]


def draw_bomb_explosion_fx_world(camera_x, camera_y):
    """월드 좌표 폭발(코어·링·스파크). 플레이어 스프라이트 위에 그리기."""
    if not bomb_explosion_fx:
        return
    for fx in bomb_explosion_fx:
        sx = int(fx["x"] - camera_x)
        sy = int(fx["y"] - camera_y)
        t = fx["t"]
        mt = fx["max_t"]
        prog = t / mt
        bc = fx.get("burst", (255, 160, 80))
        # 희생자 몸색 코어가 커지며 타오르다 사라짐
        if t < 26:
            pulse = int(255 * (1.0 - t / 26.0))
            cr = int(22 + t * 7)
            glow = pygame.Surface((cr * 2 + 14, cr * 2 + 14), pygame.SRCALPHA)
            cx_surf = cr + 7
            cy_surf = cr + 7
            inner = (
                min(255, bc[0] + 85),
                min(255, bc[1] + 75),
                min(255, bc[2] + 55),
                min(255, pulse),
            )
            pygame.draw.circle(glow, inner, (cx_surf, cy_surf), cr)
            pygame.draw.circle(
                glow,
                (255, 255, 235, min(255, pulse * 2 // 3)),
                (cx_surf, cy_surf),
                max(3, cr // 3),
            )
            screen.blit(glow, (sx - cr - 7, sy - cr - 7))
            pygame.draw.circle(screen, (255, 140, 60), (sx, sy), min(cr, 52), 3)
        # 확산 링
        for k in range(6):
            r = int(18 + t * 6.5 + k * 38 - k * k)
            if r < 6:
                continue
            fade = max(0, min(255, 300 - t * 5 - k * 38))
            if fade < 18:
                continue
            mix = k / 5.0
            col = (
                int(bc[0] * (1 - mix) + 255 * mix),
                int(bc[1] * (1 - mix) + min(255, 80 + k * 28) * mix),
                int(bc[2] * (1 - mix) + 45 * mix),
            )
            pygame.draw.circle(screen, col, (sx, sy), r, max(2, 5 - k // 2))
        # 스파크
        for i, (ang, spd, jitter) in enumerate(fx["particles"]):
            dist = spd * ((t + 1) ** 0.52) * 0.38 * jitter
            px = int(sx + math.cos(ang) * dist)
            py = int(sy + math.sin(ang) * dist)
            if -30 < px < SCREEN_WIDTH + 30 and -30 < py < SCREEN_HEIGHT + 30:
                rs = max(1, int(6 * (1.0 - prog * 0.95)))
                col_a = bc if (i % 3 == 0) else (255, 200, 80)
                pygame.draw.circle(screen, col_a, (px, py), rs)
                pygame.draw.circle(screen, (255, 60, 40), (px, py), max(1, rs - 2))


def draw_bomb_explosion_fx_overlay(camera_x, camera_y):
    """전체 화면 플래시·가장자리. 뷰 안에서 터질 때만 강하게(죽는 위치 기준)."""
    if not bomb_explosion_fx:
        return
    margin = 100
    flash_alpha = 0
    for fx in bomb_explosion_fx:
        if fx["t"] >= 14:
            continue
        sx = fx["x"] - camera_x
        sy = fx["y"] - camera_y
        if not (-margin < sx < SCREEN_WIDTH + margin and -margin < sy < SCREEN_HEIGHT + margin):
            continue
        flash_alpha = max(flash_alpha, int(200 * (1.0 - fx["t"] / 14.0)))
    if flash_alpha <= 0:
        return
    flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    flash.fill((255, 235, 200, flash_alpha))
    screen.blit(flash, (0, 0))
    rim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    edge_a = min(120, flash_alpha // 2)
    band_a = min(90, flash_alpha // 3)
    pygame.draw.rect(rim, (255, 90, 40, edge_a), (0, 0, SCREEN_WIDTH, 52))
    pygame.draw.rect(rim, (255, 90, 40, edge_a), (0, SCREEN_HEIGHT - 52, SCREEN_WIDTH, 52))
    pygame.draw.rect(rim, (255, 90, 40, edge_a), (0, 0, 52, SCREEN_HEIGHT))
    pygame.draw.rect(rim, (255, 90, 40, edge_a), (SCREEN_WIDTH - 52, 0, 52, SCREEN_HEIGHT))
    pygame.draw.rect(rim, (255, 60, 30, band_a), (0, 0, SCREEN_WIDTH, 28))
    pygame.draw.rect(rim, (255, 60, 30, band_a), (0, SCREEN_HEIGHT - 28, SCREEN_WIDTH, 28))
    screen.blit(rim, (0, 0))


def spawn_imposter_slice_fx(victim):
    """임포스터 킬: 희생자 몸을 격자 네모로 쪼개 흩어지는 연출."""
    if victim is None:
        return
    ox = getattr(victim, "dance_offset_x", 0)
    oy = getattr(victim, "dance_offset_y", 0)
    cx = victim.x + victim.width / 2 + ox
    cy = victim.y + victim.height / 2 + oy
    w = float(victim.width)
    h = float(victim.height)
    rgb = victim.color if victim.color and len(victim.color) >= 3 else (180, 180, 200)
    cols, rows = 5, 5
    gap = 0.8
    fw = (w - gap * (cols - 1)) / cols
    fh = (h - gap * (rows - 1)) / rows
    fragments = []
    y0 = -h / 2
    for row in range(rows):
        x0 = -w / 2
        for col in range(cols):
            lx = x0 + fw / 2
            ly = y0 + fh / 2
            bias = (col - cols / 2) * 0.28 + (row - rows / 2) * 0.22
            angle = random.random() * math.tau + bias
            spd = random.uniform(2.0, 5.5)
            fragments.append(
                {
                    "lx": lx,
                    "ly": ly,
                    "fw": max(2.0, fw - 0.5),
                    "fh": max(2.0, fh - 0.5),
                    "vx": math.cos(angle) * spd,
                    "vy": math.sin(angle) * spd,
                }
            )
            x0 += fw + gap
        y0 += fh + gap
    imposter_slice_fx.append(
        {
            "cx": cx,
            "cy": cy,
            "color": (int(rgb[0]), int(rgb[1]), int(rgb[2])),
            "t": 0,
            "max_t": 32,
            "fragments": fragments,
        }
    )


def update_imposter_slice_fx():
    global imposter_slice_fx
    kept = []
    for fx in imposter_slice_fx:
        fx["t"] += 1
        if fx["t"] >= fx["max_t"]:
            continue
        drag = 0.9 + 0.07 * (fx["t"] / fx["max_t"])
        for fr in fx["fragments"]:
            fr["lx"] += fr["vx"]
            fr["ly"] += fr["vy"]
            fr["vx"] *= drag
            fr["vy"] *= drag
        kept.append(fx)
    imposter_slice_fx = kept


def draw_imposter_slice_fx(camera_x, camera_y):
    if not imposter_slice_fx:
        return
    for fx in imposter_slice_fx:
        t = fx["t"]
        mt = fx["max_t"]
        fade = max(0, int(255 * (1.0 - t / mt)))
        if fade < 6:
            continue
        col = fx["color"]
        for fr in fx["fragments"]:
            wx = fx["cx"] + fr["lx"]
            wy = fx["cy"] + fr["ly"]
            sx = int(wx - camera_x)
            sy = int(wy - camera_y)
            fw = max(1, int(fr["fw"]))
            fh = max(1, int(fr["fh"]))
            pad = 2
            if sx + fw < -40 or sy + fh < -40 or sx - fw > SCREEN_WIDTH + 40 or sy - fh > SCREEN_HEIGHT + 40:
                continue
            surf = pygame.Surface((fw + pad, fh + pad), pygame.SRCALPHA)
            surf.fill((col[0], col[1], col[2], fade))
            pygame.draw.rect(surf, (255, 255, 255, fade), surf.get_rect(), 1)
            screen.blit(surf, (sx - (fw + pad) // 2, sy - (fh + pad) // 2))


def kill_by_bomb(victim):
    global spectate_doctor_mode
    if victim is None or not victim.alive:
        return False
    # 닥터 즉시 자가부활은 기존 룰 유지
    if try_doctor_self_revive_on_kill(victim):
        return False
    cx = victim.x + victim.width / 2 + getattr(victim, "dance_offset_x", 0)
    cy = victim.y + victim.height / 2 + getattr(victim, "dance_offset_y", 0)
    spawn_bomb_explosion(cx, cy, victim.color)
    victim.alive = False
    victim.ghost = True
    victim.stun_timer = 0
    bodies.append(Body(victim.x, victim.y, victim))
    dead_players.append(victim)
    if victim is player:
        spectate_doctor_mode = False
    return True


def spawn_gas_cloud_fx(cx, cy):
    global gas_cloud_fx
    gas_cloud_fx.append({"cx": float(cx), "cy": float(cy), "t": 0, "max_t": 56})


def update_gas_cloud_fx():
    global gas_cloud_fx
    for fx in gas_cloud_fx:
        fx["t"] += 1
    gas_cloud_fx = [fx for fx in gas_cloud_fx if fx["t"] < fx["max_t"]]


def draw_gas_cloud_fx_world(camera_x, camera_y):
    """착탄 지점 초록 독가스 구름(페이드·맥동)."""
    if not gas_cloud_fx:
        return
    base_r = MAD_SCIENTIST_GAS_CLOUD_RADIUS
    for fx in gas_cloud_fx:
        sx = int(fx["cx"] - camera_x)
        sy = int(fx["cy"] - camera_y)
        t = fx["t"]
        mt = fx["max_t"]
        prog = t / mt
        pulse = 0.74 + 0.26 * math.sin(prog * math.pi)
        r = max(10, int(base_r * pulse))
        alpha_o = int(210 * (1.0 - prog * 0.93))
        if alpha_o < 5:
            continue
        dim = r * 2 + 28
        surf = pygame.Surface((dim, dim), pygame.SRCALPHA)
        cx0 = dim // 2
        cy0 = dim // 2
        for k in range(6):
            rk = int(r * (1.0 - k * 0.15))
            if rk < 4:
                break
            a = max(0, min(255, alpha_o - k * 34))
            pygame.draw.circle(surf, (35, 185, 88, a), (cx0, cy0), rk)
        pygame.draw.circle(
            surf,
            (160, 255, 190, min(255, alpha_o + 25)),
            (cx0, cy0),
            max(4, r // 6),
        )
        screen.blit(surf, (sx - cx0, sy - cy0))
        ring_a = max(0, int(140 * (1.0 - prog)))
        if ring_a > 10:
            pygame.draw.circle(screen, (80, 255, 140), (sx, sy), min(r + 6, base_r + 18), 2)


def deploy_poison_gas_cloud(attacker, aim_world_x, aim_world_y):
    """원거리 독가스 살포: 조준 지점(최대 거리 클램프)에 초록 구름, 반경 내 생존자 피해."""
    global spectate_doctor_mode, player_kill_count
    if attacker is None or not attacker.alive:
        return False
    px = attacker.x + attacker.width / 2
    py = attacker.y + attacker.height / 2
    dx = aim_world_x - px
    dy = aim_world_y - py
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        dx, dy, dist = 1.0, 0.0, 1.0
    if dist > MAD_SCIENTIST_GAS_MAX_RANGE:
        s = MAD_SCIENTIST_GAS_MAX_RANGE / dist
        dx *= s
        dy *= s
    cx = px + dx
    cy = py + dy
    if not is_path_clear(px, py, cx, cy):
        return False

    r = MAD_SCIENTIST_GAS_CLOUD_RADIUS
    victims = []
    for ent in [player] + AIs:
        if ent is attacker or not ent.alive:
            continue
        ex = ent.x + ent.width / 2 + getattr(ent, "dance_offset_x", 0)
        ey = ent.y + ent.height / 2 + getattr(ent, "dance_offset_y", 0)
        if math.hypot(ex - cx, ey - cy) <= r:
            victims.append(ent)
    victims.sort(key=lambda v: math.hypot(v.x - cx, v.y - cy))

    spawn_gas_cloud_fx(cx, cy)
    n_down = 0
    guard_hit = False
    for victim in victims:
        if try_doctor_self_revive_on_kill(victim):
            continue
        victim.alive = False
        victim.ghost = True
        victim.stun_timer = 0
        bodies.append(Body(victim.x, victim.y, victim))
        dead_players.append(victim)
        attacker.stats_kills += 1
        if attacker is player:
            player_kill_count += 1
        alert_crew_witnesses_attacker(attacker, victim)
        if victim.role == "guard":
            guard_hit = True
        if victim is player:
            spectate_doctor_mode = False
        n_down += 1

    if guard_hit:
        attacker.stun_timer = STUN_DURATION
    if n_down == 0:
        set_event_notice("Poison gas spread — no one in the cloud.")
    else:
        set_event_notice(f"Poison gas cloud — {n_down} eliminated!")
    return True


def kill_by_sabotage(victim, killer=None, reason="Sabotage"):
    global spectate_doctor_mode, player_kill_count
    if victim is None or not victim.alive:
        return False
    if try_doctor_self_revive_on_kill(victim):
        return False
    victim.alive = False
    victim.ghost = True
    victim.stun_timer = 0
    bodies.append(Body(victim.x, victim.y, victim))
    dead_players.append(victim)
    if killer is not None:
        killer.stats_kills += 1
        if killer is player:
            player_kill_count += 1
    if victim is player:
        spectate_doctor_mode = False
    set_event_notice(f"{get_player_name(victim)} died from {reason}.")
    return True


def update_bombs():
    """폭탄 타이머/전달/폭발 처리."""
    global bomb_kill_notice_text, bomb_kill_notice_timer, player_kill_count
    if bomb_kill_notice_timer > 0:
        bomb_kill_notice_timer -= 1

    to_remove = []
    for i, bomb in enumerate(active_bombs):
        holder = bomb["holder"]
        if holder is None:
            to_remove.append(i)
            continue

        # 폭탄 소지자가 죽었으면 폭탄 제거
        if not holder.alive:
            to_remove.append(i)
            continue

        # AI 보유 시: 가까운 생존자 누구에게나 즉시 전달 (플레이어·붐버 포함)
        if holder is not player:
            pass_targets = [p for p in [player] + AIs if p is not holder and p.alive]
            pass_targets.sort(key=lambda t: math.hypot(holder.x - t.x, holder.y - t.y))
            for t in pass_targets:
                if math.hypot(holder.x - t.x, holder.y - t.y) <= BOMB_PASS_RANGE:
                    transfer_bomb(bomb, t)
                    break

        bomb["timer"] -= 1
        if bomb["timer"] <= 0:
            holder_after = bomb["holder"]
            if holder_after is not None and holder_after.alive:
                owner = bomb.get("owner")
                if kill_by_bomb(holder_after) and owner is not None and owner.role == "bomber":
                    owner.stats_kills += 1
                    if owner is player:
                        player_kill_count += 1
                        bomb_kill_notice_text = f"Bomb killed {get_player_name(holder_after)}!"
                        bomb_kill_notice_timer = 60 * 4
            to_remove.append(i)

    if to_remove:
        for idx in sorted(to_remove, reverse=True):
            active_bombs.pop(idx)


def get_player_bomb_timer_frames():
    """플레이어가 폭탄 보유 중이면 가장 짧은 남은 타이머(frames) 반환."""
    timers = [b["timer"] for b in active_bombs if b.get("holder") is player]
    if not timers:
        return None
    return min(timers)


def get_bomb_held_by(holder):
    for b in active_bombs:
        if b.get("holder") is holder:
            return b
    return None


def _clamp(v, lo, hi):
    return max(lo, min(v, hi))


def get_room_cell(x, y):
    """좌표가 속한 방 셀(row, col) 계산."""
    col = int((x - MARGIN_X) // cell_w)
    row = int((y - MARGIN_Y) // cell_h)
    col = _clamp(col, 0, ROOM_COLS - 1)
    row = _clamp(row, 0, ROOM_ROWS - 1)
    return row, col


def get_room_index_at(x, y):
    row, col = get_room_cell(x, y)
    return row * ROOM_COLS + col


def get_room_rect(room_index):
    if 0 <= room_index < len(room_zones):
        return room_zones[room_index]["rect"]
    row = room_index // ROOM_COLS
    col = room_index % ROOM_COLS
    return pygame.Rect(MARGIN_X + col * cell_w, MARGIN_Y + row * cell_h, cell_w, cell_h)


def get_room_center(room_index):
    rect = get_room_rect(room_index)
    return rect.centerx, rect.centery


def get_room_label(room_index):
    if 0 <= room_index < len(room_zones):
        zone = room_zones[room_index]
        return f"Room {zone['num']} ({zone['name']})"
    return f"Room {room_index + 1}"


def set_event_notice(text, frames=60 * 4):
    global event_notice_text, event_notice_timer
    event_notice_text = text
    event_notice_timer = frames


def living_players():
    return [p for p in [player] + AIs if p.alive]


def living_crews():
    return [p for p in [player] + AIs if p.alive and p.role in CREW_ROLES]


def living_sabotage_fixers():
    return [p for p in [player] + AIs if p.alive and p.role in CREW_ROLES + NEUTRAL_SIDE_ROLES]


def any_living_near(x, y, radius, people=None):
    candidates = living_players() if people is None else people
    return any(math.hypot(p.x - x, p.y - y) <= radius for p in candidates)


def can_see_point(observer, x, y):
    return (
        math.hypot(observer.x - x, observer.y - y) <= get_effective_vision_radius()
        and is_path_clear(observer.x, observer.y, x, y)
    )


def scare_living_by_ghost_prank(gx, gy):
    for person in living_players():
        if person is player:
            continue
        if person.flee_timer > 20 or not can_see_point(person, gx, gy):
            continue
        person.flee_timer = random.randint(90, 150)
        person.flee_target = (gx, gy)


def trigger_ghost_prank(actor, announce=False):
    global ghost_prank_timer, ghost_prank_pos, ghost_prank_cooldown
    if actor is None or not actor.ghost:
        return False
    ghost_prank_timer = 60 * 3
    ghost_prank_pos = (actor.x, actor.y)
    ghost_prank_cooldown = 60 * 8
    scare_living_by_ghost_prank(actor.x, actor.y)
    if announce:
        set_event_notice("Ghost prank!")
    return True


def can_use_sabotage(actor):
    return actor is not None and actor.alive and actor.role == "imposter"


def get_sabotage_win_result(owner):
    if owner is not None and owner.role == "troll":
        return "T2 Win! (Troll Sabotage)", "Troll wins."
    if owner is not None and owner.role == "bomber":
        return "T3 Win! (Bomber Sabotage)", "Bomber wins."
    return "T4 Win! (Oxygen Sabotage)", "Imposters win."


def any_crew_can_repair_room(room_index, radius=85):
    if room_index is None:
        return False
    crews = living_sabotage_fixers()
    cx, cy = get_room_center(room_index)
    if any_living_near(cx, cy, radius, crews):
        return True
    return any(any_living_near(block.centerx, block.centery, radius, crews) for block in get_room_door_blocks(room_index))


def any_crew_can_repair_point(x, y, radius=85):
    return any_living_near(x, y, radius, living_sabotage_fixers())


def get_effective_vision_radius():
    if blackout_timer > 0:
        return int(vision_radius * 0.38)
    if security_camera_feed_active():
        rect = room_zones[security_camera_view_index]["rect"]
        span = math.hypot(rect.w, rect.h)
        return int(min(960, max(vision_radius, span * 0.52 + 80)))
    return vision_radius


def get_directional_door(ai, tx, ty):
    """현재 방->목표 방 방향을 고려해 통과할 문 좌표 선택."""
    cur_row, cur_col = get_room_cell(ai.x, ai.y)
    tgt_row, tgt_col = get_room_cell(tx, ty)

    if (cur_row, cur_col) == (tgt_row, tgt_col):
        return None

    d_col = tgt_col - cur_col
    d_row = tgt_row - cur_row

    # 축 우선순위: 더 멀리 떨어진 축 먼저 이동
    use_col_first = abs(d_col) >= abs(d_row) and d_col != 0
    if use_col_first:
        if d_col > 0:
            # 오른쪽 방으로 가는 문
            door_x = MARGIN_X + (cur_col + 1) * cell_w
            door_y = MARGIN_Y + cur_row * cell_h + cell_h // 2
        else:
            # 왼쪽 방으로 가는 문
            door_x = MARGIN_X + cur_col * cell_w
            door_y = MARGIN_Y + cur_row * cell_h + cell_h // 2
        return (door_x, door_y)

    # 위/아래 방으로 가는 문
    if d_row > 0:
        door_x = MARGIN_X + cur_col * cell_w + cell_w // 2
        door_y = MARGIN_Y + (cur_row + 1) * cell_h
    else:
        door_x = MARGIN_X + cur_col * cell_w + cell_w // 2
        door_y = MARGIN_Y + cur_row * cell_h
    return (door_x, door_y)


def move_ai_with_door_priority(ai, tx, ty, speed):
    """목표로 이동하되 막히면 문을 최우선으로 찾아 우회."""
    # 문 목표가 있으면 우선 문으로 이동
    if ai.nav_door_target is not None:
        dx_d = ai.nav_door_target[0] - ai.x
        dy_d = ai.nav_door_target[1] - ai.y
        if math.hypot(dx_d, dy_d) < 45 or is_path_clear(ai.x, ai.y, tx, ty):
            ai.nav_door_target = None

    waypoint = ai.nav_door_target if ai.nav_door_target is not None else (tx, ty)
    dx = waypoint[0] - ai.x
    dy = waypoint[1] - ai.y
    dist = math.hypot(dx, dy) or 1
    mx, my = dx / dist * speed, dy / dist * speed

    # 다음 스텝이 벽 충돌이면 진행 방향 문을 새로 잡는다
    nr = pygame.Rect(ai.x + mx, ai.y + my, ai.width, ai.height)
    if check_collision(nr, ai):
        best_door = get_directional_door(ai, tx, ty)
        if best_door is not None:
            ai.nav_door_target = best_door
            dx = best_door[0] - ai.x
            dy = best_door[1] - ai.y
            dist = math.hypot(dx, dy) or 1
            mx, my = dx / dist * speed, dy / dist * speed

    apply_move_with_escape_priority(ai, mx, my, speed)

def is_path_clear(x1, y1, x2, y2):
    """두 점 사이의 경로가 벽으로 가로막혀 있는지 확인"""
    steps = 20
    for i in range(steps):
        t = i / steps
        check_x = x1 + (x2 - x1) * t
        check_y = y1 + (y2 - y1) * t
        check_rect = pygame.Rect(check_x-2, check_y-2, 4, 4)  # 더 정밀한 확인
        if check_collision(check_rect):
            return False
    return True

def try_doctor_self_revive_on_kill(victim):
    """Doctor now revives with F after becoming a ghost, so kills should still create a body."""
    return False


def has_pending_self_revive(actor):
    """Keep the round alive while a dead Doctor/Undertaker can still revive themself."""
    if not actor.ghost:
        return False
    if actor.role == "doctor" and not actor.revive_used:
        return any(b.dead_player is actor for b in bodies)
    if actor.role == "undertaker" and not actor.undertaker_revive_used:
        return any(b.dead_player is actor for b in bodies)
    return False


def revive_own_body(actor):
    """Doctor/Undertaker self revive from their own corpse."""
    global dead_players, spectate_doctor_mode
    if actor.role == "doctor":
        if actor.revive_used:
            return False
        use_revive = "doctor"
    elif actor.role == "undertaker":
        if actor.undertaker_revive_used:
            return False
        use_revive = "undertaker"
    else:
        return False

    for i, b in enumerate(bodies):
        if b.dead_player is not actor:
            continue
        actor.alive = True
        actor.ghost = False
        actor.stun_timer = 0
        actor.x, actor.y = b.x, b.y
        if actor in dead_players:
            dead_players.remove(actor)
        bodies.pop(i)
        if use_revive == "doctor":
            actor.revive_used = True
        else:
            actor.undertaker_revive_used = True
        if actor is player:
            actor.stats_revives += 1
            spectate_doctor_mode = False
        return True
    return False


def alert_crew_witnesses_attacker(attacker, victim):
    """공격/킬 목격한 크루·의사·경비: 공격자 의심 + 도망 타이머(위치는 매 프레임 갱신됨)"""
    for obs in [player] + AIs:
        if obs is attacker or obs is victim or not obs.alive or obs.role not in CREW_ROLES:
            continue
        if not can_see_player(obs, victim) or not is_path_clear(obs.x, obs.y, victim.x, victim.y):
            continue
        if not can_see_player(obs, attacker) or not is_path_clear(obs.x, obs.y, attacker.x, attacker.y):
            continue
        obs.suspect_player = attacker
        obs.flee_timer = max(obs.flee_timer, random.randint(130, 200))
        obs.flee_target = (attacker.x, attacker.y)

def compute_flee_step(ai, threat_x, threat_y, speed):
    """위협 반대 방향 + 좌우 지그재그. 합력을 speed로 정규화해 이동 속도 크기 유지."""
    dx = ai.x - threat_x
    dy = ai.y - threat_y
    dist = math.hypot(dx, dy)
    if dist < 12:  # 겹침·초근접: 임의 탈출 방향
        ang = random.random() * 2 * math.pi
        ax, ay = math.cos(ang), math.sin(ang)
    else:
        ax, ay = dx / dist, dy / dist
    px, py = -ay, ax
    ai.flee_weave_phase += 1
    weave = math.sin(ai.flee_weave_phase * 0.11) * 0.72
    mx = ax + px * weave
    my = ay + py * weave
    ln = math.hypot(mx, my) or 1
    return mx / ln * speed, my / ln * speed

def ghost_wander_step(ent, speed=None):
    """유령 맵 배회(벽은 살아 있을 때와 동일하게 충돌 처리)."""
    spd = MOVE_SPEED if speed is None else speed
    if ent.wander_target is None or math.hypot(ent.x - ent.wander_target[0], ent.y - ent.wander_target[1]) < 90:
        ent.wander_target = (random.randint(100, MAP_WIDTH - 100), random.randint(100, MAP_HEIGHT - 100))
    tx, ty = ent.wander_target[0], ent.wander_target[1]
    dx, dy = tx - ent.x, ty - ent.y
    dist = math.hypot(dx, dy) or 1
    mx, my = dx / dist * spd, dy / dist * spd
    apply_move_with_escape_priority(ent, mx, my, spd)


def do_non_role_activity(ai, speed):
    """역할 목표/미션을 못 할 때 하는 일반 행동."""
    if ai.natural_action_timer <= 0:
        ai.natural_action = random.choice(("wander", "buddy", "idle"))
        ai.natural_action_timer = random.randint(60, 180)
        if ai.natural_action == "wander":
            ai.wander_target = (random.randint(100, MAP_WIDTH - 100), random.randint(100, MAP_HEIGHT - 100))

    ai.natural_action_timer -= 1
    if ai.natural_action == "idle":
        return

    if ai.natural_action == "buddy":
        candidates = [p for p in [player] + AIs if p is not ai and p.alive and p.role != "imposter"]
        if candidates:
            buddy = min(candidates, key=lambda p: math.hypot(ai.x - p.x, ai.y - p.y))
            move_ai_with_door_priority(ai, buddy.x, buddy.y, speed)
            return

    if ai.wander_target is None or math.hypot(ai.x - ai.wander_target[0], ai.y - ai.wander_target[1]) < 80:
        ai.wander_target = (random.randint(100, MAP_WIDTH - 100), random.randint(100, MAP_HEIGHT - 100))
    move_ai_with_door_priority(ai, ai.wander_target[0], ai.wander_target[1], speed)


def update_crew_gather_event():
    """가끔 크루 4~5명이 한곳에 모여 잠깐 노는 이벤트."""
    global crew_gather_timer, crew_gather_cooldown, crew_gather_target, crew_gather_members
    global crew_gather_notice_text, crew_gather_notice_timer

    if crew_gather_notice_timer > 0:
        crew_gather_notice_timer -= 1

    if crew_gather_timer > 0:
        crew_gather_timer -= 1
        if crew_gather_timer <= 0:
            for member in crew_gather_members:
                member.spin_angle = 0
                member.dance_offset_x = 0
                member.dance_offset_y = 0
            crew_gather_target = None
            crew_gather_members = []
            crew_gather_cooldown = random.randint(60 * 6, 60 * 10)
        return

    if crew_gather_cooldown > 0:
        crew_gather_cooldown -= 1
        return

    candidates = [a for a in AIs if a.alive and a.role in CREW_ROLES and a.stun_timer <= 0]
    if len(candidates) < 4:
        crew_gather_cooldown = 60 * 8
        return

    random.shuffle(candidates)
    count = min(len(candidates), random.randint(4, 5))
    crew_gather_members = candidates[:count]
    anchor = random.choice(crew_gather_members)
    crew_gather_target = find_safe_position_near(anchor.x + random.randint(-120, 120), anchor.y + random.randint(-120, 120), 220)
    crew_gather_timer = random.randint(60 * 7, 60 * 12)
    row, col = get_room_cell(crew_gather_target[0], crew_gather_target[1])
    room_num = row * ROOM_COLS + col + 1
    crew_gather_notice_text = f"Crew dance party in Room {room_num}!"
    crew_gather_notice_timer = 60 * 4


def count_active_random_events():
    return sum(
        1
        for active in (
            blackout_timer > 0,
            locked_room_timer > 0,
            cleanup_timer > 0,
            vent_noise_timer > 0,
            security_camera_timer > 0,
            oxygen_timer > 0,
            suspicion_event_timer > 0,
            dance_challenge_timer > 0,
        )
        if active
    )


def is_sabotage_active():
    return (
        oxygen_timer > 0 and oxygen_sabotage_owner is not None
    ) or (
        blackout_timer > 0 and blackout_sabotage_owner is not None
    ) or (
        locked_room_timer > 0 and locked_room_sabotage_owner is not None
    )


def start_random_event(kind=None, sabotage_owner=None, target_room=None):
    global blackout_timer, blackout_room, locked_room_timer, locked_room
    global cleanup_timer, cleanup_room, cleanup_progress, vent_noise_timer, vent_noise_vent
    global security_camera_timer, security_camera_room, security_camera_view_index, oxygen_timer, oxygen_rooms, oxygen_fixed, oxygen_points
    global suspicion_event_timer, dance_challenge_timer, dance_challenge_room
    global blackout_sabotage_owner, locked_room_sabotage_owner, oxygen_sabotage_owner

    kind_pool = (
        "blackout",
        "locked",
        "cleanup",
        "vent_noise",
        "security",
        "oxygen",
        "suspicion",
        "dance",
    )
    # vent_noise 가중치 높음 → 벤트 소리 이벤트가 더 자주 뜸
    kind_weights = (1, 1, 1, 5, 1, 1, 1, 1)
    kind = kind or random.choices(kind_pool, weights=kind_weights, k=1)[0]
    room_index = target_room if target_room is not None else random.randrange(len(room_zones))
    is_sabotage = sabotage_owner is not None

    if kind == "blackout" and blackout_timer <= 0:
        blackout_room = room_index
        blackout_timer = 60 * (14 if is_sabotage else 22)
        blackout_sabotage_owner = sabotage_owner
        set_event_notice(f"{'Sabotage: ' if is_sabotage else ''}Blackout! Fix power in {get_room_label(room_index)}.")
        return True
    elif kind == "locked" and locked_room_timer <= 0:
        locked_room = room_index
        locked_room_timer = 60 * (10 if is_sabotage else 12)
        locked_room_sabotage_owner = sabotage_owner
        set_event_notice(f"{'Sabotage: ' if is_sabotage else ''}Doors locked around {get_room_label(room_index)}.")
        return True
    elif kind == "cleanup" and cleanup_timer <= 0:
        cleanup_room = room_index
        cleanup_progress = 0
        cleanup_timer = 60 * 28
        set_event_notice(f"Cleanup needed in {get_room_label(room_index)}.")
        return True
    elif kind == "vent_noise" and vent_noise_timer <= 0 and vents:
        vent_noise_vent = random.choice(vents)
        vent_noise_timer = 60 * 10
        set_event_notice("Vent noise detected!")
        return True
    elif kind == "security" and security_camera_timer <= 0:
        security_camera_room = next((i for i, z in enumerate(room_zones) if z["name"] == SECURITY_DESK_ROOM_NAME), room_index)
        security_camera_timer = 60 * 14
        security_camera_view_index = 0
        set_event_notice(f"Security alert! Open monitors in {SECURITY_DESK_ROOM_NAME} (B), switch rooms with [ ].")
        return True
    elif kind == "oxygen" and oxygen_timer <= 0:
        oxygen_rooms = []
        oxygen_points = [find_safe_position() for _ in range(10)]
        oxygen_fixed = [False for _ in oxygen_points]
        oxygen_timer = 60 * 40
        oxygen_sabotage_owner = sabotage_owner
        set_event_notice(f"{'Sabotage: ' if is_sabotage else ''}Oxygen alert! Fix 10 panels.")
        return True
    elif kind == "suspicion" and suspicion_event_timer <= 0:
        suspicion_event_timer = 60 * 20
        set_event_notice("Suspicion is rising.")
        return True
    elif kind == "dance" and dance_challenge_timer <= 0:
        dance_challenge_room = room_index
        dance_challenge_timer = 60 * 18
        set_event_notice(f"Dance challenge in {get_room_label(room_index)}!")
        return True
    return False


def update_random_events():
    global event_cooldown, event_notice_timer, blackout_timer, locked_room_timer
    global cleanup_timer, cleanup_progress, vent_noise_timer, security_camera_timer
    global oxygen_timer, oxygen_fixed, suspicion_event_timer, dance_challenge_timer, dance_boost_timer
    global ghost_prank_timer, ghost_prank_cooldown, sabotage_cooldown
    global blackout_sabotage_owner, locked_room_sabotage_owner, oxygen_sabotage_owner
    global winner, game_over

    if event_notice_timer > 0:
        event_notice_timer -= 1
    if dance_boost_timer > 0:
        dance_boost_timer -= 1
    if ghost_prank_cooldown > 0:
        ghost_prank_cooldown -= 1
    if ghost_prank_timer > 0:
        ghost_prank_timer -= 1
        if ghost_prank_pos is not None:
            gx, gy = ghost_prank_pos
            scare_living_by_ghost_prank(gx, gy)
    elif ghost_prank_cooldown <= 0:
        pranksters = [
            ai for ai in AIs
            if ai.ghost and any(can_see_point(target, ai.x, ai.y) for target in living_players())
        ]
        if pranksters and random.random() < 0.006:
            trigger_ghost_prank(random.choice(pranksters))
    if sabotage_cooldown > 0:
        sabotage_cooldown -= 1

    if blackout_timer > 0:
        blackout_timer -= 1
        fx, fy = get_room_center(blackout_room)
        if any_living_near(fx, fy, 70, living_sabotage_fixers()):
            blackout_timer = 0
            blackout_sabotage_owner = None
            set_event_notice("Power restored.")
        elif blackout_timer <= 0 and blackout_sabotage_owner is not None:
            candidates = living_crews()
            if candidates:
                victim = min(candidates, key=lambda p: math.hypot(p.x - fx, p.y - fy))
                kill_by_sabotage(victim, blackout_sabotage_owner, "blackout")
            blackout_sabotage_owner = None

    if locked_room_timer > 0:
        locked_room_timer -= 1
        if any_crew_can_repair_room(locked_room, 70):
            locked_room_timer = 0
            locked_room_sabotage_owner = None
            set_event_notice("Doors unlocked.")
        elif locked_room_timer <= 0 and locked_room_sabotage_owner is not None:
            trapped = [p for p in living_crews() if get_room_index_at(p.x, p.y) == locked_room]
            if trapped:
                kill_by_sabotage(random.choice(trapped), locked_room_sabotage_owner, "locked doors")
            locked_room_sabotage_owner = None

    if cleanup_timer > 0:
        cleanup_timer -= 1
        cx, cy = get_room_center(cleanup_room)
        if any_living_near(cx, cy, 85, living_crews()):
            cleanup_progress += 1
            if cleanup_progress >= 60 * 3:
                cleanup_timer = 0
                set_event_notice("Cleanup complete.")
        if cleanup_timer <= 0:
            cleanup_progress = 0

    if vent_noise_timer > 0:
        vent_noise_timer -= 1

    if security_camera_timer > 0:
        security_camera_timer -= 1

    if oxygen_timer > 0:
        oxygen_timer -= 1
        for i, point in enumerate(oxygen_points):
            if oxygen_fixed[i]:
                continue
            if any_crew_can_repair_point(point[0], point[1], 70):
                oxygen_fixed[i] = True
                set_event_notice(f"Oxygen panel {i + 1} fixed.")
        if oxygen_points and all(oxygen_fixed):
            oxygen_timer = 0
            oxygen_sabotage_owner = None
            set_event_notice("Oxygen restored.")
        elif oxygen_timer <= 0:
            winner, notice = get_sabotage_win_result(oxygen_sabotage_owner)
            game_over = True
            set_event_notice(f"Oxygen failed. {notice}")
            oxygen_sabotage_owner = None

    if suspicion_event_timer > 0:
        suspicion_event_timer -= 1

    if dance_challenge_timer > 0:
        dance_challenge_timer -= 1

    if event_cooldown > 0:
        event_cooldown -= 1
    elif not is_sabotage_active() and count_active_random_events() < 2:
        start_random_event()
        event_cooldown = random.randint(60 * 8, 60 * 16)


def get_priority_event_target_for_ai(ai):
    if ai.role not in CREW_ROLES + NEUTRAL_SIDE_ROLES or not ai.alive:
        return None
    if oxygen_timer > 0:
        targets = [point for i, point in enumerate(oxygen_points) if not oxygen_fixed[i]]
        if targets:
            return min(targets, key=lambda point: math.hypot(ai.x - point[0], ai.y - point[1]))
    if blackout_timer > 0 and blackout_room is not None:
        return get_room_center(blackout_room)
    if locked_room_timer > 0 and locked_room is not None:
        return get_room_center(locked_room)
    if is_sabotage_active():
        return None
    if cleanup_timer > 0 and cleanup_room is not None:
        return get_room_center(cleanup_room)
    if vent_noise_timer > 0 and vent_noise_vent is not None and random.random() < 0.62:
        return vent_noise_vent.x, vent_noise_vent.y
    return None


def ai_move(ai):
    global imposter_kill_cooldown, player_kill_cooldown, dead_players, troll_stun_cooldown
    speed = MOVE_SPEED
    if not (crew_gather_timer > 0 and ai in crew_gather_members):
        ai.spin_angle = 0
        ai.dance_offset_x = 0
        ai.dance_offset_y = 0
    
    if ai.venting:
        ai.vent_time -= 1
        if ai.vent_time <= 0:
            ai.venting = False
        if ai.alive:
            return
    
    if ai.ghost and ai.role == "doctor" and not ai.revive_used:
        self_body = next((b for b in bodies if b.dead_player is ai), None)
        if self_body is not None:
            if math.hypot(ai.x - self_body.x, ai.y - self_body.y) < 50:
                revive_body_by(ai)
            else:
                move_ai_with_door_priority(ai, self_body.x, self_body.y, speed)
            return

    if ai.ghost and ai.role == "undertaker" and not ai.undertaker_revive_used:
        self_body = next((b for b in bodies if b.dead_player is ai), None)
        if self_body is not None:
            if math.hypot(ai.x - self_body.x, ai.y - self_body.y) < 50:
                revive_body_by_undertaker(ai)
            else:
                move_ai_with_door_priority(ai, self_body.x, self_body.y, speed)
            return

    if ai.ghost:
        do_non_role_activity(ai, MOVE_SPEED)
        return
    
    if not ai.alive:
        return
    if ai.fake_task_timer > 0:
        ai.fake_task_timer -= 1
        return
    
    # 스턴 중이면 행동 불가
    if ai.stun_timer > 0:
        ai.stun_timer -= 1
        return
    
    # 벽 탈출은 역할 행동(미션/부활/추적)보다 항상 우선
    if ai.escape_timer > 0 and ai.escape_dir != (0, 0):
        apply_move_with_escape_priority(ai, ai.escape_dir[0], ai.escape_dir[1], speed)
        return

    # 고스트 프랭크 등 공포 반응은 임포스터/트롤/폭탄광 포함 모든 AI에게 적용
    if ai.flee_timer > 0:
        ai.flee_timer -= 1
        if ai.suspect_player and ai.suspect_player.alive:
            ai.flee_target = (ai.suspect_player.x, ai.suspect_player.y)
        if ai.flee_target:
            tx, ty = ai.flee_target[0], ai.flee_target[1]
            move_x, move_y = compute_flee_step(ai, tx, ty, speed)
            move_ai_with_door_priority(ai, ai.x + move_x, ai.y + move_y, speed)
            return

    if ai.role in CREW_ROLES + NEUTRAL_SIDE_ROLES and is_sabotage_active():
        event_target = get_priority_event_target_for_ai(ai)
        if event_target is not None:
            move_ai_with_door_priority(ai, event_target[0], event_target[1], speed)
            return

    # 모든 AI 공통: 폭탄 소지 중이면 가장 가까운 대상에게 급히 접근(전달 우선)
    held_bomb_any = get_bomb_held_by(ai)
    if held_bomb_any is not None:
        candidates = [p for p in [player] + AIs if p is not ai and p.alive]
        if candidates:
            target = min(candidates, key=lambda p: math.hypot(ai.x - p.x, ai.y - p.y))
            move_ai_with_door_priority(ai, target.x, target.y, speed)
            return

    # 폭탄광 AI: 미션/부활/신고 없이 폭탄 설치만 수행
    if ai.role == "bomber":
        if ai.bombs_remaining <= 0 and get_bomb_held_by(ai) is None:
            do_non_role_activity(ai, speed)
            return

        candidates = [p for p in [player] + AIs if p is not ai and p.alive]
        bomb_free_candidates = [p for p in candidates if get_bomb_held_by(p) is None]
        preferred_candidates = [p for p in bomb_free_candidates if p is not ai.last_bomb_target]
        if not preferred_candidates:
            preferred_candidates = bomb_free_candidates
        candidates.sort(key=lambda p: math.hypot(ai.x - p.x, ai.y - p.y))
        preferred_candidates.sort(key=lambda p: math.hypot(ai.x - p.x, ai.y - p.y))

        # 붐버가 현재 폭탄 소지 중이면 우선 다른 사람에게 전달
        held_bomb = get_bomb_held_by(ai)
        if held_bomb is not None:
            pass_targets = preferred_candidates if preferred_candidates else candidates
            for target in pass_targets:
                if math.hypot(ai.x - target.x, ai.y - target.y) <= BOMB_PASS_RANGE:
                    transfer_bomb(held_bomb, target)
                    ai.last_bomb_target = target
                    next_targets = [p for p in preferred_candidates if p is not target]
                    if next_targets:
                        move_ai_with_door_priority(ai, next_targets[0].x, next_targets[0].y, speed)
                    else:
                        do_non_role_activity(ai, speed)
                    return

        # 폭탄 없는 사람이 사거리 안에 있으면 무조건 즉시 설치
        if ai.bombs_remaining > 0:
            for target in preferred_candidates:
                d = math.hypot(ai.x - target.x, ai.y - target.y)
                if d < 90:
                    if attach_bomb(ai, target):
                        ai.last_bomb_target = target
                        next_targets = [p for p in preferred_candidates if p is not target]
                        if next_targets:
                            move_ai_with_door_priority(ai, next_targets[0].x, next_targets[0].y, speed)
                        else:
                            do_non_role_activity(ai, speed)
                        return

        # 이미 폭탄을 받은 사람은 피하고, 폭탄 없는 다른 생존자에게 접근
        if preferred_candidates:
            target = preferred_candidates[0]
            move_ai_with_door_priority(ai, target.x, target.y, speed)
        elif candidates:
            do_non_role_activity(ai, speed)
        return

    # 기계공 AI: 크루 팀이지만 환풍구 사용 가능
    if ai.role == "engineer" and not ai.venting and ai.alive:
        for vent in vents:
            if math.hypot(ai.x - vent.x, ai.y - vent.y) < 70:
                if random.random() < 0.08:
                    ai.venting = True
                    ai.vent_time = random.randint(18, 34)
                    dest = random.choice(vent.available_vents)
                    ai.x, ai.y = find_safe_position_near(dest.x, dest.y)
                break

    if ai.role=="troll":
        # ===== 트롤 AI: 크루만 공격 (임포 공격 불가), 공격 시 30초 스턴 =====
        troll_range = 55  # 공격 범위
        all_targets = [p for p in [player]+AIs if p.alive and p.role in CREW_ROLES and p.stun_timer <= 0]
        if troll_stun_cooldown <= 0 and all_targets:
            for target in all_targets:
                dist = math.hypot(ai.x-target.x, ai.y-target.y)
                if dist < troll_range and is_path_clear(ai.x, ai.y, target.x, target.y):
                    target.stun_timer = STUN_DURATION
                    troll_stun_cooldown = 90  # 1.5초 쿨다운 (게임 루프에서 감소)
                    alert_crew_witnesses_attacker(ai, target)
                    break
        # 이동: 가까운 타겟 추적 or 배회
        target_x, target_y = None, None
        for t in all_targets:
            if t.stun_timer <= 0:
                d = math.hypot(ai.x-t.x, ai.y-t.y)
                if d < vision_radius * 2:
                    target_x, target_y = t.x, t.y
                    break
        if target_x is None:
            if ai.wander_target is None or math.hypot(ai.x-ai.wander_target[0], ai.y-ai.wander_target[1]) < 80:
                ai.wander_target = (random.randint(100, MAP_WIDTH-100), random.randint(100, MAP_HEIGHT-100))
            target_x, target_y = ai.wander_target[0], ai.wander_target[1]
        dx = target_x - ai.x
        dy = target_y - ai.y
        dist = math.hypot(dx, dy) or 1
        move_x, move_y = dx/dist*speed, dy/dist*speed
        move_ai_with_door_priority(ai, ai.x + move_x, ai.y + move_y, speed)
        return

    if ai.role == "mad_scientist":
        prey = [p for p in [player] + AIs if p is not ai and p.alive]
        if ai.gas_kill_cooldown <= 0 and prey:
            closest = min(prey, key=lambda p: math.hypot(ai.x - p.x, ai.y - p.y))
            tx = closest.x + closest.width / 2
            ty = closest.y + closest.height / 2
            if deploy_poison_gas_cloud(ai, tx, ty):
                ai.gas_kill_cooldown = MAD_SCIENTIST_GAS_COOLDOWN_FRAMES
                return
            move_ai_with_door_priority(ai, closest.x, closest.y, speed)
            return
        if prey:
            closest = min(prey, key=lambda p: math.hypot(ai.x - p.x, ai.y - p.y))
            move_ai_with_door_priority(ai, closest.x, closest.y, speed)
            return
        do_non_role_activity(ai, speed)
        return

    if ai.role=="imposter":
        # ===== 똑똑한 임포스터 AI =====
        alive_crews = [p for p in [player]+AIs if p.alive and p.role in CREW_ROLES]
        
        def is_crew_isolated(crew):
            """다른 크루가 시야에 있으면 고립 아님"""
            for other in alive_crews:
                if other is crew: continue
                if math.hypot(crew.x-other.x, crew.y-other.y) < vision_radius:
                    if is_path_clear(crew.x, crew.y, other.x, other.y):
                        return False
            return True
        
        def can_kill_without_witness(me, target):
            """다른 크루가 킬 장면을 볼 수 없을 때만 True"""
            for witness in alive_crews:
                if witness is target: continue
                if math.hypot(witness.x-target.x, witness.y-target.y) < vision_radius:
                    if is_path_clear(witness.x, witness.y, target.x, target.y):
                        return False  # 목격자 있음
            return True
        
        def get_vent_near(pos, max_dist=300):
            """위치 근처 환풍구 반환"""
            for v in vents:
                if math.hypot(pos[0]-v.x, pos[1]-v.y) < max_dist:
                    return v
            return None
        
        # 1) 킬 시도 - 스턴된 크루 우선, 나중엔 꼭 트롤도 제거
        alive_trolls = [p for p in [player]+AIs if p.alive and p.role=="troll"]
        alive_bombers = [p for p in [player]+AIs if p.alive and p.role=="bomber"]
        alive_mad_scientists = [p for p in [player]+AIs if p.alive and p.role=="mad_scientist"]
        kill_targets = alive_crews + alive_trolls + alive_bombers + alive_mad_scientists
        if imposter_kill_cooldown <= 0 and kill_targets:
            best_target = None
            # 우선순위: 스턴된 크루 > 고립된 크루 > 트롤 (크루 적을 때 트롤 반드시 제거)
            stunned_crews = [t for t in alive_crews if t.stun_timer > 0]
            for target in stunned_crews:  # 1순위: 트롤이 스턴시킨 크루
                dist = math.hypot(ai.x-target.x, ai.y-target.y)
                if dist < imposter_range and is_path_clear(ai.x, ai.y, target.x, target.y):
                    best_target = target
                    break
            if not best_target:
                for target in alive_crews:  # 2순위: 고립된 크루
                    if target.stun_timer > 0: continue
                    dist = math.hypot(ai.x-target.x, ai.y-target.y)
                    if dist < imposter_range and is_path_clear(ai.x, ai.y, target.x, target.y):
                        if is_crew_isolated(target) and can_kill_without_witness(ai, target):
                            best_target = target
                            break
            if not best_target and alive_trolls:  # 3순위: 트롤 (나중엔 꼭 죽이기)
                for target in alive_trolls:
                    dist = math.hypot(ai.x-target.x, ai.y-target.y)
                    if dist < imposter_range and is_path_clear(ai.x, ai.y, target.x, target.y):
                        best_target = target
                        break
            if not best_target and alive_bombers:  # 4순위: 붐버
                for target in alive_bombers:
                    dist = math.hypot(ai.x-target.x, ai.y-target.y)
                    if dist < imposter_range and is_path_clear(ai.x, ai.y, target.x, target.y):
                        best_target = target
                        break
            if not best_target and alive_mad_scientists:  # 5순위: 미친 과학자
                for target in alive_mad_scientists:
                    dist = math.hypot(ai.x-target.x, ai.y-target.y)
                    if dist < imposter_range and is_path_clear(ai.x, ai.y, target.x, target.y):
                        best_target = target
                        break
            if best_target:
                if try_doctor_self_revive_on_kill(best_target):
                    imposter_kill_cooldown = 60
                    ai.hunt_target = None
                    return
                spawn_imposter_slice_fx(best_target)
                best_target.alive = False
                best_target.ghost = True
                best_target.stun_timer = 0
                if best_target is player:
                    print("Player died and became ghost")
                bodies.append(Body(best_target.x, best_target.y, best_target))
                dead_players.append(best_target)
                alert_crew_witnesses_attacker(ai, best_target)
                imposter_kill_cooldown = 60
                if best_target.role=="guard":
                    ai.stun_timer = STUN_DURATION  # 경비 킬 시 임포 30초 스턴
                ai.hunt_target = None
                # 킬 직후 근처에 환풍구 있으면 탈출 (똑똑한 도주)
                vent_near = get_vent_near((ai.x, ai.y), 120)
                if vent_near and random.random() < 0.6:
                    ai.venting = True
                    ai.vent_time = random.randint(25, 45)
                    dest = random.choice(vent_near.available_vents)
                    ai.x, ai.y = find_safe_position_near(dest.x, dest.y)
                    ai.wander_target = None
                    ai.hunt_target = None
                return
        
        # 2) 추적 대상: 고립된 크루, 또는 크루 적을 땐 트롤 (나중엔 꼭 트롤 죽이기)
        ai.hunt_target = None
        best_prey = None
        best_prey_score = -9999
        must_kill_troll = len(alive_crews) <= 2 and alive_trolls  # 크루 2명 이하면 트롤 추적
        for crew in alive_crews:
            if not is_crew_isolated(crew):
                continue
            dist = math.hypot(ai.x-crew.x, ai.y-crew.y)
            if dist > vision_radius * 2.5:
                continue
            score = -dist
            vent_near_prey = get_vent_near((crew.x, crew.y), 400)
            if vent_near_prey and get_vent_near((ai.x, ai.y), 150):
                score += 200
            if score > best_prey_score:
                best_prey_score = score
                best_prey = crew
        if must_kill_troll and alive_trolls:  # 트롤 죽이기 우선
            for troll in alive_trolls:
                dist = math.hypot(ai.x-troll.x, ai.y-troll.y)
                if dist < vision_radius * 2.5:
                    score = -dist + 500
                    if score > best_prey_score:
                        best_prey_score = score
                        best_prey = troll
        if best_prey:
            ai.hunt_target = best_prey
        
        # 3) 환풍구 활용 - 고립 타겟 근처로 이동 or 랜덤 재배치
        if ai.hunt_target:
            vent_near_me = get_vent_near((ai.x, ai.y), 100)
            vent_near_target = get_vent_near((ai.hunt_target.x, ai.hunt_target.y), 350)
            if vent_near_me and vent_near_target and vent_near_me is not vent_near_target:
                # 환풍구로 타겟 근처 점프 (타겟과 직선거리가 멀 때)
                direct_dist = math.hypot(ai.x-ai.hunt_target.x, ai.y-ai.hunt_target.y)
                if direct_dist > 400 and random.random() < 0.12:
                    dest = vent_near_target
                    ai.venting = True
                    ai.vent_time = random.randint(20, 40)
                    ai.x, ai.y = find_safe_position_near(dest.x, dest.y)
                    ai.wander_target = None
                    return
        else:
            for vent in vents:
                if math.hypot(ai.x-vent.x, ai.y-vent.y) < 80:
                    if random.random() < 0.06:  # 크루 찾으러 재배치
                        ai.venting = True
                        ai.vent_time = random.randint(25, 50)
                        dest = random.choice(vent.available_vents)
                        ai.x, ai.y = find_safe_position_near(dest.x, dest.y)
                        ai.wander_target = None
                    break
        
        # 4) 이동 - 추적 or 배회
        target_x, target_y = None, None
        if ai.hunt_target:
            dist_to_prey = math.hypot(ai.x-ai.hunt_target.x, ai.y-ai.hunt_target.y)
            if dist_to_prey > imposter_range + 80:  # 킬범위 밖이면 접근
                target_x, target_y = ai.hunt_target.x, ai.hunt_target.y
            elif dist_to_prey > imposter_range:
                target_x, target_y = ai.hunt_target.x, ai.hunt_target.y  # 마지막 접근
        if target_x is None:
            if ai.wander_target is None or math.hypot(ai.x-ai.wander_target[0], ai.y-ai.wander_target[1]) < 100:
                # 크루들이 모여있는 구역 근처로 배회 (기회 포착)
                if alive_crews:
                    center = (sum(p.x for p in alive_crews)/len(alive_crews),
                              sum(p.y for p in alive_crews)/len(alive_crews))
                    jitter = (random.randint(-400, 400), random.randint(-400, 400))
                    ai.wander_target = (int(center[0]+jitter[0]), int(center[1]+jitter[1]))
                else:
                    ai.wander_target = (random.randint(100, MAP_WIDTH-100), random.randint(100, MAP_HEIGHT-100))
            target_x, target_y = ai.wander_target[0], ai.wander_target[1]
        
        dx = target_x - ai.x
        dy = target_y - ai.y
        if dx == 0 and dy == 0:
            return
        move_ai_with_door_priority(ai, target_x, target_y, speed)
    else:
        # ===== 똑똑한 크루 AI =====
        alive_crews = [p for p in [player]+AIs if p.alive and p.role in CREW_ROLES and p is not ai]
        alive_imposters = [p for p in [player]+AIs if p.alive and p.role=="imposter"]
        
        def nearest_crew(exclude_suspect=True):
            """가장 가까운 다른 크루 (의심 대상 제외 가능)"""
            candidates = [c for c in alive_crews if not exclude_suspect or c is not ai.suspect_player]
            if not candidates:
                return None
            return min(candidates, key=lambda c: math.hypot(ai.x-c.x, ai.y-c.y))
        
        def am_i_isolated():
            """다른 크루가 시야에 없으면 고립"""
            for c in alive_crews:
                if math.hypot(ai.x-c.x, ai.y-c.y) < vision_radius and is_path_clear(ai.x, ai.y, c.x, c.y):
                    return False
            return True
        
        def do_move(tx, ty):
            move_ai_with_door_priority(ai, tx, ty, speed)

        event_target = get_priority_event_target_for_ai(ai)
        if event_target is not None and ai.flee_timer <= 0:
            do_move(event_target[0], event_target[1])
            return
        
        # 1) 시체 발견 - 의사/장의사 부활 시도 (신고 기능 제거)
        # 시체가 앞에 있어도 기본적으로 멈추지 않고 계속 이동
        for b in bodies:
            if math.hypot(ai.x-b.x, ai.y-b.y) < 50:
                if ai.role=="doctor" and not ai.revive_used and b.dead_player:
                    if revive_body_by(ai):
                        return
                if ai.role=="undertaker" and not ai.undertaker_revive_used and b.dead_player:
                    if revive_body_by_undertaker(ai):
                        return
                break
        
        # 1a) 닥터/장의사: 부활권이 남았으면 미션보다 시체 접근 우선
        if ai.role == "doctor" and not ai.revive_used and bodies and ai.flee_timer <= 0:
            nearest_b = min(bodies, key=lambda b: math.hypot(ai.x - b.x, ai.y - b.y))
            if math.hypot(ai.x - nearest_b.x, ai.y - nearest_b.y) >= 50:
                do_move(nearest_b.x, nearest_b.y)
                return
        if ai.role == "undertaker" and not ai.undertaker_revive_used and bodies and ai.flee_timer <= 0:
            nearest_b = min(bodies, key=lambda b: math.hypot(ai.x - b.x, ai.y - b.y))
            if math.hypot(ai.x - nearest_b.x, ai.y - nearest_b.y) >= 50:
                do_move(nearest_b.x, nearest_b.y)
                return
        
        # 1b) 크루/가드·살아 있는 닥터(부활 가능 시만): 스턴 해제
        doctor_can_heal = ai.role != "doctor" or not ai.revive_used
        if ai.role in CREW_ROLES and ai.stun_timer <= 0 and doctor_can_heal:
            for p in [player] + AIs:
                if p is ai or not p.alive or p.stun_timer <= 0:
                    continue
                if math.hypot(ai.x - p.x, ai.y - p.y) < 55:
                    cure_stun_by(ai)
                    return
        
        # 2) 의심 리셋 (가끔)
        if ai.suspect_player and random.random() < 0.003:
            ai.suspect_player = None
        
        if ai.flee_timer > 0:
            ai.flee_timer -= 1
        
        # 3) 도망 중 - 위협에서 멀어지며 지그재그(속도 크기 = speed 유지)
        if ai.flee_timer > 0 and ai.flee_target:
            if ai.suspect_player and ai.suspect_player.alive:
                ai.flee_target = (ai.suspect_player.x, ai.suspect_player.y)
            tx, ty = ai.flee_target[0], ai.flee_target[1]
            move_x, move_y = compute_flee_step(ai, tx, ty, speed)
            move_ai_with_door_priority(ai, ai.x + move_x, ai.y + move_y, speed)
            return
        
        fleeing = False
        flee_target = None
        
        # 플레이어 임포 환풍 목격
        if not fleeing and player.alive and player.venting and player.role == "imposter":
            if math.hypot(ai.x-player.x, ai.y-player.y) < vision_radius and is_path_clear(ai.x, ai.y, player.x, player.y):
                fleeing = True
                flee_target = (player.x, player.y)
                ai.suspect_player = player
        
        # AI 임포 환풍 목격
        if not fleeing:
            for imp in [a for a in AIs if a.alive and a.role=="imposter" and a.venting]:
                if math.hypot(ai.x-imp.x, ai.y-imp.y) < vision_radius and is_path_clear(ai.x, ai.y, imp.x, imp.y):
                    fleeing = True
                    flee_target = (imp.x, imp.y)
                    ai.suspect_player = imp
                    break
        
        # 의심 대상 근처면 도망 (거리 더 넓게 감지)
        if not fleeing and ai.suspect_player and ai.suspect_player.alive:
            d = math.hypot(ai.x - ai.suspect_player.x, ai.y - ai.suspect_player.y)
            if d < vision_radius * 1.2:  # 시야 밖 조금까지 경계
                fleeing = True
                flee_target = (ai.suspect_player.x, ai.suspect_player.y)
        
        if fleeing and flee_target:
            ai.flee_timer = random.randint(150, 210)  # 조금 더 오래 도망
            ai.flee_target = flee_target
            if ai.suspect_player and ai.suspect_player.alive:
                ai.flee_target = (ai.suspect_player.x, ai.suspect_player.y)
            tx, ty = ai.flee_target[0], ai.flee_target[1]
            move_x, move_y = compute_flee_step(ai, tx, ty, speed)
            move_ai_with_door_priority(ai, ai.x + move_x, ai.y + move_y, speed)
            return
        
        # 3b) 크루/가드·닥터(부활 가능 시): 스턴 크루 쪽으로 이동
        if ai.role in CREW_ROLES and ai.stun_timer <= 0 and doctor_can_heal:
            stunned = [p for p in [player] + AIs if p is not ai and p.alive and p.stun_timer > 0]
            if stunned:
                nearest = min(stunned, key=lambda p: math.hypot(ai.x - p.x, ai.y - p.y))
                d = math.hypot(ai.x - nearest.x, ai.y - nearest.y)
                if d < vision_radius * 2 and d > 55:
                    do_move(nearest.x, nearest.y)
                    return

        # 3c) 크루 댄스 파티: 모인 뒤 중심 주변을 빙글빙글 돈다
        if crew_gather_timer > 0 and crew_gather_target is not None and ai in crew_gather_members:
            dist_to_party = math.hypot(ai.x - crew_gather_target[0], ai.y - crew_gather_target[1])
            if dist_to_party > 110:
                do_move(crew_gather_target[0], crew_gather_target[1])
            else:
                member_index = crew_gather_members.index(ai)
                ticks = pygame.time.get_ticks()
                phase = ticks / 180 + member_index * (math.tau / max(1, len(crew_gather_members)))
                radius = 42 + math.sin(phase * 2.2) * 12
                dance_x = crew_gather_target[0] + math.cos(phase) * radius
                dance_y = crew_gather_target[1] + math.sin(phase) * radius
                dance_style = member_index % 3
                if dance_style == 0:
                    ai.spin_angle = (ai.spin_angle + 6) % 360
                    ai.dance_offset_x = 0
                    ai.dance_offset_y = 0
                elif dance_style == 1:
                    groove_phase = ticks / 160
                    ai.spin_angle = math.sin(groove_phase) * 16
                    ai.dance_offset_x = math.sin(groove_phase * 1.4) * 6
                    ai.dance_offset_y = 0
                else:
                    bounce_phase = ticks / 160
                    ai.spin_angle = math.sin(bounce_phase * 2) * 7
                    ai.dance_offset_x = 0
                    ai.dance_offset_y = -abs(math.sin(bounce_phase * 1.8)) * 9
                do_move(dance_x, dance_y)
            return

        # 3d) 자연 행동: 미션만 하지 않고 배회/동료 접근/잠깐 멈춤을 섞음
        if ai.natural_action_timer > 0:
            ai.natural_action_timer -= 1
            if ai.natural_action == "idle":
                return
            if ai.natural_action == "buddy" and alive_crews:
                buddy = nearest_crew(exclude_suspect=True)
                if buddy:
                    do_move(buddy.x, buddy.y)
                    return
            if ai.natural_action == "wander":
                if ai.wander_target is None or math.hypot(ai.x - ai.wander_target[0], ai.y - ai.wander_target[1]) < 70:
                    ai.wander_target = (random.randint(100, MAP_WIDTH - 100), random.randint(100, MAP_HEIGHT - 100))
                do_move(ai.wander_target[0], ai.wander_target[1])
                return
        elif random.random() < 0.007:
            ai.natural_action = random.choice(("wander", "buddy"))
            ai.natural_action_timer = random.randint(35, 100)
            if ai.natural_action == "wander":
                ai.wander_target = (random.randint(100, MAP_WIDTH - 100), random.randint(100, MAP_HEIGHT - 100))
            return
        
        # 4) 미션 수행 - 똑똑한 타겟 선택 (남은 미션 없으면 역할 행동 없이 배회만)
        remaining = [t for t in tasks if not t.completed]
        if not remaining:
            do_non_role_activity(ai, speed)
            return
        if ai.target_task is None or ai.target_task.completed:
            # 고립 상태 + 의심 대상 있으면: 다른 크루 근처 미션 우선
            if am_i_isolated() and ai.suspect_player:
                def score_task(t):
                    dist = math.hypot(ai.x - t.x, ai.y - t.y)
                    bonus = 0
                    for c in alive_crews:
                        cd = math.hypot(t.x - c.x, t.y - c.y)
                        if cd < vision_radius:
                            bonus -= 300  # 크루 근처 미션이면 가산
                    return dist + bonus
                ai.target_task = min(remaining, key=score_task)
            else:
                # 일반: 가까운 미션 + 다른 크루 근처면 약간 우선
                def score_task(t):
                    dist = math.hypot(ai.x - t.x, ai.y - t.y)
                    for c in alive_crews:
                        if math.hypot(t.x - c.x, t.y - c.y) < vision_radius:
                            dist -= 80  # 크루 옆 미션 선호
                    return dist
                ai.target_task = min(remaining, key=score_task)

        # 고립 + 의심 있을 때: 미션보다 안전 구역(다른 크루) 우선
        if am_i_isolated() and ai.suspect_player and alive_crews:
            buddy = nearest_crew(exclude_suspect=True)
            if buddy and math.hypot(ai.x - buddy.x, ai.y - buddy.y) > vision_radius:
                do_move(buddy.x, buddy.y)  # 친구 쪽으로 먼저 이동
                return

        do_move(ai.target_task.x, ai.target_task.y)
        if math.hypot(ai.x - ai.target_task.x, ai.y - ai.target_task.y) < task_range:
            ai.target_task.completed = True

def player_attack():
    global player_kill_cooldown, dead_players, player_kill_count
    
    if player.role=="imposter" and player_kill_cooldown <= 0:
        kill_targets = [p for p in AIs if p.alive and p.role in CREW_ROLES + NEUTRAL_SIDE_ROLES]
        for target in kill_targets:
            if math.hypot(player.x-target.x, player.y-target.y) < imposter_range and is_path_clear(player.x, player.y, target.x, target.y):
                if try_doctor_self_revive_on_kill(target):
                    player_kill_cooldown = 60
                    break
                spawn_imposter_slice_fx(target)
                target.alive = False
                target.ghost = True
                target.stun_timer = 0
                bodies.append(Body(target.x, target.y, target))
                dead_players.append(target)
                alert_crew_witnesses_attacker(player, target)
                player_kill_count += 1
                player.stats_kills += 1
                player_kill_cooldown = 60
                if target.role=="guard":
                    player.stun_timer = STUN_DURATION  # 경비 킬 시 임포 30초 스턴
                break

def player_sheriff_shoot(target=None):
    global dead_players
    if player.role != "sheriff" or not player.alive:
        return False
    if player.sheriff_bullets <= 0:
        set_event_notice("No bullets left.")
        return False
    px = player.x + player.width / 2
    py = player.y + player.height / 2
    if target is None:
        targets = [p for p in AIs if p.alive]
        target = next(
            (
                p for p in targets
                if math.hypot(px - (p.x + p.width / 2), py - (p.y + p.height / 2)) < 120
                and is_path_clear(px, py, p.x + p.width / 2, p.y + p.height / 2)
            ),
            None,
        )
    if target is None:
        set_event_notice("No target selected.")
        return False
    tx = target.x + target.width / 2
    ty = target.y + target.height / 2
    if not target.alive or math.hypot(px - tx, py - ty) >= 140:
        set_event_notice("Target too far to shoot.")
        return False
    if not is_path_clear(px, py, tx, ty):
        set_event_notice("Shot blocked by wall.")
        return False

    player.sheriff_bullets -= 1
    if target.role == "imposter":
        if try_doctor_self_revive_on_kill(target):
            player.sheriff_bullets += 1
            return True
        target.alive = False
        target.ghost = True
        target.stun_timer = 0
        bodies.append(Body(target.x, target.y, target))
        dead_players.append(target)
        player.stats_kills += 1
        player.sheriff_bullets += 1
        set_event_notice("Imposter down. Bullet restored.")
    else:
        if not try_doctor_self_revive_on_kill(target):
            target.alive = False
            target.ghost = True
            target.stun_timer = 0
            bodies.append(Body(target.x, target.y, target))
            dead_players.append(target)
        player.alive = False
        player.ghost = True
        player.stun_timer = 0
        bodies.append(Body(player.x, player.y, player))
        dead_players.append(player)
        set_event_notice("Wrong target. Both eliminated.")
    return True

def player_troll_stun():
    """플레이어(트롤) 스턴 공격"""
    global troll_stun_cooldown
    if player.role != "troll" or not player.alive or player.stun_timer > 0 or troll_stun_cooldown > 0:
        return
    troll_range = 55
    targets = [a for a in AIs if a.alive and a.role in CREW_ROLES and a.stun_timer <= 0]
    for target in targets:
        if math.hypot(player.x-target.x, player.y-target.y) < troll_range and is_path_clear(player.x, player.y, target.x, target.y):
            target.stun_timer = STUN_DURATION
            player.stats_stuns += 1
            troll_stun_cooldown = 90
            alert_crew_witnesses_attacker(player, target)
            break


def player_mad_scientist_gas_deploy(aim_world_x, aim_world_y):
    """플레이어(미친 과학자): 클릭 지향 원거리 독가스 살포. 40s 쿨, 벽에 막히면 실패."""
    if player.role != "mad_scientist" or not player.alive or player.stun_timer > 0:
        return False
    if player.gas_kill_cooldown > 0:
        set_event_notice(f"Gas charging ({player.gas_kill_cooldown / 60:.1f}s).")
        return False
    if not deploy_poison_gas_cloud(player, aim_world_x, aim_world_y):
        set_event_notice("Gas blocked by walls.")
        return False
    player.gas_kill_cooldown = MAD_SCIENTIST_GAS_COOLDOWN_FRAMES
    return True


def player_vent():
    """플레이어 환기"""
    global security_camera_mode
    if player.role in ("imposter", "engineer") and not player.venting and player.alive:
        for vent in vents:
            if math.hypot(player.x-vent.x, player.y-vent.y) < 50:  # 50 범위 내
                security_camera_mode = False
                player.venting = True
                player.vent_time = 30  # 30프레임 동안 환기
                dest_vent = random.choice(vent.available_vents)
                player.x, player.y = find_safe_position_near(dest_vent.x, dest_vent.y)
                return True
    return False

def report_body_action():
    """시체 신고 - 플레이어가 시체 제거"""
    return report_body_by(player)

def report_body_by(reporter):
    for i, b in enumerate(bodies):
        if math.hypot(reporter.x-b.x, reporter.y-b.y) < 50:
            bodies.pop(i)
            print(f"Body reported! Remaining bodies: {len(bodies)}")
            return True
    return False

def revive_body_by(doctor):
    global dead_players
    if doctor.role != "doctor" or doctor.revive_used:
        return False
    if doctor.ghost:
        return revive_own_body(doctor)
    for i, b in enumerate(bodies):
        if math.hypot(doctor.x-b.x, doctor.y-b.y) < 50 and b.dead_player:
            victim = b.dead_player
            victim.alive = True
            victim.ghost = False
            victim.x, victim.y = b.x, b.y
            if victim.role == "bomber":
                victim.bombs_remaining = 7  # 의사 부활 시 폭탄 7개 리필
            if victim.role == "mad_scientist":
                victim.gas_kill_cooldown = 0
            if victim in dead_players:
                dead_players.remove(victim)
            bodies.pop(i)
            doctor.revive_used = True
            if doctor is player:
                player.stats_revives += 1
            return True
    return False


def revive_body_by_undertaker(actor, body_index=None):
    """Undertaker: revive one chosen corpse once."""
    global dead_players
    if actor.role != "undertaker" or actor.undertaker_revive_used:
        return False

    if body_index is not None:
        candidates = [body_index] if 0 <= body_index < len(bodies) else []
    else:
        candidates = range(len(bodies))

    for i in candidates:
        b = bodies[i]
        if b.dead_player is None:
            continue
        if body_index is None and math.hypot(actor.x - b.x, actor.y - b.y) >= 65:
            continue
        victim = b.dead_player
        victim.alive = True
        victim.ghost = False
        victim.x, victim.y = b.x, b.y
        if victim.role == "mad_scientist":
            victim.gas_kill_cooldown = 0
        if victim in dead_players:
            dead_players.remove(victim)
        bodies.pop(i)
        actor.undertaker_revive_used = True
        if actor is player:
            player.stats_revives += 1
        return True
    return False

def cure_stun_by(actor):
    """크루/의사/경비만: 근처 스턴된 플레이어 스턴 해제 (임포·트롤 제외)"""
    if actor.role not in CREW_ROLES:
        return False
    for p in [player] + AIs:
        if p is actor or not p.alive or p.stun_timer <= 0:
            continue
        if math.hypot(actor.x - p.x, actor.y - p.y) < 55:
            p.stun_timer = 0
            return True
    return False

def check_win():
    global winner, game_over
    if game_over:
        return True
    alive_crews=[p for p in [player]+AIs if p.alive and p.role in CREW_ROLES]
    alive_imposters=[p for p in [player]+AIs if p.alive and p.role=="imposter"]
    alive_trolls=[p for p in [player]+AIs if p.alive and p.role=="troll"]
    alive_bombers=[p for p in [player]+AIs if p.alive and p.role=="bomber"]
    alive_mad_scientists=[p for p in [player]+AIs if p.alive and p.role=="mad_scientist"]
    alive_all=[p for p in [player]+AIs if p.alive]
    non_imposters=[p for p in alive_all if p.role!="imposter"]

    if any(has_pending_self_revive(p) for p in [player] + AIs):
        return False

    counted_non_imposters = [
        p for p in alive_all
        if p.role not in ("imposter",) + NEUTRAL_SIDE_ROLES
    ]

    # 특수 구도: 임포 2명 + 트롤 + 붐버만 남으면 트롤 승리
    if (
        len(alive_imposters) == 2
        and len(alive_trolls) > 0
        and len(alive_bombers) > 0
        and len(counted_non_imposters) == 0
    ):
        winner="T2 Win! (Troll)"
        game_over = True
        return True
    
    # 최후 2인 규칙: 트롤/폭탄광이 2인 생존에 포함되면 해당 역할 승리
    if len(alive_all) == 2:
        if len(alive_trolls) > 0:
            winner="T2 Win! (Troll)"
            game_over = True
            return True
        if len(alive_bombers) > 0:
            winner="T3 Win! (Bomber)"
            game_over = True
            return True
        if len(alive_mad_scientists) > 0:
            winner="T5 Win! (Mad Scientist)"
            game_over = True
            return True

    # 폭탄광 승리: 임포 2명 모두 사망(임포 생존 0) + 살아있는 폭탄광 존재
    if len(alive_imposters) == 0 and len(alive_bombers) > 0:
        winner="T3 Win! (Bomber)"
        game_over = True
        return True
    if len(alive_imposters) == 0 and len(alive_mad_scientists) > 0:
        winner="T5 Win! (Mad Scientist)"
        game_over = True
        return True
    # 임포 특수 승리: 자신 제외 1명만 남으면 승리
    # 단, 마지막 1명이 트롤/폭탄광/미친 과학자인 경우는 제외
    if len(alive_imposters) > 0 and len(non_imposters) == 1:
        if non_imposters[0].role not in NEUTRAL_SIDE_ROLES:
            winner="T4 Win! (Imposter)"
            game_over = True
            return True

    # 임포 0명 = 크루 승리 (단, 살아있는 폭탄광 승리 조건이 먼저 우선)
    if len(alive_imposters) == 0:
        winner="T1 Win! (Crew Team)"
        game_over = True
        return True
    # 임포만 남으면 즉시 임포 승리 (중립 역할 전원 제거됨)
    if len(alive_imposters) > 0 and not counted_non_imposters and not alive_trolls and not alive_bombers and not alive_mad_scientists:
        winner="T4 Win! (Imposter)"
        game_over = True
        return True
    # 임포 수 >= (임포·중립 제외 생존자) 이면 임포 승리.
    # 트롤/붐버는 counted에 들어가지 않음; 동점만 막지 않아 ‘전원 사망’까지 강요하지 않음.
    if len(alive_imposters) > 0 and len(alive_imposters) >= len(counted_non_imposters):
        winner="T4 Win! (Imposter)"
        game_over = True
        return True
    # 미션 다 하면 크루 승리
    if all(t.completed for t in tasks) and alive_crews:
        winner="T1 Win! (Tasks Complete)"
        game_over = True
        return True
    return False

def get_doctor_spectate_target():
    """Doctor entity for spectate (alive or ghost)."""
    return next((p for p in [player] + AIs if p.role == "doctor" and (p.alive or p.ghost)), None)


def get_spectate_follow_chain():
    """Spectate camera cycle: non-imposters only."""
    chain = []
    seen = set()
    allp = [player] + AIs
    for p in allp:
        if id(p) in seen or p.role == "imposter":
            continue
        if p.role == "doctor" and (p.alive or p.ghost):
            chain.append(p)
            seen.add(id(p))
    for p in allp:
        if id(p) in seen or p.role == "imposter":
            continue
        if p.role == "troll" and (p.alive or p.ghost):
            chain.append(p)
            seen.add(id(p))
    for p in allp:
        if id(p) in seen or p.role == "imposter":
            continue
        if p.role == "guard" and (p.alive or p.ghost):
            chain.append(p)
            seen.add(id(p))
    for p in allp:
        if id(p) in seen or p.role == "imposter":
            continue
        if p.role == "engineer" and (p.alive or p.ghost):
            chain.append(p)
            seen.add(id(p))
    for p in allp:
        if id(p) in seen or p.role == "imposter":
            continue
        if p.role == "undertaker" and (p.alive or p.ghost):
            chain.append(p)
            seen.add(id(p))
    for p in allp:
        if id(p) in seen or p.role == "imposter":
            continue
        if p.role == "sheriff" and (p.alive or p.ghost):
            chain.append(p)
            seen.add(id(p))
    for p in allp:
        if id(p) in seen or p.role == "imposter":
            continue
        if p.role == "bomber" and (p.alive or p.ghost):
            chain.append(p)
            seen.add(id(p))
    for p in allp:
        if id(p) in seen or p.role == "imposter":
            continue
        if p.role == "mad_scientist" and (p.alive or p.ghost):
            chain.append(p)
            seen.add(id(p))
    for p in allp:
        if id(p) in seen or p.role == "imposter":
            continue
        if p.role == "crew" and (p.alive or p.ghost):
            chain.append(p)
            seen.add(id(p))
    return chain


def get_spectate_camera_target():
    chain = get_spectate_follow_chain()
    if not chain:
        return None
    return chain[spectate_follow_index % len(chain)]


def cycle_spectate_follow_target():
    global spectate_follow_index
    chain = get_spectate_follow_chain()
    if not chain:
        return
    spectate_follow_index = (spectate_follow_index + 1) % len(chain)


def spectate_target_kind_label(subj):
    if not subj:
        return "-"
    if subj.role == "doctor":
        return "Doctor"
    if subj.role == "troll":
        return "Troll"
    if subj.role == "crew":
        return "Crew"
    if subj.role == "guard":
        return "Guard"
    if subj.role == "engineer":
        return "Engineer"
    if subj.role == "undertaker":
        return "Undertaker"
    if subj.role == "sheriff":
        return "Shooter"
    if subj.role == "bomber":
        return "Bomber"
    if subj.role == "mad_scientist":
        return "Mad Scientist"
    return subj.role


def doctor_spectate_overlay_active():
    """True when doctor-spectate overlay, ghost sprites, and role labels are active."""
    return (
        game_started
        and spectate_doctor_mode
        and player.ghost
        and player.role in SPECTATE_DOCTOR_ROLES
    )


def get_camera_pos():
    """Follow player; doctor spectate: Tab target; security cameras: watched room center."""
    global spectate_doctor_mode
    if spectate_doctor_mode and player.ghost and player.role in SPECTATE_DOCTOR_ROLES:
        subj = get_spectate_camera_target()
        if subj:
            camera_x = subj.x - SCREEN_WIDTH // 2
            camera_y = subj.y - SCREEN_HEIGHT // 2
            camera_x = max(0, min(camera_x, MAP_WIDTH - SCREEN_WIDTH))
            camera_y = max(0, min(camera_y, MAP_HEIGHT - SCREEN_HEIGHT))
            return camera_x, camera_y
        spectate_doctor_mode = False
    if security_camera_feed_active():
        ri = security_camera_view_index
        if 0 <= ri < len(room_zones):
            rect = room_zones[ri]["rect"]
            camera_x = rect.centerx - SCREEN_WIDTH // 2
            camera_y = rect.centery - SCREEN_HEIGHT // 2
            camera_x = max(0, min(camera_x, MAP_WIDTH - SCREEN_WIDTH))
            camera_y = max(0, min(camera_y, MAP_HEIGHT - SCREEN_HEIGHT))
            return camera_x, camera_y
    camera_x = player.x - SCREEN_WIDTH // 2
    camera_y = player.y - SCREEN_HEIGHT // 2
    camera_x = max(0, min(camera_x, MAP_WIDTH - SCREEN_WIDTH))
    camera_y = max(0, min(camera_y, MAP_HEIGHT - SCREEN_HEIGHT))
    return camera_x, camera_y


def get_draw_focus():
    """Reference point for drawing tasks/bodies (spectate target when active)."""
    if spectate_doctor_mode and player.ghost and player.role in SPECTATE_DOCTOR_ROLES:
        subj = get_spectate_camera_target()
        if subj:
            return subj
    if security_camera_feed_active():
        ri = security_camera_view_index
        if 0 <= ri < len(room_zones):
            rect = room_zones[ri]["rect"]
            w, h = player.width, player.height
            return SimpleNamespace(
                x=float(rect.centerx - w / 2),
                y=float(rect.centery - h / 2),
                width=w,
                height=h,
            )
    return player


def _ray_segment_intersection(px, py, dx, dy, x1, y1, x2, y2):
    sx, sy = x2 - x1, y2 - y1
    denom = dx * sy - dy * sx
    if abs(denom) < 0.00001:
        return None
    qpx, qpy = x1 - px, y1 - py
    t = (qpx * sy - qpy * sx) / denom
    u = (qpx * dy - qpy * dx) / denom
    if t >= 0 and 0 <= u <= 1:
        return t
    return None


def _cast_vision_ray(px, py, angle, wall_rects):
    dx = math.cos(angle)
    dy = math.sin(angle)
    closest = vision_radius
    for r in wall_rects:
        edges = (
            (r.left, r.top, r.right, r.top),
            (r.right, r.top, r.right, r.bottom),
            (r.right, r.bottom, r.left, r.bottom),
            (r.left, r.bottom, r.left, r.top),
        )
        for edge in edges:
            t = _ray_segment_intersection(px, py, dx, dy, *edge)
            if t is not None and 0 < t < closest:
                closest = t
    return px + dx * closest, py + dy * closest


def build_vision_polygon(focus, camera_x, camera_y):
    """Build the current line-of-sight polygon, clipped by nearby walls."""
    px = focus.x + focus.width / 2
    py = focus.y + focus.height / 2
    scan_rect = pygame.Rect(px - vision_radius, py - vision_radius, vision_radius * 2, vision_radius * 2)
    wall_rects = [w.rect for w in walls if scan_rect.colliderect(w.rect)]

    angles = [math.radians(a) for a in range(0, 360, VISION_RAY_STEP_DEG)]
    for r in wall_rects:
        for cx, cy in ((r.left, r.top), (r.right, r.top), (r.right, r.bottom), (r.left, r.bottom)):
            if math.hypot(cx - px, cy - py) <= vision_radius + max(r.w, r.h):
                base = math.atan2(cy - py, cx - px)
                angles.extend((base - 0.0008, base, base + 0.0008))

    hits = []
    for angle in angles:
        wx, wy = _cast_vision_ray(px, py, angle, wall_rects)
        hits.append((angle, (int(wx - camera_x), int(wy - camera_y))))
    hits.sort(key=lambda item: item[0])
    return [point for _, point in hits]


def get_focus_visible_zones(focus):
    """Among Us style: the whole current room/corridor stays visible."""
    px = focus.x + focus.width / 2
    py = focus.y + focus.height / 2
    point = (px, py)
    zones = []

    for z in corridor_zones:
        if z.collidepoint(point):
            zones.append(z.inflate(8, 8))

    if not zones:
        row, col = get_room_cell(px, py)
        zones.append(pygame.Rect(MARGIN_X + col * cell_w, MARGIN_Y + row * cell_h, cell_w, cell_h))

    return zones


def clear_visible_zone_on_overlay(overlay, zone, camera_x, camera_y):
    sx = int(zone.x - camera_x)
    sy = int(zone.y - camera_y)
    rect = pygame.Rect(sx, sy, zone.w, zone.h)
    if not rect.colliderect(pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)):
        return
    pygame.draw.rect(overlay, (0, 0, 0, 0), rect)


def _wall_shadow_polygon(rect, px, py, camera_x, camera_y):
    corners = [(rect.left, rect.top), (rect.right, rect.top), (rect.right, rect.bottom), (rect.left, rect.bottom)]
    angled = sorted((math.atan2(y - py, x - px), (x, y)) for x, y in corners)
    wrapped = angled + [(a + math.tau, pt) for a, pt in angled]

    largest_gap = -1
    gap_index = 0
    for i in range(len(angled)):
        gap = wrapped[i + 1][0] - wrapped[i][0]
        if gap > largest_gap:
            largest_gap = gap
            gap_index = i

    near_a = wrapped[gap_index + 1][1]
    near_b = wrapped[gap_index][1]
    shadow_len = max(SCREEN_WIDTH, SCREEN_HEIGHT) * 2

    def projected(point):
        x, y = point
        dx, dy = x - px, y - py
        dist = math.hypot(dx, dy) or 1
        return x + dx / dist * shadow_len, y + dy / dist * shadow_len

    far_b = projected(near_b)
    far_a = projected(near_a)
    points = (near_a, near_b, far_b, far_a)
    return [(int(x - camera_x), int(y - camera_y)) for x, y in points]


def draw_wall_blocked_vision(focus, camera_x, camera_y):
    if not game_started or focus is None:
        return

    px = focus.x + focus.width / 2
    py = focus.y + focus.height / 2
    sx = int(px - camera_x)
    sy = int(py - camera_y)
    visible_world = pygame.Rect(camera_x - 80, camera_y - 80, SCREEN_WIDTH + 160, SCREEN_HEIGHT + 160)
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

    for wall in walls:
        if not visible_world.colliderect(wall.rect):
            continue
        if wall.rect.collidepoint(px, py):
            continue
        shadow = _wall_shadow_polygon(wall.rect, px, py, camera_x, camera_y)
        pygame.draw.polygon(overlay, (0, 0, 0, 190), shadow)

    if blackout_timer > 0:
        radius = get_effective_vision_radius()
        blackout = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        blackout.fill((0, 0, 0, 225))
        for scale, alpha in ((1.00, 0), (1.10, 70), (1.22, 130)):
            pygame.draw.circle(blackout, (0, 0, 0, alpha), (sx, sy), int(radius * scale))
        overlay.blit(blackout, (0, 0))

    screen.blit(overlay, (0, 0))


def draw_crew_gather_music_notes(camera_x, camera_y):
    if crew_gather_timer <= 0 or not crew_gather_members:
        return

    ticks = pygame.time.get_ticks()
    notes = ("♪", "♫")
    for i, member in enumerate(crew_gather_members):
        if not member.alive:
            continue
        phase = ticks / 260 + i * 1.7
        note = notes[i % len(notes)]
        sx = int(member.x - camera_x + member.width + 5 + math.sin(phase) * 10)
        sy = int(member.y - camera_y - 14 - (math.sin(phase * 1.4) + 1) * 8)
        if -40 < sx < SCREEN_WIDTH + 40 and -40 < sy < SCREEN_HEIGHT + 40:
            color = (255, 235, 120) if i % 2 == 0 else (140, 220, 255)
            rendered = font.render(note, True, color)
            screen.blit(rendered, (sx, sy))


def draw_player_dance_music_notes(camera_x, camera_y):
    if not (player.alive or player.ghost):
        return
    if not (player.spin_angle % 360 or player.dance_offset_x or player.dance_offset_y):
        return

    ticks = pygame.time.get_ticks()
    note_sets = (
        ("♪", "♫"),
        ("♫", "♬"),
        ("♩", "♬"),
    )
    color_sets = (
        ((255, 235, 120), (255, 205, 80)),
        ((140, 220, 255), (80, 180, 255)),
        ((220, 160, 255), (255, 140, 220)),
    )
    style = max(0, min(player.dance_note_style, len(note_sets) - 1))
    notes = note_sets[style]
    colors = color_sets[style]
    for i in range(2):
        phase = ticks / 230 + i * 2.1
        sx = int(player.x - camera_x + player.width + 8 + math.sin(phase) * 13)
        sy = int(player.y - camera_y - 18 - (math.sin(phase * 1.5) + 1) * 10 - i * 6)
        if -50 < sx < SCREEN_WIDTH + 50 and -50 < sy < SCREEN_HEIGHT + 50:
            rendered = font.render(notes[(ticks // 300 + i) % len(notes)], True, colors[(ticks // 300 + i) % len(colors)])
            screen.blit(rendered, (sx, sy))


def draw_fake_task_effects(camera_x, camera_y):
    for actor in [player] + AIs:
        if actor.fake_task_timer <= 0 or not actor.alive:
            continue
        sx = int(actor.x - camera_x + actor.width // 2)
        sy = int(actor.y - camera_y - 28)
        if -60 < sx < SCREEN_WIDTH + 60 and -60 < sy < SCREEN_HEIGHT + 60:
            text = nick_font.render("TASK...", True, (255, 230, 120))
            screen.blit(text, (sx - text.get_width() // 2, sy))
            pygame.draw.circle(screen, (255, 230, 120), (sx, sy + 28), 18, 2)


def draw_event_marker(camera_x, camera_y, x, y, label, color):
    sx = int(x - camera_x)
    sy = int(y - camera_y)
    if not (-80 < sx < SCREEN_WIDTH + 80 and -80 < sy < SCREEN_HEIGHT + 80):
        return
    pygame.draw.circle(screen, color, (sx, sy), 26, 3)
    pygame.draw.circle(screen, color, (sx, sy), 7)
    text = nick_font.render(label, True, color)
    screen.blit(text, (sx - text.get_width() // 2, sy - 48))


def draw_random_event_effects(camera_x, camera_y):
    for block in get_active_door_blocks():
        sx = block.x - camera_x
        sy = block.y - camera_y
        if sx < SCREEN_WIDTH and sy < SCREEN_HEIGHT and sx + block.w > 0 and sy + block.h > 0:
            pygame.draw.rect(screen, (18, 18, 24), (sx, sy, block.w, block.h))
            pygame.draw.rect(screen, (255, 120, 80), (sx, sy, block.w, block.h), 2)
    if blackout_timer > 0 and blackout_room is not None:
        draw_event_marker(camera_x, camera_y, *get_room_center(blackout_room), "FIX POWER", (160, 190, 255))
    if locked_room_timer > 0 and locked_room is not None:
        rect = get_room_rect(locked_room)
        sx = rect.x - camera_x
        sy = rect.y - camera_y
        pygame.draw.rect(screen, (255, 120, 80), (sx, sy, rect.w, rect.h), 4)
        draw_event_marker(camera_x, camera_y, rect.centerx, rect.centery, "LOCKED", (255, 120, 80))
    if cleanup_timer > 0 and cleanup_room is not None:
        draw_event_marker(camera_x, camera_y, *get_room_center(cleanup_room), "CLEAN", (120, 255, 170))
    if vent_noise_timer > 0 and vent_noise_vent is not None:
        draw_event_marker(camera_x, camera_y, vent_noise_vent.x, vent_noise_vent.y, "NOISE", (180, 220, 255))
    if security_camera_feed_active():
        ri = security_camera_view_index
        if 0 <= ri < len(room_zones):
            rect = room_zones[ri]["rect"]
            sx = rect.x - camera_x
            sy = rect.y - camera_y
            if sx < SCREEN_WIDTH and sy < SCREEN_HEIGHT and sx + rect.w > 0 and sy + rect.h > 0:
                pygame.draw.rect(screen, (80, 190, 255), (sx, sy, rect.w, rect.h), 3)
            draw_event_marker(camera_x, camera_y, rect.centerx, rect.centery, "CAM", (140, 220, 255))
            for subject in [player] + AIs:
                if not subject.alive:
                    continue
                if get_room_index_at(subject.x + subject.width / 2, subject.y + subject.height / 2) != ri:
                    continue
                sx = int(subject.x - camera_x + subject.width // 2)
                sy = int(subject.y - camera_y - 24)
                if -40 < sx < SCREEN_WIDTH + 40 and -40 < sy < SCREEN_HEIGHT + 40:
                    pygame.draw.circle(screen, (140, 220, 255), (sx, sy), 5, 1)
    if oxygen_timer > 0:
        for i, point in enumerate(oxygen_points):
            if not oxygen_fixed[i]:
                sx = int(point[0] - camera_x)
                sy = int(point[1] - camera_y)
                if -40 < sx < SCREEN_WIDTH + 40 and -40 < sy < SCREEN_HEIGHT + 40:
                    pygame.draw.rect(screen, (255, 130, 130), (sx, sy, 25, 25))
                    pygame.draw.rect(screen, WHITE, (sx, sy, 25, 25), 2)
                    label = nick_font.render(f"O2-{i + 1}", True, (255, 170, 170))
                    screen.blit(label, (sx + 12 - label.get_width() // 2, sy - label.get_height() - 2))
    if dance_challenge_timer > 0 and dance_challenge_room is not None:
        draw_event_marker(camera_x, camera_y, *get_room_center(dance_challenge_room), "DANCE", (255, 200, 120))
    if ghost_prank_timer > 0 and ghost_prank_pos is not None:
        ticks = pygame.time.get_ticks()
        gx, gy = ghost_prank_pos
        for i, note in enumerate(("BOO", "♪", "♫")):
            phase = ticks / 180 + i * 2
            sx = int(gx - camera_x + math.cos(phase) * 42)
            sy = int(gy - camera_y + math.sin(phase) * 28)
            if -50 < sx < SCREEN_WIDTH + 50 and -50 < sy < SCREEN_HEIGHT + 50:
                text = font.render(note, True, (210, 210, 255))
                screen.blit(text, (sx, sy))


def draw_sabotage_room_selection(camera_x, camera_y):
    if not sabotage_select_mode:
        return
    color = (255, 120, 80) if sabotage_select_mode == "locked" else (255, 130, 130)
    for zone in room_zones:
        rect = zone["rect"]
        sx = rect.x - camera_x
        sy = rect.y - camera_y
        if sx < SCREEN_WIDTH and sy < SCREEN_HEIGHT and sx + rect.w > 0 and sy + rect.h > 0:
            pygame.draw.rect(screen, color, (sx, sy, rect.w, rect.h), 2)
            label = nick_font.render(str(zone["num"]), True, color)
            screen.blit(label, (sx + rect.w // 2 - label.get_width() // 2, sy + rect.h // 2 - label.get_height() // 2))


def get_event_status_lines():
    lines = []
    if oxygen_timer > 0:
        fixed = sum(1 for v in oxygen_fixed if v)
        prefix = "SABOTAGE " if oxygen_sabotage_owner is not None else ""
        lines.append(f"{prefix}Oxygen {fixed}/{len(oxygen_points)} {oxygen_timer // 60}s")
    if blackout_timer > 0:
        prefix = "SABOTAGE " if blackout_sabotage_owner is not None else ""
        lines.append(f"{prefix}Blackout {blackout_timer // 60}s")
    if locked_room_timer > 0:
        prefix = "SABOTAGE " if locked_room_sabotage_owner is not None else ""
        lines.append(f"{prefix}Locked {get_room_label(locked_room)} {locked_room_timer // 60}s")
    if cleanup_timer > 0:
        lines.append(f"Cleanup {cleanup_progress // 60}/3s")
    if vent_noise_timer > 0:
        lines.append(f"Vent noise {vent_noise_timer // 60}s")
    if security_camera_timer > 0:
        lines.append(
            f"Security alert {security_camera_timer // 60}s  |  {SECURITY_DESK_ROOM_NAME} room: B monitors  |  [ ] room"
        )
    if suspicion_event_timer > 0:
        lines.append(f"Suspicion high {suspicion_event_timer // 60}s")
    if dance_challenge_timer > 0:
        lines.append(f"Dance challenge {dance_challenge_timer // 60}s")
    if dance_boost_timer > 0:
        lines.append(f"Dance boost {dance_boost_timer // 60}s")
    return lines


def get_alive_doctor():
    return next((p for p in [player] + AIs if p.role == "doctor" and p.alive), None)


def player_can_use_doctor_spectate():
    """Ghost players can spectate (imposter included)."""
    return (
        player.ghost
        and player.role in SPECTATE_DOCTOR_ROLES
        and len(get_spectate_follow_chain()) > 0
    )


ROLE_HELP_LINES = [
    (
        "Crew",
        "Goal: finish all tasks and stay alive.",
        "Actions: walk to yellow tasks to complete them automatically; repair O2, power, and locked doors by standing near the marker.",
    ),
    (
        "Doctor",
        "Goal: help the crew team survive.",
        "Keys: F revives one dead player near a body; G cures a stunned player. If you die, move to your corpse and press F to self-revive once.",
    ),
    (
        "Guard",
        "Goal: protect the crew team.",
        "Keys: G cures stunned players. Killing a Guard stuns the killer for 30 seconds.",
    ),
    (
        "Engineer",
        "Goal: finish tasks and quickly fix emergencies.",
        "Keys: E uses vents while alive. Engineers can still complete tasks and repair sabotage like crew.",
    ),
    (
        "Undertaker",
        "Goal: bring one dead player back and support the crew team.",
        "Keys: F revives one player near a body. If you die, move to your corpse and press F to self-revive once.",
    ),
    (
        "Shooter",
        "Goal: remove imposters without shooting innocents.",
        "Controls: click a nearby player to shoot. Hitting an imposter restores your bullet; a wrong shot kills both you and the target.",
    ),
    (
        "Imposter",
        "Goal: eliminate the crew until imposters control the round.",
        "Controls: click nearby players to kill; Q fakes a task near a task; 1 starts Blackout, 2 starts Oxygen, 3 starts Door Lock.",
    ),
    (
        "Troll",
        "Goal: create chaos and win special endgame situations.",
        "Actions: stun crew members at close range. Trolls can repair sabotage by reaching O2 panels, power, or locked doors.",
    ),
    (
        "Bomber",
        "Goal: win with bombs or special endgame situations.",
        "Controls: click a nearby player to attach a bomb; if you hold a bomb, click someone to pass it. Bombs explode after 15 seconds.",
    ),
    (
        "Mad Scientist",
        "Goal: Team T5 — eliminate others with poison gas; win when imposters are gone while you live, or in certain 2-player endings.",
        "Controls: left-click the map to deploy a long-range poison gas cloud (max range, blocked by walls). Anyone in the green cloud dies (40s cooldown). Killing a Guard stuns you for 30 seconds.",
    ),
    (
        "Ghost",
        "Goal: keep moving after death and use ghost-only tricks.",
        "Keys: WASD moves as a ghost; C/X/Z dances; K triggers a ghost prank that scares living players who see it.",
    ),
]


def get_role_color(role):
    r = role.lower()
    if r == "shooter":
        r = "sheriff"
    if r == "imposter":
        return ORANGE
    if r == "troll":
        return TROLL_COLOR
    if r == "bomber":
        return BOMBER_COLOR
    if r == "mad_scientist":
        return MAD_SCIENTIST_COLOR
    if r == "doctor":
        return DOCTOR_COLOR
    if r == "guard":
        return GUARD_COLOR
    if r == "engineer":
        return ENGINEER_COLOR
    if r == "undertaker":
        return UNDERTAKER_COLOR
    if r == "sheriff":
        return GUARD_COLOR
    return CYAN


def get_main_menu_buttons():
    bw, bh = 320, 70
    x = SCREEN_WIDTH // 2 - bw // 2
    y = SCREEN_HEIGHT // 2 + 10
    return {
        "start": pygame.Rect(x, y, bw, bh),
        "howto": pygame.Rect(x, y + 90, bw, bh),
    }


def get_how_to_back_button():
    return pygame.Rect(40, SCREEN_HEIGHT - 95, 220, 58)


def draw_button(rect, text, fill, border=WHITE):
    pygame.draw.rect(screen, fill, rect, border_radius=12)
    pygame.draw.rect(screen, border, rect, 3, border_radius=12)
    label = menu_font.render(text, True, WHITE)
    screen.blit(label, label.get_rect(center=rect.center))


def draw_main_menu():
    screen.fill((12, 16, 28))
    title = title_font.render("Spiral of Suspicion", True, (140, 220, 255))
    subtitle = font.render("Survive, deceive, repair, or sabotage.", True, (210, 220, 235))
    role_hint = font.render("Your role will be revealed after the game starts.", True, (190, 200, 220))
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 190)))
    screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 115)))
    screen.blit(role_hint, role_hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 72)))

    buttons = get_main_menu_buttons()
    draw_button(buttons["start"], "Start Game", (35, 95, 70), (120, 255, 170))
    draw_button(buttons["howto"], "How to Play", (70, 70, 105), (180, 190, 255))

    hint = nick_font.render("Enter: Start  |  H: How to Play  |  ESC: Exit", True, (170, 180, 205))
    screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 48)))


def draw_how_to_page():
    screen.fill((10, 12, 24))
    title = title_font.render("How to Play", True, YELLOW)
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 54)))

    y = 110
    x = max(50, SCREEN_WIDTH // 2 - 650)
    role_w = 155
    line_gap = 24
    role_gap = 12
    for role, goal, action in ROLE_HELP_LINES:
        role_color = get_role_color(role.lower())
        role_label = nick_font.render(f"{role}:", True, role_color)
        goal_text = nick_font.render(goal, True, WHITE)
        action_text = nick_font.render(action, True, (205, 215, 235))
        screen.blit(role_label, (x, y))
        screen.blit(goal_text, (x + role_w, y))
        screen.blit(action_text, (x + role_w, y + line_gap))
        y += line_gap * 2 + role_gap

    controls = [
        "Common Keys: WASD move | Shift sprint | M hold: minimap | C spin | X groove | Z bounce | ESC quit.",
        "Sabotage Rules: Imposters start sabotage. Crew team, Troll, and Bomber can stop it by reaching the marked objective.",
        "Win Notes: Tasks complete = Crew Team win. Oxygen failure = sabotage owner team wins. Special Troll/Bomber endgames can override.",
    ]
    y += 4
    for line in controls:
        rendered = nick_font.render(line, True, (170, 220, 255))
        screen.blit(rendered, (x, y))
        y += 25

    draw_button(get_how_to_back_button(), "Back", (75, 55, 55), (255, 180, 150))
    hint = nick_font.render("ESC or Backspace: Back to Main Menu", True, (170, 180, 205))
    screen.blit(hint, (290, SCREEN_HEIGHT - 78))


ROLE_REVEAL_MS = 3000


def draw_role_reveal_screen(now_ms):
    elapsed = now_ms - round_session_start_ms
    left_ms = max(0, ROLE_REVEAL_MS - elapsed)
    sec_left = max(0, math.ceil(left_ms / 1000))
    veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    veil.fill((0, 0, 0, 230))
    screen.blit(veil, (0, 0))
    role_color = get_role_color(player.role)
    role_line = title_font.render(
        f"YOUR ROLE: {get_role_display_name(player.role).upper()}",
        True,
        role_color,
    )
    screen.blit(role_line, role_line.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)))
    t_line = font.render(f"The game starts in {sec_left}…", True, (220, 225, 240))
    screen.blit(t_line, t_line.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 35)))


MINIMAP_MAX_W = 300
MINIMAP_MAX_H = 220
MINIMAP_SCREEN_MARGIN = 14


def draw_minimap(camera_x, camera_y):
    """전체 맵 축약: 방·복도·화면 영역·생존자 위치(역할 색 없음). 우하단 오버레이."""
    mw = MINIMAP_MAX_W
    mh = int(round(MINIMAP_MAX_W * MAP_HEIGHT / MAP_WIDTH))
    if mh > MINIMAP_MAX_H:
        mh = MINIMAP_MAX_H
        mw = int(round(MINIMAP_MAX_H * MAP_WIDTH / MAP_HEIGHT))

    pad = 3
    surf_w, surf_h = mw + pad * 2, mh + pad * 2
    surf = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
    surf.fill((10, 12, 22, 236))
    inner = pygame.Rect(pad, pad, mw, mh)

    def w2m(wx, wy):
        return (pad + int(wx * mw / MAP_WIDTH), pad + int(wy * mh / MAP_HEIGHT))

    for cz in corridor_zones:
        x0, y0 = w2m(cz.x, cz.y)
        x1, y1 = w2m(cz.x + cz.w, cz.y + cz.h)
        rw, rh = max(1, x1 - x0), max(1, y1 - y0)
        pygame.draw.rect(surf, (38, 46, 60), (x0, y0, rw, rh))

    for zone in room_zones:
        rz = zone["rect"]
        x0, y0 = w2m(rz.x, rz.y)
        x1, y1 = w2m(rz.x + rz.w, rz.y + rz.h)
        rw, rh = max(2, x1 - x0), max(2, y1 - y0)
        c = zone["color"]
        dim = (min(255, c[0] // 2 + 25), min(255, c[1] // 2 + 25), min(255, c[2] // 2 + 30))
        pygame.draw.rect(surf, dim, (x0, y0, rw, rh))
        pygame.draw.rect(surf, (85, 95, 115), (x0, y0, rw, rh), 1)

    vx, vy = w2m(camera_x, camera_y)
    vw = max(2, int(SCREEN_WIDTH * mw / MAP_WIDTH))
    vh = max(2, int(SCREEN_HEIGHT * mh / MAP_HEIGHT))
    pygame.draw.rect(surf, (255, 230, 120), (vx, vy, vw, vh), 2)

    for p in [player] + AIs:
        if not p.alive and not (p is player and p.ghost):
            continue
        if p is not player and p.ghost:
            continue
        cx = p.x + p.width / 2
        cy = p.y + p.height / 2
        mx, my = w2m(cx, cy)
        if not inner.collidepoint(mx, my):
            continue
        if p is player:
            pygame.draw.circle(surf, (255, 220, 90), (mx, my), 4)
            pygame.draw.circle(surf, (40, 30, 10), (mx, my), 4, 1)
        else:
            pygame.draw.circle(surf, (200, 210, 230), (mx, my), 2)

    pygame.draw.rect(surf, (130, 150, 180), surf.get_rect(), 2)
    title = nick_font.render("M: Map", True, (200, 210, 230))
    surf.blit(title, (pad + 4, pad + 4))

    dest_x = SCREEN_WIDTH - surf_w - MINIMAP_SCREEN_MARGIN
    dest_y = SCREEN_HEIGHT - surf_h - MINIMAP_SCREEN_MARGIN - 36
    screen.blit(surf, (dest_x, dest_y))


# ================= 게임 루프 =================
game_started = False
round_session_start_ms = None
menu_page = "main"
spectate_doctor_mode = False
spectate_follow_index = 0  # 관전 시 get_spectate_follow_chain() 안에서의 대상 인덱스
# 벽과 겹치지 않는 안전한 위치로 플레이어와 AI 재배치
player.x, player.y = find_safe_position()
for ai in AIs:
    ai.x, ai.y = find_safe_position()

# 타스크 위치 안전하게 재설정
for task in tasks:
    task.x, task.y = find_safe_position()

while True:
    screen.fill(GRAY)
    now_ms = pygame.time.get_ticks()
    round_playing = (
        game_started
        and round_session_start_ms is not None
        and now_ms - round_session_start_ms >= ROLE_REVEAL_MS
    )

    if game_started:
        camera_x, camera_y = get_camera_pos()
        draw_focus = get_draw_focus()
    else:
        camera_x, camera_y = MAP_WIDTH//2 - SCREEN_WIDTH//2, MAP_HEIGHT//2 - SCREEN_HEIGHT//2
        draw_focus = player
    
    for event in pygame.event.get():
        if event.type==pygame.QUIT: pygame.quit(); sys.exit()
        if event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE:
                if not game_started and menu_page == "howto":
                    menu_page = "main"
                elif game_started:
                    reset_match_state()
                    game_started = False
                    round_session_start_ms = None
                    menu_page = "main"
                else:
                    pygame.quit(); sys.exit()
            if not game_started:
                if menu_page == "main":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        game_started = True
                        round_session_start_ms = pygame.time.get_ticks()
                    elif event.key == pygame.K_h:
                        menu_page = "howto"
                elif menu_page == "howto" and event.key in (pygame.K_BACKSPACE, pygame.K_h):
                    menu_page = "main"
                continue
            if not round_playing:
                continue
            if event.key == pygame.K_k and game_started and player.ghost:
                trigger_ghost_prank(player, announce=True)
            if event.key == pygame.K_q and game_started and player.alive and player.role == "imposter":
                start_fake_task(player)
            if game_started and can_use_sabotage(player) and sabotage_cooldown <= 0:
                if event.key == pygame.K_1 and start_random_event("blackout", player):
                    sabotage_cooldown = 60 * 25
                elif event.key == pygame.K_2 and start_random_event("oxygen", player):
                    sabotage_cooldown = 60 * 25
                elif event.key == pygame.K_3 and locked_room_timer <= 0:
                    sabotage_select_mode = "locked"
                    set_event_notice("Select a room to lock.")
            if event.key==pygame.K_e and game_started and player.stun_timer <= 0:  # E 키로 환기
                if player.role in ("imposter", "engineer") and player.alive:
                    if player_vent():
                        pass  # 환기 실행됨
            # Ghosts: no R/G. Ghost Doctor: F (revive) only
            if event.key == pygame.K_f and game_started and player.stun_timer <= 0:
                if player.ghost and player.role in ("doctor", "undertaker"):
                    revive_own_body(player)
                elif player.alive:
                    revive_body_by(player)
                    if player.role == "undertaker":
                        revive_body_by_undertaker(player)
            if event.key == pygame.K_g and game_started and player.alive and player.stun_timer <= 0:
                cure_stun_by(player)
            if event.key == pygame.K_v and game_started and player_can_use_doctor_spectate():
                spectate_doctor_mode = not spectate_doctor_mode
                if spectate_doctor_mode:
                    spectate_follow_index = 0
            if (
                event.key == pygame.K_TAB
                and game_started
                and spectate_doctor_mode
                and player.ghost
                and player.role in SPECTATE_DOCTOR_ROLES
            ):
                cycle_spectate_follow_target()
            if event.key == pygame.K_b and player.alive and player.stun_timer <= 0:
                if player_in_security_room():
                    security_camera_mode = not security_camera_mode
                else:
                    security_camera_mode = False
            if security_camera_feed_active():
                if event.key in (pygame.K_LEFTBRACKET, pygame.K_COMMA):
                    security_camera_view_index = (security_camera_view_index - 1) % len(room_zones)
                elif event.key in (pygame.K_RIGHTBRACKET, pygame.K_PERIOD):
                    security_camera_view_index = (security_camera_view_index + 1) % len(room_zones)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not game_started:
            if menu_page == "main":
                buttons = get_main_menu_buttons()
                if buttons["start"].collidepoint(event.pos):
                    game_started = True
                    round_session_start_ms = pygame.time.get_ticks()
                elif buttons["howto"].collidepoint(event.pos):
                    menu_page = "howto"
            elif menu_page == "howto" and get_how_to_back_button().collidepoint(event.pos):
                menu_page = "main"
            continue
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and game_started
            and round_playing
            and not game_over
        ):
            mx, my = event.pos
            world_x = mx + camera_x
            world_y = my + camera_y
            if sabotage_select_mode and can_use_sabotage(player) and sabotage_cooldown <= 0:
                selected_room = get_room_index_at(world_x, world_y)
                if start_random_event(sabotage_select_mode, player, selected_room):
                    sabotage_cooldown = 60 * 25
                    sabotage_select_mode = None
                continue
            # 클릭된 엔티티 찾기 (자기 자신 제외)
            clicked = None
            for ent in [player] + AIs:
                if ent is player:
                    continue
                if ent.alive and ent.rect().collidepoint(world_x, world_y):
                    clicked = ent
                    break
            if clicked and player.alive:
                transferred = False
                for bomb in active_bombs:
                    if bomb["holder"] is player and clicked.alive:
                        transfer_bomb(bomb, clicked)
                        transferred = True
                        break
                if transferred:
                    continue
            if player.alive and player.role == "mad_scientist":
                player_mad_scientist_gas_deploy(world_x, world_y)
                continue
            if clicked and player.alive:
                if player.role == "sheriff":
                    player_sheriff_shoot(clicked)
                    continue
                if player.role == "bomber":
                    attach_bomb(player, clicked)
                    continue

    if not game_started:
        if menu_page == "howto":
            draw_how_to_page()
        else:
            draw_main_menu()
        pygame.display.flip()
        clock.tick(60)
        continue

    if not game_over and game_started and round_playing:
        if security_camera_mode and player.alive and not player_in_security_room():
            security_camera_mode = False
        # 스턴 감소
        if player.stun_timer > 0:
            player.stun_timer -= 1
        
        if player.stun_timer <= 0 or player.ghost:
            keys=pygame.key.get_pressed()
            player_speed = MOVE_SPEED
            if dance_boost_timer > 0:
                player_speed = 6.5
            can_dance = (player.alive or player.ghost) and not player.venting
            spinning_in_place = keys[pygame.K_c] and can_dance
            grooving_in_place = keys[pygame.K_x] and can_dance
            bouncing_in_place = keys[pygame.K_z] and can_dance
            dancing_in_place = spinning_in_place or grooving_in_place or bouncing_in_place
            shift_pressed = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
            is_moving_input = keys[pygame.K_a] or keys[pygame.K_d] or keys[pygame.K_w] or keys[pygame.K_s]
            can_shift = shift_cooldown_frames <= 0 and shift_energy_frames > 0
            using_shift = shift_pressed and is_moving_input and can_shift
            if using_shift:
                player_speed = MOVE_SPEED * SHIFT_SPEED_MULTIPLIER
            dx=dy=0
            if keys[pygame.K_a]: dx=-player_speed
            if keys[pygame.K_d]: dx=player_speed
            if keys[pygame.K_w]: dy=-player_speed
            if keys[pygame.K_s]: dy=player_speed
            if dancing_in_place:
                phase = pygame.time.get_ticks() / 160
                player.dance_offset_x = 0
                player.dance_offset_y = 0
            if spinning_in_place:
                player.spin_angle = (player.spin_angle + 6) % 360
                player.dance_note_style = 0
            elif grooving_in_place:
                player.spin_angle = math.sin(phase) * 16
                player.dance_offset_x = math.sin(phase * 1.4) * 6
                player.dance_note_style = 1
            elif bouncing_in_place:
                player.spin_angle = math.sin(phase * 2) * 7
                player.dance_offset_y = -abs(math.sin(phase * 1.8)) * 9
                player.dance_note_style = 2
            else:
                player.spin_angle = 0
                player.dance_offset_x = 0
                player.dance_offset_y = 0
                player.dance_note_style = 0

            if (
                dancing_in_place
                and dance_challenge_timer > 0
                and dance_challenge_room is not None
                and get_room_index_at(player.x, player.y) == dance_challenge_room
            ):
                dance_boost_timer = 60 * 6
                dance_challenge_timer = 0
                set_event_notice("Dance challenge cleared! Speed boost.")

            player.flee_timer = 0
            player.flee_target = None
            
            apply_move_with_escape_priority(player, dx, dy, player_speed)

            # Shift stamina/cooldown 처리
            if using_shift:
                shift_energy_frames = max(0, shift_energy_frames - 1)
                if shift_energy_frames == 0:
                    shift_cooldown_frames = SHIFT_COOLDOWN_FRAMES
            elif shift_cooldown_frames <= 0:
                # 쿨다운이 아닐 때만 천천히 회복 (연타 방지 + 체감 개선)
                shift_energy_frames = min(SHIFT_MAX_DURATION_FRAMES, shift_energy_frames + 1)

            # 플레이어 미션
            for t in tasks:
                if not t.completed and math.hypot(player.x-t.x,player.y-t.y)<task_range and player.role in CREW_ROLES and player.alive:
                    t.completed=True
                    player.stats_tasks_completed += 1

            # 플레이어 공격 (임포) / 스턴 (트롤)
            if player.alive:
                player_attack()
                player_troll_stun()
        
        # 플레이어가 누군가를 죽인 후 감지 (체계적)
        if len(bodies) > last_body_count:
            last_body_count = len(bodies)
            # 새로 추가된 시체 위치
            new_body = bodies[-1]
            # 근처 각 AI가 플레이어를 의심하게 함
            for ai in AIs:
                if ai.alive and ai.role in CREW_ROLES and player.alive:
                    dist_to_body = math.hypot(ai.x - new_body.x, ai.y - new_body.y)
                    dist_to_player = math.hypot(ai.x - player.x, ai.y - player.y)
                    # 시체가 300 근처이고 플레이어도 가까우면 의심
                    body_sense = 480 if suspicion_event_timer > 0 else 300
                    player_sense = 620 if suspicion_event_timer > 0 else 400
                    if dist_to_body < body_sense and dist_to_player < player_sense:
                        ai.suspect_player = player  # 플레이어를 의심
        
        # 플레이어 상태 업데이트
        if player.fake_task_timer > 0:
            player.fake_task_timer -= 1
        if player.venting:
            player.vent_time -= 1
            if player.vent_time <= 0:
                player.venting = False

        update_crew_gather_event()
        update_random_events()

        # AI 이동
        for ai in AIs:
            ai_move(ai)
        
        # 쿨다운 감소
        if imposter_kill_cooldown > 0:
            imposter_kill_cooldown -= 1
        if player_kill_cooldown > 0:
            player_kill_cooldown -= 1
        if troll_stun_cooldown > 0:
            troll_stun_cooldown -= 1
        for ent in [player] + AIs:
            if ent.gas_kill_cooldown > 0:
                ent.gas_kill_cooldown -= 1
        if shift_cooldown_frames > 0:
            shift_cooldown_frames -= 1
            if shift_cooldown_frames == 0:
                shift_energy_frames = SHIFT_MAX_DURATION_FRAMES

        update_bombs()

    if game_started:
        update_vent_proximity_audio(round_playing, game_over, game_started)

    if round_playing and check_win():
        pass

    if game_started:
        update_bomb_explosion_fx()
        update_gas_cloud_fx()
        update_imposter_slice_fx()

    # =============== 화면 그리기 ===============
    for z in corridor_zones:
        sx = z.x - camera_x
        sy = z.y - camera_y
        if sx < SCREEN_WIDTH and sy < SCREEN_HEIGHT and sx + z.w > 0 and sy + z.h > 0:
            pygame.draw.rect(screen, CORRIDOR_FLOOR, (sx, sy, z.w, z.h))
            pygame.draw.rect(screen, ZONE_BORDER, (sx, sy, z.w, z.h), 2)
            # 우주선 복도 느낌의 중앙 네온 라인
            if z.w > z.h:
                line_y = sy + z.h // 2
                start_x = int(sx + 8)
                end_x = int(sx + z.w - 8)
                for lx in range(start_x, end_x, 28):
                    pygame.draw.line(screen, NEON_LINE, (lx, int(line_y)), (min(lx + 14, end_x), int(line_y)), 2)
            else:
                line_x = sx + z.w // 2
                start_y = int(sy + 8)
                end_y = int(sy + z.h - 8)
                for ly in range(start_y, end_y, 28):
                    pygame.draw.line(screen, NEON_LINE, (int(line_x), ly), (int(line_x), min(ly + 14, end_y)), 2)

    for zone in room_zones:
        rz = zone["rect"]
        sx = rz.x - camera_x
        sy = rz.y - camera_y
        if sx < SCREEN_WIDTH and sy < SCREEN_HEIGHT and sx + rz.w > 0 and sy + rz.h > 0:
            pygame.draw.rect(screen, zone["color"], (sx, sy, rz.w, rz.h))
            pygame.draw.rect(screen, ZONE_BORDER, (sx, sy, rz.w, rz.h), 3)
            # 방 모서리 패널 포인트
            pygame.draw.circle(screen, ROOM_ACCENT, (sx + 16, sy + 16), 6)
            pygame.draw.circle(screen, ROOM_ACCENT, (sx + rz.w - 16, sy + 16), 6)
            pygame.draw.circle(screen, ROOM_ACCENT, (sx + 16, sy + rz.h - 16), 6)
            pygame.draw.circle(screen, ROOM_ACCENT, (sx + rz.w - 16, sy + rz.h - 16), 6)

            # 방 내부 소품 느낌(테이블/콘솔)
            if zone["name"] in ("Cafeteria", "Office", "Vault"):
                tw, th = min(260, rz.w // 3), min(120, rz.h // 4)
                tx = sx + rz.w // 2 - tw // 2
                ty = sy + rz.h // 2 - th // 2
                pygame.draw.rect(screen, (74, 92, 120), (tx, ty, tw, th), border_radius=12)
                pygame.draw.rect(screen, (140, 170, 210), (tx, ty, tw, th), 2, border_radius=12)
            elif zone["name"] in ("Electrical", "Security", "Admin", "Comms"):
                cw, ch = min(140, rz.w // 4), min(80, rz.h // 5)
                cx = sx + rz.w - cw - 24
                cy = sy + 24
                pygame.draw.rect(screen, (52, 70, 92), (cx, cy, cw, ch), border_radius=8)
                pygame.draw.rect(screen, NEON_LINE, (cx + 8, cy + 8, cw - 16, 10), border_radius=4)
                pygame.draw.rect(screen, (120, 220, 170), (cx + 8, cy + 24, cw - 26, 8), border_radius=4)
            label = nick_font.render(f"{zone['num']}. {zone['name']}", True, (190, 200, 220))
            screen.blit(label, (sx + 12, sy + 10))

    for w in walls:
        w.draw(camera_x, camera_y)
    
    for t in tasks:
        t.draw(draw_focus, camera_x, camera_y)
    
    for b in bodies:
        b.draw(draw_focus, camera_x, camera_y)
    
    for vent in vents:
        vent.draw(camera_x, camera_y)
    
    hide_imposters_in_spectate = doctor_spectate_overlay_active()
    for p in [player]+AIs:
        if hide_imposters_in_spectate and p.role == "imposter":
            continue
        if p.alive or p.ghost:
            p.draw(camera_x, camera_y)

    draw_crew_gather_music_notes(camera_x, camera_y)
    draw_player_dance_music_notes(camera_x, camera_y)
    draw_fake_task_effects(camera_x, camera_y)
    draw_random_event_effects(camera_x, camera_y)
    if game_started:
        draw_bomb_explosion_fx_world(camera_x, camera_y)
        draw_gas_cloud_fx_world(camera_x, camera_y)
        draw_imposter_slice_fx(camera_x, camera_y)
    draw_sabotage_room_selection(camera_x, camera_y)
    if round_playing:
        draw_wall_blocked_vision(draw_focus, camera_x, camera_y)

    if round_playing and security_camera_feed_active() and not doctor_spectate_overlay_active():
        z = room_zones[security_camera_view_index]
        alert = f"   alert {security_camera_timer // 60}s" if security_camera_timer > 0 else ""
        cam_txt = font.render(
            f"SECURITY CAM  #{z['num']} {z['name']}   [ ] or , .   B: exit{alert}",
            True,
            (180, 235, 255),
        )
        cr = cam_txt.get_rect(center=(SCREEN_WIDTH // 2, 38))
        pygame.draw.rect(screen, (12, 20, 34), cr.inflate(28, 10))
        pygame.draw.rect(screen, (70, 120, 160), cr.inflate(28, 10), 2)
        screen.blit(cam_txt, cr)

    # Doctor spectate: role labels; "Me" on your corpse
    if doctor_spectate_overlay_active() and round_playing:
        subj = get_spectate_camera_target()
        kind = spectate_target_kind_label(subj)
        banner = font.render(f"[ Doctor spectate · focus: {kind} ]  Tab: next  V: off", True, DOCTOR_COLOR)
        screen.blit(banner, (SCREEN_WIDTH // 2 - banner.get_width() // 2, 6))
        nick_h = nick_font.get_height() + 2
        for p in [player] + AIs:
            if p.role not in SPECTATE_ROLE_LABELS:
                continue
            if not (p.alive or p.ghost):
                continue
            label, lc = SPECTATE_ROLE_LABELS[p.role]
            sx = int(p.x - camera_x + p.width // 2)
            sy = int(p.y - camera_y)
            lab = font.render(label, True, lc)
            screen.blit(lab, (sx - lab.get_width() // 2, sy - lab.get_height() - nick_h - 4))
        my_corpse = next((b for b in bodies if b.dead_player is player), None)
        if my_corpse:
            mtx = int(my_corpse.x - camera_x + my_corpse.width // 2)
            mty = int(my_corpse.y - camera_y)
            mlab = font.render("Me", True, YELLOW)
            screen.blit(mlab, (mtx - mlab.get_width() // 2, mty - mlab.get_height() - 2))
    
    # 임포스터 / 미친 과학자: 킬·가스 사거리 시각화
    if game_started and round_playing and player.alive and player.role == "imposter":
        player_screen_x = player.x - camera_x + player.width//2
        player_screen_y = player.y - camera_y + player.height//2
        pygame.draw.circle(screen, (255,0,0,100), (player_screen_x, player_screen_y), imposter_range, 1)
    if game_started and round_playing and player.alive and player.role == "mad_scientist":
        player_screen_x = player.x - camera_x + player.width // 2
        player_screen_y = player.y - camera_y + player.height // 2
        pygame.draw.circle(screen, (60, 220, 120, 90), (player_screen_x, player_screen_y), MAD_SCIENTIST_GAS_MAX_RANGE, 1)
    
    # 시야 범위 시각화 (살아 있을 때 / 닥터 관전 중에는 닥터 시야)
    if game_started and round_playing and player.alive:
        pygame.draw.circle(screen, (50, 50, 100), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), get_effective_vision_radius(), 1)
    elif (
        game_started
        and round_playing
        and spectate_doctor_mode
        and player.ghost
        and player.role in SPECTATE_DOCTOR_ROLES
        and get_spectate_camera_target()
    ):
        pygame.draw.circle(screen, (50, 80, 120), (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), get_effective_vision_radius(), 1)

    # =============== HUD 표시 ===============
    if game_started and round_playing:
        LINE_H = 30
        y = 10
        total_count = len([player] + AIs)
        alive_count = sum(1 for p in [player] + AIs if p.alive)
        dead_count = total_count - alive_count
        crew_count = sum(1 for p in [player]+AIs if p.alive and p.role == "crew")
        team1_count = sum(1 for p in [player]+AIs if p.alive and p.role in CREW_ROLES)
        impostor_count = sum(1 for p in [player]+AIs if p.alive and p.role=="imposter")
        troll_count = sum(1 for p in [player]+AIs if p.alive and p.role=="troll")
        bomber_count = sum(1 for p in [player]+AIs if p.alive and p.role=="bomber")
        mad_sci_count = sum(1 for p in [player]+AIs if p.alive and p.role=="mad_scientist")
        engineer_count = sum(1 for p in [player]+AIs if p.alive and p.role=="engineer")
        undertaker_count = sum(1 for p in [player]+AIs if p.alive and p.role=="undertaker")
        shooter_count = sum(1 for p in [player]+AIs if p.alive and p.role=="sheriff")
        doctor = next((p for p in [player]+AIs if p.role=="doctor"), None)
        guard = next((p for p in [player]+AIs if p.role=="guard"), None)
        engineer = next((p for p in [player]+AIs if p.role=="engineer"), None)
        undertaker = next((p for p in [player]+AIs if p.role=="undertaker"), None)
        dr_alive = 1 if doctor and doctor.alive else 0
        guard_alive = 1 if guard and guard.alive else 0
        engineer_alive = 1 if engineer and engineer.alive else 0
        undertaker_alive = 1 if undertaker and undertaker.alive else 0
        rev_status = "Used" if doctor and getattr(doctor, "revive_used", False) else ("OK" if doctor else "-")

        if crew_gather_notice_timer > 0 and crew_gather_notice_text:
            notice = font.render(crew_gather_notice_text, True, YELLOW)
            notice_rect = notice.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 170))
            pygame.draw.rect(screen, BLACK, notice_rect.inflate(44, 18))
            pygame.draw.rect(screen, YELLOW, notice_rect.inflate(44, 18), 3)
            screen.blit(notice, notice_rect)
        if event_notice_timer > 0 and event_notice_text:
            notice_color = RED if event_notice_text.startswith("Sabotage:") else (140, 220, 255)
            notice = font.render(event_notice_text, True, notice_color)
            notice_rect = notice.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 130))
            pygame.draw.rect(screen, BLACK, notice_rect.inflate(44, 18))
            pygame.draw.rect(screen, notice_color, notice_rect.inflate(44, 18), 3)
            screen.blit(notice, notice_rect)
        if sabotage_select_mode:
            mode_name = "Door lock"
            notice = font.render(f"{mode_name}: click Room 1-40", True, ORANGE)
            notice_rect = notice.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 90))
            pygame.draw.rect(screen, BLACK, notice_rect.inflate(44, 18))
            pygame.draw.rect(screen, ORANGE, notice_rect.inflate(44, 18), 3)
            screen.blit(notice, notice_rect)
        
        t1 = font.render(
            f"Nick: {player.nickname}  |  Role: {player.role.upper()}  |  Total: {total_count}  |  Alive: {alive_count}  |  Dead: {dead_count}",
            True,
            WHITE,
        )
        screen.blit(t1, (10, y)); y += LINE_H
        t2 = font.render(f"Crew: {crew_count}  Doctor: {dr_alive}  Guard: {guard_alive}  Engineer: {engineer_count}  Undertaker: {undertaker_count}  Shooter: {shooter_count}", True, WHITE)
        screen.blit(t2, (10, y)); y += LINE_H
        t2b = font.render(
            f"Troll: {troll_count}  Bomber: {bomber_count}  MadSci: {mad_sci_count}  Imposter: {impostor_count}",
            True,
            WHITE,
        )
        screen.blit(t2b, (10, y)); y += LINE_H
        t2c = font.render(
            "Teams: T1(Crew…)  T2(Troll)  T3(Bomber)  T4(Imposter)  T5(Mad Scientist)",
            True,
            (190, 210, 230),
        )
        screen.blit(t2c, (10, y)); y += LINE_H
        t3 = font.render(f"Tasks: {sum(1 for t in tasks if t.completed)}/{len(tasks)}  |  Dead: {dead_count}", True, WHITE)
        screen.blit(t3, (10, y)); y += LINE_H
        t_stats = font.render(
            f"This round: My Tasks {player.stats_tasks_completed}  Kills {player.stats_kills}  Stuns {player.stats_stuns}  Revives {player.stats_revives}",
            True,
            (210, 220, 230),
        )
        screen.blit(t_stats, (10, y)); y += LINE_H
        if shift_cooldown_frames > 0:
            shift_text = f"Sprint: COOLDOWN {shift_cooldown_frames/60:.1f}s"
            shift_color = (255, 170, 120)
        else:
            shift_text = f"Sprint: {shift_energy_frames/60:.1f}s / 5.0s"
            shift_color = (140, 220, 255)
        t_shift = font.render(shift_text, True, shift_color)
        screen.blit(t_shift, (10, y)); y += LINE_H
        event_lines = get_event_status_lines()
        if event_lines:
            t_event = font.render("Events: " + "  |  ".join(event_lines[:3]), True, (160, 220, 255))
            screen.blit(t_event, (10, y)); y += LINE_H
        if player.alive:
            t_cam_hud = nick_font.render(
                "Security cams: Security room — B: monitor on/off  |  [ or , : prev feed  |  ] or . : next  |  leave room / vent: closes",
                True,
                (150, 218, 255),
            )
            screen.blit(t_cam_hud, (10, y))
            y += 26
        if player_can_use_doctor_spectate():
            ts = font.render(
                f"Doctor spectate: {'ON' if spectate_doctor_mode else 'OFF'} (V)  Camera: Tab (Doctor>Troll>Guard>Crew)",
                True,
                DOCTOR_COLOR,
            )
            screen.blit(ts, (10, y)); y += LINE_H
        
        if player.alive and player.role == "imposter":
            t4 = font.render(f"Kills: {player_kill_count}  Cooldown: {max(0, player_kill_cooldown//10)}s", True, ORANGE)
            screen.blit(t4, (10, y)); y += LINE_H
            t4fake = font.render("Q: fake task near a task", True, ORANGE)
            screen.blit(t4fake, (10, y)); y += LINE_H
        if can_use_sabotage(player):
            sabotage_text = (
                f"Sabotage: 1 Blackout  2 Oxygen  3 Lock  |  CD {sabotage_cooldown / 60:.1f}s"
                if sabotage_cooldown > 0
                else "Sabotage: 1 Blackout  2 Oxygen(10 panels)  3 Lock(select room)"
            )
            t4s = font.render(sabotage_text, True, ORANGE)
            screen.blit(t4s, (10, y)); y += LINE_H
        if player.alive and player.role == "troll":
            t4 = font.render("Stun crew! Win when Imp=Crew", True, TROLL_COLOR)
            screen.blit(t4, (10, y)); y += LINE_H
        if player.role == "doctor":
            if player.alive:
                t4 = font.render(f"F: Revive  G: Cure Stun  Status: {rev_status}", True, DOCTOR_COLOR)
            else:
                t4 = font.render(
                    f"Ghost: F self-revive at YOUR body only  |  No R/G  |  Revive: {rev_status}",
                    True,
                    DOCTOR_COLOR,
                )
            screen.blit(t4, (10, y)); y += LINE_H
        if player.alive and player.role == "guard":
            t4 = font.render("Imposter 30s stun if kills you", True, GUARD_COLOR)
            screen.blit(t4, (10, y)); y += LINE_H
        if player.role == "engineer":
            t4 = font.render("Engineer: Crew team  |  E: Vent", True, ENGINEER_COLOR)
            screen.blit(t4, (10, y)); y += LINE_H
        if player.role == "undertaker":
            t4 = font.render(f"Undertaker: F revive nearest corpse (1x)  |  Used: {player.undertaker_revive_used}", True, UNDERTAKER_COLOR)
            screen.blit(t4, (10, y)); y += LINE_H
            near_body = None
            near_dist = 1e9
            for b in bodies:
                d = math.hypot(player.x - b.x, player.y - b.y)
                if d < near_dist:
                    near_dist = d
                    near_body = b
            if near_body is not None and near_body.dead_player is not None and near_dist < 220:
                corpse_role = near_body.dead_player.role.upper()
                t4b = font.render(f"Corpse Role Seen: {corpse_role}", True, UNDERTAKER_COLOR)
                screen.blit(t4b, (10, y)); y += LINE_H
                # 화면 상단 중앙에 크게 표시 (확실한 식별)
                corpse_banner = font.render(f"CORPSE ROLE: {corpse_role}", True, UNDERTAKER_COLOR)
                corpse_rect = corpse_banner.get_rect(center=(SCREEN_WIDTH // 2, 44))
                pygame.draw.rect(screen, BLACK, corpse_rect.inflate(24, 10))
                screen.blit(corpse_banner, corpse_rect)
        if player.role == "sheriff":
            if get_bomb_held_by(player) is not None:
                t4 = font.render(
                    f"Shooter: BOMB on you — LClick player to PASS bomb  |  Bullets: {player.sheriff_bullets}",
                    True,
                    BOMBER_COLOR,
                )
            else:
                t4 = font.render(f"Shooter: LClick shoot target  |  Bullets: {player.sheriff_bullets}", True, GUARD_COLOR)
            screen.blit(t4, (10, y)); y += LINE_H
        if player.role == "bomber":
            t4 = font.render(f"Bomber: LClick plant/pass bomb  |  Bombs left: {player.bombs_remaining}", True, BOMBER_COLOR)
            screen.blit(t4, (10, y)); y += LINE_H
            if bomb_kill_notice_timer > 0 and bomb_kill_notice_text:
                t4b = font.render(bomb_kill_notice_text, True, BOMBER_COLOR)
                screen.blit(t4b, (10, y)); y += LINE_H
        if player.role == "mad_scientist":
            gcd = max(0, player.gas_kill_cooldown)
            t4 = font.render(
                f"Mad Scientist (T5): LClick aim → poison gas cloud (range {MAD_SCIENTIST_GAS_MAX_RANGE}px, splash {MAD_SCIENTIST_GAS_CLOUD_RADIUS})  |  CD: {gcd / 60:.1f}s / 40.0s",
                True,
                MAD_SCIENTIST_COLOR,
            )
            screen.blit(t4, (10, y)); y += LINE_H
        if player.venting:
            vent_text = font.render("VENTING...", True, CYAN)
            vent_rect = vent_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2-100))
            screen.blit(vent_text, vent_rect)
        if player.stun_timer > 0:
            stun_sec = player.stun_timer // 60
            stun_text = font.render(f"STUNNED! {stun_sec}s", True, TROLL_COLOR)
            stun_rect = stun_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2-80))
            pygame.draw.rect(screen, BLACK, stun_rect.inflate(20, 10))
            screen.blit(stun_text, stun_rect)

        # 오른쪽 상단 전용: 의사/장의사 부활권 상태
        doctor_used = bool(doctor and getattr(doctor, "revive_used", False))
        undertaker_used = bool(undertaker and getattr(undertaker, "undertaker_revive_used", False))
        dr_text = font.render(f"Doctor Revive: {'USED' if doctor_used else 'READY'}", True, (255, 130, 130) if doctor_used else DOCTOR_COLOR)
        ut_text = font.render(f"Undertaker Revive: {'USED' if undertaker_used else 'READY'}", True, (255, 130, 130) if undertaker_used else UNDERTAKER_COLOR)
        max_w = max(dr_text.get_width(), ut_text.get_width())
        panel_w = max_w + 24
        panel_h = dr_text.get_height() + ut_text.get_height() + 18
        panel_x = SCREEN_WIDTH - panel_w - 12
        panel_y = 10
        pygame.draw.rect(screen, (15, 15, 20), (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(screen, (90, 90, 110), (panel_x, panel_y, panel_w, panel_h), 2)
        screen.blit(dr_text, (panel_x + 12, panel_y + 6))
        screen.blit(ut_text, (panel_x + 12, panel_y + 8 + dr_text.get_height()))
        
        if player_can_use_doctor_spectate():
            ctrl_text = font.render(
                "Ghost: WASD  |  V: spectate  |  Tab: camera  |  Hold M: map  |  ESC: menu",
                True,
                (160, 160, 200),
            )
        elif player.ghost and player.role == "doctor":
            ctrl_text = font.render(
                "Ghost (Doctor): WASD  |  F: self-revive  |  Hold M: map  |  ESC: menu",
                True,
                DOCTOR_COLOR,
            )
        elif player.ghost:
            ctrl_text = font.render(
                "Ghost: WASD  |  C/X/Z: Dance  |  K: prank  |  Hold M: map  |  ESC: menu",
                True,
                (140, 140, 160),
            )
        else:
            if player.role == "mad_scientist":
                ctrl_text = font.render(
                    "WASD  |  Poison: LClick where to spray gas (green ring = max range)  |  M map  |  C/X/Z  |  E/F/G  |  ESC",
                    True,
                    (100, 100, 100),
                )
            else:
                ctrl_text = font.render(
                    "WASD  |  Security: B & [ ] or , . (see HUD line)  |  M map  |  C/X/Z  |  E/F/G  |  ESC",
                    True,
                    (100, 100, 100),
                )
        screen.blit(ctrl_text, (10, SCREEN_HEIGHT - LINE_H - 5))

        # 플레이어 폭탄 경고 HUD
        player_bomb_timer = get_player_bomb_timer_frames()
        if player_bomb_timer is not None and player.alive:
            sec_left = player_bomb_timer / 60.0
            warning = font.render(f"!!! BOMB ON YOU: {sec_left:.1f}s  |  CLICK SOMEONE NOW !!!", True, (255, 70, 70))
            wr = warning.get_rect(center=(SCREEN_WIDTH // 2, 46))
            pygame.draw.rect(screen, BLACK, wr.inflate(22, 10))
            screen.blit(warning, wr)

        # 폭탄 타이머 표시 (화면 내 소지자만)
        for bomb in active_bombs:
            holder = bomb["holder"]
            if holder is None or not holder.alive:
                continue
            sx = holder.x - camera_x + holder.width // 2
            sy = holder.y - camera_y - 18
            if -50 < sx < SCREEN_WIDTH + 50 and -50 < sy < SCREEN_HEIGHT + 50:
                sec = bomb["timer"] / 60.0
                bt = nick_font.render(f"BOMB {sec:.1f}s", True, (255, 120, 120))
                screen.blit(bt, (sx - bt.get_width() // 2, sy))

        if not game_over and pygame.key.get_pressed()[pygame.K_m]:
            draw_minimap(camera_x, camera_y)

    if game_over:
        win_text = font.render(winner, True, YELLOW)
        win_rect = win_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
        pygame.draw.rect(screen, BLACK, win_rect.inflate(40, 40))
        screen.blit(win_text, win_rect)
        
        restart_text = font.render("ESC: Main menu", True, WHITE)
        screen.blit(restart_text, (SCREEN_WIDTH//2-100, SCREEN_HEIGHT//2+50))

    if game_started and not round_playing and round_session_start_ms is not None and not game_over:
        draw_role_reveal_screen(now_ms)

    if game_started and bomb_explosion_fx:
        draw_bomb_explosion_fx_overlay(camera_x, camera_y)

    pygame.display.flip()
    clock.tick(60)