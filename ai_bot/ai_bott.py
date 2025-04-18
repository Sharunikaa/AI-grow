import os
import json
import streamlit as st
from dataclasses import dataclass
from typing import Literal
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.llms import Ollama
from langchain.chains import create_retrieval_chain

from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.output_parsers import StrOutputParser
import streamlit.components.v1 as components

# Constants
PDF_FILE = "../input.pdf"
HISTORY_FILE = "chat_history.json"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
LLM_MODEL = "llama3.2:3b"

@dataclass
class Message:
    origin: Literal["human", "ai"]
    message: str

# Function to load or initialize chat history
def load_chat_history():
    return json.load(open(HISTORY_FILE, "r")) if os.path.exists(HISTORY_FILE) else []

def save_chat_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

def clear_chat_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)

def is_engagement_query(query):
    keywords = ["engagement", "post", "trend", "interaction"]
    return any(kw in query.lower() for kw in keywords)

# Load and process document
def setup_vector_database():
    loader = PyPDFLoader(PDF_FILE)
    documents = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100).split_documents(loader.load())
    return Chroma.from_documents(documents, SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL))

def initialize_session():
    if "history" not in st.session_state:
        st.session_state.history = load_chat_history()

    if "retrieval_chain" not in st.session_state:
        llm = Ollama(model=LLM_MODEL)
        db = setup_vector_database()

        retrieval_prompt = ChatPromptTemplate.from_messages([
            ("system", """
            Use retrieved data to generate an engaging response:
            {context}.
            Encourage user curiosity and interactions while aligning with brand tone.
            Respond concisely in 4-5 lines.
            """),
            ("human", "{input}")
        ])

        engagement_chain = create_stuff_documents_chain(llm, retrieval_prompt)
        st.session_state.retrieval_chain = create_retrieval_chain(db.as_retriever(), engagement_chain)

        general_prompt = ChatPromptTemplate.from_messages([
            ("system", "Provide engaging, curiosity-driven responses to user questions."),
            ("user", "Question: {input}")
        ])
        st.session_state.general_chain = general_prompt | llm | StrOutputParser()

def process_user_input():
    user_query = st.session_state.user_input.strip()
    if not user_query:
        return

    context = "\n".join(f"{msg['origin']}: {msg['message']}" for msg in st.session_state.history)

    if is_engagement_query(user_query):
        response = st.session_state.retrieval_chain.invoke({"input": context + "\n" + user_query})['answer']
    else:
        response = st.session_state.general_chain.invoke({"input": context + "\n" + user_query})

    st.session_state.history.extend([
        {"origin": "human", "message": user_query},
        {"origin": "ai", "message": response}
    ])
    save_chat_history(st.session_state.history)

def apply_custom_styles():
    st.markdown("""
    <style>
        .chat-bubble {
            padding: 10px;
            border-radius: 10px;
            margin: 5px 0;
            max-width: 80%;
            word-wrap: break-word;
        }
        .human-bubble {
            background-color: #0078FF;
            color: white;
            align-self: flex-end;
        }
        .ai-bubble {
            background-color: #f0f0f0;
            color: black;
            align-self: flex-start;
        }
        .chat-row {
            display: flex;
            justify-content: flex-start;
        }
        .row-reverse {
            justify-content: flex-end;
        }
    </style>
    """, unsafe_allow_html=True)

def render_chat_interface():
    st.title("🚀 AI Engagement Assistant")

    chat_area = st.container()
    with chat_area:
        for chat in st.session_state.history:
            chat_bubble = f"""
            <div class='chat-row {'row-reverse' if chat['origin'] == 'human' else ''}'>
                <div class='chat-bubble {'human-bubble' if chat['origin'] == 'human' else 'ai-bubble'}'>
                    {chat['message']}
                </div>
            </div>
            """
            st.markdown(chat_bubble, unsafe_allow_html=True)

    with st.form("chat-form"):
        st.text_input("Ask about engagement trends, posts, and insights! ✨", key="user_input")
        st.form_submit_button("Submit", on_click=process_user_input)

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

def main():
    st.sidebar.button("New Chat", on_click=lambda: [st.session_state.update({"history": []}), clear_chat_history()])
    initialize_session()
    apply_custom_styles()
    render_chat_interface()

if __name__ == "__main__":
    main()
