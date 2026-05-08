const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 1400, height: 2400 });
  await page.goto('file:///Users/jeffmiddleton/Desktop/claudegames/claudcade-site/font-test.html');
  await new Promise(r => setTimeout(r, 1000));
  await page.screenshot({ path: '/Users/jeffmiddleton/Desktop/claudegames/claudcade-site/font-test-screenshot.png', fullPage: true });
  console.log('Screenshot saved');
  await browser.close();
})();
