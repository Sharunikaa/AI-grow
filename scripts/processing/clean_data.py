import pymongo
import re
import nltk
import emoji
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "company_data"
TARGET_COLLECTION = "engagement_data"

def preprocess_text(text):
    text = emoji.demojize(text)
    text = text.lower()
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'[^a-z\s]', '', text)
    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    tokens = [word for word in tokens if word not in stop_words]
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(word) for word in tokens]
    return ' '.join(tokens)

def preprocess_data():
    mongo_client = pymongo.MongoClient(MONGODB_URI)
    db = mongo_client[DATABASE_NAME]
    collection = db[TARGET_COLLECTION]
    
    docs = list(collection.find())
    print(f"Preprocessing {len(docs)} documents")

    for doc in docs:
        if "content" in doc and doc["content"]:
            cleaned_content = preprocess_text(doc["content"])
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"cleaned_content": cleaned_content}}
            )
    print("Preprocessing complete")
    mongo_client.close()

if __name__ == "__main__":
    preprocess_data()
