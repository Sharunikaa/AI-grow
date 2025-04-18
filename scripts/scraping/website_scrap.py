import requests
from bs4 import BeautifulSoup
import pymongo
import re
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGODB_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "company_data"
MINISO_QA_COLLECTION = "miniso_qa_data"

def preprocess_text(text):
    """Clean and normalize text for analysis (from clean_data.py)."""
    text = text.lower()
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'[^a-z\s#/@:!]', '', text)  # Keep basic symbols
    return text

def scrape_miniso_page_static(url):
    """Scrape static content from Miniso India using Beautiful Soup."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Retrieved {url} with status {response.status_code}")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug: Print first 500 chars of HTML to verify content
        logger.debug(f"HTML sample from {url}: {soup.prettify()[:500]}")
        
        qa_data = []
        
        # Scrape products (e.g., /products, adjust if not on these URLs)
        if "products" in url.lower():
            products = soup.find_all('div', class_='product-grid-item')  # Adjust class after inspection
            for product in products:
                title = product.find('h3', class_='product-name').text.strip() if product.find('h3', class_='product-name') else ""
                description = product.find('p', class_='product-details').text.strip() if product.find('p', class_='product-details') else ""
                if title and description:
                    cleaned_content = preprocess_text(description)
                    category = infer_category(title)
                    qa = generate_qa(cleaned_content, category)
                    if qa:
                        qa_data.append({
                            "question": qa["question"],
                            "answer": qa["answer"],
                            "product_category": category,
                            "source_url": url,
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        })
                    else:
                        logger.warning(f"No Q&A generated for product: {title}")

        # Scrape blogs/articles (e.g., /our-blogs, /articles)
        elif "blogs" in url.lower() or "articles" in url.lower():
            articles = soup.find_all('article', class_='blog-post')  # Adjust class after inspection
            for article in articles:
                content = article.find('div', class_='blog-content').text.strip() if article.find('div', class_='blog-content') else ""
                if content:
                    cleaned_content = preprocess_text(content)
                    category = infer_category_from_content(cleaned_content)
                    qa = generate_qa(cleaned_content, category)
                    if qa:
                        qa_data.append({
                            "question": qa["question"],
                            "answer": qa["answer"],
                            "product_category": category,
                            "source_url": url,
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        })
                    else:
                        logger.warning(f"No Q&A generated for blog content: {content[:50]}...")

        # Scrape FAQs or static info (e.g., /about-miniso, /, /store-locator)
        else:
            content_blocks = soup.find_all('div', class_='content-block')  # Adjust class after inspection
            for block in content_blocks:
                content = block.text.strip()
                if content:
                    cleaned_content = preprocess_text(content)
                    category = "general"
                    qa = generate_qa(cleaned_content, category)
                    if qa:
                        qa_data.append({
                            "question": qa["question"],
                            "answer": qa["answer"],
                            "product_category": category,
                            "source_url": url,
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        })
                    else:
                        logger.warning(f"No Q&A generated for content block: {content[:50]}...")

        logger.info(f"Scraped {len(qa_data)} Q&A pairs from {url} (static)")
        return qa_data
    except Exception as e:
        logger.error(f"Error scraping {url} (static): {e}")
        return []

def scrape_miniso_page_dynamic(url):
    """Scrape dynamic content from Miniso India using Selenium (if static scraping fails)."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')  # Avoid detection
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(url)
        time.sleep(3)  # Wait for JavaScript to load
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        logger.debug(f"Dynamic HTML sample from {url}: {soup.prettify()[:500]}")
        
        qa_data = []
        if "products" in url.lower():
            products = soup.find_all('div', class_='product-grid-item')  # Adjust class after inspection
            for product in products:
                title = product.find('h3', class_='product-name').text.strip() if product.find('h3', class_='product-name') else ""
                description = product.find('p', class_='product-details').text.strip() if product.find('p', class_='product-details') else ""
                if title and description:
                    cleaned_content = preprocess_text(description)
                    category = infer_category(title)
                    qa = generate_qa(cleaned_content, category)
                    if qa:
                        qa_data.append({
                            "question": qa["question"],
                            "answer": qa["answer"],
                            "product_category": category,
                            "source_url": url,
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        })
        elif "blogs" in url.lower() or "articles" in url.lower():
            articles = soup.find_all('article', class_='blog-post')  # Adjust class after inspection
            for article in articles:
                content = article.find('div', class_='blog-content').text.strip() if article.find('div', class_='blog-content') else ""
                if content:
                    cleaned_content = preprocess_text(content)
                    category = infer_category_from_content(cleaned_content)
                    qa = generate_qa(cleaned_content, category)
                    if qa:
                        qa_data.append({
                            "question": qa["question"],
                            "answer": qa["answer"],
                            "product_category": category,
                            "source_url": url,
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        })
        else:
            content_blocks = soup.find_all('div', class_='content-block')  # Adjust class after inspection
            for block in content_blocks:
                content = block.text.strip()
                if content:
                    cleaned_content = preprocess_text(content)
                    category = "general"
                    qa = generate_qa(cleaned_content, category)
                    if qa:
                        qa_data.append({
                            "question": qa["question"],
                            "answer": qa["answer"],
                            "product_category": category,
                            "source_url": url,
                            "timestamp": datetime.utcnow().isoformat() + "Z"
                        })

        logger.info(f"Scraped {len(qa_data)} Q&A pairs from {url} (dynamic)")
        return qa_data
    except Exception as e:
        logger.error(f"Error scraping {url} (dynamic): {e}")
        return []
    finally:
        driver.quit()

def infer_category(product_name):
    """Infer product category based on product name (simplified heuristic)."""
    product_name_lower = product_name.lower()
    categories = {
        "plushies": ["bear", "plushie", "toy"],
        "storage": ["bin", "box", "organizer"],
        "cosmetics": ["skincare", "cosmetic", "makeup"],
        "stationery": ["pen", "notebook", "pencil"],
        "kitchenware": ["mug", "plate", "utensil"]
    }
    for category, keywords in categories.items():
        if any(keyword in product_name_lower for keyword in keywords):
            return category
    return "general"

def infer_category_from_content(content):
    """Infer product category from blog/article content."""
    content_lower = content.lower()
    categories = {
        "plushies": ["bear", "plushie", "toy"],
        "storage": ["bin", "box", "organizer"],
        "cosmetics": ["skincare", "cosmetic", "makeup"],
        "stationery": ["pen", "notebook", "pencil"],
        "kitchenware": ["mug", "plate", "utensil"]
    }
    for category, keywords in categories.items():
        if any(keyword in content_lower for keyword in keywords):
            return category
    return "general"

def generate_qa(content, product_category):
    """Generate Q&A pairs from content with enhanced logic and debugging."""
    if not content:
        logger.warning("Empty content provided to generate_qa")
        return None

    logger.info(f"Generating Q&A for content: {content[:100]}... Category: {product_category}")
    keywords = ["features", "details", "uses", "benefits", "product", "item"]
    if any(keyword in content for keyword in keywords) or product_category != "general":
        question = f"What are the features or details of Miniso’s {product_category} products mentioned here?"
        answer = content
        return {"question": question, "answer": answer}
    logger.warning(f"No Q&A generated for content: {content[:100]}... Category: {product_category}")
    return None

def store_miniso_qa():
    mongo_client = pymongo.MongoClient(MONGODB_URI)
    db = mongo_client[DATABASE_NAME]
    collection = db[MINISO_QA_COLLECTION]

    base_urls = [
        "https://www.minisoindia.com/our-blogs",
        "https://www.minisoindia.com/about-miniso",
        "https://www.minisoindia.com/store-locator",
        "https://www.minisoindia.com/"
    ]

    all_qa_data = []
    for url in base_urls:
        # Try static scraping first
        qa_data = scrape_miniso_page_static(url)
        if not qa_data:  # If static fails, try dynamic
            qa_data = scrape_miniso_page_dynamic(url)
            if not qa_data:
                logger.warning(f"No Q&A pairs scraped from {url} (static or dynamic)")
        if qa_data:
            all_qa_data.extend(qa_data)

    if all_qa_data:
        collection.insert_many(all_qa_data)
        logger.info(f"Stored {len(all_qa_data)} Q&A pairs in MongoDB")
    else:
        logger.warning("No Q&A pairs to store")

    mongo_client.close()

if __name__ == "__main__":
    store_miniso_qa()