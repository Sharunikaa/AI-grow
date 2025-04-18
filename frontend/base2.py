import streamlit as st
import pandas as pd
import requests
import time

BASE_URL = "http://localhost:5000"

st.set_page_config(page_title="AI-Grow Dashboard", layout="wide")

col1, col2 = st.columns([4, 1])
with col1:
    st.markdown("<h1 style='text-align: left; color: #FF5733;'>AI-Grow</h1>", unsafe_allow_html=True)
with col2:
    st.markdown("[🔗 Slack Workspace](https://slack.com)", unsafe_allow_html=True)

col3, col4, col5 = st.columns(3)
with col3:
    analysis_type = st.selectbox("🔍 Select Analysis", ["Engagement Score", "Sentiment Analysis", "Clustering"])
with col4:
    trend_type = st.selectbox("📈 Analysis Trend", ["Trend Analysis", "Prediction"])
with col5:
    hot_topics = st.selectbox("🔥 Hot Topics", ["Ranking Communities"])

st.subheader("📌 Community Question & Engagement Metrics")
question = "How does Miniso ensure product quality across global markets?"
st.markdown(f"**💬 Question:** {question}")

metrics_response = requests.get(f"{BASE_URL}/get_engagement_metrics")
metrics_data = metrics_response.json() if metrics_response.status_code == 200 else {}

col1, col2, col3 = st.columns(3)
col1.metric(label="👍 Total Upvotes", value=metrics_data.get("upvotes", 0))
col2.metric(label="😊 Total Positive", value=metrics_data.get("positive_sentiment", 0))
col3.metric(label="😠 Total Negative", value=metrics_data.get("negative_sentiment", 0))

st.subheader("📈 Post Growth Over Time")

growth_response = requests.get(f"{BASE_URL}/get_post_growth")
growth_data = growth_response.json() if growth_response.status_code == 200 else {}

if growth_data:
    df_growth = pd.DataFrame(growth_data)
    st.line_chart(df_growth.set_index("Date"))
else:
    st.warning("No post growth data available!")

st.sidebar.header("✅ Chatbot Approval System")
pending_message_response = requests.get(f"{BASE_URL}/get_approved_message")
pending_message = pending_message_response.json().get("message", "No pending messages")

st.sidebar.subheader("Pending Messages")
st.sidebar.write(f"**📢 Pending:** {pending_message}")

if st.sidebar.button("Approve & Post"):
    requests.post(f"{BASE_URL}/approve_message", json={"message": pending_message, "status": "approved"})
    st.sidebar.success("Message Approved & Sent to Slack/Teams!")
    requests.post(f"{BASE_URL}/send_message", json={"message": pending_message})
    time.sleep(2)
    st.rerun()


st.subheader("📊 Sentiment Analysis Over Time")
sentiment_response = requests.get(f"{BASE_URL}/get_sentiment_analysis")
sentiment_data = sentiment_response.json() if sentiment_response.status_code == 200 else {}

if sentiment_data:
    df_sentiment = pd.DataFrame(sentiment_data)
    st.line_chart(df_sentiment.set_index("timestamp")["sentiment_score"])
else:
    st.warning("No sentiment data available!")


st.sidebar.subheader("📝 AI-Assisted Content Generation")
custom_message = st.sidebar.text_area("Enter AI-generated response:")
if st.sidebar.button("Generate & Post"):
    requests.post(f"{BASE_URL}/send_message", json={"message": custom_message})
    st.sidebar.success("AI-Generated Message Sent!")

st.sidebar.markdown("---")
st.sidebar.write("Developed by **AI-Grow Team** 🚀")

