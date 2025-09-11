from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dual_retriever import DualRAGRetriever  # Updated import
from llm_provider import LLMManager
from prompt import EventHubPrompts
from memory import EventHubMemory
from dotenv import load_dotenv
import uvicorn

load_dotenv()

app = FastAPI(
    title="EventHub Chatbot API",
    description="LangChain-powered chatbot with dual RAG (local + events)",
    version="1.0.0"
)

# Configure CORS for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://sench729-eventhub.hf.space",
        "http://localhost:8080",
        "https://eventhu-5fow.vercel.app",
        "https://event-hub-coral.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    retrieval_mode: str = "combined"  # "combined", "local", "events", "none"

class ChatResponse(BaseModel):
    response: str
    session_id: str
    sources_used: list[str]

# Global chatbot instances cache
chatbots = {}

def get_chatbot(session_id: str) -> "EventHubChatbot":
    """Get or create chatbot instance for session"""
    if session_id not in chatbots:
        chatbots[session_id] = EventHubChatbot(session_id)
    return chatbots[session_id]

class EventHubChatbot:
    def __init__(self, session_id: str = "default"):
        """Initialize all chatbot components with dual RAG"""
        try:
            self.retriever = DualRAGRetriever("https://sench729-eventhub.hf.space")  # Updated to dual retriever
            self.retriever_available = True
        except Exception as e:
            print(f"✗ Retriever error: {e}")
            self.retriever = None
            self.retriever_available = False
        
        try:
            self.llm = LLMManager()
        except Exception as e:
            print(f"✗ LLM error: {e}")
            raise
        
        self.prompts = EventHubPrompts()
        self.memory = EventHubMemory(session_id=session_id)
    
    async def get_response(self, user_input: str, retrieval_mode: str = "combined") -> tuple[str, list[str]]:
        """Get chatbot response with flexible retrieval options"""
        try:
            context = ""
            sources_used = []
        
            # Get context based on retrieval mode
            if self.retriever_available and retrieval_mode != "none":
                if retrieval_mode == "combined":
                    context = await self.retriever.get_formatted_context_async(user_input, n_results=2)
                    sources_used = ["knowledge_base", "current_events"]
                elif retrieval_mode == "local":
                    context = self.retriever.get_local_context_only(user_input, n_results=2)
                    sources_used = ["knowledge_base"]
                elif retrieval_mode == "events":
                    context = await self.retriever.get_events_context_only_async(user_input)
                sources_used = ["current_events"]
        
            # Create messages with context and history
            messages = self.prompts.create_messages(
                human_input=user_input,
                context=context,
                chat_history=self.memory.get_recent_messages(6)
            )
        
            # Get LLM response
            response = self.llm.get_response(messages)
        
            # Save to memory
            self.memory.add_user_message(user_input)
            self.memory.add_ai_message(response)
        
            return response, sources_used
        
        except Exception as e:
            error_msg = f"I encountered an error: {str(e)[:100]}. Please try again."
            self.memory.add_user_message(user_input)
            self.memory.add_ai_message(error_msg)
            return error_msg, ["error"]

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "EventHub Chatbot API with Dual RAG is running"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint with flexible retrieval options"""
    try:
        chatbot = get_chatbot(request.session_id)
        response, sources = await chatbot.get_response(
            request.message, 
            request.retrieval_mode
        )
        
        return ChatResponse(
            response=response,
            session_id=request.session_id,
            sources_used=sources
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/local")
async def chat_local_only(request: ChatRequest):
    """Chat endpoint using only local knowledge base"""
    request.retrieval_mode = "local"
    return await chat_endpoint(request)

@app.post("/chat/events") 
async def chat_events_only(request: ChatRequest):
    """Chat endpoint using only event search"""
    request.retrieval_mode = "events"
    return await chat_endpoint(request)

if __name__ == "__main__":
    uvicorn.run(
        "chatbot:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )