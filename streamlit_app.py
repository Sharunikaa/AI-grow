import os
import json
import streamlit as st
import requests
import pandas as pd
import pymongo
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from datetime import datetime
import pytz
import logging
from statsmodels.tsa.arima.model import ARIMA
from dateutil import parser
import plotly.express as px
import streamlit.components.v1 as components
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ---------------------------
# Global Constants & Setup
# ---------------------------
st.set_page_config(page_title="AI-Grow Dashboard", layout="wide")

# Load configuration from environment variables
BASE_URL = os.getenv("BASE_URL", "http://localhost:5000")
CHATBOT_API_URL = os.getenv("CHATBOT_API_URL", "http://localhost:7000/chatbot_response")
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "company_data")
TOP_POSTS_COLLECTION = os.getenv("TOP_POSTS_COLLECTION", "top_engagement_posts")
TARGET_COLLECTION = os.getenv("TARGET_COLLECTION", "engagement_data")
SLACK_WORKSPACE_URL = os.getenv("SLACK_WORKSPACE_URL")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

PRODUCT_CATEGORIES = ["earbuds", "skincare", "storage", "plushies", "cosmetics", "stationery", "toys", "home goods", "electronics"]
SUGGESTED_COMMUNITIES = {
    "storage": ["r/minimalism", "r/frugal"],
    "cosmetics": ["r/beauty"],
    "toys": ["r/plushies"],
    "electronics": ["r/gadgets"]
}

# Ensure nltk vader lexicon is available
try:
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------
# Chatbot Interactive Functions (Using Chatbot API)
# ---------------------------
def load_chat_history():
    return json.load(open("chat_history.json", "r")) if os.path.exists("chat_history.json") else []

def save_chat_history(history):
    with open("chat_history.json", "w") as f:
        json.dump(history, f)

def clear_chat_history():
    if os.path.exists("chat_history.json"):
        os.remove("chat_history.json")

def process_user_input_api():
    user_query = st.session_state.user_input.strip()
    if not user_query:
        return
    data = {"question": user_query}
    try:
        response = requests.post(CHATBOT_API_URL, json=data)
        if response.status_code == 200:
            answer = response.json().get("answer")
        else:
            answer = "Error: Unable to retrieve chatbot response."
    except Exception as e:
        answer = f"Error: {e}"
    st.session_state.history.append({"origin": "human", "message": user_query})
    st.session_state.history.append({"origin": "ai", "message": answer})
    save_chat_history(st.session_state.history)

def render_chat_interface():
    st.title("🚀 AI Engagement Assistant")
    chat_area = st.container()
    with chat_area:
        for chat in st.session_state.history:
            chat_bubble = f"""
            <div class='chat-row {'row-reverse' if chat['origin'] == 'human' else ''}' style="margin: 10px 0;">
                <div style="padding: 10px; border-radius: 10px; max-width: 80%; word-wrap: break-word; {'background-color: #0078FF; color: white;' if chat['origin']=='human' else 'background-color: #f0f0f0; color: black;'}">
                    {chat['message']}
                </div>
            </div>
            """
            st.markdown(chat_bubble, unsafe_allow_html=True)
    with st.form("chat-form"):
        st.text_input("Ask about engagement trends, posts, and insights! ✨", key="user_input")
        st.form_submit_button("Submit", on_click=process_user_input_api)
    components.html("""
    <script>
    const streamlitDoc = window.parent.document;
    const buttons = Array.from(streamlitDoc.querySelectorAll('.stButton > button'));
    const submitButton = buttons.find(el => el.innerText === 'Submit');
    streamlitDoc.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            submitButton.click();
        }
    });
    </script>
    """, height=0, width=0)

def chatbot_interactive():
    st.header("Chatbot Interactive")
    if "history" not in st.session_state:
        st.session_state.history = load_chat_history()
    render_chat_interface()

# ---------------------------
# Slack Approval Functions
# ---------------------------
def get_questions():
    client = pymongo.MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    collection = db[TOP_POSTS_COLLECTION]
    query = {"engagement_score": {"$exists": True}}
    cursor = collection.find(query).sort("engagement_score", -1)
    questions = []
    for doc in cursor:
        question = doc.get("cleaned_content") or doc.get("title") or doc.get("content")
        questions.append(question)
    client.close()
    return questions

def get_chatbot_response_api(question):
    data = {"question": question}
    try:
        response = requests.post(CHATBOT_API_URL, json=data)
        if response.status_code == 200:
            return response.json().get("answer")
        else:
            return "Error: Unable to retrieve chatbot response."
    except Exception as e:
        return f"Error: {e}"

def send_to_slack(message):
    payload = {"text": message}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        return response.status_code
    except Exception as e:
        return None

def slack_approval_page():
    st.header("Slack Approval")
    st.markdown("This section displays top questions with their AI-generated responses. Please choose 'Yes' to approve each Q&A for posting to Slack.")
    questions = get_questions()
    if not questions:
        st.warning("No questions found.")
        return
    for idx, question in enumerate(questions, start=1):
        answer = get_chatbot_response_api(question)
        st.markdown(f"**Q{idx}:** {question}")
        st.markdown(f"**A{idx}:** {answer}")
        approval_choice = st.radio(f"Approve Q{idx}?", options=["Yes", "No"], key=f"approval_choice_{idx}")
        if approval_choice == "Yes":
            qa_message = (
                f"*Q{idx}:* {question}\n"
                f"*A{idx}:* {answer}\n"
                f"Approved for posting."
            )
            status = send_to_slack(qa_message)
            if status == 200:
                st.success(f"Q{idx} approved and sent to Slack.")
            else:
                st.error(f"Failed to send Q{idx} to Slack.")
        else:
            st.info(f"Q{idx} not approved.")
        st.markdown("---")

# ---------------------------
# Dashboard Visualizations Functions
# ---------------------------
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

def parse_timestamp(timestamp):
    if isinstance(timestamp, (float, int)):
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
        if 'cleaned_content' in doc and isinstance(doc['cleaned_content'], str):
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

    df = df.dropna(subset=['cleaned_content', 'sentiment_score'])
    if df.empty:
         st.warning("No data available for clustering after cleaning.")
         return df

    vectorizer = TfidfVectorizer(max_features=1000)
    X = vectorizer.fit_transform(df["cleaned_content"])

    X = pd.concat([pd.DataFrame(X.toarray()), df["sentiment_score"].reset_index(drop=True)], axis=1)
    X.columns = X.columns.astype(str)

    kmeans = KMeans(n_clusters=5, random_state=42, n_init='auto')
    df["cluster"] = kmeans.fit_predict(X)
    return df

def rank_communities(df):
    if df.empty or 'engagement_score' not in df.columns or 'product_category' not in df.columns:
        st.warning("No data available to rank communities. Make sure 'engagement_score' and 'product_category' columns are present.")
        return None

    community_data = []
    for product, communities in SUGGESTED_COMMUNITIES.items():
        for community in communities:
            community_data.append((product, community))
    community_df = pd.DataFrame(community_data, columns=['product_category', 'suggested_community'])
    df = pd.merge(df, community_df, on='product_category', how='left')
    community_ranking = df.groupby('suggested_community')['engagement_score'].mean().sort_values(ascending=False)
    return community_ranking

def analyze_trends(df):
    if df.empty or 'cleaned_content' not in df.columns or 'timestamp' not in df.columns:
        st.warning("Insufficient data for trend analysis.")
        return None

    df['timestamp'] = df['timestamp'].apply(parse_timestamp)
    miniso_mentions = {}
    for i, doc in df.iterrows():
        content = doc["cleaned_content"]
        timestamp = doc["timestamp"]
        try:
            if isinstance(timestamp, str):
                month = parser.parse(timestamp).strftime('%Y-%m')
            elif isinstance(timestamp, (float, int)):
                month = datetime.fromtimestamp(timestamp).strftime('%Y-%m')
            elif isinstance(timestamp, datetime):
                month = timestamp.strftime('%Y-%m')
            else:
                logger.warning(f"Invalid timestamp format in document {doc.get('_id', '')}")
                continue
        except ValueError as e:
            logger.warning(f"Error parsing timestamp in document {doc.get('_id', '')}: {e}")
            continue
        if "miniso" in content.lower():
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

def dashboard_page():
    st.subheader("Social Media Analysis Dashboard")
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

    if run_clustering:
        df = cluster_data(df)
        st.subheader("Cluster Analysis")
        if not df.empty:
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

    if run_ranking:
        community_ranking = rank_communities(df)
        st.subheader("Community Ranking")
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

    if run_trends:
        miniso_mentions = analyze_trends(df)
        st.subheader("Trend Analysis")
        if miniso_mentions:
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
            
    if run_prediction:
        forecasts = predict_trends(df)
        st.subheader("Trend Prediction")
        if forecasts:
            for category, forecast in forecasts.items():
                st.write(f"**{category} Forecast (3 months)**:")
                if forecast is not None:
                    st.dataframe(forecast)
                else:
                    st.write("Forecast not available.")
        else:
            st.write("No forecasts available.")

# ---------------------------
# Home Page
# ---------------------------
def home_page():
    st.subheader("📌 Community Question & Engagement Metrics")
    
    # Get engagement metrics from API
    try:
        metrics_response = requests.get(f"{BASE_URL}/get_engagement_metrics")
        metrics_data = metrics_response.json() if metrics_response.status_code == 200 else {}
    except Exception as e:
        st.error("Error fetching engagement metrics: " + str(e))
        metrics_data = {}
        
    col1, col2, col3 = st.columns(3)
    col1.metric(label="👍 Total Upvotes", value=metrics_data.get("upvotes", 0))
    col2.metric(label="😊 Total Positive", value=metrics_data.get("positive_sentiment", 0))
    col3.metric(label="😠 Total Negative", value=metrics_data.get("negative_sentiment", 0))
    
    st.subheader("📊 Sentiment Analysis Over Time")
    try:
        sentiment_response = requests.get(f"{BASE_URL}/get_sentiment_analysis")
        sentiment_data = sentiment_response.json() if sentiment_response.status_code == 200 else {}
    except Exception as e:
        st.error("Error fetching sentiment analysis data: " + str(e))
        sentiment_data = {}

    if sentiment_data:
        df_sentiment = pd.DataFrame(sentiment_data)
        # Ensure the timestamp column is a datetime object
        df_sentiment['timestamp'] = pd.to_datetime(df_sentiment['timestamp'], errors='coerce')
        # Drop rows with invalid dates
        df_sentiment = df_sentiment.dropna(subset=['timestamp'])
        # Group by date (daily average) to smooth the data
        df_daily = df_sentiment.groupby(df_sentiment['timestamp'].dt.date)['sentiment_score'].mean().reset_index()
        df_daily.columns = ['Date', 'Average Sentiment Score']
        
        # Create a neat line chart with markers using Plotly Express
        fig = px.line(df_daily, x='Date', y='Average Sentiment Score',
                    title="Average Daily Sentiment Analysis",
                    markers=True,
                    template="plotly_white")
        fig.update_layout(xaxis_title="Date", yaxis_title="Average Sentiment Score")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No sentiment data available!")

    
    # Display sample top questions (static sample)
    def display_top_miniso_questions():
        top_questions = [
            {
                "question": "What are Miniso's unique product offerings?",
                "platform": "Reddit",
                "sentiment": "positive",
                "ai_ans": "Miniso offers a wide range of stylish, affordable products from household items to electronics."
            },
            {
                "question": "How does Miniso ensure product quality?",
                "platform": "Quora",
                "sentiment": "neutral",
                "ai_ans": "They maintain quality through strict supplier screening and regular quality checks."
            },
            {
                "question": "What is the customer feedback on Miniso's pricing?",
                "platform": "Discord",
                "sentiment": "positive",
                "ai_ans": "Customers appreciate the value for money, noting that the pricing is highly competitive."
            },
            {
                "question": "How has Miniso's social media engagement evolved over time?",
                "platform": "Reddit",
                "sentiment": "neutral",
                "ai_ans": "Engagement has steadily increased, reflecting growing brand awareness."
            },
            {
                "question": "What digital marketing strategies does Miniso employ?",
                "platform": "Reddit",
                "sentiment": "positive",
                "ai_ans": "Miniso leverages influencer collaborations and creative content to boost its digital presence."
            }
        ]
        st.subheader("💡 Top Engagement Questions Related to Miniso")
        for idx, doc in enumerate(top_questions, start=1):
            st.markdown(f"**Q{idx}: {doc.get('question', 'No question provided')}**")
            st.markdown(f"**Platform:** {doc.get('platform', 'N/A')}")
            st.markdown(f"**Sentiment:** {doc.get('sentiment', 'N/A')}")
            st.markdown(f"**AI Answer:** {doc.get('ai_ans', 'No answer provided')}")
            st.markdown("---")
    
    display_top_miniso_questions()

# ---------------------------
# Main App Layout
# ---------------------------
def main():
    st.title("AI-Grow")
    
    # Sidebar: select between Home, Dashboard Visualizations, Chatbot Interactive, and Slack Approval
    page_option = st.sidebar.selectbox("Select Page", 
                                        ["Home", "Dashboard Visualizations", "Chatbot Interactive", "Slack Approval"],
                                        index=0)
    
    # Add Slack Workspace link to sidebar
    if SLACK_WORKSPACE_URL:
        st.sidebar.markdown(f"[🔗 Visit Slack Workspace]({SLACK_WORKSPACE_URL})", unsafe_allow_html=True)
    
    if page_option == "Home":
        home_page()
    elif page_option == "Dashboard Visualizations":
        dashboard_page()
    elif page_option == "Chatbot Interactive":
        chatbot_interactive()
    elif page_option == "Slack Approval":
        slack_approval_page()

if __name__ == "__main__":
    main()
