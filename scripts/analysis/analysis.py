import pymongo
import pandas as pd
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from collections import Counter
from datetime import datetime
import pytz
import logging
from statsmodels.tsa.arima.model import ARIMA
from dateutil import parser

nltk.download('vader_lexicon')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "company_data"
TARGET_COLLECTION = "engagement_data"

PRODUCT_CATEGORIES = ["earbuds", "skincare", "storage", "plushies", "cosmetics", "stationery", "toys", "home goods",
                      "electronics"]


# utilities

def establish_mongodb_connection():
    mongo_client = pymongo.MongoClient(MONGODB_URI)
    db = mongo_client[DATABASE_NAME]
    collection = db[TARGET_COLLECTION]
    return mongo_client, collection


def close_mongodb_connection(mongo_client):
    if mongo_client:
        mongo_client.close()


def parse_timestamp(timestamp):
    if isinstance(timestamp, (float, int)):  # Handles both float and int timestamps
        try:
            return datetime.fromtimestamp(timestamp, tz=pytz.UTC).replace(tzinfo=None)
        except OSError:
            raise ValueError(f"Invalid UNIX timestamp: {timestamp}")
    elif isinstance(timestamp, str):
        try:
            dt = parser.parse(timestamp)
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except ValueError as e:
            raise ValueError(f"Unsupported timestamp format: {timestamp}, error: {e}")
    elif isinstance(timestamp, datetime):
        return timestamp.replace(tzinfo=None) if timestamp.tzinfo else timestamp
    else:
        raise ValueError(f"Unsupported timestamp format: {timestamp}, type: {type(timestamp)}")


# Functionalities

def calculate_engagement_score():
    mongo_client, collection = establish_mongodb_connection()
    try:
        docs = list(collection.find())
        if not docs:
            print("No data found in the engagement_data collection.")
            return

        upvotes = [doc["engagement_metrics"].get("upvotes", 0) for doc in docs]
        comments = [doc["engagement_metrics"].get("comments", 0) for doc in docs]
        shares = [doc["engagement_metrics"].get("shares", 0) for doc in docs]

        max_upvotes = max(upvotes) or 1
        max_comments = max(comments) or 1
        max_shares = max(shares) or 1

        for doc in docs:
            u = doc["engagement_metrics"].get("upvotes", 0) / max_upvotes
            c = doc["engagement_metrics"].get("comments", 0) / max_comments
            s = doc["engagement_metrics"].get("shares", 0) / max_shares
            score = (0.4 * u) + (0.4 * c) + (0.2 * s)
            collection.update_one({"_id": doc["_id"]}, {"$set": {"engagement_score": score}})

        print("Engagement scores calculated and updated in MongoDB.")
    finally:
        close_mongodb_connection(mongo_client)


def perform_sentiment_analysis():
    mongo_client, collection = establish_mongodb_connection()
    try:
        sia = SentimentIntensityAnalyzer()
        docs = list(collection.find({"cleaned_content": {"$exists": True}}))

        for doc in docs:
            scores = sia.polarity_scores(doc["cleaned_content"])
            sentiment = "positive" if scores["compound"] > 0.05 else "negative" if scores[
                                                                                       "compound"] < -0.05 else "neutral"
            collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"sentiment": sentiment, "sentiment_score": scores["compound"]}}
            )

        print("Sentiment analysis complete and results updated in MongoDB.")
    finally:
        close_mongodb_connection(mongo_client)


def cluster_data():
    mongo_client, collection = establish_mongodb_connection()
    try:
        docs = list(collection.find({"cleaned_content": {"$exists": True}, "sentiment": {"$exists": True}}))
        df = pd.DataFrame(docs)

        vectorizer = TfidfVectorizer(max_features=1000)
        X = vectorizer.fit_transform(df["cleaned_content"])

        X = pd.concat([pd.DataFrame(X.toarray()), df["sentiment_score"].reset_index(drop=True)], axis=1)
        X.columns = X.columns.astype(str)

        kmeans = KMeans(n_clusters=5, random_state=42)
        df["cluster"] = kmeans.fit_predict(X)

        for i, row in df.iterrows():
            collection.update_one({"_id": row["_id"]}, {"$set": {"cluster": int(row["cluster"])}})

        for cluster in range(5):
            cluster_data = df[df["cluster"] == cluster]
            print(f"\nCluster {cluster}:")
            print("  Top Products:", Counter(cluster_data["product_category"]).most_common(3))
            print("  Sentiment:", Counter(cluster_data["sentiment"]).most_common())

        print("Data clustering complete and cluster assignments updated in MongoDB.")
    finally:
        close_mongodb_connection(mongo_client)


def rank_communities():
    mongo_client, collection = establish_mongodb_connection()
    try:
        docs = list(collection.find({"engagement_score": {"$exists": True}}))
        df = pd.DataFrame(docs)

        platform_ranking = df.groupby("platform")["engagement_score"].mean().sort_values(ascending=False)
        print("\nPlatform Ranking by Engagement:")
        print(platform_ranking)

        for category in PRODUCT_CATEGORIES:
            category_data = df[df["product_category"] == category]
            if not category_data.empty:
                top_platforms = category_data.groupby("platform")["engagement_score"].mean().sort_values(
                    ascending=False)
                print(f"\n{category} Top Platforms:")
                print(top_platforms.head(3))

        suggestions = {
            "storage": ["r/minimalism", "r/frugal"],
            "cosmetics": ["r/beauty"],
            "toys": ["r/plushies"],
            "electronics": ["r/gadgets"]
        }
        print("\nSuggested Communities:")
        for category, communities in suggestions.items():
            print(f"{category}: {communities}")
    finally:
        close_mongodb_connection(mongo_client)


def analyze_trends():
    mongo_client, collection = establish_mongodb_connection()
    try:
        docs = list(collection.find({"cleaned_content": {"$exists": True}}))
        product_counts = Counter()
        monthly_trends = {}

        for doc in docs:
            content = doc["cleaned_content"]
            timestamp = doc["timestamp"]
            try:
                month = datetime.fromtimestamp(timestamp).strftime("%Y-%m") if isinstance(timestamp,
                                                                                          float) else datetime.strptime(
                    timestamp, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%Y-%m") if isinstance(timestamp, str) else ""
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid timestamp in document {doc['_id']}: {e}")
                continue

            for category in PRODUCT_CATEGORIES:
                if category in content:
                    product_counts[category] += 1
                    monthly_trends.setdefault(month, Counter())[category] += 1

        logger.info("Top Products:")
        print("Top Products:", product_counts.most_common(5))
        for month, counts in monthly_trends.items():
            logger.info(f"{month}: {counts.most_common(3)}")
            print(f"{month}: {counts.most_common(3)}")
    finally:
        close_mongodb_connection(mongo_client)


def predict_trends():
    mongo_client, collection = establish_mongodb_connection()
    try:
        docs = list(collection.find({"timestamp": {"$exists": True}}))
        df = pd.DataFrame(docs)

        df["parsed_timestamp"] = df["timestamp"].apply(parse_timestamp)
        df["month"] = pd.to_datetime(df["parsed_timestamp"]).dt.to_period("M")

        time_series = df.groupby(["month", "product_category"]).size().unstack(fill_value=0)

        for category in PRODUCT_CATEGORIES:
            if category in time_series.columns:
                try:
                    model = ARIMA(time_series[category], order=(1, 1, 1))
                    fit = model.fit()
                    forecast = fit.forecast(steps=3)
                    logger.info(f"{category} Forecast (3 months) for {category}: {forecast}")
                    print(f"{category} Forecast (3 months): {forecast}")
                except Exception as e:
                    logger.warning(f"Failed to forecast for {category}: {e}")
    finally:
        close_mongodb_connection(mongo_client)


def store_top_engagement_posts():
    mongo_client, collection = establish_mongodb_connection()
    try:
        top_posts = list(collection.find({"engagement_score": {"$exists": True}})
                         .sort("engagement_score", -1)
                         .limit(20))

        if not top_posts:
            print("No posts found with engagement scores.")
            return

        db = mongo_client[DATABASE_NAME]
        top_collection = db["top_engagement_posts"]

        top_collection.delete_many({})

        for post in top_posts:
            top_collection.insert_one(post)

        print("Top 20 engagement posts stored successfully in 'top_engagement_posts' collection.")
    finally:
        close_mongodb_connection(mongo_client)


if __name__ == "_main_":
    calculate_engagement_score()
    perform_sentiment_analysis()
    cluster_data()
    rank_communities()
    analyze_trends()
    predict_trends()
    store_top_engagement_posts()
