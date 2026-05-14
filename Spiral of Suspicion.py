<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
  <title>Spiral of Suspicion</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: #080b14;
      font-family: "Segoe UI", "Malgun Gothic", Arial, sans-serif;
      color: white;
    }
    canvas {
      display: block;
      width: 100vw;
      height: 100vh;
      background: #323232;
      image-rendering: auto;
    }
    #hint {
      position: fixed;
      right: 14px;
      bottom: 10px;
      color: rgba(220, 230, 255, 0.55);
      font-size: 13px;
      pointer-events: none;
      text-shadow: 0 1px 3px #000;
    }
  </style>
</head>
<body>
  <canvas id="game"></canvas>
  <div id="hint">HTML5 Canvas port</div>

  <script>
  "use strict";

  const canvas = document.getElementById("game");
  const ctx = canvas.getContext("2d");

  let SCREEN_WIDTH = 1280;
  let SCREEN_HEIGHT = 720;
  const MAP_WIDTH = 7000;
  const MAP_HEIGHT = 5200;
  const FPS = 60;

  const COLORS = {
    white: "#ffffff",
    black: "#000000",
    red: "#ff4040",
    green: "#00ff66",
    blue: "#5088ff",
    yellow: "#ffe65a",
    gray: "#323232",
    darkGray: "#1e1e1e",
    purple: "#960096",
    cyan: "#00ffff",
    orange: "#ffa500",
    roomA: "#222a3a",
    roomB: "#2a2440",
    roomC: "#243834",
    corridor: "#3a3a42",
    border: "#5a5a6e",
    neon: "#78beff",
    accent: "#5a96d2",
    troll: "#80ff00",
    doctor: "#00c8c8",
    guard: "#6464ff",
    bomber: "#ff5a5a",
    mad: "#5adc82",
    engineer: "#78dcff",
    undertaker: "#b48cdc"
  };

  const ROLE_QUOTA = {
    crew: 9,
    imposter: 2,
    doctor: 1,
    guard: 1,
    engineer: 1,
    undertaker: 1,
    sheriff: 1,
    bomber: 1,
    troll: 1,
    mad_scientist: 1
  };

  const CREW_ROLES = ["crew", "doctor", "guard", "engineer", "undertaker", "sheriff"];
  const NEUTRAL_SIDE_ROLES = ["troll", "bomber", "mad_scientist"];
  const ROLE_DISPLAY_NAME = {
    crew: "Crew",
    doctor: "Doctor",
    guard: "Guard",
    engineer: "Engineer",
    undertaker: "Undertaker",
    sheriff: "Shooter",
    imposter: "Imposter",
    troll: "Troll",
    bomber: "Bomber",
    mad_scientist: "Mad Scientist"
  };

  const ROLE_HELP_LINES = [
    ["Crew", "Complete tasks and survive.", "Walk over yellow tasks."],
    ["Doctor", "Crew team. Revive one corpse.", "F near body."],
    ["Guard", "Crew team. Punishes killers.", "If killed by imposter, killer is stunned."],
    ["Engineer", "Crew team. Can use vents.", "E near cyan vent."],
    ["Undertaker", "Crew team. Revive one corpse and identify roles.", "F near body."],
    ["Shooter", "Crew team. Shoot imposters.", "Left click target. Wrong shot kills you too."],
    ["Imposter", "Eliminate crew and neutral roles.", "Auto-kill nearby. E vent. 1/2/3 sabotage."],
    ["Troll", "Stun crew and reach a special endgame.", "Auto-stun nearby crew."],
    ["Bomber", "Plant bombs and survive.", "Left click target to plant/pass bomb."],
    ["Mad Scientist", "Poison everyone else.", "Left click to throw gas cloud."]
  ];

  const NICKNAME_POOL = [
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
    "Zoe", "Robin", "Sunny", "River", "Cloud", "Stone", "Flame", "Storm"
  ];

  const MOVE_SPEED = 5.2;
  const SHIFT_SPEED_MULTIPLIER = 1.8;
  const SHIFT_MAX_FRAMES = 5 * FPS;
  const SHIFT_COOLDOWN_FRAMES = 30 * FPS;
  const IMPOSTER_RANGE = 52;
  const TASK_RANGE = 42;
  const STUN_DURATION = 30 * FPS;
  const BOMB_FUSE_FRAMES = 15 * FPS;
  const BOMB_PASS_RANGE = 72;
  const GAS_RANGE = 420;
  const GAS_RADIUS = 108;
  const GAS_COOLDOWN_FRAMES = 40 * FPS;
  const ROLE_REVEAL_MS = 3000;

  const keys = new Set();
  let mouse = { x: 0, y: 0 };

  let player;
  let AIs = [];
  let tasks = [];
  let vents = [];
  let walls = [];
  let roomZones = [];
  let corridorZones = [];
  let bodies = [];
  let activeBombs = [];
  let gasClouds = [];
  let explosions = [];
  let slashFx = [];
  let eventNotice = "";
  let eventNoticeTimer = 0;
  let gameStarted = false;
  let menuPage = "main";
  let roundStartTime = 0;
  let gameOver = false;
  let winner = "";
  let playerKillCooldown = 0;
  let imposterKillCooldown = 0;
  let trollStunCooldown = 0;
  let playerKillCount = 0;
  let shiftEnergy = SHIFT_MAX_FRAMES;
  let shiftCooldown = 0;
  let sabotageCooldown = 0;
  let sabotageSelectMode = null;
  let blackoutTimer = 0;
  let oxygenTimer = 0;
  let oxygenPoints = [];
  let oxygenFixed = [];
  let lockedRoomTimer = 0;
  let lockedRoom = null;
  let showMap = false;

  function resize() {
    const dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
    SCREEN_WIDTH = Math.floor(window.innerWidth);
    SCREEN_HEIGHT = Math.floor(window.innerHeight);
    canvas.width = Math.floor(SCREEN_WIDTH * dpr);
    canvas.height = Math.floor(SCREEN_HEIGHT * dpr);
    canvas.style.width = SCREEN_WIDTH + "px";
    canvas.style.height = SCREEN_HEIGHT + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  window.addEventListener("resize", resize);
  resize();

  function rand(min, max) {
    return Math.random() * (max - min) + min;
  }

  function randInt(min, max) {
    return Math.floor(rand(min, max + 1));
  }

  function shuffle(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = randInt(0, i);
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    return arr;
  }

  function dist(a, b, c, d) {
    return Math.hypot(a - c, b - d);
  }

  function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
  }

  function colorRandom() {
    return `rgb(${randInt(60, 255)}, ${randInt(60, 255)}, ${randInt(60, 255)})`;
  }

  function roleColor(role) {
    return {
      imposter: COLORS.red,
      troll: COLORS.troll,
      doctor: COLORS.doctor,
      guard: COLORS.guard,
      engineer: COLORS.engineer,
      undertaker: COLORS.undertaker,
      sheriff: COLORS.guard,
      bomber: COLORS.bomber,
      mad_scientist: COLORS.mad
    }[role] || COLORS.white;
  }

  function roleName(role) {
    return ROLE_DISPLAY_NAME[role] || role;
  }

  class Rect {
    constructor(x, y, w, h) {
      this.x = x;
      this.y = y;
      this.w = w;
      this.h = h;
    }
    contains(x, y) {
      return x >= this.x && x <= this.x + this.w && y >= this.y && y <= this.y + this.h;
    }
    intersects(other) {
      return this.x < other.x + other.w && this.x + this.w > other.x &&
             this.y < other.y + other.h && this.y + this.h > other.y;
    }
  }

  class Actor {
    constructor(x, y, color, role = "crew", avoidPlayer = false) {
      this.x = x;
      this.y = y;
      this.w = 25;
      this.h = 25;
      this.color = color;
      this.role = role;
      this.nickname = "";
      this.alive = true;
      this.ghost = false;
      this.targetTask = null;
      this.wanderTarget = null;
      this.venting = false;
      this.ventTime = 0;
      this.stunTimer = 0;
      this.reviveUsed = false;
      this.undertakerReviveUsed = false;
      this.sheriffBullets = 1;
      this.bombsRemaining = 7;
      this.lastBombTarget = null;
      this.gasCooldown = 0;
      this.avoidPlayer = avoidPlayer;
      this.suspectPlayer = null;
      this.fleeTimer = 0;
      this.fleeTarget = null;
      this.spinAngle = 0;
      this.danceOffsetX = 0;
      this.danceOffsetY = 0;
      this.statsTasks = 0;
      this.statsKills = 0;
      this.statsStuns = 0;
      this.statsRevives = 0;
    }
    rect(nx = this.x, ny = this.y) {
      return new Rect(nx, ny, this.w, this.h);
    }
    center() {
      return { x: this.x + this.w / 2, y: this.y + this.h / 2 };
    }
  }

  class Task {
    constructor(x, y, type = "normal") {
      this.x = x;
      this.y = y;
      this.w = 25;
      this.h = 25;
      this.type = type;
      this.completed = false;
    }
    rect() {
      return new Rect(this.x, this.y, this.w, this.h);
    }
  }

  class Body {
    constructor(x, y, deadPlayer) {
      this.x = x;
      this.y = y;
      this.w = 25;
      this.h = 25;
      this.deadPlayer = deadPlayer;
    }
  }

  class Vent {
    constructor(x, y, id) {
      this.x = x;
      this.y = y;
      this.id = id;
      this.radius = 15;
      this.available = [];
    }
  }

  function setNotice(text, frames = 240) {
    eventNotice = text;
    eventNoticeTimer = frames;
  }

  function buildMap() {
    walls = [
      new Rect(0, 0, MAP_WIDTH, 50),
      new Rect(0, 0, 50, MAP_HEIGHT),
      new Rect(0, MAP_HEIGHT - 50, MAP_WIDTH, 50),
      new Rect(MAP_WIDTH - 50, 0, 50, MAP_HEIGHT)
    ];
    roomZones = [];
    corridorZones = [];

    const WALL_THICK = 46;
    const ROOM_COLS = 8;
    const ROOM_ROWS = 5;
    const MARGIN_X = 70;
    const MARGIN_Y = 70;
    const DOOR_SIZE = 170;
    const cellW = Math.floor((MAP_WIDTH - MARGIN_X * 2) / ROOM_COLS);
    const cellH = Math.floor((MAP_HEIGHT - MARGIN_Y * 2) / ROOM_ROWS);
    const roomNames = [
      "Cafeteria", "Admin", "Weapons", "Navigation", "Shields",
      "MedBay", "Storage", "Electrical", "Reactor", "Security",
      "Upper Engine", "Lower Engine", "Comms", "O2", "Specimen",
      "Laboratory", "Office", "Vitals", "Armory", "Vault"
    ];
    while (roomNames.length < ROOM_COLS * ROOM_ROWS) {
      roomNames.push(`Sector ${roomNames.length + 1}`);
    }
    const palette = [COLORS.roomA, COLORS.roomB, COLORS.roomC];
    let idx = 0;
    for (let row = 0; row < ROOM_ROWS; row++) {
      for (let col = 0; col < ROOM_COLS; col++) {
        let rx = MARGIN_X + col * cellW + Math.floor(WALL_THICK / 2);
        let ry = MARGIN_Y + row * cellH + Math.floor(WALL_THICK / 2);
        const baseRw = cellW - WALL_THICK;
        const baseRh = cellH - WALL_THICK;
        const rw = Math.floor(baseRw * 0.92);
        const rh = Math.floor(baseRh * 0.92);
        rx += Math.floor((baseRw - rw) / 2);
        ry += Math.floor((baseRh - rh) / 2);
        roomZones.push({
          num: idx + 1,
          name: roomNames[idx],
          rect: new Rect(rx, ry, rw, rh),
          color: palette[(row + col) % palette.length]
        });
        idx++;
      }
    }

    for (let col = 1; col < ROOM_COLS; col++) {
      const x = MARGIN_X + col * cellW - Math.floor(WALL_THICK / 2);
      for (let row = 0; row < ROOM_ROWS; row++) {
        const y0 = MARGIN_Y + row * cellH;
        const y1 = y0 + cellH;
        const doorCenter = y0 + Math.floor(cellH / 2);
        const topH = Math.max(0, doorCenter - Math.floor(DOOR_SIZE / 2) - y0);
        const botY = doorCenter + Math.floor(DOOR_SIZE / 2);
        const botH = Math.max(0, y1 - botY);
        if (topH > 0) walls.push(new Rect(x, y0, WALL_THICK, topH));
        if (botH > 0) walls.push(new Rect(x, botY, WALL_THICK, botH));
      }
    }

    for (let row = 1; row < ROOM_ROWS; row++) {
      const y = MARGIN_Y + row * cellH - Math.floor(WALL_THICK / 2);
      for (let col = 0; col < ROOM_COLS; col++) {
        const x0 = MARGIN_X + col * cellW;
        const x1 = x0 + cellW;
        const doorCenter = x0 + Math.floor(cellW / 2);
        const leftW = Math.max(0, doorCenter - Math.floor(DOOR_SIZE / 2) - x0);
        const rightX = doorCenter + Math.floor(DOOR_SIZE / 2);
        const rightW = Math.max(0, x1 - rightX);
        if (leftW > 0) walls.push(new Rect(x0, y, leftW, WALL_THICK));
        if (rightW > 0) walls.push(new Rect(rightX, y, rightW, WALL_THICK));
      }
    }

    for (let col = 1; col < ROOM_COLS; col++) {
      const cx = MARGIN_X + col * cellW - WALL_THICK;
      corridorZones.push(new Rect(cx, MARGIN_Y, WALL_THICK * 2, ROOM_ROWS * cellH));
    }
    for (let row = 1; row < ROOM_ROWS; row++) {
      const cy = MARGIN_Y + row * cellH - WALL_THICK;
      corridorZones.push(new Rect(MARGIN_X, cy, ROOM_COLS * cellW, WALL_THICK * 2));
    }

    vents = [
      new Vent(600, 800, 0), new Vent(MAP_WIDTH - 600, 800, 1),
      new Vent(600, MAP_HEIGHT - 800, 2), new Vent(MAP_WIDTH - 600, MAP_HEIGHT - 800, 3),
      new Vent(MAP_WIDTH / 2, MAP_HEIGHT / 2, 4), new Vent(1500, 1200, 5),
      new Vent(MAP_WIDTH - 1500, 1200, 6), new Vent(1500, MAP_HEIGHT - 1500, 7),
      new Vent(MAP_WIDTH - 1500, MAP_HEIGHT - 1500, 8), new Vent(MAP_WIDTH / 4, MAP_HEIGHT / 3, 9),
      new Vent(MAP_WIDTH * 3 / 4, MAP_HEIGHT / 3, 10), new Vent(MAP_WIDTH / 4, MAP_HEIGHT * 2 / 3, 11),
      new Vent(MAP_WIDTH * 3 / 4, MAP_HEIGHT * 2 / 3, 12), new Vent(2600, MAP_HEIGHT / 2, 13),
      new Vent(MAP_WIDTH - 2600, MAP_HEIGHT / 2, 14)
    ];
    for (const v of vents) {
      v.available = vents.filter(other => other !== v);
    }
  }

  function collides(rect) {
    return walls.some(w => rect.intersects(w));
  }

  function findSafePosition() {
    for (let tries = 0; tries < 3000; tries++) {
      const x = randInt(90, MAP_WIDTH - 120);
      const y = randInt(90, MAP_HEIGHT - 120);
      const r = new Rect(x, y, 25, 25);
      if (!collides(r)) return { x, y };
    }
    return { x: MAP_WIDTH / 2, y: MAP_HEIGHT / 2 };
  }

  function findSafeNear(cx, cy, radius = 90) {
    for (let tries = 0; tries < 200; tries++) {
      const angle = rand(0, Math.PI * 2);
      const d = rand(20, radius);
      const x = clamp(cx + Math.cos(angle) * d, 60, MAP_WIDTH - 90);
      const y = clamp(cy + Math.sin(angle) * d, 60, MAP_HEIGHT - 90);
      if (!collides(new Rect(x, y, 25, 25))) return { x, y };
    }
    return findSafePosition();
  }

  function assignNames() {
    const pool = shuffle([...NICKNAME_POOL]);
    [player, ...AIs].forEach((p, i) => {
      p.nickname = pool[i] || `Guest${i + 1}`;
    });
  }

  function resetGame() {
    buildMap();
    bodies = [];
    activeBombs = [];
    gasClouds = [];
    explosions = [];
    slashFx = [];
    eventNotice = "";
    eventNoticeTimer = 0;
    gameOver = false;
    winner = "";
    playerKillCooldown = 0;
    imposterKillCooldown = 0;
    trollStunCooldown = 0;
    playerKillCount = 0;
    shiftEnergy = SHIFT_MAX_FRAMES;
    shiftCooldown = 0;
    sabotageCooldown = 0;
    sabotageSelectMode = null;
    blackoutTimer = 0;
    oxygenTimer = 0;
    oxygenPoints = [];
    oxygenFixed = [];
    lockedRoomTimer = 0;
    lockedRoom = null;

    const roleKeys = Object.keys(ROLE_QUOTA);
    const playerRole = roleKeys[randInt(0, roleKeys.length - 1)];
    player = new Actor(MAP_WIDTH / 2, MAP_HEIGHT / 2, colorRandom(), playerRole);
    const safe = findSafePosition();
    player.x = safe.x;
    player.y = safe.y;

    const aiRoles = [];
    for (const [role, count] of Object.entries(ROLE_QUOTA)) {
      const remain = count - (role === playerRole ? 1 : 0);
      for (let i = 0; i < remain; i++) aiRoles.push(role);
    }
    shuffle(aiRoles);
    AIs = aiRoles.map((role, i) => {
      const pos = findSafePosition();
      return new Actor(pos.x, pos.y, colorRandom(), role, i === 0);
    });
    assignNames();

    const taskTypes = ["normal", "normal", "normal", "fix", "fix", "upload"];
    tasks = [];
    for (let i = 0; i < 100; i++) {
      const pos = findSafePosition();
      tasks.push(new Task(pos.x, pos.y, taskTypes[randInt(0, taskTypes.length - 1)]));
    }
  }

  function startGame() {
    resetGame();
    gameStarted = true;
    roundStartTime = performance.now();
    menuPage = "main";
  }

  function roundPlaying() {
    return gameStarted && performance.now() - roundStartTime >= ROLE_REVEAL_MS;
  }

  function moveActor(actor, dx, dy) {
    if (!actor.alive && !actor.ghost) return;
    let nx = actor.x + dx;
    if (!collides(actor.rect(nx, actor.y))) actor.x = clamp(nx, 50, MAP_WIDTH - actor.w - 50);
    let ny = actor.y + dy;
    if (!collides(actor.rect(actor.x, ny))) actor.y = clamp(ny, 50, MAP_HEIGHT - actor.h - 50);
  }

  function moveToward(actor, tx, ty, speed = MOVE_SPEED) {
    const c = actor.center();
    const d = Math.hypot(tx - c.x, ty - c.y) || 1;
    moveActor(actor, (tx - c.x) / d * speed, (ty - c.y) / d * speed);
  }

  function livingPlayers() {
    return [player, ...AIs].filter(p => p.alive);
  }

  function livingCrews() {
    return livingPlayers().filter(p => CREW_ROLES.includes(p.role));
  }

  function killActor(victim, killer = null, reason = "kill") {
    if (!victim || !victim.alive) return false;
    victim.alive = false;
    victim.ghost = true;
    victim.stunTimer = 0;
    bodies.push(new Body(victim.x, victim.y, victim));
    slashFx.push({ x: victim.x + 12, y: victim.y + 12, t: 24, color: victim.color });
    if (killer) {
      killer.statsKills += 1;
      if (killer === player) playerKillCount += 1;
      if (victim.role === "guard" && killer.role === "imposter") {
        killer.stunTimer = STUN_DURATION;
      }
    }
    setNotice(`${victim.nickname} died by ${reason}.`);
    return true;
  }

  function reviveNear(actor, undertaker = false) {
    if (!actor.alive && !actor.ghost) return false;
    if (undertaker && actor.undertakerReviveUsed) return false;
    if (!undertaker && actor.role !== "doctor") return false;
    if (!undertaker && actor.reviveUsed) return false;
    let bestIndex = -1;
    let bestDist = Infinity;
    for (let i = 0; i < bodies.length; i++) {
      const b = bodies[i];
      const d = dist(actor.x, actor.y, b.x, b.y);
      if (d < bestDist) {
        bestDist = d;
        bestIndex = i;
      }
    }
    if (bestIndex < 0 || bestDist > 70) return false;
    const body = bodies[bestIndex];
    const victim = body.deadPlayer;
    if (!victim) return false;
    victim.alive = true;
    victim.ghost = false;
    victim.x = body.x;
    victim.y = body.y;
    victim.stunTimer = 0;
    if (victim.role === "bomber") victim.bombsRemaining = 7;
    if (victim.role === "mad_scientist") victim.gasCooldown = 0;
    bodies.splice(bestIndex, 1);
    if (undertaker) actor.undertakerReviveUsed = true;
    else actor.reviveUsed = true;
    if (actor === player) actor.statsRevives += 1;
    setNotice(`${actor.nickname} revived ${victim.nickname}.`);
    return true;
  }

  function cureStun(actor) {
    if (!CREW_ROLES.includes(actor.role)) return false;
    for (const p of [player, ...AIs]) {
      if (p !== actor && p.alive && p.stunTimer > 0 && dist(actor.x, actor.y, p.x, p.y) < 60) {
        p.stunTimer = 0;
        setNotice(`${p.nickname} was cured.`);
        return true;
      }
    }
    return false;
  }

  function getBombHeldBy(holder) {
    return activeBombs.find(b => b.holder === holder) || null;
  }

  function attachBomb(owner, target) {
    if (!owner || owner.role !== "bomber" || owner.bombsRemaining <= 0 || !target.alive) return false;
    if (getBombHeldBy(target)) return false;
    owner.bombsRemaining -= 1;
    activeBombs.push({ owner, holder: target, timer: BOMB_FUSE_FRAMES });
    setNotice(`${target.nickname} has a bomb!`);
    return true;
  }

  function transferBomb(bomb, newHolder) {
    if (!bomb || !newHolder || !newHolder.alive) return false;
    bomb.holder = newHolder;
    setNotice(`Bomb passed to ${newHolder.nickname}.`);
    return true;
  }

  function updateBombs() {
    for (let i = activeBombs.length - 1; i >= 0; i--) {
      const bomb = activeBombs[i];
      if (!bomb.holder || !bomb.holder.alive) {
        activeBombs.splice(i, 1);
        continue;
      }
      bomb.timer -= 1;
      if (bomb.timer <= 0) {
        const c = bomb.holder.center();
        explosions.push({ x: c.x, y: c.y, t: 36, color: bomb.holder.color });
        killActor(bomb.holder, bomb.owner, "bomb");
        activeBombs.splice(i, 1);
      }
    }
  }

  function deployGas(owner, wx, wy) {
    if (!owner.alive || owner.role !== "mad_scientist" || owner.gasCooldown > 0) return false;
    const c = owner.center();
    const d = dist(c.x, c.y, wx, wy);
    if (d > GAS_RANGE) {
      const angle = Math.atan2(wy - c.y, wx - c.x);
      wx = c.x + Math.cos(angle) * GAS_RANGE;
      wy = c.y + Math.sin(angle) * GAS_RANGE;
    }
    gasClouds.push({ x: wx, y: wy, t: 150, owner });
    owner.gasCooldown = GAS_COOLDOWN_FRAMES;
    setNotice("Poison gas deployed.");
    for (const p of [player, ...AIs]) {
      if (p !== owner && p.alive && dist(p.x, p.y, wx, wy) < GAS_RADIUS) {
        killActor(p, owner, "poison gas");
      }
    }
    return true;
  }

  function playerVent() {
    if (!["imposter", "engineer"].includes(player.role) || !player.alive || player.venting) return false;
    for (const v of vents) {
      if (dist(player.x, player.y, v.x, v.y) < 55) {
        const dest = v.available[randInt(0, v.available.length - 1)];
        const pos = findSafeNear(dest.x, dest.y);
        player.x = pos.x;
        player.y = pos.y;
        player.venting = true;
        player.ventTime = 30;
        setNotice("Vented.");
        return true;
      }
    }
    return false;
  }

  function playerAutoActions() {
    if (!player.alive || player.stunTimer > 0) return;
    if (player.role === "imposter" && playerKillCooldown <= 0) {
      const targets = AIs.filter(p => p.alive && (CREW_ROLES.includes(p.role) || NEUTRAL_SIDE_ROLES.includes(p.role)));
      for (const t of targets) {
        if (dist(player.x, player.y, t.x, t.y) < IMPOSTER_RANGE) {
          killActor(t, player, "imposter");
          playerKillCooldown = FPS;
          break;
        }
      }
    }
    if (player.role === "troll" && trollStunCooldown <= 0) {
      const targets = AIs.filter(p => p.alive && CREW_ROLES.includes(p.role) && p.stunTimer <= 0);
      for (const t of targets) {
        if (dist(player.x, player.y, t.x, t.y) < 58) {
          t.stunTimer = STUN_DURATION;
          trollStunCooldown = 90;
          player.statsStuns += 1;
          setNotice(`${t.nickname} stunned.`);
          break;
        }
      }
    }
  }

  function clickAction(wx, wy) {
    if (!gameStarted || !roundPlaying() || gameOver) return;
    if (sabotageSelectMode === "locked" && player.role === "imposter" && sabotageCooldown <= 0) {
      const idx = roomZones.findIndex(z => z.rect.contains(wx, wy));
      if (idx >= 0) {
        lockedRoom = idx;
        lockedRoomTimer = 15 * FPS;
        sabotageCooldown = 25 * FPS;
        sabotageSelectMode = null;
        setNotice(`Sabotage: ${roomZones[idx].name} locked.`);
      }
      return;
    }
    let clicked = null;
    for (const ent of AIs) {
      if (ent.alive && ent.rect().contains(wx, wy)) {
        clicked = ent;
        break;
      }
    }
    if (clicked && player.alive) {
      const held = getBombHeldBy(player);
      if (held && dist(player.x, player.y, clicked.x, clicked.y) < BOMB_PASS_RANGE) {
        transferBomb(held, clicked);
        return;
      }
      if (player.role === "sheriff") {
        if (player.sheriffBullets <= 0) {
          setNotice("No bullets left.");
          return;
        }
        if (dist(player.x, player.y, clicked.x, clicked.y) > 145) {
          setNotice("Target too far.");
          return;
        }
        player.sheriffBullets -= 1;
        if (clicked.role === "imposter") {
          killActor(clicked, player, "shooter");
          player.sheriffBullets += 1;
          setNotice("Imposter down. Bullet restored.");
        } else {
          killActor(clicked, player, "wrong shot");
          killActor(player, clicked, "wrong shot");
        }
        return;
      }
      if (player.role === "bomber" && dist(player.x, player.y, clicked.x, clicked.y) < 115) {
        attachBomb(player, clicked);
        return;
      }
    }
    if (player.alive && player.role === "mad_scientist") {
      deployGas(player, wx, wy);
    }
  }

  function doAITask(ai) {
    if (!ai.targetTask || ai.targetTask.completed) {
      const remaining = tasks.filter(t => !t.completed);
      if (remaining.length === 0) return false;
      ai.targetTask = remaining.reduce((best, t) => {
        return dist(ai.x, ai.y, t.x, t.y) < dist(ai.x, ai.y, best.x, best.y) ? t : best;
      }, remaining[0]);
    }
    moveToward(ai, ai.targetTask.x, ai.targetTask.y);
    if (dist(ai.x, ai.y, ai.targetTask.x, ai.targetTask.y) < TASK_RANGE) {
      ai.targetTask.completed = true;
      ai.statsTasks += 1;
    }
    return true;
  }

  function aiWander(ai) {
    if (!ai.wanderTarget || dist(ai.x, ai.y, ai.wanderTarget.x, ai.wanderTarget.y) < 80) {
      ai.wanderTarget = findSafePosition();
    }
    moveToward(ai, ai.wanderTarget.x, ai.wanderTarget.y);
  }

  function updateAI(ai) {
    if (ai.venting) {
      ai.ventTime -= 1;
      if (ai.ventTime <= 0) ai.venting = false;
      return;
    }
    if (ai.ghost) {
      aiWander(ai);
      return;
    }
    if (!ai.alive) return;
    if (ai.stunTimer > 0) {
      ai.stunTimer -= 1;
      return;
    }
    if (ai.gasCooldown > 0) ai.gasCooldown -= 1;

    const heldBomb = getBombHeldBy(ai);
    if (heldBomb) {
      const candidates = livingPlayers().filter(p => p !== ai);
      if (candidates.length) {
        const target = candidates.reduce((best, p) => dist(ai.x, ai.y, p.x, p.y) < dist(ai.x, ai.y, best.x, best.y) ? p : best, candidates[0]);
        if (dist(ai.x, ai.y, target.x, target.y) < BOMB_PASS_RANGE) transferBomb(heldBomb, target);
        else moveToward(ai, target.x, target.y);
      }
      return;
    }

    if (ai.role === "doctor" && !ai.reviveUsed && bodies.length) {
      const body = bodies.reduce((best, b) => dist(ai.x, ai.y, b.x, b.y) < dist(ai.x, ai.y, best.x, best.y) ? b : best, bodies[0]);
      if (dist(ai.x, ai.y, body.x, body.y) < 70) reviveNear(ai, false);
      else moveToward(ai, body.x, body.y);
      return;
    }

    if (ai.role === "undertaker" && !ai.undertakerReviveUsed && bodies.length) {
      const body = bodies.reduce((best, b) => dist(ai.x, ai.y, b.x, b.y) < dist(ai.x, ai.y, best.x, best.y) ? b : best, bodies[0]);
      if (dist(ai.x, ai.y, body.x, body.y) < 70) reviveNear(ai, true);
      else moveToward(ai, body.x, body.y);
      return;
    }

    if (ai.role === "engineer" && Math.random() < 0.01) {
      const near = vents.find(v => dist(ai.x, ai.y, v.x, v.y) < 70);
      if (near) {
        const dest = near.available[randInt(0, near.available.length - 1)];
        const pos = findSafeNear(dest.x, dest.y);
        ai.x = pos.x;
        ai.y = pos.y;
        ai.venting = true;
        ai.ventTime = randInt(18, 34);
        return;
      }
    }

    if (ai.role === "bomber") {
      const candidates = livingPlayers().filter(p => p !== ai && !getBombHeldBy(p));
      if (ai.bombsRemaining > 0 && candidates.length) {
        const target = candidates.reduce((best, p) => dist(ai.x, ai.y, p.x, p.y) < dist(ai.x, ai.y, best.x, best.y) ? p : best, candidates[0]);
        if (dist(ai.x, ai.y, target.x, target.y) < 100) attachBomb(ai, target);
        else moveToward(ai, target.x, target.y);
        return;
      }
      aiWander(ai);
      return;
    }

    if (ai.role === "troll") {
      const targets = livingPlayers().filter(p => p !== ai && CREW_ROLES.includes(p.role) && p.stunTimer <= 0);
      if (trollStunCooldown <= 0 && targets.length) {
        const target = targets.reduce((best, p) => dist(ai.x, ai.y, p.x, p.y) < dist(ai.x, ai.y, best.x, best.y) ? p : best, targets[0]);
        if (dist(ai.x, ai.y, target.x, target.y) < 58) {
          target.stunTimer = STUN_DURATION;
          trollStunCooldown = 90;
          ai.statsStuns += 1;
        } else {
          moveToward(ai, target.x, target.y);
        }
        return;
      }
      aiWander(ai);
      return;
    }

    if (ai.role === "mad_scientist") {
      const targets = livingPlayers().filter(p => p !== ai);
      if (targets.length) {
        const target = targets.reduce((best, p) => dist(ai.x, ai.y, p.x, p.y) < dist(ai.x, ai.y, best.x, best.y) ? p : best, targets[0]);
        if (ai.gasCooldown <= 0 && dist(ai.x, ai.y, target.x, target.y) < GAS_RANGE) {
          deployGas(ai, target.x, target.y);
        } else {
          moveToward(ai, target.x, target.y);
        }
        return;
      }
      aiWander(ai);
      return;
    }

    if (ai.role === "imposter") {
      const targets = livingPlayers().filter(p => p !== ai && (CREW_ROLES.includes(p.role) || NEUTRAL_SIDE_ROLES.includes(p.role)));
      if (targets.length) {
        const target = targets.reduce((best, p) => dist(ai.x, ai.y, p.x, p.y) < dist(ai.x, ai.y, best.x, best.y) ? p : best, targets[0]);
        if (imposterKillCooldown <= 0 && dist(ai.x, ai.y, target.x, target.y) < IMPOSTER_RANGE) {
          killActor(target, ai, "imposter");
          imposterKillCooldown = FPS;
        } else {
          moveToward(ai, target.x, target.y);
        }
        return;
      }
      aiWander(ai);
      return;
    }

    if (!doAITask(ai)) aiWander(ai);
  }

  function getRoomIndexAt(x, y) {
    return roomZones.findIndex(z => z.rect.contains(x, y));
  }

  function startSabotage(kind) {
    if (player.role !== "imposter" || sabotageCooldown > 0 || !player.alive) return;
    if (kind === "blackout") {
      blackoutTimer = 15 * FPS;
      sabotageCooldown = 25 * FPS;
      setNotice("Sabotage: Blackout!");
    } else if (kind === "oxygen") {
      oxygenTimer = 35 * FPS;
      oxygenFixed = [];
      oxygenPoints = shuffle(roomZones.map(z => ({
        x: z.rect.x + z.rect.w / 2,
        y: z.rect.y + z.rect.h / 2,
        room: z.name
      }))).slice(0, 10);
      sabotageCooldown = 25 * FPS;
      setNotice("Sabotage: Oxygen failure. Fix 10 panels!");
    } else if (kind === "locked") {
      sabotageSelectMode = "locked";
      setNotice("Click a room to lock.");
    }
  }

  function updateSabotage() {
    if (sabotageCooldown > 0) sabotageCooldown -= 1;
    if (blackoutTimer > 0) blackoutTimer -= 1;
    if (lockedRoomTimer > 0) {
      lockedRoomTimer -= 1;
      if (lockedRoomTimer <= 0) lockedRoom = null;
    }
    if (oxygenTimer > 0) {
      oxygenTimer -= 1;
      oxygenPoints.forEach((p, i) => {
        if (!oxygenFixed.includes(i) && player.alive && dist(player.x, player.y, p.x, p.y) < 80) {
          oxygenFixed.push(i);
          setNotice(`Oxygen panel fixed (${oxygenFixed.length}/${oxygenPoints.length}).`);
        }
      });
      if (oxygenFixed.length >= oxygenPoints.length) {
        oxygenTimer = 0;
        setNotice("Oxygen restored.");
      } else if (oxygenTimer <= 0) {
        winner = "T4 Win! (Oxygen sabotage)";
        gameOver = true;
      }
    }
  }

  function updatePlayer() {
    if (player.stunTimer > 0) {
      player.stunTimer -= 1;
      return;
    }
    if (player.gasCooldown > 0) player.gasCooldown -= 1;
    if (player.venting) {
      player.ventTime -= 1;
      if (player.ventTime <= 0) player.venting = false;
    }

    const canMove = player.alive || player.ghost;
    if (!canMove || player.venting) return;
    let speed = MOVE_SPEED;
    const moving = keys.has("KeyW") || keys.has("KeyA") || keys.has("KeyS") || keys.has("KeyD");
    const sprint = (keys.has("ShiftLeft") || keys.has("ShiftRight")) && moving && shiftCooldown <= 0 && shiftEnergy > 0 && player.alive;
    if (sprint) speed *= SHIFT_SPEED_MULTIPLIER;
    let dx = 0;
    let dy = 0;
    if (keys.has("KeyA")) dx -= speed;
    if (keys.has("KeyD")) dx += speed;
    if (keys.has("KeyW")) dy -= speed;
    if (keys.has("KeyS")) dy += speed;
    if (dx && dy) {
      dx *= Math.SQRT1_2;
      dy *= Math.SQRT1_2;
    }
    moveActor(player, dx, dy);

    if (sprint) {
      shiftEnergy = Math.max(0, shiftEnergy - 1);
      if (shiftEnergy <= 0) shiftCooldown = SHIFT_COOLDOWN_FRAMES;
    } else if (shiftCooldown <= 0) {
      shiftEnergy = Math.min(SHIFT_MAX_FRAMES, shiftEnergy + 1);
    }
    if (shiftCooldown > 0) {
      shiftCooldown -= 1;
      if (shiftCooldown <= 0) shiftEnergy = SHIFT_MAX_FRAMES;
    }

    const dancing = keys.has("KeyC") || keys.has("KeyX") || keys.has("KeyZ");
    if (dancing) player.spinAngle = (player.spinAngle + 7) % 360;
    else player.spinAngle = 0;

    if (player.alive && CREW_ROLES.includes(player.role)) {
      for (const t of tasks) {
        if (!t.completed && dist(player.x, player.y, t.x, t.y) < TASK_RANGE) {
          t.completed = true;
          player.statsTasks += 1;
        }
      }
    }
    playerAutoActions();
  }

  function update() {
    if (!gameStarted || !roundPlaying() || gameOver) return;
    updatePlayer();
    AIs.forEach(updateAI);
    updateBombs();
    updateSabotage();

    if (eventNoticeTimer > 0) eventNoticeTimer -= 1;
    if (playerKillCooldown > 0) playerKillCooldown -= 1;
    if (imposterKillCooldown > 0) imposterKillCooldown -= 1;
    if (trollStunCooldown > 0) trollStunCooldown -= 1;

    gasClouds = gasClouds.filter(g => --g.t > 0);
    explosions = explosions.filter(e => --e.t > 0);
    slashFx = slashFx.filter(f => --f.t > 0);
    checkWin();
  }

  function checkWin() {
    if (gameOver) return true;
    const alive = livingPlayers();
    const aliveCrews = alive.filter(p => CREW_ROLES.includes(p.role));
    const aliveImps = alive.filter(p => p.role === "imposter");
    const aliveTrolls = alive.filter(p => p.role === "troll");
    const aliveBombers = alive.filter(p => p.role === "bomber");
    const aliveMad = alive.filter(p => p.role === "mad_scientist");
    const countedNonImps = alive.filter(p => p.role !== "imposter" && !NEUTRAL_SIDE_ROLES.includes(p.role));
    const nonImps = alive.filter(p => p.role !== "imposter");

    if (alive.length <= 2) {
      if (aliveTrolls.length) winner = "T2 Win! (Troll)";
      else if (aliveBombers.length) winner = "T3 Win! (Bomber)";
      else if (aliveMad.length) winner = "T5 Win! (Mad Scientist)";
      if (winner) {
        gameOver = true;
        return true;
      }
    }
    if (aliveImps.length === 0 && aliveBombers.length) winner = "T3 Win! (Bomber)";
    else if (aliveImps.length === 0 && aliveMad.length) winner = "T5 Win! (Mad Scientist)";
    else if (aliveImps.length === 0) winner = "T1 Win! (Crew Team)";
    else if (aliveImps.length > 0 && nonImps.length === 1 && !NEUTRAL_SIDE_ROLES.includes(nonImps[0].role)) winner = "T4 Win! (Imposter)";
    else if (aliveImps.length > 0 && aliveImps.length >= countedNonImps.length) winner = "T4 Win! (Imposter)";
    else if (tasks.every(t => t.completed) && aliveCrews.length) winner = "T1 Win! (Tasks Complete)";

    if (winner) {
      gameOver = true;
      return true;
    }
    return false;
  }

  function getCamera() {
    const focus = player;
    return {
      x: clamp(focus.x + focus.w / 2 - SCREEN_WIDTH / 2, 0, MAP_WIDTH - SCREEN_WIDTH),
      y: clamp(focus.y + focus.h / 2 - SCREEN_HEIGHT / 2, 0, MAP_HEIGHT - SCREEN_HEIGHT)
    };
  }

  function drawRectWorld(r, color, cam, stroke = null, lineWidth = 1) {
    const x = r.x - cam.x;
    const y = r.y - cam.y;
    if (x > SCREEN_WIDTH || y > SCREEN_HEIGHT || x + r.w < 0 || y + r.h < 0) return;
    ctx.fillStyle = color;
    ctx.fillRect(x, y, r.w, r.h);
    if (stroke) {
      ctx.strokeStyle = stroke;
      ctx.lineWidth = lineWidth;
      ctx.strokeRect(x, y, r.w, r.h);
    }
  }

  function drawText(text, x, y, size = 18, color = COLORS.white, align = "left") {
    ctx.font = `${size}px "Segoe UI", "Malgun Gothic", Arial, sans-serif`;
    ctx.fillStyle = color;
    ctx.textAlign = align;
    ctx.textBaseline = "top";
    ctx.fillText(text, x, y);
  }

  function drawActor(p, cam) {
    if (!p.alive && !p.ghost) return;
    if (p.venting && p.alive) return;
    const x = p.x - cam.x + p.danceOffsetX;
    const y = p.y - cam.y + p.danceOffsetY;
    if (x < -40 || y < -40 || x > SCREEN_WIDTH + 40 || y > SCREEN_HEIGHT + 40) return;
    ctx.save();
    ctx.globalAlpha = p.ghost ? 0.45 : 1;
    ctx.translate(x + p.w / 2, y + p.h / 2);
    if (p.spinAngle) ctx.rotate(p.spinAngle * Math.PI / 180);
    ctx.fillStyle = p.color;
    ctx.fillRect(-p.w / 2, -p.h / 2, p.w, p.h);
    ctx.strokeStyle = p.stunTimer > 0 ? COLORS.troll : COLORS.white;
    ctx.lineWidth = 2;
    ctx.strokeRect(-p.w / 2, -p.h / 2, p.w, p.h);
    ctx.fillStyle = COLORS.white;
    roundRect(ctx, -3, -p.h / 2 + 3, 6, 5, 2, true, false);
    ctx.restore();
    ctx.globalAlpha = 1;
    drawText(p.nickname, x + p.w / 2, y - 22, 13, p.ghost ? "#dddddd" : COLORS.white, "center");
  }

  function roundRect(c, x, y, w, h, r, fill, stroke) {
    c.beginPath();
    c.moveTo(x + r, y);
    c.arcTo(x + w, y, x + w, y + h, r);
    c.arcTo(x + w, y + h, x, y + h, r);
    c.arcTo(x, y + h, x, y, r);
    c.arcTo(x, y, x + w, y, r);
    c.closePath();
    if (fill) c.fill();
    if (stroke) c.stroke();
  }

  function drawWorld() {
    const cam = getCamera();
    ctx.fillStyle = COLORS.gray;
    ctx.fillRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT);

    for (const z of corridorZones) {
      drawRectWorld(z, COLORS.corridor, cam, COLORS.border, 2);
      const sx = z.x - cam.x;
      const sy = z.y - cam.y;
      ctx.strokeStyle = COLORS.neon;
      ctx.lineWidth = 2;
      if (z.w > z.h) {
        const yy = sy + z.h / 2;
        for (let x = sx + 8; x < sx + z.w - 8; x += 28) {
          ctx.beginPath();
          ctx.moveTo(x, yy);
          ctx.lineTo(Math.min(x + 14, sx + z.w - 8), yy);
          ctx.stroke();
        }
      } else {
        const xx = sx + z.w / 2;
        for (let y = sy + 8; y < sy + z.h - 8; y += 28) {
          ctx.beginPath();
          ctx.moveTo(xx, y);
          ctx.lineTo(xx, Math.min(y + 14, sy + z.h - 8));
          ctx.stroke();
        }
      }
    }

    for (const zone of roomZones) {
      drawRectWorld(zone.rect, zone.color, cam, COLORS.border, 3);
      const sx = zone.rect.x - cam.x;
      const sy = zone.rect.y - cam.y;
      if (sx < SCREEN_WIDTH && sy < SCREEN_HEIGHT && sx + zone.rect.w > 0 && sy + zone.rect.h > 0) {
        ctx.fillStyle = COLORS.accent;
        [[16, 16], [zone.rect.w - 16, 16], [16, zone.rect.h - 16], [zone.rect.w - 16, zone.rect.h - 16]].forEach(([x, y]) => {
          ctx.beginPath();
          ctx.arc(sx + x, sy + y, 6, 0, Math.PI * 2);
          ctx.fill();
        });
        if (["Cafeteria", "Office", "Vault"].includes(zone.name)) {
          ctx.fillStyle = "#4a5c78";
          roundRect(ctx, sx + zone.rect.w / 2 - 110, sy + zone.rect.h / 2 - 45, 220, 90, 12, true, false);
          ctx.strokeStyle = "#8caad2";
          roundRect(ctx, sx + zone.rect.w / 2 - 110, sy + zone.rect.h / 2 - 45, 220, 90, 12, false, true);
        }
        drawText(`${zone.num}. ${zone.name}`, sx + 12, sy + 10, 14, "#c8d4e8");
      }
    }

    for (const w of walls) drawRectWorld(w, COLORS.darkGray, cam);

    for (const t of tasks) {
      if (dist(t.x, t.y, player.x, player.y) > 360 && player.alive) continue;
      drawRectWorld(t.rect(), t.completed ? COLORS.green : COLORS.yellow, cam, COLORS.white, 2);
    }

    for (const b of bodies) {
      drawRectWorld(new Rect(b.x, b.y, b.w, b.h), COLORS.purple, cam, COLORS.white, 1);
      if (player.role === "undertaker" && dist(player.x, player.y, b.x, b.y) < 220 && b.deadPlayer) {
        drawText(`Corpse: ${roleName(b.deadPlayer.role)}`, b.x - cam.x + 12, b.y - cam.y - 22, 14, COLORS.undertaker, "center");
      }
    }

    for (const v of vents) {
      const x = v.x - cam.x;
      const y = v.y - cam.y;
      if (x < -40 || y < -40 || x > SCREEN_WIDTH + 40 || y > SCREEN_HEIGHT + 40) continue;
      ctx.fillStyle = COLORS.cyan;
      ctx.beginPath();
      ctx.arc(x, y, v.radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = COLORS.white;
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    for (const g of gasClouds) {
      const x = g.x - cam.x;
      const y = g.y - cam.y;
      const alpha = Math.max(0.08, g.t / 150 * 0.35);
      ctx.fillStyle = `rgba(60, 220, 110, ${alpha})`;
      ctx.beginPath();
      ctx.arc(x, y, GAS_RADIUS, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "rgba(120, 255, 170, 0.8)";
      ctx.stroke();
    }

    for (const e of explosions) {
      const x = e.x - cam.x;
      const y = e.y - cam.y;
      const r = (36 - e.t) * 3;
      ctx.fillStyle = `rgba(255, 140, 60, ${e.t / 36})`;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }

    for (const f of slashFx) {
      const x = f.x - cam.x;
      const y = f.y - cam.y;
      ctx.strokeStyle = `rgba(255, 255, 255, ${f.t / 24})`;
      ctx.lineWidth = 5;
      ctx.beginPath();
      ctx.moveTo(x - 20, y - 20);
      ctx.lineTo(x + 20, y + 20);
      ctx.moveTo(x + 18, y - 18);
      ctx.lineTo(x - 18, y + 18);
      ctx.stroke();
    }

    for (const p of [player, ...AIs]) drawActor(p, cam);

    for (const bomb of activeBombs) {
      const h = bomb.holder;
      if (!h || !h.alive) continue;
      const sx = h.x - cam.x + h.w / 2;
      const sy = h.y - cam.y - 40;
      drawText(`BOMB ${(bomb.timer / FPS).toFixed(1)}s`, sx, sy, 13, COLORS.bomber, "center");
    }

    for (let i = 0; i < oxygenPoints.length; i++) {
      if (oxygenFixed.includes(i) || oxygenTimer <= 0) continue;
      const p = oxygenPoints[i];
      const x = p.x - cam.x;
      const y = p.y - cam.y;
      ctx.strokeStyle = COLORS.orange;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.arc(x, y, 24, 0, Math.PI * 2);
      ctx.stroke();
      drawText("O2", x, y - 8, 14, COLORS.orange, "center");
    }

    if (sabotageSelectMode) {
      for (const z of roomZones) {
        const sx = z.rect.x - cam.x;
        const sy = z.rect.y - cam.y;
        ctx.strokeStyle = "rgba(255, 165, 0, 0.85)";
        ctx.lineWidth = 4;
        ctx.strokeRect(sx, sy, z.rect.w, z.rect.h);
      }
    }

    drawVisionOverlay();
    drawHUD(cam);
    if (showMap) drawMinimap(cam);
  }

  function drawVisionOverlay() {
    if (!roundPlaying() || player.ghost) return;
    const radius = blackoutTimer > 0 ? 165 : 780;
    const gradient = ctx.createRadialGradient(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, radius * 0.3, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, radius);
    gradient.addColorStop(0, "rgba(0,0,0,0)");
    gradient.addColorStop(0.72, "rgba(0,0,0,0.18)");
    gradient.addColorStop(1, "rgba(0,0,0,0.88)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT);
  }

  function drawHUD(cam) {
    if (!roundPlaying()) return;
    const alive = livingPlayers();
    const dead = ROLE_TOTAL - alive.length;
    const crewCount = alive.filter(p => CREW_ROLES.includes(p.role)).length;
    const impCount = alive.filter(p => p.role === "imposter").length;
    const trollCount = alive.filter(p => p.role === "troll").length;
    const bomberCount = alive.filter(p => p.role === "bomber").length;
    const madCount = alive.filter(p => p.role === "mad_scientist").length;
    const completed = tasks.filter(t => t.completed).length;
    const heldBomb = getBombHeldBy(player);
    let y = 10;
    drawText(`Nick: ${player.nickname} | Role: ${roleName(player.role).toUpperCase()} | Total: ${ROLE_TOTAL} | Alive: ${alive.length} | Dead: ${dead}`, 10, y, 20); y += 28;
    drawText(`Crew Team: ${crewCount} | Imposter: ${impCount} | Troll: ${trollCount} | Bomber: ${bomberCount} | MadSci: ${madCount}`, 10, y, 18); y += 26;
    drawText(`Tasks: ${completed}/${tasks.length} | My Tasks ${player.statsTasks} | Kills ${player.statsKills} | Stuns ${player.statsStuns} | Revives ${player.statsRevives}`, 10, y, 18, "#dce6f5"); y += 26;
    const sprintText = shiftCooldown > 0 ? `Sprint: COOLDOWN ${(shiftCooldown / FPS).toFixed(1)}s` : `Sprint: ${(shiftEnergy / FPS).toFixed(1)}s / 5.0s`;
    drawText(sprintText, 10, y, 18, shiftCooldown > 0 ? "#ffaa78" : "#8cdcff"); y += 26;
    if (eventNoticeTimer > 0 && eventNotice) {
      drawText(eventNotice, SCREEN_WIDTH / 2, 92, 24, eventNotice.startsWith("Sabotage") ? COLORS.red : "#8cdcff", "center");
    }
    if (oxygenTimer > 0) {
      drawText(`Oxygen: ${(oxygenTimer / FPS).toFixed(1)}s | Fixed ${oxygenFixed.length}/${oxygenPoints.length}`, 10, y, 18, COLORS.orange); y += 26;
    }
    if (blackoutTimer > 0) {
      drawText(`Blackout: ${(blackoutTimer / FPS).toFixed(1)}s`, 10, y, 18, COLORS.red); y += 26;
    }
    if (lockedRoomTimer > 0 && lockedRoom !== null) {
      drawText(`Locked Room: ${roomZones[lockedRoom].name} ${(lockedRoomTimer / FPS).toFixed(1)}s`, 10, y, 18, COLORS.orange); y += 26;
    }
    if (player.alive && player.role === "imposter") {
      drawText(`Kills: ${playerKillCount} | Kill CD ${(playerKillCooldown / FPS).toFixed(1)}s | E vent | Q fake task | Sabotage: 1 blackout 2 oxygen 3 lock (${(sabotageCooldown / FPS).toFixed(1)}s)`, 10, y, 18, COLORS.orange); y += 26;
    }
    if (player.role === "doctor") {
      drawText(player.alive ? `Doctor: F revive | G cure stun | Used: ${player.reviveUsed}` : "Ghost Doctor: move to your body and press F", 10, y, 18, COLORS.doctor); y += 26;
    }
    if (player.role === "engineer") {
      drawText("Engineer: Crew team | E near vent", 10, y, 18, COLORS.engineer); y += 26;
    }
    if (player.role === "undertaker") {
      drawText(`Undertaker: F revive nearest corpse | Used: ${player.undertakerReviveUsed}`, 10, y, 18, COLORS.undertaker); y += 26;
    }
    if (player.role === "sheriff") {
      drawText(`Shooter: Left click target | Bullets: ${player.sheriffBullets}`, 10, y, 18, COLORS.guard); y += 26;
    }
    if (player.role === "bomber") {
      drawText(`Bomber: Left click plant/pass bomb | Bombs left: ${player.bombsRemaining}`, 10, y, 18, COLORS.bomber); y += 26;
    }
    if (player.role === "mad_scientist") {
      drawText(`Mad Scientist: Left click gas | CD ${(player.gasCooldown / FPS).toFixed(1)}s`, 10, y, 18, COLORS.mad); y += 26;
    }
    if (player.stunTimer > 0) {
      drawText(`STUNNED ${(player.stunTimer / FPS).toFixed(1)}s`, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 85, 30, COLORS.troll, "center");
    }
    if (player.venting) {
      drawText("VENTING...", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 120, 30, COLORS.cyan, "center");
    }
    if (heldBomb && player.alive) {
      drawText(`!!! BOMB ON YOU: ${(heldBomb.timer / FPS).toFixed(1)}s | CLICK SOMEONE NOW !!!`, SCREEN_WIDTH / 2, 46, 24, COLORS.bomber, "center");
    }
    drawText("WASD move | Shift sprint | M hold map | C/X/Z dance | E/F/G actions | ESC menu", 10, SCREEN_HEIGHT - 32, 16, "#a0a0b8");

    if (player.alive && player.role === "imposter") {
      const r = IMPOSTER_RANGE;
      ctx.strokeStyle = "rgba(255,0,0,0.8)";
      ctx.beginPath();
      ctx.arc(player.x - cam.x + player.w / 2, player.y - cam.y + player.h / 2, r, 0, Math.PI * 2);
      ctx.stroke();
    }
    if (player.alive && player.role === "mad_scientist") {
      ctx.strokeStyle = "rgba(80,220,120,0.8)";
      ctx.beginPath();
      ctx.arc(player.x - cam.x + player.w / 2, player.y - cam.y + player.h / 2, GAS_RANGE, 0, Math.PI * 2);
      ctx.stroke();
    }
  }

  const ROLE_TOTAL = Object.values(ROLE_QUOTA).reduce((a, b) => a + b, 0);

  function drawMinimap(cam) {
    const mw = 300;
    const mh = Math.round(mw * MAP_HEIGHT / MAP_WIDTH);
    const pad = 4;
    const x0 = SCREEN_WIDTH - mw - 22;
    const y0 = SCREEN_HEIGHT - mh - 62;
    ctx.fillStyle = "rgba(10,12,22,0.92)";
    ctx.fillRect(x0 - pad, y0 - pad, mw + pad * 2, mh + pad * 2);
    function w2m(x, y) {
      return [x0 + x / MAP_WIDTH * mw, y0 + y / MAP_HEIGHT * mh];
    }
    for (const z of corridorZones) {
      const [x, y] = w2m(z.x, z.y);
      const [x2, y2] = w2m(z.x + z.w, z.y + z.h);
      ctx.fillStyle = "#26303c";
      ctx.fillRect(x, y, Math.max(1, x2 - x), Math.max(1, y2 - y));
    }
    for (const r of roomZones) {
      const [x, y] = w2m(r.rect.x, r.rect.y);
      const [x2, y2] = w2m(r.rect.x + r.rect.w, r.rect.y + r.rect.h);
      ctx.fillStyle = "#47556d";
      ctx.fillRect(x, y, Math.max(2, x2 - x), Math.max(2, y2 - y));
      ctx.strokeStyle = "#718098";
      ctx.strokeRect(x, y, Math.max(2, x2 - x), Math.max(2, y2 - y));
    }
    const [vx, vy] = w2m(cam.x, cam.y);
    ctx.strokeStyle = COLORS.yellow;
    ctx.lineWidth = 2;
    ctx.strokeRect(vx, vy, SCREEN_WIDTH / MAP_WIDTH * mw, SCREEN_HEIGHT / MAP_HEIGHT * mh);
    for (const p of [player, ...AIs]) {
      if (!p.alive && !(p === player && p.ghost)) continue;
      const c = p.center();
      const [x, y] = w2m(c.x, c.y);
      ctx.fillStyle = p === player ? COLORS.yellow : "#d0d8e8";
      ctx.beginPath();
      ctx.arc(x, y, p === player ? 4 : 2, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.strokeStyle = "#8296b4";
    ctx.strokeRect(x0 - pad, y0 - pad, mw + pad * 2, mh + pad * 2);
    drawText("M: Map", x0 + 5, y0 + 5, 14, "#d0d8e8");
  }

  function buttonRect(offsetY) {
    const bw = 320;
    const bh = 70;
    return new Rect(SCREEN_WIDTH / 2 - bw / 2, SCREEN_HEIGHT / 2 + offsetY, bw, bh);
  }

  function drawButton(r, text, fill, stroke) {
    ctx.fillStyle = fill;
    roundRect(ctx, r.x, r.y, r.w, r.h, 12, true, false);
    ctx.strokeStyle = stroke || COLORS.white;
    ctx.lineWidth = 3;
    roundRect(ctx, r.x, r.y, r.w, r.h, 12, false, true);
    drawText(text, r.x + r.w / 2, r.y + 18, 28, COLORS.white, "center");
  }

  function drawMainMenu() {
    ctx.fillStyle = "#0c101c";
    ctx.fillRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT);
    drawText("Spiral of Suspicion", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 195, 64, "#8cdcff", "center");
    drawText("Survive, deceive, repair, or sabotage.", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 112, 26, "#d2dceb", "center");
    drawText("Your role will be revealed after the game starts.", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 70, 22, "#c4ccd8", "center");
    drawButton(buttonRect(10), "Start Game", "#235f46", "#78ffaa");
    drawButton(buttonRect(100), "How to Play", "#464669", "#b4beff");
    drawText("Enter: Start | H: How to Play | ESC: Close tab/window", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 52, 18, "#aab4cd", "center");
  }

  function drawHowTo() {
    ctx.fillStyle = "#0a0c18";
    ctx.fillRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT);
    drawText("How to Play", SCREEN_WIDTH / 2, 34, 56, COLORS.yellow, "center");
    let y = 110;
    const x = Math.max(42, SCREEN_WIDTH / 2 - 650);
    for (const [role, goal, action] of ROLE_HELP_LINES) {
      const key = role.toLowerCase().replace(" ", "_");
      drawText(`${role}:`, x, y, 18, roleColor(key));
      drawText(goal, x + 170, y, 18, COLORS.white);
      drawText(action, x + 170, y + 24, 16, "#cdd8eb");
      y += 58;
    }
    drawText("Common: WASD move | Shift sprint | Hold M map | C/X/Z dance | ESC main menu.", x, y + 6, 17, "#aae0ff");
    drawText("This is a browser Canvas port of the original Pygame file. Some Pygame-only audio/camera details are simplified.", x, y + 32, 16, "#9eabc5");
    const back = new Rect(40, SCREEN_HEIGHT - 95, 220, 58);
    drawButton(back, "Back", "#4b3737", "#ffb496");
    drawText("ESC or Backspace: Back", 290, SCREEN_HEIGHT - 78, 17, "#aab4cd");
  }

  function drawRoleReveal() {
    drawWorld();
    ctx.fillStyle = "rgba(0,0,0,0.88)";
    ctx.fillRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT);
    const elapsed = performance.now() - roundStartTime;
    const left = Math.max(0, Math.ceil((ROLE_REVEAL_MS - elapsed) / 1000));
    drawText(`YOUR ROLE: ${roleName(player.role).toUpperCase()}`, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 58, 52, roleColor(player.role), "center");
    drawText(`The game starts in ${left}...`, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 35, 28, "#dde5f0", "center");
  }

  function drawGameOver() {
    drawWorld();
    ctx.fillStyle = "rgba(0,0,0,0.72)";
    ctx.fillRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT);
    drawText(winner, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 28, 38, COLORS.yellow, "center");
    drawText("ESC: Main menu | Enter: Restart", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 42, 22, COLORS.white, "center");
  }

  function render() {
    if (!gameStarted) {
      if (menuPage === "howto") drawHowTo();
      else drawMainMenu();
      return;
    }
    if (!roundPlaying()) {
      drawRoleReveal();
      return;
    }
    if (gameOver) drawGameOver();
    else drawWorld();
  }

  function loop() {
    update();
    render();
    requestAnimationFrame(loop);
  }

  window.addEventListener("keydown", e => {
    keys.add(e.code);
    if (["Space", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].includes(e.code)) e.preventDefault();
    if (!gameStarted) {
      if (menuPage === "main") {
        if (e.code === "Enter" || e.code === "Space") startGame();
        if (e.code === "KeyH") menuPage = "howto";
      } else if (menuPage === "howto" && (e.code === "Escape" || e.code === "Backspace" || e.code === "KeyH")) {
        menuPage = "main";
      }
      return;
    }
    if (e.code === "Escape") {
      gameStarted = false;
      menuPage = "main";
      return;
    }
    if (gameOver && e.code === "Enter") {
      startGame();
      return;
    }
    if (!roundPlaying() || gameOver) return;
    if (e.code === "KeyM") showMap = true;
    if (e.code === "KeyE") playerVent();
    if (e.code === "KeyF") {
      if (player.role === "doctor") reviveNear(player, false);
      if (player.role === "undertaker") reviveNear(player, true);
    }
    if (e.code === "KeyG") cureStun(player);
    if (e.code === "Digit1") startSabotage("blackout");
    if (e.code === "Digit2") startSabotage("oxygen");
    if (e.code === "Digit3") startSabotage("locked");
    if (e.code === "KeyQ" && player.role === "imposter") setNotice("Faking task...");
  });

  window.addEventListener("keyup", e => {
    keys.delete(e.code);
    if (e.code === "KeyM") showMap = false;
  });

  canvas.addEventListener("mousemove", e => {
    const r = canvas.getBoundingClientRect();
    mouse.x = e.clientX - r.left;
    mouse.y = e.clientY - r.top;
  });

  canvas.addEventListener("mousedown", e => {
    const r = canvas.getBoundingClientRect();
    const sx = e.clientX - r.left;
    const sy = e.clientY - r.top;
    if (!gameStarted) {
      if (menuPage === "main") {
        if (buttonRect(10).contains(sx, sy)) startGame();
        else if (buttonRect(100).contains(sx, sy)) menuPage = "howto";
      } else {
        const back = new Rect(40, SCREEN_HEIGHT - 95, 220, 58);
        if (back.contains(sx, sy)) menuPage = "main";
      }
      return;
    }
    const cam = getCamera();
    clickAction(sx + cam.x, sy + cam.y);
  });

  resetGame();
  loop();
  </script>
</body>
</html>
