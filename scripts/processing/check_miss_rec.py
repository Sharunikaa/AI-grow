import pymongo
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "company_data"

mongo_client = pymongo.MongoClient(MONGODB_URI)
db = mongo_client[DATABASE_NAME]

collections = ["reddit_data", "discord_data", "quora_data"]

for collection_name in collections:
    collection = db[collection_name]
    total_docs = collection.count_documents({})
    missing_record_id = collection.count_documents({"record_id": {"$exists": False}})
    print(f"{collection_name}: Total docs = {total_docs}, Missing record_id = {missing_record_id}")

mongo_client.close()
