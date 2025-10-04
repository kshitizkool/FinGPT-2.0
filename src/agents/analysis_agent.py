from src.agents.base_agent import BaseAgent
from typing import Dict, Any
import numpy as np
import logging
from src.tools.metrics_calculator import MetricsCalculator

logger = logging.getLogger(__name__)

class AnalysisAgent(BaseAgent):
	"""Performs quantitative calculations and financial modeling"""
	def __init__(self, config: Dict):
		super().__init__(config, "analysis_agent")
		self.metrics_calculator = MetricsCalculator()

	def calculate_metrics(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
		"""Calculate financial metrics for each stock"""
		results = {}
		for symbol, data in stock_data.items():
			try:
				prices = data.get("prices", [])
				metrics = self.metrics_calculator.calculate_all(prices)
				# Key financials from Yahoo (if present)
				financials = data.get("financials", {})
				quarterly = data.get("quarterly_financials", {})
				earnings = data.get("earnings", {})
				news = data.get("news", [])

				# Compute YoY revenue change and profitability from reported financials
				yoy_revenue = None
				profitability = None
				try:
					# Prefer keyed annual financials if present (e.g., timestamps -> dict)
					key_fin = data.get("key_financials") or financials or {}

					# Normalize keys (timestamps) and sort descending by date
					if isinstance(key_fin, dict) and key_fin:
						# keys may be pandas Timestamp or strings
						entries = []
						for k, v in key_fin.items():
							try:
								# try to coerce to string key for sorting
								entries.append((str(k), v))
							except Exception:
								entries.append((k, v))
						# assume insertion order approximates recency; pick two most recent available
						# safer: sort by key string (ISO date) descending
						entries_sorted = sorted(entries, key=lambda kv: kv[0], reverse=True)
						latest = entries_sorted[0][1] if entries_sorted else {}
						prev = entries_sorted[1][1] if len(entries_sorted) > 1 else None

						# helper to find revenue/net income in report dict using common key variants
						def _find_amount(dct, possibles):
							if not isinstance(dct, dict):
								return None
							for key in possibles:
								if key in dct and dct[key] is not None:
									return dct[key]
							# fallback: case-insensitive search
							for k, v in dct.items():
								if isinstance(k, str) and k.lower() in [p.lower() for p in possibles]:
									return v
							return None

						rev_latest = _find_amount(latest, ["Total Revenue", "TotalRevenue", "revenue", "Revenue", "totalRevenue"]) 
						rev_prev = _find_amount(prev, ["Total Revenue", "TotalRevenue", "revenue", "Revenue", "totalRevenue"]) if prev else None
						ni_latest = _find_amount(latest, ["Net Income", "netIncome", "NetIncome", "Net Income Common Stockholders"]) 

						try:
							if rev_latest is not None and rev_prev is not None and float(rev_prev) != 0:
								yoy_revenue = float(rev_latest - rev_prev) / float(rev_prev)
						except Exception:
							yoy_revenue = None

						try:
							if ni_latest is not None and rev_latest is not None and float(rev_latest) != 0:
								profitability = float(ni_latest) / float(rev_latest)
						except Exception:
							profitability = None
				except Exception:
					yoy_revenue = None
					profitability = None

				# Recent performance: last 30 days change
				recent_perf = None
				try:
					if prices and len(prices) >= 2:
						recent = prices[-30:] if len(prices) >= 30 else prices
						if recent:
							recent_perf = (recent[-1] - recent[0]) / recent[0] if recent[0] else None
				except Exception:
					recent_perf = None
				# Normalize numeric types to native python types for JSON/markdown rendering
				def _to_native(x):
					try:
						if isinstance(x, (np.generic,)):
							return float(x)
						if isinstance(x, dict):
							return {k: _to_native(v) for k, v in x.items()}
						if isinstance(x, list):
							return [_to_native(v) for v in x]
						return x
					except Exception:
						return x

				metrics_native = _to_native(metrics)
				financials_native = _to_native(financials)
				quarterly_native = _to_native(quarterly)
				earnings_native = _to_native(earnings)
				news_native = []
				try:
					# sanitize news entries
					for n in (news or [])[:10]:
						if not isinstance(n, dict):
							continue
						news_native.append({
							"title": n.get("title") or n.get("headline") or None,
							"publisher": n.get("publisher") or n.get("source") or None,
							"link": n.get("link") or n.get("url") or None,
							"date": str(n.get("providerPublishedDate") or n.get("datetime") or n.get("date")) if (n.get("providerPublishedDate") or n.get("datetime") or n.get("date")) else None
						})
				except Exception:
					news_native = []

				results[symbol] = {
					"metrics": metrics_native,
					"key_financials": financials_native,
					"quarterly_financials": quarterly_native,
					"earnings": earnings_native,
					"yoy_revenue_change": _to_native(yoy_revenue),
					"profitability_ratio": _to_native(profitability),
					"recent_performance_30d": _to_native(recent_perf),
					"news": news_native
				}
			except Exception as e:
				logger.error(f"Error calculating metrics for {symbol}: {e}")
				results[symbol] = {"error": str(e)}
		return results

	def process(self, state: Dict) -> Dict:
		"""Process analysis phase"""
		stock_data = state.get("stock_data", {})
		if not stock_data:
			state["error"] = "No stock data available for analysis"
			return state
		metrics = self.calculate_metrics(stock_data)
		# store detailed analysis per symbol
		state["analysis_results"] = metrics
		# Also build a small summary table for downstream display
		summary = {}
		for sym, details in metrics.items():
			m = details.get("metrics") if isinstance(details, dict) else {}
			summary[sym] = {
				"cagr": m.get("cagr") if m else None,
				"sharpe_ratio": m.get("sharpe_ratio") if m else None,
				"volatility": m.get("volatility") if m else None
			}
		state["analysis_summary"] = summary
		self.log_action("metrics_calculated", {"count": len(metrics)})
		return state
