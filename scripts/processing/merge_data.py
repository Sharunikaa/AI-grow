import pymongo
from dotenv import load_dotenv

load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "company_data"
SOURCE_COLLECTIONS = ["reddit_data", "discord_data", "quora_data"]
TARGET_COLLECTION = "engagement_data"

PRODUCT_CATEGORIES = ["earbuds", "skincare", "storage", "plushies", "cosmetics", "stationery", "toys", "home goods", "electronics"]

def combine_collections():
    mongo_client = pymongo.MongoClient(MONGODB_URI)
    db = mongo_client[DATABASE_NAME]

    all_data = []
    
    # Reddit Data
    reddit_collection = db["reddit_data"]
    reddit_docs = list(reddit_collection.find())
    print(f"Found {len(reddit_docs)} documents in reddit_data")
    for doc in reddit_docs:
        if "record_id" not in doc:
            print(f"Warning: Skipping Reddit doc missing record_id: {doc['_id']}")
            continue
        all_data.append(doc)

    # Discord Data
    discord_collection = db["discord_data"]
    discord_docs = list(discord_collection.find())
    print(f"Found {len(discord_docs)} documents in discord_data")
    for doc in discord_docs:
        if "record_id" not in doc:
            print(f"Warning: Skipping Discord doc missing record_id: {doc['_id']}")
            continue
        all_data.append(doc)

    # Quora Data (adjust schema)
    quora_collection = db["quora_data"]
    quora_docs = list(quora_collection.find())
    print(f"Found {len(quora_docs)} documents in quora_data")
    for doc in quora_docs:
        content_lower = doc["content"].lower()
        category = next((cat for cat in PRODUCT_CATEGORIES if cat in content_lower), "general")
        all_data.append({
            "record_id": doc["record_id"],
            "platform": doc["platform"],
            "content": doc["content"],
            "title": doc["title"],
            "url": doc["url"],
            "engagement_metrics": doc["engagement_metrics"],
            "timestamp": doc["timestamp"],
            "product_category": category,
            "platform_specific": doc["platform_specific"],
            "raw_data": doc["raw_data"]
        })

    # Deduplicate by record_id
    unique_data = {}
    for item in all_data:
        unique_data[item["record_id"]] = item  # record_id is guaranteed here
    deduplicated_data = list(unique_data.values())
    print(f"Deduplicated to {len(deduplicated_data)} unique records")

    # Store in engagement_data
    target_collection = db[TARGET_COLLECTION]
    existing_ids = set(doc["record_id"] for doc in target_collection.find({"record_id": {"$in": list(unique_data.keys())}}))
    new_data = [item for item in deduplicated_data if item["record_id"] not in existing_ids and item["content"]]

    if new_data:
        target_collection.insert_many(new_data)
        print(f"Stored {len(new_data)} new unique records in engagement_data")
    else:
        print("No new records to store")

    mongo_client.close()

if __name__ == "__main__":
    combine_collections()
