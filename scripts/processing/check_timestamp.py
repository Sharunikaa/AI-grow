import pymongo
from datetime import datetime
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "company_data"
TARGET_COLLECTION = "engagement_data"

mongo_client = pymongo.MongoClient(MONGODB_URI)
db = mongo_client[DATABASE_NAME]
collection = db[TARGET_COLLECTION]

# Print a few documents to check the timestamp format and type
for doc in collection.find().limit(5):
    print(doc["timestamp"], type(doc["timestamp"]))

mongo_client.close()
