from src.agents.base_agent import BaseAgent
from typing import Dict, Any

class RouterAgent(BaseAgent):
	"""Router agent that handles query routing and guardrails"""
    
	def __init__(self, config: Dict):
		super().__init__(config, "router_agent")
		self.allowed_sectors = config["sectors"]["allowed_sectors"]
    
	def check_guardrails(self, query: str) -> Dict[str, Any]:
		"""Check if query is within allowed sectors"""
		query_lower = query.lower()
        
		# Check for allowed sector keywords
		allowed = False
		detected_sector = None
        
		for sector in self.allowed_sectors:
			for keyword in sector["keywords"]:
				if keyword.lower() in query_lower:
					allowed = True
					detected_sector = sector["name"]
					break
			if allowed:
				break
        
		if not allowed:
			return {
				"allowed": False,
				"message": ("I apologize, but I can only help with queries related to "
						  "Information Technology (IT) and Pharmaceutical sector stocks. "
						  "Please ask me about IT or Pharma companies and their stock analysis."),
				"detected_sector": None
			}
        
		return {
			"allowed": True,
			"message": f"Query approved for {detected_sector} sector analysis.",
			"detected_sector": detected_sector
		}
    
	def route_query(self, query: str, mode: str) -> Dict[str, Any]:
		"""Route query to appropriate processing mode"""
		guardrails_result = self.check_guardrails(query)
        
		if not guardrails_result["allowed"]:
			return {
				"route": "decline",
				"message": guardrails_result["message"]
			}
        
		return {
			"route": mode,  # "basic" or "deep_research"
			"sector": guardrails_result["detected_sector"],
			"approved": True
		}
    
	def process(self, state: Dict) -> Dict:
		"""Process routing logic"""
		query = state.get("query", "")
		mode = state.get("mode", "basic")
        
		routing_result = self.route_query(query, mode)
        
		state.update({
			"routing_result": routing_result,
			"approved": routing_result.get("approved", False),
			"sector": routing_result.get("sector"),
			"route": routing_result.get("route")
		})
        
		self.log_action("query_routed", routing_result)
		return state
