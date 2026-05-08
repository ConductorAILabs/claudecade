// Real arcade effects with Phaser
// Phaser.AUTO can't always pick a renderer when we hand it a detached canvas;
// CANVAS is explicit and works in every modern browser without a WebGL probe.
const config = {
  type: Phaser.CANVAS,
  width: window.innerWidth,
  height: window.innerHeight,
  parent: document.body,
  transparent: true,
  scene: {
    create: create,
    update: update,
  },
};

const game = new Phaser.Game(config);

// Module-level scene handle so DOM click handlers can spawn effects.
let arcadeScene = null;

// ── Themed click effects ──────────────────────────────────────────────────────
// Each game card plays out a tiny ASCII scene when clicked: an actor moves
// across the card region, fires/swings/jumps, and the resulting impact
// particles spread outward. All Phaser.Text objects, all monospace ASCII art.

const COL = {
  cyan:    '#00e5ff',
  green:   '#7CFC00',
  pink:    '#ff2d78',
  gold:    '#ffd700',
  white:   '#ffffff',
  red:     '#ff5555',
  purple:  '#9370db',
  blue:    '#00bfff',
  orange:  '#ff9933',
  dim:     '#888888',
};

function makeText(s, x, y, color, size, bold = true) {
  const t = arcadeScene.add.text(x, y, s, {
    fontFamily: 'Monaco, "Courier New", monospace',
    fontSize:   size + 'px',
    color:      color,
    fontStyle:  bold ? 'bold' : 'normal',
  });
  t.setOrigin(0.5);
  t.setDepth(1000);
  return t;
}

function fadeOut(t, duration = 500, drift = { dx: 0, dy: 0 }) {
  arcadeScene.tweens.add({
    targets:    t,
    x:          t.x + drift.dx,
    y:          t.y + drift.dy,
    alpha:      { from: t.alpha, to: 0 },
    duration:   duration,
    ease:       'Cubic.easeOut',
    onComplete: () => t.destroy(),
  });
}

function impactBurst(x, y, glyphs, colors, count = 12) {
  for (let i = 0; i < count; i++) {
    const g     = glyphs[Math.floor(Math.random() * glyphs.length)];
    const c     = colors[i % colors.length];
    const sz    = 12 + Math.floor(Math.random() * 12);
    const t     = makeText(g, x, y, c, sz);
    const ang   = Math.random() * Math.PI * 2;
    const spd   = 60 + Math.random() * 220;
    const dx    = Math.cos(ang) * spd;
    const dy    = Math.sin(ang) * spd - 30;
    const dur   = 600 + Math.random() * 500;
    arcadeScene.tweens.add({
      targets:    t,
      x:          x + dx,
      y:          y + dy + 60,
      alpha:      { from: 1, to: 0 },
      angle:      (Math.random() - 0.5) * 360,
      scale:      { from: 1, to: 0.5 },
      duration:   dur,
      ease:       'Cubic.easeOut',
      onComplete: () => t.destroy(),
    });
  }
}

// ── Per-game scene scripts ────────────────────────────────────────────────────
const SCENES = {
  // Space shooter: ship flies right, fires bullet, enemy explodes
  ctype: (cx, cy) => {
    const W = window.innerWidth;
    const ship  = makeText(' ╱‾‾╲\n╞══▷  ▶\n ╲__╱', cx - 200, cy, COL.cyan, 20);
    const enemy = makeText('◁━━◆━━▷', cx + 220, cy, COL.red, 22);
    arcadeScene.tweens.add({ targets: ship,  x: cx - 60,  duration: 600, ease: 'Cubic.easeOut' });
    arcadeScene.tweens.add({ targets: enemy, x: cx + 80,  duration: 600, ease: 'Cubic.easeOut' });
    arcadeScene.time.delayedCall(550, () => {
      const bullet = makeText('═►', cx - 30, cy, COL.gold, 18);
      arcadeScene.tweens.add({ targets: bullet, x: cx + 80, duration: 180, ease: 'Linear', onComplete: () => bullet.destroy() });
    });
    arcadeScene.time.delayedCall(740, () => {
      enemy.setText('  ✦BOOM✦  '); enemy.setColor(COL.gold);
      impactBurst(cx + 80, cy, ['*','✦','◆','·','✧','+'], [COL.gold, COL.red, COL.white], 16);
    });
    arcadeScene.time.delayedCall(900, () => { fadeOut(ship, 400, { dx: 200, dy: 0 }); fadeOut(enemy, 400); });
  },

  // Run & gun: runner sprints right, fires forward, target hit
  claudtra: (cx, cy) => {
    const runner = makeText('[O_O]\n  ╫─►\n  ╱╲', cx - 180, cy, COL.green, 18);
    const target = makeText(' ╳ ', cx + 160, cy, COL.red, 24);
    arcadeScene.tweens.add({ targets: runner, x: cx - 60, duration: 700, ease: 'Cubic.easeOut' });
    arcadeScene.time.delayedCall(550, () => {
      for (let i = 0; i < 3; i++) {
        arcadeScene.time.delayedCall(i * 80, () => {
          const b = makeText('━►', cx - 20, cy, COL.gold, 16);
          arcadeScene.tweens.add({ targets: b, x: cx + 140, duration: 160, ease: 'Linear', onComplete: () => b.destroy() });
        });
      }
    });
    arcadeScene.time.delayedCall(900, () => {
      target.setText('BANG!'); target.setColor(COL.gold);
      impactBurst(cx + 160, cy, ['▓','◆','*','×','+'], [COL.gold, COL.red, COL.white], 14);
    });
    arcadeScene.time.delayedCall(1050, () => { fadeOut(runner, 400, { dx: 100 }); fadeOut(target, 400); });
  },

  // Fighting: two fighters approach, clash, KO text appears
  fight: (cx, cy) => {
    const p1 = makeText('╔══╗\n║▲▲║\n║▼ ║\n╚══╝', cx - 180, cy, COL.cyan, 16);
    const p2 = makeText('╔══╗\n║● ●║\n║ ○║\n╚══╝', cx + 180, cy, COL.pink, 16);
    arcadeScene.tweens.add({ targets: p1, x: cx - 50, duration: 500, ease: 'Cubic.easeOut' });
    arcadeScene.tweens.add({ targets: p2, x: cx + 50, duration: 500, ease: 'Cubic.easeOut' });
    arcadeScene.time.delayedCall(540, () => {
      const clash = makeText('✦', cx, cy, COL.gold, 36);
      const pow   = makeText('POW!', cx - 10, cy - 30, COL.gold, 28);
      const bam   = makeText('BAM!', cx + 30, cy + 20, COL.pink, 24);
      impactBurst(cx, cy, ['✦','★','◆','╳','*','+'], [COL.gold, COL.pink, COL.white, COL.red], 18);
      arcadeScene.tweens.add({ targets: p1, x: cx - 90,  duration: 200, ease: 'Bounce.easeOut' });
      arcadeScene.tweens.add({ targets: p2, x: cx + 90,  duration: 200, ease: 'Bounce.easeOut' });
      fadeOut(clash, 600, { dy: -10 });
      fadeOut(pow,   700, { dy: -30 });
      fadeOut(bam,   700, { dy: 30 });
    });
    arcadeScene.time.delayedCall(900, () => {
      const ko = makeText('K.O.', cx, cy, COL.red, 48);
      ko.setAlpha(0);
      arcadeScene.tweens.add({ targets: ko, alpha: { from: 0, to: 1 }, scale: { from: 0.5, to: 1.2 }, duration: 250, yoyo: true, hold: 100, onComplete: () => ko.destroy() });
      fadeOut(p1, 500, { dx: -60 }); fadeOut(p2, 500, { dx: 60 });
    });
  },

  // Platformer: figure jumps, lands on enemy, coin pops
  superclaudio: (cx, cy) => {
    const hero = makeText('(*)\n /|\\\n / \\', cx - 120, cy + 30, COL.cyan, 18);
    const enemy = makeText('(--)\n  ‾', cx + 80, cy + 50, COL.red, 18);
    // Run toward enemy
    arcadeScene.tweens.add({ targets: hero, x: cx + 60, duration: 600, ease: 'Cubic.easeOut' });
    // Jump arc (custom: tween y down then up)
    arcadeScene.tweens.add({ targets: hero, y: cy - 30, duration: 300, ease: 'Quad.easeOut', delay: 350 });
    arcadeScene.tweens.add({ targets: hero, y: cy + 40, duration: 200, ease: 'Quad.easeIn',  delay: 650 });
    // Stomp + coin
    arcadeScene.time.delayedCall(870, () => {
      enemy.setText('▓▓▓'); enemy.setColor(COL.dim);
      const coin = makeText('$', cx + 80, cy + 30, COL.gold, 28);
      arcadeScene.tweens.add({ targets: coin, y: cy - 60, alpha: { from: 1, to: 0 }, duration: 700, ease: 'Cubic.easeOut', onComplete: () => coin.destroy() });
      const stomp = makeText('STOMP!', cx + 80, cy + 10, COL.gold, 22);
      fadeOut(stomp, 500, { dy: -20 });
      impactBurst(cx + 80, cy + 30, ['★','◆','*','✦'], [COL.gold, COL.white, COL.pink], 10);
    });
    arcadeScene.time.delayedCall(1100, () => { fadeOut(hero, 500); fadeOut(enemy, 500); });
  },

  // Racing: car zooms across with speed lines, finishes at flag
  claudturismo: (cx, cy) => {
    const car = makeText('◢▶', cx - 250, cy, COL.pink, 28);
    // Speed lines trail behind
    for (let i = 0; i < 5; i++) {
      arcadeScene.time.delayedCall(i * 60, () => {
        const line = makeText('═══', cx - 250 + i * 50, cy, COL.gold, 18);
        arcadeScene.tweens.add({ targets: line, x: line.x - 80, alpha: { from: 0.8, to: 0 }, duration: 400, onComplete: () => line.destroy() });
      });
    }
    arcadeScene.tweens.add({ targets: car, x: cx + 200, duration: 800, ease: 'Cubic.easeOut' });
    arcadeScene.time.delayedCall(800, () => {
      const flag = makeText('▓░▓░▓\n░▓░▓░\n▓░▓░▓', cx + 220, cy, COL.white, 18);
      const txt  = makeText('FINISH!', cx, cy - 40, COL.gold, 28);
      fadeOut(txt, 700, { dy: -20 });
      impactBurst(cx + 200, cy, ['★','◆','VROOM','✦'], [COL.gold, COL.pink, COL.white], 12);
      fadeOut(car, 500, { dx: 100 }); fadeOut(flag, 800);
    });
  },

  // Creature RPG: trainer throws ball, captures wild creature
  claudemon: (cx, cy) => {
    const trainer  = makeText('[T]\n /|\\', cx - 180, cy, COL.cyan, 18);
    const creature = makeText('╭───╮\n│◉ ◉│\n╰─◡─╯', cx + 140, cy, COL.green, 18);
    arcadeScene.tweens.add({ targets: trainer,  x: cx - 80, duration: 500 });
    arcadeScene.time.delayedCall(550, () => {
      const ball = makeText('◉', cx - 50, cy, COL.red, 24);
      // Arc the ball
      arcadeScene.tweens.add({ targets: ball, x: cx + 140, duration: 500, ease: 'Linear' });
      arcadeScene.tweens.add({ targets: ball, y: cy - 50,  duration: 250, ease: 'Quad.easeOut' });
      arcadeScene.tweens.add({ targets: ball, y: cy,       duration: 250, ease: 'Quad.easeIn', delay: 250, onComplete: () => ball.destroy() });
    });
    arcadeScene.time.delayedCall(1100, () => {
      creature.setText('  ◉  '); creature.setColor(COL.gold);
      const caught = makeText('CAUGHT!', cx + 140, cy - 40, COL.gold, 24);
      fadeOut(caught, 700, { dy: -25 });
      impactBurst(cx + 140, cy, ['★','✦','♥','◉','✧'], [COL.gold, COL.green, COL.white], 14);
      fadeOut(trainer, 600, { dx: -40 });
      fadeOut(creature, 600);
    });
  },

  // JRPG: hero swings sword, enemy takes damage, +99 HP appears
  finalclaudesy: (cx, cy) => {
    const hero  = makeText('[K]\n ⚔', cx - 160, cy, COL.cyan, 22);
    const enemy = makeText(' ◣◢◣\n(◉◉)\n ║║', cx + 120, cy, COL.purple, 18);
    arcadeScene.tweens.add({ targets: hero, x: cx - 30, duration: 500, ease: 'Cubic.easeOut' });
    arcadeScene.time.delayedCall(540, () => {
      const slash = makeText('╲═══►', cx, cy, COL.gold, 28);
      arcadeScene.tweens.add({ targets: slash, x: cx + 140, alpha: { from: 1, to: 0 }, duration: 350, ease: 'Linear', onComplete: () => slash.destroy() });
      const dmg = makeText('-99 HP', cx + 120, cy - 30, COL.red, 22);
      arcadeScene.tweens.add({ targets: dmg, y: cy - 80, alpha: { from: 1, to: 0 }, duration: 700, ease: 'Cubic.easeOut', onComplete: () => dmg.destroy() });
      impactBurst(cx + 120, cy, ['✦','★','◆','╳','*','SLASH!'], [COL.gold, COL.red, COL.white, COL.purple], 16);
    });
    arcadeScene.time.delayedCall(950, () => {
      const win = makeText('VICTORY!', cx, cy, COL.gold, 32);
      win.setAlpha(0);
      arcadeScene.tweens.add({ targets: win, alpha: { from: 0, to: 1 }, scale: { from: 0.5, to: 1.1 }, duration: 250, yoyo: true, hold: 150, onComplete: () => win.destroy() });
      fadeOut(hero, 500, { dx: -60 }); fadeOut(enemy, 500);
    });
  },
};

function spawnBurst(x, y, gameId) {
  if (!arcadeScene) return;
  const scene = SCENES[gameId] || SCENES.ctype;
  scene(x, y);
}

window.spawnBurst = spawnBurst;

function create() {
  arcadeScene = this;

  const canvas = this.game.canvas;
  canvas.style.position = 'fixed';
  canvas.style.top = '0';
  canvas.style.left = '0';
  canvas.style.zIndex = '1';
  canvas.style.pointerEvents = 'none';
  canvas.style.opacity = '0.8';

  const graphics = this.make.graphics({ x: 0, y: 0, add: false });
  graphics.fillStyle(0xcccccc, 1);
  graphics.fillCircle(1.5, 1.5, 1.5);
  graphics.generateTexture('pixel', 3, 3);
  graphics.destroy();

  // Particle emitter — Phaser 3.60+ API. createEmitter() was removed; the
  // ParticleEmitter is now returned directly from this.add.particles(x,y,key,cfg).
  const particles = this.add.particles(0, 0, 'pixel', {
    speed:    { min: 40, max: 100 },
    angle:    { min: 200, max: 340 },
    scale:    { start: 1, end: 0 },
    lifespan: 1500,
    gravityY: 300,
    emitting: false,   // manual emit only — we call emitParticleAt() below
  });

  // Drop a few particles from a random x at the top of the screen each tick.
  this.time.addEvent({
    delay: 300,
    callback: () => {
      particles.emitParticleAt(
        Math.random() * window.innerWidth,
        -20,
        2
      );
    },
    loop: true
  });

  // Screen flicker effect
  this.time.addEvent({
    delay: 5000,
    callback: () => {
      canvas.style.opacity = '0.1';
      this.time.delayedCall(80, () => {
        canvas.style.opacity = '0.8';
      });
    },
    loop: true
  });
}

function update() {}

// Add hover effects + click-burst to game cards
document.addEventListener('DOMContentLoaded', () => {
  const cards = document.querySelectorAll('.game-card');

  cards.forEach(card => {
    card.style.transition = 'all 0.2s';
    card.style.cursor = 'pointer';

    card.addEventListener('mouseenter', () => {
      card.style.boxShadow = '0 0 25px rgba(204, 204, 204, 0.4), inset 0 0 20px rgba(204, 204, 204, 0.1)';
      card.style.transform = 'scale(1.01)';

      // Glitch effect
      const offset = (Math.random() - 0.5) * 1.5;
      card.style.transform = `scale(1.01) translateX(${offset}px)`;
    });

    card.addEventListener('mouseleave', () => {
      card.style.boxShadow = 'none';
      card.style.transform = 'scale(1)';
    });

    // Click: spawn a themed burst from the card's center.
    card.addEventListener('click', (e) => {
      const gameId = card.dataset.game || 'ctype';
      const rect   = card.getBoundingClientRect();
      const cx     = rect.left + rect.width  / 2;
      const cy     = rect.top  + rect.height / 2;
      window.spawnBurst(cx, cy, gameId);

      // Brief satisfying flash on the card itself
      card.style.boxShadow = '0 0 60px rgba(255, 255, 255, 0.8), inset 0 0 30px rgba(255, 255, 255, 0.2)';
      setTimeout(() => {
        card.style.boxShadow = '0 0 25px rgba(204, 204, 204, 0.4), inset 0 0 20px rgba(204, 204, 204, 0.1)';
      }, 180);
    });
  });
});
