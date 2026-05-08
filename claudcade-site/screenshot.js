const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();

  // Set viewport to capture the full width
  await page.setViewport({
    width: 1400,
    height: 2000
  });

  // Navigate to the site
  await page.goto('http://localhost:8000/public/', {
    waitUntil: 'networkidle2'
  });

  // Take screenshot
  const screenshotPath = path.join(__dirname, 'screenshot.png');
  await page.screenshot({ path: screenshotPath, fullPage: true });

  console.log(`Screenshot saved to: ${screenshotPath}`);

  await browser.close();
})();
