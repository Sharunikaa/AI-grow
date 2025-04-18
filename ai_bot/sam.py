import pymongo
import requests

# Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "company_data")
SLACK_WORKSPACE_URL = os.getenv("SLACK_WORKSPACE_URL")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
CHATBOT_API_URL = "http://localhost:7000/chatbot_response"

def get_questions():
    
    client = pymongo.MongoClient(MONGODB_URI)
    db = client[DATABASE_NAME]
    collection = db[COLLECTION_NAME]

    query = {"engagement_score": {"$exists": True}}
    
    # Sort descending by engagement_score
    cursor = collection.find(query).sort("engagement_score", -1)
    questions = []
    for doc in cursor:
        # Prefer cleaned_content; fallback to title or content.
        question = doc.get("cleaned_content") or doc.get("title") or doc.get("content")
        questions.append(question)
    client.close()
    return questions

def get_chatbot_response(question):
    
    data = {"question": question}
    response = requests.post(CHATBOT_API_URL, json=data)
    if response.status_code == 200:
        return response.json().get("answer")
    else:
        return "Error: Unable to retrieve chatbot response."

def send_to_slack(message):
    
    payload = {"text": message}
    response = requests.post(SLACK_WEBHOOK_URL, json=payload)
    return response.status_code

def process_and_send_responses():
    
    questions = get_questions()
    if not questions:
        print("No questions found.")
        return

    for idx, question in enumerate(questions, start=1):
        answer = get_chatbot_response(question)
        qa_message = (
            f"*Q{idx}:* {question}\n"
            f"*A{idx}:* {answer}\n"
            f"Please review and approve this response."
        )
        
        print(f"Sending to Slack:\n{qa_message}\n")
        send_status = send_to_slack(qa_message)
        if send_status == 200:
            print("Message sent to Slack successfully.")
        else:
            print("Failed to send message to Slack.")
        
        # Simulate an approval process (manual input for demonstration)
        approval = input(f"Approve Q{idx}? (yes/no): ")
        if approval.lower() == "yes":
            print(f"Q{idx} approved and posted!\n")
            # Optionally: mark the Q&A as posted in your system
        else:
            print(f"Q{idx} not approved, skipping.\n")
        print("=" * 50 + "\n")

if __name__ == "__main__":
    process_and_send_responses()
