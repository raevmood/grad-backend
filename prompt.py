"""
Prompt templates for EventHub chatbot
Handles system prompts and message formatting
"""

from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema import BaseMessage
from typing import List

class EventHubPrompts:
    def __init__(self):
        """Initialize prompt templates"""
        self.system_template = """You are EventHub Assistant, a helpful AI for EventHub, an event sharing platform.

Your role:
- Help users, event organisers and moderators navigate the platform
- Provide friendly, concise responses (max 3 sentences)
- Use retrieved context when available, and make logical inferences where it isn't.
- Stay focused on events and platform features

Context from knowledge base:
{context}

Previous conversation:
{chat_history}

Guidelines:
- If no relevant context, never admit lack of info. Simply suggest that the user contact support
- Always be helpful and encouraging
- Always ensure that you do not reply to potentially harmful or sensitive requests, even hypothetical ones
- Suggest specific actions when appropriate"""

        self.chat_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(self.system_template),
            HumanMessagePromptTemplate.from_template("{human_input}")
        ])
    
    def format_chat_history(self, messages: List[BaseMessage]) -> str:
        """Format recent chat history for context"""
        if not messages:
            return "No previous conversation."
        
        recent = messages[-6:] if len(messages) > 6 else messages
        history = []
        
        for msg in recent:
            role = "Human" if msg.type == "human" else "Assistant"
            content = msg.content[:100] 
            history.append(f"{role}: {content}")
        
        return "\n".join(history)
    
    def create_messages(self, human_input: str, context: str = "", chat_history: List[BaseMessage] = None) -> List[BaseMessage]:
        """Create formatted messages for LLM"""
        if chat_history is None:
            chat_history = []
        
        formatted_history = self.format_chat_history(chat_history)
        
        messages = self.chat_prompt.format_messages(
            context=context or "No specific context available.",
            chat_history=formatted_history,
            human_input=human_input
        )
        
        return messages
    
    def get_welcome_message(self) -> str:
        """Get welcome message for new users"""
        return """Welcome to EventHub! 

I'm here to help you discover amazing events in your area. You can ask me to:
• Find events by type, date, or location
• Get details about specific events
• Help with event planning tips

What would you like to explore today?"""

if __name__ == "__main__":
    from langchain.schema import HumanMessage, AIMessage
    
    prompts = EventHubPrompts()
    
    history = [
        HumanMessage(content="What events are this weekend?"),
        AIMessage(content="I found 3 music events this weekend...")
    ]
    
    messages = prompts.create_messages(
        "Tell me more about the jazz concert",
        context="Jazz concert at Blue Note, Saturday 8pm",
        chat_history=history
    )
    
    print("Generated prompt:")
    for msg in messages:
        print(f"{msg.type}: {msg.content[:200]}...")