const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 2400 });
  await page.goto('file://' + path.join(__dirname, 'font-test.html'));
  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: path.join(__dirname, 'font-test-screenshot.png'), fullPage: true });
  console.log('Screenshot saved');
  await browser.close();
})();
