
import os
import requests
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()


class SerpApiTool:
	"""Lightweight SerpApi wrapper to fetch news results.

	Tries SerpApi first; if no results and a TAVILY_API_KEY is present, falls back to Tavily.
	"""

	def __init__(self, api_key: str = None, tavily_key: str = None):
		self.api_key = api_key or os.getenv('SERP_API_KEY')
		self.tavily_key = tavily_key or os.getenv('TAVILY_API_KEY')

	def _serpapi_search(self, query: str, num: int = 5) -> List[Dict]:
		if not self.api_key:
			return []
		params = {
			"q": query,
			"engine": "google",
			"tbm": "nws",
			"api_key": self.api_key,
			"num": num,
		}
		try:
			r = requests.get("https://serpapi.com/search.json", params=params, timeout=10)
			if r.status_code != 200:
				return []
			j = r.json()
			items = []
			for n in j.get('news_results', [])[:num]:
				items.append({
					"title": n.get('title'),
					"snippet": n.get('snippet') or n.get('body'),
					"source": n.get('source'),
					"link": n.get('link') or n.get('url'),
					"published_at": n.get('date') or n.get('published_at')
				})
			return items
		except Exception:
			return []

	def _tavily_search(self, query: str, num: int = 5) -> List[Dict]:
		"""Fallback to Tavily if available. Tavily's public API for this workspace is not fully specified,
		so this method uses a conservative request pattern: GET /v1/news/search?q=... with API key header.
		If your Tavily endpoint differs, update this function accordingly.
		"""
		if not self.tavily_key:
			return []
		try:
			headers = {"Authorization": f"Bearer {self.tavily_key}"}
			params = {"q": query, "limit": num}
			# Using a conservative, likely Tavily dev endpoint — adjust if you have a different URL
			r = requests.get("https://api.tavily.ai/v1/news/search", headers=headers, params=params, timeout=8)
			if r.status_code != 200:
				return []
			j = r.json()
			items = []
			# Expecting a list under 'articles' or top-level list
			for n in (j.get('articles') or j.get('results') or j)[:num]:
				items.append({
					"title": n.get('title'),
					"snippet": n.get('snippet') or n.get('summary') or n.get('body'),
					"source": n.get('source') or n.get('publisher'),
					"link": n.get('url') or n.get('link'),
					"published_at": n.get('published_at') or n.get('date')
				})
			return items
		except Exception:
			return []

	def search_news(self, query: str, num: int = 5) -> List[Dict]:
		"""Return a list of news items for the query.
		Each item is a dict with keys: title, snippet, source, link, published_at
		Tries SerpApi then Tavily as fallback.
		"""
		items = self._serpapi_search(query, num=num)
		if items:
			return items
		# try tavily
		items = self._tavily_search(query, num=num)
		return items or []

	def get_article_text(self, url: str, timeout: int = 8) -> Dict:
		"""Fetch a URL and attempt to extract the main article text and title.

		Returns a dict: {"title": str or None, "text": str or ""}
		This function tries to use BeautifulSoup if available; otherwise falls back to
	
a simple tag-stripping approach. It is conservative to avoid heavy dependencies.
		"""
		if not url:
			return {"title": None, "text": ""}
		try:
			r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
			if r.status_code != 200:
				return {"title": None, "text": ""}
			html = r.text
		except Exception:
			return {"title": None, "text": ""}
		title = None
		text = ""
		# Try BeautifulSoup if installed
		try:
			from bs4 import BeautifulSoup
			bs = BeautifulSoup(html, 'lxml')
			# Title
			if bs.title and bs.title.string:
				title = bs.title.string.strip()
			# Prefer <article> tag
			article = bs.find('article')
			if article:
				text = article.get_text(separator='\n').strip()
			else:
				# fallback: join all <p> tags
				ps = [p.get_text().strip() for p in bs.find_all('p') if p.get_text().strip()]
				# keep paragraphs longer than a threshold, join
				ps = [p for p in ps if len(p) > 80]
				if not ps:
					ps = [p.get_text().strip() for p in bs.find_all('p')]
				text = '\n\n'.join(ps).strip()
		except Exception:
			# bs4 not available or parsing failed; fallback to naive extraction
			import re
			# extract title tag
			m = re.search(r'<title[^>]*>(.*?)</title>', html, flags=re.I|re.S)
			if m:
				title = re.sub(r'\s+', ' ', m.group(1)).strip()
			# strip tags and condense whitespace
			text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.I|re.S)
			text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.I|re.S)
			text = re.sub(r'<[^>]+>', ' ', text)
			text = re.sub(r'\s+', ' ', text).strip()
			# heuristics: cut to first 2000 chars
			if len(text) > 2000:
				text = text[:2000]
		return {"title": title, "text": text}
