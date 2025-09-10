import asyncio
import json
from typing import Dict, Any, Optional
import httpx


class EventRAGClient:
    def __init__(self, base_url: str = "https://sench729-eventhub.hf.space"):
        self.base_url = base_url.rstrip("/")
        self.timeout = 30.0
        print(f"→ EventRAGClient initialized with base_url: {self.base_url}")

    async def _send_mcp_request(self, method: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Send JSON-RPC request to MCP server endpoint"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        print(f"→ Sending MCP request: {method} with params: {params}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/mcp/tools/call", 
                    json=request
                )
                response.raise_for_status()
                response_data = response.json()
                
            print(f"✓ MCP request {method} completed successfully")
            
        except httpx.ConnectError as e:
            error_msg = f"Connection failed to {self.base_url}: {e}"
            print(f"✗ {error_msg}")
            raise Exception(error_msg)
        except httpx.TimeoutException as e:
            error_msg = f"Request timeout after {self.timeout}s: {e}"
            print(f"✗ {error_msg}")
            raise Exception(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Request error: {e}"
            print(f"✗ {error_msg}")
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            print(f"✗ {error_msg}")
            raise Exception(error_msg)

        if "error" in response_data:
            error_msg = f"MCP Error: {response_data['error']}"
            print(f"✗ {error_msg}")
            raise Exception(error_msg)

        return response_data.get("result", {})

    async def _send_direct_request(self, endpoint: str, payload: Dict) -> Dict[str, Any]:
        """Send direct request to FastAPI endpoints"""
        print(f"→ Sending direct request to {endpoint}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    json=payload
                )
                response.raise_for_status()
                response_data = response.json()
                
            print(f"✓ Direct request to {endpoint} completed successfully")
            return response_data
            
        except Exception as e:
            error_msg = f"Direct request to {endpoint} failed: {e}"
            print(f"✗ {error_msg}")
            raise Exception(error_msg)

    async def search_events(self, query: str, user_id: str = "default") -> Dict[str, Any]:
        """Search for events using natural language query"""
        print(f"→ Searching events: query='{query}', user_id='{user_id}'")
        
        try:
            # Try MCP endpoint first (preferred for RAG context)
            try:
                result = await self._send_mcp_request(
                    "tools/call",
                    {
                        "name": "search_events",
                        "arguments": {"query": query, "user_id": user_id}
                    }
                )

                if "content" in result and len(result["content"]) > 0:
                    content_text = result["content"][0].get("text", "{}")
                    parsed_result = json.loads(content_text)
                    
                    if "error" in parsed_result:
                        print(f"✗ MCP search returned error: {parsed_result['error']}")
                        return parsed_result
                    
                    event_count = parsed_result.get("results_count", 0)
                    print(f"✓ MCP search completed: found {event_count} events")
                    return parsed_result
                else:
                    raise Exception("No content in MCP response")
                    
            except Exception as mcp_error:
                print(f"✗ MCP search failed: {mcp_error}, trying direct API...")
                
                # Fallback to direct FastAPI endpoint
                direct_result = await self._send_direct_request("/search", {
                    "query": query,
                    "user_id": user_id
                })
                
                # Convert direct API response to MCP format
                events = direct_result.get("results", [])
                formatted_result = {
                    "query": query,
                    "results_count": len(events),
                    "events": events[:10]
                }
                
                print(f"✓ Direct search completed: found {len(events)} events")
                return formatted_result
                
        except Exception as e:
            error_msg = f"Search failed: {str(e)}"
            print(f"✗ {error_msg}")
            return {"error": error_msg}

    async def get_all_events(self) -> Dict[str, Any]:
        """Get all available events"""
        print("→ Fetching all events")
        
        try:
            # Try MCP endpoint first
            try:
                result = await self._send_mcp_request(
                    "tools/call",
                    {"name": "get_all_events", "arguments": {}}
                )

                if "content" in result and len(result["content"]) > 0:
                    content_text = result["content"][0].get("text", "{}")
                    parsed_result = json.loads(content_text)
                    
                    if "error" in parsed_result:
                        print(f"✗ MCP get all events returned error: {parsed_result['error']}")
                        return parsed_result
                    
                    total_events = parsed_result.get("total_events", 0)
                    returned_events = len(parsed_result.get("events", []))
                    print(f"✓ MCP retrieved {returned_events} of {total_events} total events")
                    return parsed_result
                else:
                    raise Exception("No content in MCP response")
                    
            except Exception as mcp_error:
                print(f"✗ MCP get all events failed: {mcp_error}")
                # For get_all_events, we don't have a direct FastAPI equivalent
                # so we'll search with a broad query
                return await self.search_events("events")
                
        except Exception as e:
            error_msg = f"Failed to get events: {str(e)}"
            print(f"✗ {error_msg}")
            return {"error": error_msg}

    async def format_events_for_llm(self, events_data: Dict[str, Any]) -> str:
        """Format events data for LLM consumption"""
        print("→ Formatting events for LLM")
        
        if "error" in events_data:
            error_msg = f"Error retrieving events: {events_data['error']}"
            print(f"✗ {error_msg}")
            return error_msg

        events = events_data.get("events", [])
        if not events:
            msg = "No events found matching your criteria."
            print(f"→ {msg}")
            return msg

        results_count = events_data.get("results_count", len(events))
        total_found = events_data.get("total_found", results_count)
        
        # Start formatting
        if "query" in events_data:
            formatted = f"Found {results_count} events matching '{events_data['query']}':\n\n"
        else:
            formatted = f"Found {results_count} events:\n\n"

        # Add note about limited results if applicable
        if len(events) < total_found:
            formatted += f"(Showing top {len(events)} of {total_found} total results)\n\n"

        # Format each event
        for i, event in enumerate(events[:10], 1):  # Limit to 10 for LLM context
            formatted += f"{i}. {event.get('title', 'Untitled Event')}\n"
            
            location = event.get('location', 'Location TBA')
            if location:
                formatted += f"   📍 Location: {location}\n"
            
            start_date = event.get('startDateTime', 'Date TBA')
            if start_date:
                formatted += f"   📅 Date: {start_date}\n"
            
            # Price formatting
            if event.get('isFree', False):
                formatted += f"   💰 Price: Free\n"
            elif event.get('price'):
                formatted += f"   💰 Price: ${event.get('price')}\n"
            else:
                formatted += f"   💰 Price: TBA\n"
            
            category = event.get('category', 'Uncategorized')
            if category:
                formatted += f"   🏷️ Category: {category}\n"
            
            organizer = event.get('organizer')
            if organizer:
                formatted += f"   👥 Organizer: {organizer}\n"
            
            tags = event.get('tags')
            if tags:
                formatted += f"   🏷️ Tags: {tags}\n"
            
            formatted += "\n"

        result = formatted.strip()
        print(f"✓ Formatted {len(events)} events for LLM ({len(result)} characters)")
        return result

    async def health_check(self) -> Dict[str, Any]:
        """Check if the EventHub API is healthy"""
        print("→ Performing health check")
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/")
                response.raise_for_status()
                health_data = response.json()
                
            print(f"✓ Health check passed: {health_data.get('status', 'unknown')}")
            return health_data
            
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            print(f"✗ {error_msg}")
            return {"error": error_msg, "status": "unhealthy"}


async def test_client():
    """Test the EventRAG client functionality"""
    print("=" * 60)
    print("Starting EventRAG Client Tests")
    print("=" * 60)
    
    # Test with HF Spaces URL
    test_urls = [
        "https://sench729-eventhub.hf.space",  # HF Spaces deployment
        # "http://127.0.0.1:8000"  # Local development
    ]
    
    for base_url in test_urls:
        print(f"\n🧪 Testing with: {base_url}")
        print("-" * 40)
        
        client = EventRAGClient(base_url=base_url)

        try:
            # Health check
            print("\n1. Testing health check...")
            health = await client.health_check()
            if "error" not in health:
                print(f"✓ API Status: {health.get('status', 'unknown')}")
                # HF Spaces might not have mcp_server_active field
                mcp_active = health.get('mcp_server_active', 'unknown')
                print(f"✓ MCP Server Active: {mcp_active}")
            else:
                print(f"✗ Health check failed: {health['error']}")
                continue  # Skip other tests if health check fails
            
            # Test event search
            print("\n2. Testing event search...")
            search_query = "music"
            search_result = await client.search_events(search_query)
            formatted = await client.format_events_for_llm(search_result)
            
            print("Search Results Preview:")
            print("-" * 30)
            print(formatted[:500] + "..." if len(formatted) > 500 else formatted)
            
            # Test get all events
            print("\n3. Testing get all events...")
            all_events = await client.get_all_events()
            if "error" not in all_events:
                total = all_events.get('total_events', 0)
                returned = len(all_events.get('events', []))
                print(f"✓ Total events available: {total}")
                print(f"✓ Events returned: {returned}")
            else:
                print(f"✗ Get all events failed: {all_events['error']}")
            
        except Exception as e:
            print(f"\n✗ Tests failed for {base_url}: {e}")
        
        print(f"\n{'='*40}")

    print("\nAll endpoint tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_client())