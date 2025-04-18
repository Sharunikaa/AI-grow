# 🌱 AI-Grow: Engagement Analytics & Assistant Platform

<div align="center">
  
  <br>
  <p><strong>Understand, analyze, and optimize your customer engagement with AI</strong></p>
  <p>
    <a href="#-quick-start">Quick Start</a> •
    <a href="#-features">Features</a> •
    <a href="#-demo">Demo</a> •
    <a href="#-installation">Installation</a> •
    <a href="#-usage">Usage</a> •
    <a href="#-architecture">Architecture</a>
  </p>
</div>

---

## 🚀 Quick Start

```bash
# Start the chatbot API
cd ai_bot
python bot.py

# In a new terminal, start the main application
cd ..
python streamlit_app.py

# Access in your browser: http://localhost:8501
```

---

## 📋 Project Overview

AI-Grow is a comprehensive engagement analytics and AI assistant platform that helps businesses:

- 📊 **Monitor engagement metrics** across multiple platforms
- 🧠 **Generate AI-powered insights** from customer interactions
- 💬 **Automate responses** with intelligent context-aware chatbots
- 📱 **Analyze sentiment** to understand customer emotions
- 🔮 **Predict trends** for proactive business strategy


---

## ✨ Features

<details open>
<summary><b>📈 Analytics Dashboard</b></summary>
<br>

- **Real-time Engagement Metrics** - Track user engagement with interactive visualizations
- **Sentiment Analysis** - Color-coded sentiment trends with timeline filtering
- **Community Clustering** - Interactive cluster maps of user communities
- **Trend Prediction** - Interactive forecasting with adjustable parameters

</details>

<details>
<summary><b>🤖 AI Engagement Assistant</b></summary>
<br>

- **Context-Aware Responses** - Intelligent responses based on your knowledge base
- **Dual-Mode Processing**:
  - 💼 **Engagement Mode** - Optimized for customer interaction queries
  - 🌐 **General Mode** - Handles broader questions with contextual awareness
- **PDF Knowledge Base** - Automatically processes and learns from your documents
- **Persistent Chat History** - Maintains conversation context for natural interactions

</details>

<details>
<summary><b>✅ Content Approval System</b></summary>
<br>

- **Slack Integration** - Review and approve AI-generated content with a simple click
- **Quality Control** - Human-in-the-loop verification system for brand consistency
- **Multi-platform Publishing** - Distribute approved content across channels

</details>

<details>
<summary><b>🔄 Data Processing Pipeline</b></summary>
<br>

- **Multi-source Collection** - Gather data from Discord, Reddit, Quora, and websites
- **Automated Cleaning** - Standardize data formats across platforms
- **Analysis Tools** - Specialized tools for data verification and completeness checks

</details>

---

## 🎬 Demo

> **Try asking the AI Assistant:**
> 
> "How can I improve customer engagement on social media?"
> 
> "What are the current sentiment trends for our skincare products?"
> 
> "Generate a report on our top-performing content from last month."

---

## 🔧 Installation

### Prerequisites

- ✅ Python 3.10+ ([Download](https://www.python.org/downloads/))
- ✅ MongoDB instance ([Setup Guide](https://docs.mongodb.com/manual/installation/))
- ✅ Ollama with llama3.2:3b model ([Installation](https://ollama.ai/download))
- ✅ Node.js for scraping scripts ([Download](https://nodejs.org/))

### Step-by-Step Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-username/ai-grow.git
   cd ai-grow
   ```

2. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up scraping tools**

   ```bash
   cd scripts/scraping/website_scrap
   npm install
   cd ../quora_scrap
   npm install
   ```

4. **Configure your environment**
   - Add your PDF knowledge base as `input.pdf` in the main directory
   - Update MongoDB connection string in `streamlit_app.py` if needed
   - Configure Slack workspace URL in global constants

---

## 📱 Usage

### Dashboard Navigation

Navigate through the platform using the sidebar menu:

| Section | Description | Key Features |
|---------|-------------|--------------|
| **🏠 Home** | Overview dashboard | Key metrics, quick links |
| **📊 Dashboard** | Detailed analytics | Charts, insights, trends |
| **💬 Chatbot** | AI assistant interface | Query input, response history |
| **✅ Slack Approval** | Content review system | Approve/reject interface |

### AI Assistant Examples

```
USER: What engagement trends do you see in our electronics category?
AI: Based on recent data, electronics engagement shows a 23% increase in comment 
rates with peak activity on Thursdays. Video content about product comparisons 
generates 3x more interactions than other formats.
```

### Data Collection Workflow

1. Run specific scraping script:
   ```bash
   python scripts/scraping/reddit_scrap.py
   ```
2. Process and clean data:
   ```bash
   python scripts/processing/clean_data.py
   python scripts/processing/merge_data.py
   ```
3. Run analysis:
   ```bash
   python scripts/analysis/analysis.py
   ```

---

## 🏗️ Architecture

The project follows a modular architecture designed for scalability and maintainability:

```
ai_bot/            # AI chatbot components
  ├─ ai_bott.py    # Streamlit chatbot interface
  ├─ bot.py        # Flask API for chatbot functionality
  ├─ sam.py        # Additional chatbot utilities
  └─ chroma_db/    # Vector database for document storage

frontend/          # User interface components
  ├─ base2.py      # Base dashboard layout
  └─ dashboard.py  # Dashboard visualizations

scripts/           # Data processing and analysis
  ├─ analysis/     # Analytics scripts
  ├─ processing/   # Data cleaning and preparation
  └─ scraping/     # Data collection from various sources

static/            # UI assets and styling
```

### Technology Stack

<table>
  <tr>
    <td><strong>Frontend</strong></td>
    <td>Streamlit, Plotly</td>
  </tr>
  <tr>
    <td><strong>Backend</strong></td>
    <td>Flask, MongoDB, ChromaDB</td>
  </tr>
  <tr>
    <td><strong>AI/ML</strong></td>
    <td>LangChain, Ollama (llama3.2:3b), SentenceTransformer, NLTK, scikit-learn</td>
  </tr>
  <tr>
    <td><strong>Integration</strong></td>
    <td>Slack API</td>
  </tr>
</table>

---

## 🔍 Project Structure Details

<details>
<summary>Click to expand file details</summary>

- **chat_history.json**: Stores conversation history with timestamps and message types
- **input.pdf**: Knowledge base document used for AI context and learning
- **streamlit_app.py**: Main application entry point with routing and UI components
- **ai_bot/**: 
  - **ai_bott.py**: Core chatbot UI implementation
  - **bot.py**: REST API backend for chatbot functionality
  - **chroma_db/**: Vector database for document embeddings
- **frontend/**: UI component implementation
- **scripts/**: Data processing utilities
  - **analysis/**: Performance analytics scripts
  - **processing/**: Data cleaning tools
  - **scraping/**: Platform-specific data collectors
- **static/**: UI assets including images and stylesheets

</details>

---

## 👥 Contributing

We welcome contributions to improve AI-Grow! Here's how to get started:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please check the [issues page](https://github.com/your-username/ai-grow/issues) for any open tasks.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---


