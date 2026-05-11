const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 2000 });
  await page.goto('file://' + path.join(__dirname, 'font-builder.html'));
  await page.screenshot({ path: path.join(__dirname, 'font-builder-screenshot.png'), fullPage: true });
  console.log('Screenshot saved to: font-builder-screenshot.png');
  await browser.close();
})();
