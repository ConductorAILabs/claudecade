const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 2000 });
  await page.goto('file:///Users/jeffmiddleton/Desktop/claudegames/claudcade-site/font-builder.html');
  await page.screenshot({ path: '/Users/jeffmiddleton/Desktop/claudegames/claudcade-site/font-builder-screenshot.png', fullPage: true });
  console.log('Screenshot saved to: font-builder-screenshot.png');
  await browser.close();
})();
