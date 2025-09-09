"""
MCP Client to connect EventHub RAG tools to LLM
Updated for current MCP package structure
"""

import asyncio
import json
import subprocess
from typing import Optional, Dict, Any

class EventRAGClient:
    def __init__(self, server_path: str = "./mcp_event_server.py"):
        """Initialize MCP client for EventHub RAG"""
        self.server_path = server_path
        self.process = None
    
    async def connect(self):
        """Connect to the MCP server via subprocess"""
        try:
            self.process = subprocess.Popen(
                ["python", self.server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            print(f"✓ Started MCP server process")
            return True
                
        except Exception as e:
            print(f"✗ Failed to start MCP server: {e}")
            raise
    
    async def _send_request(self, method: str, params: Dict = None) -> Dict[str, Any]:
        """Send JSON-RPC request to MCP server"""
        if not self.process:
            raise RuntimeError("Not connected to MCP server")
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json)
            self.process.stdin.flush()
            
            # Read response
            response_line = self.process.stdout.readline()
            response = json.loads(response_line)
            
            if "error" in response:
                raise Exception(f"MCP Error: {response['error']}")
            
            return response.get("result", {})
            
        except Exception as e:
            raise Exception(f"MCP communication error: {e}")
    
    async def search_events(self, query: str, user_id: str = "default") -> Dict[str, Any]:
        """Search for events using natural language query"""
        try:
            result = await self._send_request(
                "tools/call",
                {
                    "name": "search_events",
                    "arguments": {"query": query, "user_id": user_id}
                }
            )
            
            # Parse the text content
            if "content" in result and len(result["content"]) > 0:
                content_text = result["content"][0].get("text", "{}")
                return json.loads(content_text)
            else:
                return {"error": "No response from server"}
                
        except Exception as e:
            return {"error": f"Search failed: {str(e)}"}
    
    async def get_all_events(self) -> Dict[str, Any]:
        """Get all available events"""
        try:
            result = await self._send_request(
                "tools/call",
                {
                    "name": "get_all_events",
                    "arguments": {}
                }
            )
            
            if "content" in result and len(result["content"]) > 0:
                content_text = result["content"][0].get("text", "{}")
                return json.loads(content_text)
            else:
                return {"error": "No response from server"}
                
        except Exception as e:
            return {"error": f"Failed to get events: {str(e)}"}
    
    async def format_events_for_llm(self, events_data: Dict[str, Any]) -> str:
        """Format event results for LLM consumption"""
        if "error" in events_data:
            return f"Error retrieving events: {events_data['error']}"
        
        events = events_data.get("events", [])
        if not events:
            return "No events found matching your criteria."
        
        formatted = f"Found {events_data.get('results_count', len(events))} events:\n\n"
        
        for i, event in enumerate(events[:5], 1):  # Limit to top 5 for LLM context
            formatted += f"{i}. **{event.get('title', 'Untitled Event')}**\n"
            formatted += f"   📍 {event.get('location', 'Location TBA')}\n"
            formatted += f"   📅 {event.get('startDateTime', 'Date TBA')}\n"
            formatted += f"   💰 {'Free' if event.get('isFree') else f\"${event.get('price', 'TBA')}\"}\n"
            formatted += f"   🏷️ {event.get('category', 'Uncategorized')}\n"
            if event.get('tags'):
                formatted += f"   🔖 {event.get('tags')}\n"
            formatted += "\n"
        
        return formatted.strip()
    
    def cleanup(self):
        """Clean up subprocess"""
        if self.process:
            self.process.terminate()
            self.process = None

# Standalone usage example
async def test_client():
    """Test the MCP client"""
    client = EventRAGClient()
    
    try:
        await client.connect()
        
        # Test search
        print("Testing event search...")
        search_result = await client.search_events("free tech events in San Francisco")
        formatted = await client.format_events_for_llm(search_result)
        print("Search Results:")
        print(formatted)
        print("-" * 50)
        
        # Test get all
        print("Testing get all events...")
        all_events = await client.get_all_events()
        print(f"Total events available: {all_events.get('total_events', 0)}")
        
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        client.cleanup()

if __name__ == "__main__":
    asyncio.run(test_client())