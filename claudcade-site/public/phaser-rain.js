// Terminal rain background for hero section — uses Phaser 3
(function () {
  const CHARS = '█▒░│─┼╔╗╚╝║═◆★●▷◁▸◈▽△01';

  class RainScene extends Phaser.Scene {
    create() {
      const { width, height } = this.scale;
      const SIZE = 14;
      const cols = Math.ceil(width / SIZE);

      this.drops = Array.from({ length: cols }, (_, i) => {
        const isPink = Math.random() < 0.04;
        const text = this.add.text(
          i * SIZE,
          Phaser.Math.Between(-height, 0),
          CHARS[Phaser.Math.Between(0, CHARS.length - 1)],
          {
            fontFamily: "'Share Tech Mono', 'Courier New', monospace",
            fontSize: `${SIZE - 1}px`,
            color: isPink ? '#ff2d78' : '#e0e0e0',
          }
        ).setAlpha(isPink ? 0.13 : 0.038 + Math.random() * 0.03);

        return {
          text,
          speed: Phaser.Math.FloatBetween(22, 65),
          charTimer: 0,
          charInterval: Phaser.Math.Between(6, 20),
        };
      });
    }

    update(_, delta) {
      const dt = delta / 1000;
      const { height } = this.scale;

      this.drops.forEach(d => {
        d.text.y += d.speed * dt;
        d.charTimer++;
        if (d.charTimer >= d.charInterval) {
          d.charTimer = 0;
          d.text.setText(CHARS[Math.floor(Math.random() * CHARS.length)]);
        }
        if (d.text.y > height + 20) {
          d.text.y = Phaser.Math.Between(-60, -10);
        }
      });
    }
  }

  function init() {
    const hero = document.getElementById('hero');
    if (!hero || typeof Phaser === 'undefined') return;

    const canvas = document.createElement('canvas');
    canvas.id = 'rain-canvas';
    hero.insertBefore(canvas, hero.firstChild);

    const game = new Phaser.Game({
      type: Phaser.CANVAS,
      canvas,
      transparent: true,
      width: hero.offsetWidth || window.innerWidth,
      height: hero.offsetHeight || window.innerHeight,
      scene: RainScene,
      input: false,
      audio: { noAudio: true },
      scale: { mode: Phaser.Scale.NONE },
    });

    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        game.scale.resize(hero.offsetWidth, hero.offsetHeight);
      }, 150);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
