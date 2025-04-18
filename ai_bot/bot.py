import os
import json
from flask import Flask, request, jsonify
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.llms import Ollama
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Constants from environment variables
PDF_FILE = os.getenv("PDF_FILE", "../input.pdf")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:3b")
PORT = int(os.getenv("CHATBOT_PORT", 7000))

# Setup vector database
def setup_vector_database():
    loader = PyPDFLoader(PDF_FILE)
    documents = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100).split_documents(loader.load())
    return Chroma.from_documents(documents, SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL))

# Initialize chains
db = setup_vector_database()
llm = Ollama(model=LLM_MODEL)

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
retrieval_chain = create_retrieval_chain(db.as_retriever(), engagement_chain)

general_prompt = ChatPromptTemplate.from_messages([
    ("system", "Provide engaging, curiosity-driven responses to user questions."),
    ("user", "Question: {input}")
])
general_chain = general_prompt | llm | StrOutputParser()

def get_chatbot_response(question):
    # For simplicity, here we use an empty context.
    context = ""
    # If question appears to be about engagement, use retrieval; else use general chain.
    if "engagement" in question.lower():
        response = retrieval_chain.invoke({"input": context + "\n" + question})['answer']
    else:
        response = general_chain.invoke({"input": context + "\n" + question})
    return response

@app.route("/chatbot_response", methods=["POST"])
def chatbot_response():
    data = request.get_json()
    question = data.get("question")
    if not question:
        return jsonify({"error": "No question provided"}), 400
    answer = get_chatbot_response(question)
    return jsonify({"answer": answer})

@app.route("/")
def home():
    return jsonify({"message": "Welcome to the AI-Grow Chatbot API!"})

if __name__ == "__main__":
    app.run(debug=True, port=PORT)

