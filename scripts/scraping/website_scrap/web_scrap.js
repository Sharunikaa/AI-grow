const puppeteer = require("puppeteer");
const fs = require("fs");
const { MongoClient } = require("mongodb");
const path = require("path");
const crypto = require("crypto");

(async () => {
    const urls = [
        "https://www.minisoindia.com/our-blogs",
        "https://www.minisoindia.com/about-miniso",
        "https://www.minisoindia.com/store-locator",
        "https://www.minisoindia.com/"
    ];

    const browser = await puppeteer.launch({
        headless: false,
        args: ["--window-size=1920,1080", "--disable-blink-features=AutomationControlled"]
    });
    const page = await browser.newPage();

    const cookiesFilePath = path.join(__dirname, "cookies.json");
    if (fs.existsSync(cookiesFilePath)) {
        const cookies = JSON.parse(fs.readFileSync(cookiesFilePath, "utf-8"));
        await page.setCookie(...cookies);
        console.log("Loaded cookies successfully.");
    }

    const uniqueDocs = new Map();

    async function scrapeUrl(url, retries = 3) {
        for (let attempt = 0; attempt < retries; attempt++) {
            try {
                console.log(`🔍 Scraping Miniso India: ${url} (Attempt ${attempt + 1})`);
                await page.goto(url, { waitUntil: "networkidle2", timeout: 120000 });

                const updatedCookies = await page.cookies();
                fs.writeFileSync(cookiesFilePath, JSON.stringify(updatedCookies, null, 2));
                console.log("Updated cookies saved.");

                for (let i = 0; i < 5; i++) {
                    console.log(`Scrolling... (${i + 1}/5)`);
                    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
                    await new Promise(resolve => setTimeout(resolve, 3000));
                }

                const rawData = await page.evaluate(() => {
                    const results = [];

                    // About Page
                    if (window.location.href.includes("about-miniso")) {
                        document.querySelectorAll(".tab-pane#brand_profile p").forEach(p => {
                            const content = p.innerText.trim();
                            if (content) {
                                results.push({ type: "general", content, html: p.outerHTML });
                            }
                        });
                    }

                    // Store Locator
                    if (window.location.href.includes("store-locator")) {
                        // From visible store blocks
                        document.querySelectorAll(".store_locator").forEach(el => {
                            const name = el.querySelector("strong")?.innerText.trim() || "";
                            const details = Array.from(el.querySelectorAll("p")).map(p => p.innerText.trim()).join("\n");
                            if (name || details) {
                                results.push({ type: "location", content: `${name}\n${details}`, html: el.outerHTML });
                            }
                        });
                        // From select options
                        document.querySelectorAll("#storelocation option").forEach(option => {
                            const name = option.innerText.trim();
                            if (name) {
                                results.push({ type: "location", content: name, html: option.outerHTML });
                            }
                        });
                        // From script JSON
                        document.querySelectorAll("script").forEach(script => {
                            const scriptContent = script.textContent;
                            if (scriptContent.includes("store[")) {
                                const storeMatches = scriptContent.match(/store\['(\d+)'\]='([^']+)'/g);
                                if (storeMatches) {
                                    storeMatches.forEach(match => {
                                        const [, id, mapUrl] = match.match(/store\['(\d+)'\]='([^']+)'/);
                                        const storeEl = document.querySelector(`.storeloc[for="${id}"]`)?.closest(".store_locator");
                                        const name = storeEl?.querySelector("strong")?.innerText.trim() || "";
                                        const details = storeEl ? Array.from(storeEl.querySelectorAll("p")).map(p => p.innerText.trim()).join("\n") : "";
                                        results.push({
                                            type: "location",
                                            content: `${name}\n${details}\nMap: ${mapUrl}`,
                                            html: storeEl?.outerHTML || ""
                                        });
                                    });
                                }
                            }
                        });
                    }

                    // Blogs
                    if (window.location.href.includes("our-blogs")) {
                        document.querySelectorAll("article, .blog-post, .post, div").forEach(el => {
                            const content = el.innerText.trim();
                            if (content && content.length > 20) {
                                results.push({ type: "blog", content, html: el.outerHTML });
                            }
                        });
                    }

                    // Homepage (categories or banners)
                    if (window.location.href === "https://www.minisoindia.com/") {
                        document.querySelectorAll(".category, .banner, .section").forEach(el => {
                            const content = el.innerText.trim();
                            if (content && content.length > 20) {
                                results.push({ type: "general", content, html: el.outerHTML });
                            }
                        });
                    }

                    return results;
                });

                console.log(`Found ${rawData.length} raw content blocks for ${url}`);
                rawData.forEach(item => {
                    const key = `${url}-${item.type}-${item.content || item.html}`;
                    if (!uniqueDocs.has(key)) {
                        uniqueDocs.set(key, {
                            type: item.type,
                            content: item.content || "",
                            html: item.html || "",
                            source_url: url,
                            timestamp: new Date().toISOString()
                        });
                    }
                });

                return;
            } catch (error) {
                console.error(`Error scraping ${url}: ${error.message}`);
                if (attempt < retries - 1) {
                    await new Promise(resolve => setTimeout(resolve, 5000));
                } else {
                    console.error(`Failed after ${retries} attempts for ${url}`);
                }
            }
        }
    }

    for (const url of urls) {
        await scrapeUrl(url);
    }

    // Products
    const productCategoryUrl = "https://www.minisoindia.com/category/top-categories/daily-life-products/";
    console.log(`🔍 Following product category: ${productCategoryUrl}`);
    let pageNum = 1;
    let hasNext = true;

    while (hasNext && pageNum <= 7) {
        const paginatedUrl = `${productCategoryUrl}${pageNum > 1 ? `?page=${pageNum}` : ""}`;
        await scrapeUrl(paginatedUrl);

        const productData = await page.evaluate(() => {
            const results = [];
            document.querySelectorAll(".all-products-box").forEach(el => {
                const name = el.querySelector(".shop-title a")?.innerText.trim() || "";
                const url = el.querySelector("a")?.href || "";
                if (name && url) {
                    results.push({ type: "product", content: JSON.stringify({ name, url }), html: "" });
                }
            });
            return results;
        });

        console.log(`Found ${productData.length} products on page ${pageNum}`);
        productData.forEach(item => {
            const key = `${paginatedUrl}-${item.type}-${item.content}`;
            if (!uniqueDocs.has(key)) {
                uniqueDocs.set(key, {
                    type: item.type,
                    content: item.content,
                    html: item.html,
                    source_url: paginatedUrl,
                    timestamp: new Date().toISOString()
                });
            }
        });

        hasNext = await page.evaluate((nextPage) => !!document.querySelector(`a[href*="?page=${nextPage}"]`), pageNum + 1);
        pageNum++;
    }

    const deduplicatedDocs = Array.from(uniqueDocs.values());
    console.log(`Deduplicated to ${deduplicatedDocs.length} unique raw documents`);

    if (deduplicatedDocs.length === 0) {
        console.log("No raw documents found! Check selectors or page structure.");
        await browser.close();
        return;
    }

    const client = new MongoClient("mongodb://localhost:27017/");
    try {
        await client.connect();
        const db = client.db("company_posts");
        const collection = db.collection("miniso_raw_data");

        const mongoData = deduplicatedDocs.map(doc => ({
            record_id: `${doc.source_url.split("/").pop()}-${crypto.randomUUID().split("-")[0]}`,
            platform: "MinisoIndia",
            content: doc.content,
            html: doc.html,
            url: doc.source_url,
            type: doc.type,
            timestamp: doc.timestamp,
            platform_specific: {},
            raw_data: doc
        }));

        const existingIds = new Set(
            (await collection.find({ record_id: { $in: mongoData.map(d => d.record_id) } }).toArray())
                .map(doc => doc.record_id)
        );
        const newData = mongoData.filter(d => !existingIds.has(d.record_id) && (d.content || d.html));

        if (newData.length > 0) {
            await collection.insertMany(newData);
            console.log(`Stored ${newData.length} new unique raw documents in MongoDB`);
        } else {
            console.log("No new raw documents to store");
        }
    } catch (error) {
        console.error("MongoDB error:", error);
    } finally {
        await client.close();
    }

    await browser.close();
})();