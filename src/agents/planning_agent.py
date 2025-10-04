from src.agents.base_agent import BaseAgent
from typing import Dict, List
from langchain_core.prompts import ChatPromptTemplate
import logging

logger = logging.getLogger(__name__)

class PlanningAgent(BaseAgent):
	"""Agent responsible for creating research plans"""
    
	def __init__(self, config: Dict):
		super().__init__(config, "planning_agent")
    
	def create_research_plan(self, query: str, sector: str) -> Dict:
		"""Create a comprehensive research plan"""

		# Define sector-specific stock lists
		sector_entry = None
		for s in self.config.get("sectors", {}).get("allowed_sectors", []):
			if s.get("name") == sector:
				sector_entry = s
				break

		if not sector_entry:
			return {"error": "Sector not found"}

		# Normalize stocks: support either a simple list under 'stocks' or a dict under 'stock_symbols'
		stocks_list = []
		if isinstance(sector_entry.get("stocks"), list):
			stocks_list = sector_entry.get("stocks", [])
		elif isinstance(sector_entry.get("stock_symbols"), dict):
			# If configuration provides categorized symbols, flatten them
			sym_dict = sector_entry.get("stock_symbols", {})
			# collect high and low performers if present
			stocks_list = sym_dict.get("high_performers", []) + sym_dict.get("low_performers", [])

		# Fallback if still empty
		if not stocks_list:
			return {"error": "No stocks defined for sector"}

		# Detect if the user's query is requesting a specific ticker/company
		query_lower = query.lower()
		# Build a mapping of normalized short symbols (e.g., TCS) -> full symbol (e.g., TCS.NS)
		symbol_map = {}
		for s in stocks_list:
			short = s.split('.')[0].lower()
			symbol_map[short] = s

		requested_symbols = []
		for token in query_lower.replace(',', ' ').split():
			if token.upper() in [k.upper() for k in symbol_map.keys()] or token in symbol_map:
				# match short symbol
				short = token.split('.')[0].lower()
				if short in symbol_map:
					requested_symbols.append(symbol_map[short])

		# If no explicit ticker tokens found, try resolving company name via Yahoo tool (best-effort)
		if not requested_symbols:
			try:
				from src.tools.yahoo_finance_tool import YahooFinanceTool
				yahoo = YahooFinanceTool(self.config)
				# Prefer N-grams from the query (3 to 1 words) to find company names; avoid resolving the entire raw query
				tokens = query_lower.replace(',', ' ').split()
				for n in range(3, 0, -1):
					for i in range(0, max(1, len(tokens) - n + 1)):
						phrase = ' '.join(tokens[i:i + n])
						# skip overly long phrases and non-alphabetic phrases
						if len(phrase.split()) > 4:
							continue
						resolved = yahoo.resolve_symbol(phrase)
						if resolved:
							# validate resolved candidate
							try:
								import yfinance as _yf
								info = _yf.Ticker(resolved).info
								if info and isinstance(info, dict) and (info.get('shortName') or info.get('longName') or info.get('regularMarketPrice')):
									requested_symbols.append(resolved)
									break
							except Exception:
								continue
					if requested_symbols:
						break
				# As a last resort, try resolving compact queries/tickers only
				if not requested_symbols and len(tokens) <= 4:
					try:
						resolved = yahoo.resolve_symbol(query)
						if resolved:
							try:
								import yfinance as _yf
								info = _yf.Ticker(resolved).info
								if info and isinstance(info, dict) and (info.get('shortName') or info.get('longName') or info.get('regularMarketPrice')):
									requested_symbols.append(resolved)
							except Exception:
								pass
					except Exception:
						pass
			except Exception:
				# If symbol resolution fails, continue without requested_symbols
				pass

		# If user specifically requested tickers, restrict the plan to those
		if requested_symbols:
			stocks_list = requested_symbols

		# Create research plan
		# If user requested specific symbols, focus the objective and only include those
		if requested_symbols:
			objective_text = f"Comprehensive analysis of {', '.join(requested_symbols)}"
			high_perf = stocks_list[:5]
			low_perf = []
		else:
			objective_text = f"Comprehensive analysis of {sector} sector stocks"
			high_perf = stocks_list[:5]
			low_perf = stocks_list[-5:] if len(stocks_list) > 5 else []

		plan = {
			"objective": objective_text,
			"target_sector": sector,
			"stocks_to_analyze": {
				"high_performers": high_perf,
				"low_performers": low_perf
			},
			"research_areas": [
				"Current stock prices and historical performance",
				"Financial metrics calculation (CAGR, Sharpe Ratio, Volatility)",
				"Recent financial reports and news analysis",
				"Sector-specific trends and market conditions",
				"Risk assessment and comparative analysis"
			],
			"data_sources": [
				"Yahoo Finance API for stock data",
				"PDF financial reports via RAG system",
				"Web search for recent news and analysis"
			],
			"deliverables": [
				"Stock performance metrics table",
				"Comparative analysis charts",
				"Risk-adjusted return analysis",
				"Structured final report with recommendations"
			]
		}
        
		# Generate clarifying questions if needed
		clarifying_questions = self._generate_clarifying_questions(query, plan)
		if clarifying_questions:
			plan["clarifying_questions"] = clarifying_questions
        
		return plan
    
	def _generate_clarifying_questions(self, query: str, plan: Dict) -> List[str]:
		"""Generate clarifying questions based on query analysis"""
		questions = []
        
		# Use LLM to generate contextual questions
		prompt = ChatPromptTemplate.from_messages([
			("system", """You are a financial research planning assistant. Based on the user's query and research plan, 
			generate 2-3 specific clarifying questions that would help provide a more targeted analysis. 
			Focus on investment timeframe, risk tolerance, specific metrics of interest, or comparison preferences.
			Return only the questions, one per line."""),
			("human", f"Query: {query}\nPlan: {plan}")
		])
        
		try:
			response = self.llm.invoke(prompt.format_messages())
			questions = [q.strip() for q in response.content.split('\n') if q.strip()]
		except Exception as e:
			logger.warning(f"Could not generate clarifying questions: {e}")
        
		return questions[:3]  # Limit to 3 questions
    
	def process(self, state: Dict) -> Dict:
		"""Process planning phase"""
		query = state.get("query", "")
		sector = state.get("sector", "")
        
		if not sector:
			state["error"] = "No sector specified for planning"
			return state
        
		research_plan = self.create_research_plan(query, sector)
        
		state.update({
			"research_plan": research_plan,
			"planning_complete": True
		})
        
		self.log_action("research_plan_created", {"sector": sector, "stocks": len(research_plan.get("stocks_to_analyze", {}).get("high_performers", []))})
		return state
