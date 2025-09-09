"""
Memory manager for EventHub chatbot
Handles conversation history and session management
"""

from langchain.schema import BaseMessage, HumanMessage, AIMessage
from typing import List, Dict, Optional
import json
import os
from datetime import datetime

class EventHubMemory:
    def __init__(self, session_id: str = "default", max_messages: int = 20, persist_path: str = "./chat_memory"):
        """Initialize memory manager"""
        self.session_id = session_id
        self.max_messages = max_messages
        self.persist_path = persist_path
        self.messages: List[BaseMessage] = []
        
        # Create memory directory
        os.makedirs(persist_path, exist_ok=True)
        
        # Load existing conversation
        self.load_memory()
    
    def add_message(self, message: BaseMessage) -> None:
        """Add message to memory"""
        self.messages.append(message)
        
        # Keep only recent messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
        
        # Auto-save
        self.save_memory()
    
    def add_user_message(self, content: str) -> None:
        """Add user message"""
        self.add_message(HumanMessage(content=content))
    
    def add_ai_message(self, content: str) -> None:
        """Add AI response"""
        self.add_message(AIMessage(content=content))
    
    def get_messages(self) -> List[BaseMessage]:
        """Get all messages"""
        return self.messages.copy()
    
    def get_recent_messages(self, count: int = 6) -> List[BaseMessage]:
        """Get recent messages for context"""
        return self.messages[-count:] if len(self.messages) > count else self.messages
    
    def clear_memory(self) -> None:
        """Clear conversation history"""
        self.messages = []
        self.save_memory()
    
    def save_memory(self) -> None:
        """Save memory to file"""
        try:
            file_path = os.path.join(self.persist_path, f"{self.session_id}.json")
            
            # Convert messages to serializable format
            data = {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "messages": []
            }
            
            for msg in self.messages:
                data["messages"].append({
                    "type": msg.type,
                    "content": msg.content
                })
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Memory save error: {e}")
    
    def load_memory(self) -> None:
        """Load memory from file"""
        try:
            file_path = os.path.join(self.persist_path, f"{self.session_id}.json")
            
            if not os.path.exists(file_path):
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Reconstruct messages
            self.messages = []
            for msg_data in data.get("messages", []):
                if msg_data["type"] == "human":
                    self.messages.append(HumanMessage(content=msg_data["content"]))
                elif msg_data["type"] == "ai":
                    self.messages.append(AIMessage(content=msg_data["content"]))
                    
        except Exception as e:
            print(f"Memory load error: {e}")
            self.messages = []
    
    def get_conversation_summary(self) -> str:
        """Get brief conversation summary"""
        if not self.messages:
            return "No conversation history."
        
        recent = self.get_recent_messages(4)
        summary = f"Recent conversation ({len(recent)} messages):\n"
        
        for msg in recent:
            role = "You" if msg.type == "human" else "Assistant"
            content = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            summary += f"• {role}: {content}\n"
        
        return summary.strip()

# Test function
if __name__ == "__main__":
    memory = EventHubMemory(session_id="test_session")
    
    # Test conversation
    memory.add_user_message("What events are happening this weekend?")
    memory.add_ai_message("I found 5 great events this weekend! There's a jazz concert, food festival...")
    memory.add_user_message("Tell me about the jazz concert")
    
    print("Conversation summary:")
    print(memory.get_conversation_summary())
    
    print("\nRecent messages:")
    for msg in memory.get_recent_messages():
        print(f"{msg.type}: {msg.content}")