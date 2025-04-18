import streamlit as st
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
import plotly.express as px
import plotly.graph_objects as go

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = "company_data"
TARGET_COLLECTION = "engagement_data"
PRODUCT_CATEGORIES = ["earbuds", "skincare", "storage", "plushies", "cosmetics", "stationery", "toys", "home goods", "electronics"]
SUGGESTED_COMMUNITIES = {
    "storage": ["r/minimalism", "r/frugal"],
    "cosmetics": ["r/beauty"],
    "toys": ["r/plushies"],
    "electronics": ["r/gadgets"]
}

try:
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# utilities
@st.cache_resource
def get_mongodb_collection():
    mongo_client = pymongo.MongoClient(MONGODB_URI)
    db = mongo_client[DATABASE_NAME]
    collection = db[TARGET_COLLECTION]
    return collection, mongo_client

def close_mongodb_connection(mongo_client):
    if mongo_client:
        mongo_client.close()
@st.cache_data(ttl=3600)
def load_data():
    collection, mongo_client = get_mongodb_collection()
    try:
        docs = list(collection.find())
        df = pd.DataFrame(docs)
        return df
    except Exception as e:
        st.error(f"Error loading data from MongoDB: {e}")
        return pd.DataFrame()
    finally:
        close_mongodb_connection(mongo_client)
#data preprocessing
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

def calculate_engagement_score(df):
    if df.empty:
        st.warning("No data available to calculate engagement scores.")
        return df

    upvotes = [doc["engagement_metrics"].get("upvotes", 0) for i, doc in df.iterrows()]
    comments = [doc["engagement_metrics"].get("comments", 0) for i, doc in df.iterrows()]
    shares = [doc["engagement_metrics"].get("shares", 0) for i, doc in df.iterrows()]

    max_upvotes = max(upvotes) or 1
    max_comments = max(comments) or 1
    max_shares = max(shares) or 1

    engagement_scores = []
    for i, doc in df.iterrows():
        u = doc["engagement_metrics"].get("upvotes", 0) / max_upvotes
        c = doc["engagement_metrics"].get("comments", 0) / max_comments
        s = doc["engagement_metrics"].get("shares", 0) / max_shares
        score = (0.4 * u) + (0.4 * c) + (0.2 * s)
        engagement_scores.append(score)

    df["engagement_score"] = engagement_scores
    return df

def perform_sentiment_analysis(df):
    if df.empty:
        st.warning("No data available for sentiment analysis.")
        return df

    sia = SentimentIntensityAnalyzer()
    sentiments = []
    sentiment_scores = []
    for i, doc in df.iterrows():
        if 'cleaned_content' in doc and isinstance(doc['cleaned_content'], str): #Added check to make sure that it is a string
            scores = sia.polarity_scores(doc["cleaned_content"])
            sentiment = "positive" if scores["compound"] > 0.05 else "negative" if scores["compound"] < -0.05 else "neutral"
            sentiments.append(sentiment)
            sentiment_scores.append(scores["compound"])
        else:
            sentiments.append(None)
            sentiment_scores.append(None)

    df["sentiment"] = sentiments
    df["sentiment_score"] = sentiment_scores
    return df

def cluster_data(df):
    if df.empty or 'cleaned_content' not in df.columns or 'sentiment_score' not in df.columns:
        st.warning("Insufficient data for clustering.")
        return df

    df = df.dropna(subset=['cleaned_content', 'sentiment_score'])  # Drop rows with missing values
    if df.empty:
         st.warning("No data available for clustering after cleaning.")
         return df

    vectorizer = TfidfVectorizer(max_features=1000)
    X = vectorizer.fit_transform(df["cleaned_content"])

    X = pd.concat([pd.DataFrame(X.toarray()), df["sentiment_score"].reset_index(drop=True)], axis=1)
    X.columns = X.columns.astype(str)

    kmeans = KMeans(n_clusters=5, random_state=42, n_init='auto')  # Explicitly set n_init
    df["cluster"] = kmeans.fit_predict(X)
    return df

def rank_communities(df):
    if df.empty or 'engagement_score' not in df.columns or 'product_category' not in df.columns:
        st.warning("No data available to rank communities. Make sure 'engagement_score' and 'product_category' columns are present.")
        return None

    # Create a list of tuples with (product_category, platform)
    community_data = []
    for product, communities in SUGGESTED_COMMUNITIES.items():
        for community in communities:
            community_data.append((product, community))
    community_df = pd.DataFrame(community_data, columns=['product_category', 'suggested_community'])

    # Merge with the main DataFrame
    df = pd.merge(df, community_df, on='product_category', how='left')

    # Group by suggested community and calculate the mean engagement score
    community_ranking = df.groupby('suggested_community')['engagement_score'].mean().sort_values(ascending=False)

    return community_ranking

def analyze_trends(df):
    if df.empty or 'cleaned_content' not in df.columns or 'timestamp' not in df.columns:
        st.warning("Insufficient data for trend analysis.")
        return None, None

    df['timestamp'] = df['timestamp'].apply(parse_timestamp)

    # Count mentions of "Miniso" over time
    miniso_mentions = {}
    for i, doc in df.iterrows():
        content = doc["cleaned_content"]
        timestamp = doc["timestamp"]

        try:
            if isinstance(timestamp, str):
                month = parser.parse(timestamp).strftime('%Y-%m')  # Parse string to datetime
            elif isinstance(timestamp, float) or isinstance(timestamp, int):
                month = datetime.fromtimestamp(timestamp).strftime('%Y-%m')  # Unix timestamp
            elif isinstance(timestamp, datetime):
                month = timestamp.strftime('%Y-%m')  # Datetime object
            else:
                logger.warning(f"Invalid timestamp format in document {doc['_id']}")
                continue  # Skip to the next document
        except ValueError as e:
            logger.warning(f"Error parsing timestamp in document {doc['_id']}: {e}")
            continue
        if "miniso" in content.lower():  # Case-insensitive check
            miniso_mentions.setdefault(month, 0)
            miniso_mentions[month] += 1

    return miniso_mentions

def predict_trends(df):
    if df.empty or 'timestamp' not in df.columns:
        st.warning("Insufficient data for trend prediction.")
        return {}

    df['timestamp'] = df['timestamp'].apply(parse_timestamp)
    df["month"] = pd.to_datetime(df["timestamp"]).dt.to_period("M")

    time_series = df.groupby(["month", "product_category"]).size().unstack(fill_value=0)
    forecasts = {}
    for category in PRODUCT_CATEGORIES:
        if category in time_series.columns:
            try:
                model = ARIMA(time_series[category], order=(1, 1, 1))
                fit = model.fit()
                forecast = fit.forecast(steps=3)
                forecasts[category] = forecast
            except Exception as e:
                logger.warning(f"Failed to forecast for {category}: {e}")
                forecasts[category] = None
    return forecasts


def main():
    st.set_page_config(layout="wide")  # Use the full width of the page
    st.title("Social Media Analysis Dashboard")

    df = load_data()

    with st.sidebar:
        st.header("Analysis Options")
        run_engagement = st.checkbox("Calculate Engagement Scores", value=True)
        run_sentiment = st.checkbox("Perform Sentiment Analysis", value=True)
        run_clustering = st.checkbox("Cluster Data", value=True)
        run_ranking = st.checkbox("Rank Communities", value=True)
        run_trends = st.checkbox("Analyze Trends", value=True)
        run_prediction = st.checkbox("Predict Trends", value=False)


    plot_key = 1

    if run_engagement:
        df = calculate_engagement_score(df)
        st.subheader("Engagement Analysis")

        if not df.empty:
            platform_engagement = df.groupby("platform")["engagement_score"].mean().sort_values(ascending=False)
            st.write("### Average Engagement Score by Platform")
            fig_platform_engagement = px.bar(
                x=platform_engagement.index,
                y=platform_engagement.values,
                labels={'x': 'Platform', 'y': 'Average Engagement Score'},
                title='Average Engagement Score by Platform'
            )
            st.plotly_chart(fig_platform_engagement, use_container_width=True, key=f"platform_engagement_{plot_key}")
            plot_key += 1
            st.write("### Distribution of Engagement Scores")
            fig_engagement_dist = px.histogram(
                df,
                x="engagement_score",
                title="Distribution of Engagement Scores"
            )
            st.plotly_chart(fig_engagement_dist, use_container_width=True, key=f"engagement_distribution_{plot_key}")
            plot_key += 1

    if run_sentiment:
        df = perform_sentiment_analysis(df)
        st.subheader("Sentiment Analysis")

        if not df.empty:

            sentiment_counts = df["sentiment"].value_counts()
            st.write("### Sentiment Distribution")
            fig_sentiment = px.pie(
                values=sentiment_counts.values,
                names=sentiment_counts.index,
                title="Sentiment Distribution",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            st.plotly_chart(fig_sentiment, use_container_width=True, key=f"sentiment_pie_{plot_key}")
            plot_key += 1

    #clustering(k-means)
    if run_clustering:
        df = cluster_data(df)
        st.subheader("Cluster Analysis")
        if not df.empty:
            # Cluster Distribution
            cluster_counts = df["cluster"].value_counts().sort_index()
            st.write("### Cluster Distribution")
            fig_cluster = px.bar(
                x=cluster_counts.index.astype(str),
                y=cluster_counts.values,
                labels={'x': 'Cluster', 'y': 'Number of Posts'},
                title="Number of Posts per Cluster"
            )
            st.plotly_chart(fig_cluster, use_container_width=True, key=f"cluster_chart_{plot_key}")
            plot_key += 1

    # ranking
    if run_ranking:
        community_ranking = rank_communities(df)
        st.subheader("Community Ranking")

        # sorted ranks
        st.markdown(f"<div style='font-size: 24px; font-weight: bold;'>Suggested Communities</div>", unsafe_allow_html=True)


        if community_ranking is not None:
            fig_community_ranking = px.bar(
                x=community_ranking.index,
                y=community_ranking.values,
                labels={'suggested_community': 'Community', 'engagement_score': 'Average Engagement Score'},
                title='Ranking of Suggested Communities',
            )
            st.plotly_chart(fig_community_ranking, use_container_width=True, key=f"community_ranking_chart_{plot_key}")
            plot_key += 1

    # Trend Analysis
    if run_trends:
        miniso_mentions = analyze_trends(df)

        st.subheader("Trend Analysis")
        if miniso_mentions:
            # Monthly Trends Line Chart for Miniso Mentions
            miniso_mentions_df = pd.DataFrame(list(miniso_mentions.items()), columns=['Month', 'Mentions'])
            try:

                miniso_mentions_df['Month'] = pd.to_datetime(miniso_mentions_df['Month'], format='%Y-%m')

                if miniso_mentions_df['Month'].isnull().any():
                    st.warning("Some months could not be parsed. Check timestamp format.")
                    miniso_mentions_df = miniso_mentions_df.dropna(subset=['Month'])
                miniso_mentions_df = miniso_mentions_df.sort_values(by='Month')

                fig_miniso_trends = px.line(
                    miniso_mentions_df,
                    x='Month',
                    y='Mentions',
                    labels={'Month': 'Month', 'Mentions': 'Number of Mentions'},
                    title='Monthly Trends in Miniso Mentions'
                )
                st.plotly_chart(fig_miniso_trends, use_container_width=True, key=f"miniso_trends_{plot_key}")
                plot_key += 1

            except Exception as e:
                st.error(f"Error generating monthly trends chart: {e}")
        else:
            st.warning("No monthly trends data to display.")
            
    # --- Trend Prediction ---
    if run_prediction:
        forecasts = predict_trends(df)
        st.subheader("Trend Prediction")
        if forecasts:
            for category, forecast in forecasts.items():
                st.write(f"**{category} Forecast (3 months)**:")
                if forecast is not None:
                    st.dataframe(forecast)  # Display forecast as a table
                else:
                    st.write("Forecast not available.")
        else:
            st.write("No forecasts available.")

if __name__ == "__main__":
    main()
