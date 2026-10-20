const { chromium } = require('playwright');
const path = require('path');

(async () => {
    const targetUrl = process.argv[2];
    const launchScriptUrl = process.argv[3];

    if (!targetUrl) {
        console.error(JSON.stringify({ success: false, error: "Missing required targetUrl argument" }));
        process.exit(1);
    }

    let browser;
    try {
        browser = await chromium.launch({
            headless: true,
            proxy: {
                server: 'http://111.101.30.111:9090',
            }
        });

        const context = await browser.newContext({
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport: { width: 1920, height: 1080 },
            javaScriptEnabled: true
        });

        const page = await context.newPage();
        const firedRules = [];
        const conditionNotMet = [];
        const failedToExecute = [];
        const networkTags = [];
        const debugLogs = [];

        page.on('console', msg => {
            const text = msg.text();
            // Capture ANY log containing common Adobe Launch keywords or emojis
            if (text.includes('Rule') && text.includes('fired')) {
                if (!firedRules.includes(text)) firedRules.push(text);
            }

            if (text.includes('Condition') && text.includes('was not met')) {
                if (!conditionNotMet.includes(text)) conditionNotMet.push(text);
            }

            if (text.includes('Failed to execute') && text.includes('rule')) {
                if (!failedToExecute.includes(text)) failedToExecute.push(text);
            }
        });

        page.on('request', request => {
            const url = request.url();
            // Added Samsung's specific CNAME (smetrics.samsung.com) just in case
            if (url.includes('/b/ss/') || url.includes('/ee/v1/interact') || url.includes('smetrics.samsung.com')) {
                if (!networkTags.includes(url)) networkTags.push(url);
            }
        });

        // BROADER INTERCEPTION
        let scriptSwapped = false; // Track if we actually swapped anything

        await page.route('**/*.js*', route => {
            const reqUrl = route.request().url();

            // Catch main launch script ONLY. Exclude RC (Rule Components) and EX (Extensions).
            if (reqUrl.includes('adobedtm') && reqUrl.includes('launch-') && !reqUrl.includes('/RC') && !reqUrl.includes('/EX') && reqUrl !== launchScriptUrl) {
                debugLogs.push(`Swapped MAIN production script: ${reqUrl}`);
                scriptSwapped = true;
                route.continue({ url: launchScriptUrl });
            } else {
                // Let all other scripts (including Launch components) load normally
                route.continue();
            }
        });

        await page.addInitScript(() => {
            window.localStorage.setItem('sdsat_debug', 'true');
            window.sessionStorage.setItem('sdsat_debug', 'true');
        });

        debugLogs.push(`Navigating to ${targetUrl}...`);
        await page.goto(targetUrl, { waitUntil: 'load', timeout: 45000 });

        // Force _satellite to turn on debug logging in the browser console
        await page.evaluate(() => {
            if (window._satellite && typeof window._satellite.setDebug === 'function') {
                window._satellite.setDebug(true);
            } else {
                // Backup in case _satellite is stored under a custom object name
                window._satellite = window._satellite || {};
                window._satellite.setDebug = window._satellite.setDebug || function () { };
            }
        }).catch(() => { });

        // FALLBACK: If we didn't find a script to swap, force inject it manually
        if (launchScriptUrl && !scriptSwapped) {
            debugLogs.push("No production script found to swap. Forcing direct injection of dev script...");
            await page.addScriptTag({ url: launchScriptUrl });
        }

        // AGGRESSIVE COOKIE CLICKER
        try {
            debugLogs.push("Executing aggressive cookie acceptance...");
            await page.evaluate(() => {
                const buttons = Array.from(document.querySelectorAll('button, a'));
                // Find any button that says "Accept All" or "Agree"
                const acceptBtn = buttons.find(b => b.innerText && b.innerText.match(/accept all|agree/i));
                if (acceptBtn) {
                    acceptBtn.click();
                }
            });
            await page.waitForTimeout(4000);
        } catch (e) {
            debugLogs.push("Cookie clicker failed: " + e.message);
        }

        // TAKE A SCREENSHOT
        // This saves 'bot_view.png' right next to this script file
        const screenshotPath = path.join(__dirname, 'bot_view.png');
        try {
            await page.screenshot({ path: screenshotPath, fullPage: true, timeout: 10000 });
            debugLogs.push(`Screenshot saved to: ${screenshotPath}`);
        } catch (e) {
            debugLogs.push("Failed to take screenshot: " + e.message);
        }

        await page.evaluate(() => {
            if (document.body) {
                window.scrollTo(0, document.body.scrollHeight);
            }
        }).catch(e => debugLogs.push("Failed to scroll: " + e.message));
        await page.waitForTimeout(5000);

        console.log(JSON.stringify({
            success: true,
            rules_fired: firedRules,
            condition_not_met: conditionNotMet,
            failed: failedToExecute,
            network_tags: networkTags,
            debug_activity: debugLogs
        }));

    } catch (error) {
        console.log(JSON.stringify({ success: false, error: error.message }));
    } finally {
        if (browser) {
            await browser.close();
        }
        process.exit(0);
    }
})();