"""
LLM providers for EventHub chatbot
Gemini as primary, Groq as backup
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain.schema import BaseMessage
import os
from typing import List, Union
from dotenv import load_dotenv
load_dotenv()

class LLMManager:
    def __init__(self):
        """Initialize both LLM providers"""
        gemini_key = os.getenv('GOOGLE_API_KEY')
        if not gemini_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        self.primary_llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=gemini_key,
            temperature=0.7,
            max_tokens=512
        )
        
        # Backup: Groq
        groq_key = os.getenv('GROQ_API_KEY')
        if not groq_key:
            print("Warning: GROQ_API_KEY not set, backup unavailable")
            self.backup_llm = None
        else:
            self.backup_llm = ChatGroq(
                model="mixtral-8x7b-32768",
                groq_api_key=groq_key,
                temperature=0.7,
                max_tokens=512
            )
    
    def get_response(self, messages: List[BaseMessage]) -> str:
        """Get response with fallback logic"""
        # Try Gemini first
        try:
            response = self.primary_llm.invoke(messages)
            return response.content
        except Exception as e:
            print(f"Gemini error: {e}")
            
            # Fallback to Groq
            if self.backup_llm:
                try:
                    response = self.backup_llm.invoke(messages)
                    return response.content
                except Exception as e:
                    print(f"Groq error: {e}")
            
            return "I'm having trouble processing your request. Please try again."
    
    def stream_response(self, messages: List[BaseMessage]):
        """Stream response with fallback (for future use)"""
        try:
            return self.primary_llm.stream(messages)
        except Exception as e:
            print(f"Gemini streaming error: {e}")
            if self.backup_llm:
                return self.backup_llm.stream(messages)
            return iter(["Error: Unable to stream response"])

# Test function
if __name__ == "__main__":
    from langchain.schema import HumanMessage
    
    llm_manager = LLMManager()
    test_messages = [HumanMessage(content="Hello, how are you?")]
    response = llm_manager.get_response(test_messages)
    print(response)