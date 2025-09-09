"""
Dual RAG retriever combining local ChromaDB with remote MCP event search
Uses local knowledge base as primary, MCP events as supplementary context
"""

import asyncio
from typing import List, Optional
from retriever import EventHubRetriever  # Your original local retriever
from mcp_client import EventRAGClient

class DualRAGRetriever:
    """Combined retriever using both local knowledge base and remote event MCP"""
    
    def __init__(self, mcp_server_path: str = "./mcp_event_server.py"):
        """Initialize both local and MCP retrievers"""
        try:
            self.local_retriever = EventHubRetriever()
            self.local_available = True
            print("✓ Local retriever loaded")
        except Exception as e:
            print(f"✗ Local retriever error: {e}")
            self.local_retriever = None
            self.local_available = False
        
        # Initialize MCP client for remote events
        self.mcp_client = EventRAGClient(mcp_server_path)
        self.mcp_connected = False
    
    async def _ensure_mcp_connected(self):
        """Ensure MCP connection is established"""
        if not self.mcp_connected:
            try:
                await self.mcp_client.connect()
                self.mcp_connected = True
                print("✓ MCP event retriever connected")
            except Exception as e:
                print(f"✗ MCP connection failed: {e}")
                self.mcp_connected = False
    
    def get_formatted_context(self, query: str, n_results: int = 3) -> str:
        """Get combined context from both local and remote sources"""
        return asyncio.run(self._get_dual_context_async(query, n_results))
    
    async def _get_dual_context_async(self, query: str, n_results: int = 3) -> str:
        """Async retrieval from both sources"""
        contexts = []
        
        # 1. Get local knowledge base context (primary)
        if self.local_available:
            try:
                local_context = self.local_retriever.get_formatted_context(query, n_results)
                if local_context and local_context != "No relevant context found.":
                    contexts.append(f"📚 **Knowledge Base:**\n{local_context}")
            except Exception as e:
                print(f"Local retrieval error: {e}")
        
        # 2. Get event-specific context (supplementary)
        try:
            await self._ensure_mcp_connected()
            if self.mcp_connected:
                # Search for events related to query
                events_result = await self.mcp_client.search_events(query)
                events_context = await self.mcp_client.format_events_for_llm(events_result)
                
                if events_context and "No events found" not in events_context:
                    contexts.append(f"🎉 **Current Events:**\n{events_context}")
        except Exception as e:
            print(f"MCP retrieval error: {e}")
        
        # 3. Combine contexts
        if not contexts:
            return "No relevant context found from available sources."
        
        combined = "\n\n" + "─" * 50 + "\n\n"
        combined = combined.join(contexts)
        
        return combined
    
    def get_local_context_only(self, query: str, n_results: int = 3) -> str:
        """Get only local knowledge base context"""
        if self.local_available:
            return self.local_retriever.get_formatted_context(query, n_results)
        return "Local knowledge base not available."
    
    def get_events_context_only(self, query: str) -> str:
        """Get only event-specific context"""
        return asyncio.run(self._get_events_only_async(query))
    
    async def _get_events_only_async(self, query: str) -> str:
        """Get events context only"""
        try:
            await self._ensure_mcp_connected()
            if self.mcp_connected:
                events_result = await self.mcp_client.search_events(query)
                return await self.mcp_client.format_events_for_llm(events_result)
            return "Event search service not available."
        except Exception as e:
            return f"Error retrieving events: {str(e)}"

# Test the dual retriever
if __name__ == "__main__":
    async def test_dual_retriever():
        retriever = DualRAGRetriever()
        
        # Test combined retrieval
        print("=== COMBINED RETRIEVAL ===")
        context = retriever.get_formatted_context("music events and concerts")
        print(context)
        
        print("\n=== LOCAL ONLY ===")
        local = retriever.get_local_context_only("music events")
        print(local)
        
        print("\n=== EVENTS ONLY ===") 
        events = retriever.get_events_context_only("music events in New York")
        print(events)
    
    asyncio.run(test_dual_retriever())