import yfinance as yf
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class YahooFinanceTool:
	"""Fetches stock data and fundamentals from Yahoo Finance"""

	def __init__(self, config):
		self.config = config

	def _df_to_dict(self, df: pd.DataFrame):
		try:
			return df.fillna(0).to_dict()
		except Exception:
			return {}

	def get_stock_data(self, symbol):
		ticker = yf.Ticker(symbol)
		stock_info = {}
		try:
			hist = ticker.history(period="5y")
			prices = hist["Close"].tolist() if not hist.empty else []
			stock_info["prices"] = prices

			# Basic info
			try:
				stock_info["info"] = ticker.info
			except Exception:
				stock_info["info"] = {}

			# Financial statements
			try:
				stock_info["financials"] = self._df_to_dict(ticker.financials)
			except Exception:
				stock_info["financials"] = {}
			try:
				stock_info["quarterly_financials"] = self._df_to_dict(ticker.quarterly_financials)
			except Exception:
				stock_info["quarterly_financials"] = {}
			try:
				stock_info["balance_sheet"] = self._df_to_dict(ticker.balance_sheet)
			except Exception:
				stock_info["balance_sheet"] = {}
			try:
				stock_info["cashflow"] = self._df_to_dict(ticker.cashflow)
			except Exception:
				stock_info["cashflow"] = {}
			try:
				stock_info["earnings"] = self._df_to_dict(ticker.earnings)
			except Exception:
				stock_info["earnings"] = {}

			# News
			try:
				news = []
				if hasattr(ticker, "news"):
					raw_news = ticker.news
				else:
					raw_news = []
				for n in raw_news or []:
					# Keep title, publisher, link and providerPublishedDate
					news.append({
						"title": n.get("title"),
						"publisher": n.get("publisher"),
						"link": n.get("link"),
						"providerPublishedDate": n.get("providerPublishedDate")
					})
				stock_info["news"] = news
			except Exception:
				stock_info["news"] = []

		except Exception as e:
			logger.error(f"Yahoo fetch failed for {symbol}: {e}")
			stock_info = {"prices": [], "info": {}, "financials": {}, "news": []}

		return stock_info

	def resolve_symbol(self, query: str) -> str:
		"""Try to resolve a company name or partial symbol to a Yahoo ticker symbol.
		Best-effort: try variations and check ticker.info for matching longName or shortName.
		Returns symbol string (e.g., 'TCS.NS') or None if not found.
		"""
		query_norm = query.strip()
		# If user already provided something that looks like a ticker, return it
		if "." in query_norm or query_norm.isupper():
			# try direct ticker
			try:
				# quick sanity check: fetch info
				info = yf.Ticker(query_norm).info
				if info and isinstance(info, dict) and info.get("shortName"):
					return query_norm
			except Exception:
				pass

		# Build candidate list using config and simple heuristics (no external search dependency)
		candidates = []

		# 1) If config contains allowed_sectors and stocks, try matching short names
		try:
			for s in self.config.get("sectors", {}).get("allowed_sectors", []):
				for sym in s.get("stocks", []) or []:
					if sym:
						short = sym.split(".")[0].lower()
						# if query matches company name token or short symbol, add candidate
						if query_norm.lower() == short or query_norm.lower() in s.get("keywords", []):
							candidates.append(sym)
						# also if query tokens appear in keyword list
						for kw in s.get("keywords", []):
							if query_norm.lower() in str(kw).lower():
								candidates.append(sym)
		except Exception:
			# ignore config parsing errors
			pass

		# 2) Heuristic: try adding common market suffixes for Indian NSE if query is alphabetic
		if not candidates and query_norm.replace(" ", "").isalpha():
			candidates.append(query_norm.upper() + ".NS")
			# also try uppercase without suffix
			candidates.append(query_norm.upper())

		# Validate candidates
		for cand in candidates:
			try:
				info = yf.Ticker(cand).info
				if info and isinstance(info, dict):
					longname = (info.get("longName") or info.get("shortName") or "").lower()
					# match if query token appears in long/short name or short symbol equals query
					short_sym = cand.split('.')[0].lower()
					if query_norm.lower() in longname or query_norm.split()[0].lower() in longname or query_norm.lower() == short_sym:
						return cand
			except Exception:
				continue

		# Not found
		return None
