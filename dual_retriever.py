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
    
    def __init__(self, base_url: str = "https://sench729-eventhub.hf.space"):
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
        self.mcp_client = EventRAGClient(base_url)
        self.mcp_available = True
        print("✓ MCP event client initialized")
    
    async def _check_mcp_health(self):
        """Check if MCP service is available"""
        try:
            health = await self.mcp_client.health_check()
            if "error" not in health:
                print("✓ MCP event service is healthy")
                return True
            else:
                print(f"✗ MCP health check failed: {health['error']}")
                return False
        except Exception as e:
            print(f"✗ MCP health check error: {e}")
            return False
    
    async def get_formatted_context_async(self, query: str, n_results: int = 3) -> str:
        """Async method to get combined context from both local and remote sources"""
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
        if self.mcp_available:
            try:
                # Check if service is healthy first
                is_healthy = await self._check_mcp_health()
                if is_healthy:
                    # Search for events related to query
                    events_result = await self.mcp_client.search_events(query)
                    events_context = await self.mcp_client.format_events_for_llm(events_result)
                    
                    if events_context and "No events found" not in events_context:
                        contexts.append(f"🎉 **Current Events:**\n{events_context}")
                else:
                    print("MCP service not available, skipping events context")
            except Exception as e:
                print(f"MCP retrieval error: {e}")
                self.mcp_available = False
        
        # 3. Combine contexts
        if not contexts:
            return "No relevant context found from available sources."
        
        combined = "\n\n" + "─" * 50 + "\n\n"
        combined = combined.join(contexts)
        
        return combined
    
    def get_formatted_context(self, query: str, n_results: int = 3) -> str:
        """Synchronous wrapper - only use when not in an async context"""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're already in an event loop, we can't use asyncio.run()
            raise RuntimeError("Cannot use synchronous method from within async context. Use get_formatted_context_async() instead.")
        except RuntimeError as e:
            if "no running event loop" in str(e).lower():
                # No event loop running, safe to use asyncio.run()
                return asyncio.run(self.get_formatted_context_async(query, n_results))
            else:
                # Re-raise the error about being in async context
                raise e
    
    def get_local_context_only(self, query: str, n_results: int = 3) -> str:
        """Get only local knowledge base context"""
        if self.local_available:
            return self.local_retriever.get_formatted_context(query, n_results)
        return "Local knowledge base not available."
    
    async def get_events_context_only_async(self, query: str) -> str:
        """Async method to get only event-specific context"""
        if not self.mcp_available:
            return "Event search service not available."
            
        try:
            # Check if service is healthy first
            is_healthy = await self._check_mcp_health()
            if is_healthy:
                events_result = await self.mcp_client.search_events(query)
                return await self.mcp_client.format_events_for_llm(events_result)
            else:
                return "Event search service is not healthy."
        except Exception as e:
            self.mcp_available = False
            return f"Error retrieving events: {str(e)}"
    
    def get_events_context_only(self, query: str) -> str:
        """Synchronous wrapper for events context - only use when not in async context"""
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're already in an event loop, we can't use asyncio.run()
            raise RuntimeError("Cannot use synchronous method from within async context. Use get_events_context_only_async() instead.")
        except RuntimeError as e:
            if "no running event loop" in str(e).lower():
                # No event loop running, safe to use asyncio.run()
                return asyncio.run(self.get_events_context_only_async(query))
            else:
                # Re-raise the error about being in async context
                raise e

# Test the dual retriever
if __name__ == "__main__":
    async def test_dual_retriever():
        # Initialize with the correct base URL for your EventHub service
        retriever = DualRAGRetriever("https://sench729-eventhub.hf.space")
        
        # Test combined retrieval (using async method)
        print("=== COMBINED RETRIEVAL ===")
        context = await retriever.get_formatted_context_async("music events and concerts")
        print(context)
        
        print("\n=== LOCAL ONLY ===")
        local = retriever.get_local_context_only("music events")
        print(local)
        
        print("\n=== EVENTS ONLY ===") 
        events = await retriever.get_events_context_only_async("music")
        print(events)
    
    asyncio.run(test_dual_retriever())