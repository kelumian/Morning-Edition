require('dotenv').config();
const { chromium } = require('playwright-core');

(async () => {
  console.log("🚀 Launching headless Termux Chromium...");
  
  try {
    const browser = await chromium.launch({
      headless: true,
      executablePath: process.env.CHROMIUM_PATH || '/data/data/com.termux/files/usr/bin/chromium-browser',
      args: [
        '--no-sandbox', 
        '--disable-gpu', 
        '--disable-dev-shm-usage'
      ]
    });
    
    const page = await browser.newPage();
    
    // Test navigation to verify the browser works on your phone
    console.log("🌐 Testing browser engine by loading Google...");
    await page.goto('https://www.google.com');
    const title = await page.title();
    console.log(`✅ Success! Browser loaded page. Title: "${title}"`);
    
    // Your NotebookLM session loading and "Generate" clicking logic goes here
    
    await browser.close();
    console.log("🏁 Browser closed successfully.");
  } catch (error) {
    console.error("❌ Browser automation crashed:", error);
  }
})();
