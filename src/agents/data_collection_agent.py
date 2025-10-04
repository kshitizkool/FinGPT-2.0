from src.agents.base_agent import BaseAgent
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class DataCollectionAgent(BaseAgent):
	"""Agent responsible for collecting stock data and financial reports"""
    
	def __init__(self, config: Dict):
		super().__init__(config, "data_collection_agent")
    
	def collect_stock_data(self, symbols: List[str]) -> Dict:
		"""Collect stock data from Yahoo Finance"""
		from src.tools.yahoo_finance_tool import YahooFinanceTool
		from src.tools.web_search import SerpApiTool

		yahoo_tool = YahooFinanceTool(self.config)
		serp = SerpApiTool()
		stock_data = {}
        
		for symbol in symbols:
			try:
				data = yahoo_tool.get_stock_data(symbol)
				# Always fetch web search news (SerpApi/Tavily) for each symbol
				try:
					web_news_items = serp.search_news(f"{symbol} stock news")
					# map SerpApi fields to a standard shape
					web_news = [{
						'title': n.get('title'),
						'publisher': n.get('source') or n.get('publisher'),
						'link': n.get('link') or n.get('url'),
						'providerPublishedDate': n.get('published_at') or n.get('date'),
						'snippet': n.get('snippet') or n.get('body') or n.get('summary')
					} for n in web_news_items]
					data['web_news'] = web_news
				except Exception:
					logger.exception(f"SerpApi/Tavily web search failed for {symbol}")

				# Summarize yfinance news articles (as before)
				for n in (data.get('news') or []):
					try:
						link = n.get('link') or n.get('url') or None
						if link and not n.get('article_text'):
							art = serp.get_article_text(link)
							if art and art.get('text'):
								n['article_text'] = art.get('text')
								n['article_title'] = art.get('title')
					except Exception:
						logger.debug(f"Failed to fetch article text for {symbol} link={link}")
					# Summarize yfinance news
					art_text = n.get('article_text') or ""
					art_title = n.get('article_title') or n.get('title') or ""
					if art_text and len(art_text) > 200:
						try:
							prompt = f"""
You are a concise financial summarizer. Read the article text below and return:
1) 3 short bullet points (1-2 sentences each) focusing on: numeric financial impacts (revenue/earnings/guidance), analyst actions/comments, and regulatory/macro events;
2) a one-line Highlights: summary that contains the single most important fact.

Title: {art_title}

Article:
{art_text}

"""
							resp = self.llm.generate([{"role": "user", "content": prompt}])
							summary_text = getattr(resp, 'content', None) or (resp[0].text if isinstance(resp, (list, tuple)) and resp else str(resp))
							n['summary'] = summary_text
						except Exception:
							pass
					else:
						if not n.get('summary'):
							n['summary'] = n.get('snippet') or art_title or ""

				# Summarize web search news articles
				web_news = data.get('web_news', [])
				for wn in web_news:
					snippet = wn.get('snippet') or wn.get('title') or ""
					if snippet and len(snippet) > 40:
						try:
							prompt = f"""
You are a financial news summarizer. Read the snippet below and return:
1) 2-3 bullet points on key financial impacts, analyst comments, or macro/regulatory events.
2) a one-line Highlights: summary with the most important fact.

Snippet:
{snippet}
"""
							resp = self.llm.generate([{"role": "user", "content": prompt}])
							summary_text = getattr(resp, 'content', None) or (resp[0].text if isinstance(resp, (list, tuple)) and resp else str(resp))
							wn['summary'] = summary_text
						except Exception:
							pass
					else:
						if not wn.get('summary'):
							wn['summary'] = snippet

				# Aggregate web news summaries for this symbol
				try:
					web_aggregates = []
					for wn in web_news[:8]:
						if wn.get('summary'):
							web_aggregates.append(f"- {wn.get('title') or ''}: {wn.get('summary')}")
					if web_aggregates:
						agg_prompt = (
							"You are a financial research assistant. Given the following recent web news summaries for a single stock, "
							"produce: (A) 4 concise bullets on price/earnings/guidance drivers; (B) 3 'Key Highlights'; "
							"and (C) a short 'Implication for investors'. Return as plain text with clear headings.\n\n"
							+ "\n".join(web_aggregates)
						)
						resp2 = self.llm.generate([{"role": "user", "content": agg_prompt}])
						agg_text = getattr(resp2, 'content', None) or (resp2[0].text if isinstance(resp2, (list, tuple)) and resp2 else str(resp2))
						data['web_news_summary'] = agg_text
				except Exception:
					pass
				stock_data[symbol] = data
			except Exception as e:
				logger.error(f"Failed to collect data for {symbol}: {e}")
				stock_data[symbol] = {"error": str(e)}
        
		return stock_data
    
	def collect_financial_reports(self, symbols: List[str], sector: str) -> Dict:
		"""Collect financial reports via RAG system"""
		from src.rag.retriever import FinancialReportRetriever
        
		retriever = FinancialReportRetriever(self.config)
		reports = {}
        
		for symbol in symbols:
			try:
				relevant_docs = retriever.retrieve_reports(symbol, sector)
				reports[symbol] = relevant_docs
			except Exception as e:
				logger.error(f"Failed to retrieve reports for {symbol}: {e}")
				reports[symbol] = {"error": str(e)}
        
		return reports
    
	def process(self, state: Dict) -> Dict:
		"""Process data collection phase"""
		research_plan = state.get("research_plan", {})
        
		if not research_plan:
			state["error"] = "No research plan available for data collection"
			return state
        
		# Get stock symbols to analyze
		stocks = research_plan.get("stocks_to_analyze", {})
		all_symbols = stocks.get("high_performers", []) + stocks.get("low_performers", [])
        
		if not all_symbols:
			state["error"] = "No stock symbols found in research plan"
			return state
        
		# Collect stock data
		stock_data = self.collect_stock_data(all_symbols)
        
		# Collect financial reports
		sector = research_plan.get("target_sector", "")
		financial_reports = self.collect_financial_reports(all_symbols, sector)
        
		state.update({
			"stock_data": stock_data,
			"financial_reports": financial_reports,
			"data_collection_complete": True
		})
        
		self.log_action("data_collected", {
			"symbols": all_symbols, 
			"success_count": len([s for s in stock_data.values() if "error" not in s])
		})
        
		return state
