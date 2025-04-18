const { CrawlingAPI } = require('crawlbase');
const api = new CrawlingAPI({ token: 'nZB6pAmOpwrrJwP-vqO6YQ' });
const puppeteer = require("puppeteer");
const fs = require("fs");
const { MongoClient } = require("mongodb");

(async () => {
    // Define product-specific queries in-place
    const productQueries = [
        "Miniso ",
        "Miniso earbuds",
        "Miniso skincare",
        "Miniso storage",
        "Miniso cosmetics",
        "Miniso stationery",
        "Miniso plushies"
    ];

    // Launch Puppeteer
    const browser = await puppeteer.launch({ headless: false, args: ["--window-size=1920,1080"] });
    const page = await browser.newPage();
    const uniqueQuestions = {}; // For deduplication by link

    // Load cookies
    const cookiesFilePath = "cookies.json";
    if (fs.existsSync(cookiesFilePath)) {
        const cookies = JSON.parse(fs.readFileSync(cookiesFilePath, "utf-8"));
        await page.setCookie(...cookies);
        console.log("Loaded cookies successfully.");
    }

    // Scrape each query
    for (const searchQuery of productQueries) {
        const quoraURL = `https://www.quora.com/search?q=${encodeURIComponent(searchQuery)}&type=question`; // Fixed syntax
        console.log(`🔍 Scraping Quora for: ${searchQuery}`);

        await page.goto(quoraURL, { waitUntil: "networkidle2", timeout: 60000 });

        const updatedCookies = await page.cookies();
        fs.writeFileSync(cookiesFilePath, JSON.stringify(updatedCookies, null, 2));
        console.log("Updated cookies saved.");

        // Close login popup if it appears
        try {
            await page.waitForSelector('[aria-label="Close"]', { timeout: 5000 });
            await page.click('[aria-label="Close"]');
            console.log("Closed login popup");
        } catch (e) {
            console.log("No login popup detected");
        }

        // Scroll to load more results
        for (let i = 0; i < 5; i++) {
            console.log(`Scrolling... (${i + 1}/5)`);
            await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
            await new Promise(resolve => setTimeout(resolve, 3000));
        }

        // Extract data (unchanged from your working logic)
        const questionsData = await page.evaluate(() => {
            let results = [];
            document.querySelectorAll("div.q-box span").forEach(el => {
                let title = el.innerText.trim();
                let linkElement = el.closest("a");
                let link = linkElement ? "https://www.quora.com" + linkElement.getAttribute("href") : "N/A";
                let upvotesEl = el.closest("div")?.querySelector("span[class*='Voter']") || el.closest("div")?.querySelector("span");
                let upvotes = upvotesEl ? upvotesEl.innerText.trim() : "0";
                let commentsEl = el.closest("div")?.querySelector("a[href*='/comments/']");
                let comments = commentsEl ? commentsEl.innerText.trim() : "0";
                let timeEl = el.closest("div")?.querySelector("a[aria-label]");
                let time = timeEl ? timeEl.innerText.trim() : "Unknown";

                if (title && link && link !== "N/A") {
                    results.push({ title, link, upvotes, comments, time });
                }
            });
            return results;
        });

        console.log(`Found ${questionsData.length} questions for ${searchQuery}`);

        // Deduplicate in memory
        questionsData.forEach(q => {
            if (!uniqueQuestions[q.link]) {
                uniqueQuestions[q.link] = q;
            }
        });
    }

    const deduplicatedData = Object.values(uniqueQuestions);
    console.log(`Deduplicated to ${deduplicatedData.length} unique questions`);

    if (deduplicatedData.length === 0) {
        console.log("No questions were found across all queries! Check Quora's page structure.");
        await browser.close();
        return;
    }

    // Store in MongoDB
    const client = new MongoClient("mongodb://localhost:27017/");
    await client.connect();
    const db = client.db("company_posts");
    const collection = db.collection("quora_data");

    const mongoData = deduplicatedData.map(q => ({
        record_id: q.link.split("/").pop(),
        platform: "Quora",
        content: q.title,
        title: q.title,
        url: q.link,
        engagement_metrics: {
            upvotes: parseInt(q.upvotes) || 0,
            comments: parseInt(q.comments) || 0,
            shares: 0,
            likes: 0,
            follows: 0
        },
        timestamp: q.time !== "Unknown" ? q.time : new Date().toISOString(),
        platform_specific: {},
        raw_data: q
    }));

    // Check for existing records and insert only new ones
    const existingIds = new Set(
        (await collection.find({ record_id: { $in: mongoData.map(d => d.record_id) } }).toArray())
            .map(doc => doc.record_id)
    );
    const newData = mongoData.filter(d => !existingIds.has(d.record_id) && d.content !== "");

    if (newData.length > 0) {
        await collection.insertMany(newData);
        console.log(`Stored ${newData.length} new unique questions in MongoDB`);
    } else {
        console.log("No new questions to store");
    }

    await browser.close();
    await client.close();
})();