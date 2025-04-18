import os
import praw
import pymongo
from dotenv import load_dotenv

load_dotenv()

def fetch_reddit_data(queries, limit_per_query=100):
    CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    USER_AGENT = os.getenv("REDDIT_USER_AGENT")
    MONGODB_URI = os.getenv("MONGODB_URI")
    DATABASE_NAME = "company_data"
    COLLECTION_NAME = "reddit_data"
    
    mongo_client = pymongo.MongoClient(MONGODB_URI)
    db = mongo_client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]
    
    reddit = praw.Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, user_agent=USER_AGENT)
    all_posts = []
    
    # Product categories for tagging
    product_categories = ["earbuds", "skincare", "storage", "cosmetics", "stationery", "plushies", "toys", "accessories", "home goods", "electronics"]

    for query in queries:
        try:
            posts = list(reddit.subreddit('all').search(query=query, limit=limit_per_query))
            print(f"Query: {query} -> Found {len(posts)} posts")
            for post in posts:
                content_text = (post.title + " " + post.selftext).lower()
                # Tag product category based on content
                category = next((cat for cat in product_categories if cat in content_text), "general")
                post_data = {
                    "record_id": post.id,
                    "platform": "Reddit",
                    "content": post.selftext,
                    "title": post.title,
                    "author": str(post.author) if post.author else "unknown",
                    "timestamp": post.created_utc,
                    "url": post.url,
                    "engagement_metrics": {
                        "upvotes": post.score,
                        "comments": post.num_comments,
                        "shares": post.num_crossposts,
                        "likes": 0,
                        "follows": 0
                    },
                    "product_category": category,
                    "platform_specific": {"subreddit": post.subreddit.display_name},
                    "raw_data": {"post_id": post.id}
                }
                all_posts.append(post_data)
        except Exception as e:
            print(f"Error with query {query}: {e}")
    
    # Remove duplicates and insert
    unique_posts = {post["record_id"]: post for post in all_posts}
    if unique_posts:
        # Check for existing posts to avoid duplicates
        existing_ids = set(doc["record_id"] for doc in collection.find({"record_id": {"$in": list(unique_posts.keys())}}, {"record_id": 1}))
        new_posts = [post for post in unique_posts.values() if post["record_id"] not in existing_ids]
        if new_posts:
            collection.insert_many(new_posts)
            print(f"Stored {len(new_posts)} unique Reddit posts")
    return list(unique_posts.values())

if __name__ == "__main__":
    product_queries = [
        "Miniso", "Miniso haul", "Miniso products",
        "Miniso earbuds", "Miniso skincare", "Miniso storage", "Miniso cosmetics",
        "Miniso stationery", "Miniso plushies", "Miniso toys", "Miniso accessories",
        "Miniso home goods", "Miniso electronics", "Miniso affordable",
        "need affordable earbuds", "need affordable storage", "Miniso minimal lifestyle",
        "Daiso earbuds", "Muji storage"
    ]
    reddit_posts = fetch_reddit_data(product_queries)
