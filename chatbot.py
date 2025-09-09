"""
Main EventHub chatbot class
Combines all components: LLM, memory, retriever, and prompts
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from retriever import EventHubRetriever
from llm_provider import LLMManager
from prompt import EventHubPrompts
from memory import EventHubMemory
from dotenv import load_dotenv
import uvicorn

load_dotenv()

app = FastAPI(
    title="EventHub Chatbot API",
    description="LangChain-powered chatbot with retrieval and memory",
    version="1.0.0"
)

# Configure CORS for localhost testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    use_retrieval: bool = True

class ChatResponse(BaseModel):
    response: str
    session_id: str

# Global chatbot instances cache
chatbots = {}

def get_chatbot(session_id: str) -> "EventHubChatbot":
    """Get or create chatbot instance for session"""
    if session_id not in chatbots:
        chatbots[session_id] = EventHubChatbot(session_id)
    return chatbots[session_id]

class EventHubChatbot:
    def __init__(self, session_id: str = "default"):
        """Initialize all chatbot components"""
        try:
            self.retriever = EventHubRetriever()
        except Exception as e:
            print(f"✗ Retriever error: {e}")
            self.retriever = None
        
        try:
            self.llm = LLMManager()
        except Exception as e:
            print(f"✗ LLM error: {e}")
            raise
        
        self.prompts = EventHubPrompts()
        self.memory = EventHubMemory(session_id=session_id)
    
    def get_response(self, user_input: str, use_retrieval: bool = True) -> str:
        """Get chatbot response to user input"""
        try:
            context = ""
            if use_retrieval and self.retriever:
                context = self.retriever.get_formatted_context(user_input, n_results=2)
            
            messages = self.prompts.create_messages(
                human_input=user_input,
                context=context,
                chat_history=self.memory.get_recent_messages(6)
            )
            
            response = self.llm.get_response(messages)
            
            self.memory.add_user_message(user_input)
            self.memory.add_ai_message(response)
            
            return response
            
        except Exception as e:
            error_msg = f"I encountered an error: {str(e)[:100]}. Please try again."
            self.memory.add_user_message(user_input)
            self.memory.add_ai_message(error_msg)
            return error_msg

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "EventHub Chatbot API is running"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint"""
    try:
        chatbot = get_chatbot(request.session_id)
        response = chatbot.get_response(request.message, request.use_retrieval)
        
        return ChatResponse(
            response=response,
            session_id=request.session_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "chatbot:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )