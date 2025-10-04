from src.agents.base_agent import BaseAgent
from typing import Dict, Any
import logging
 
from src.rag.retriever import FinancialReportRetriever

logger = logging.getLogger(__name__)


class ReportAgent(BaseAgent):
	"""Synthesizes findings into structured reports with visualizations"""
	def __init__(self, config: Dict):
		super().__init__(config, "report_agent")
		self.retriever = FinancialReportRetriever(config)

	def _markdown_section(self, title: str, body: str) -> str:
		return f"## {title}\n\n{body}\n\n"

	def process(self, state: Dict) -> Dict:
		"""Generate final report from all agent outputs"""
		analysis = state.get("analysis_results", {})
	# validation = state.get("validation_results", {})
		research_plan = state.get("research_plan", {})
		financial_reports = state.get("financial_reports", {})
		stock_data = state.get("stock_data", {})
		if not analysis:
			state["error"] = "No analysis results for report generation"
			return state

		agent_trace = state.get("agent_trace", [])
		md = []
		md.append("# Deep Research Report\n")
		md.append("**Agents/Tools Invoked:** " + ", ".join(agent_trace) + "\n")
		if research_plan and isinstance(research_plan, dict):
			md.append("## Research Plan\n")
			if research_plan.get("objective"):
				md.append(f"**Objective:** {research_plan['objective']}\n")
			if research_plan.get("target_sector"):
				md.append(f"**Sector:** {research_plan['target_sector']}\n")
			if research_plan.get("stocks_to_analyze"):
				stocks = research_plan['stocks_to_analyze']
				md.append(f"**Stocks:** {', '.join(stocks.get('high_performers', []) + stocks.get('low_performers', []))}\n")
			if research_plan.get("research_areas"):
				md.append("**Research Areas:** " + ", ".join(research_plan['research_areas']) + "\n")
			if research_plan.get("data_sources"):
				md.append("**Data Sources:** " + ", ".join(research_plan['data_sources']) + "\n")
			if research_plan.get("deliverables"):
				md.append("**Deliverables:** " + ", ".join(research_plan['deliverables']) + "\n")
			if research_plan.get("clarifying_questions"):
				md.append("**Clarifying Questions:** " + ", ".join(research_plan['clarifying_questions']) + "\n")
			md.append("\n---\n")
		report_struct = {"symbols": {}}
		# Metrics Table
		if analysis:
			md.append("## Key Metrics Table\n")
			headers = ["Symbol", "CAGR", "Sharpe", "Sortino", "Max Drawdown", "Volatility"]
			rows = []
			for symbol, details in analysis.items():
				m = details.get("metrics", {})
				rows.append([
					symbol,
					m.get("cagr"),
					m.get("sharpe_ratio"),
					m.get("sortino_ratio"),
					m.get("max_drawdown"),
					m.get("volatility")
				])
			md.append("| " + " | ".join(headers) + " |\n")
			md.append("|" + "|".join(["---"] * len(headers)) + "|\n")
			for row in rows:
				md.append("| " + " | ".join([str(x) if x is not None else "-" for x in row]) + " |\n")
			md.append("\n---\n")

		# Per-symbol deep sections
		for symbol, details in analysis.items():
			metrics = details.get("metrics", {})
			key_fin = details.get("key_financials") or {}
			quarterly = details.get("quarterly_financials") or {}
			earnings = details.get("earnings") or {}
			yoy = details.get("yoy_revenue_change")
			profit = details.get("profitability_ratio")
			recent = details.get("recent_performance_30d")
			news = details.get("news", [])

			# Company header
			company_name = None
			try:
				info = stock_data.get(symbol, {}).get("info", {}) if stock_data else {}
				company_name = info.get("longName") or info.get("shortName") or None
			except Exception:
				company_name = None

			# Key Financials & performance
			kf_lines = []
			cagr = metrics.get('cagr') if metrics else None
			kf_lines.append(f"CAGR: {cagr:.2%}" if isinstance(cagr, (float, int)) else f"CAGR: {cagr if cagr is not None else 'N/A'}")
			if isinstance(recent, (float, int)):
				kf_lines.append(f"30d change: {recent:.2%}")
			else:
				kf_lines.append(f"30d change: {recent if recent is not None else 'N/A'}")
			if yoy is not None:
				try:
					kf_lines.append(f"Revenue YoY (latest): {yoy:.2%}")
				except Exception:
					kf_lines.append(f"Revenue YoY (latest): {yoy}")
			else:
				kf_lines.append("Revenue YoY (latest): N/A")
			if profit is not None:
				try:
					kf_lines.append(f"Profitability (net/revenue): {profit:.2%}")
				except Exception:
					kf_lines.append(f"Profitability (net/revenue): {profit}")
			else:
				kf_lines.append("Profitability: N/A")

			# News summary (top 5)
			news_lines = []
			for n in (news[:5] if news else []):
				title = n.get('title') or n.get('headline') or n.get('summary')
				pub = n.get('publisher') or n.get('provider')
				art_text = n.get('article_text')
				art_title = n.get('article_title') or title
				if art_text:
					prompt = (
						f"Read the following news article about {company_name or symbol}.\n\nTitle: {art_title}\n\nArticle:\n{art_text}\n\n"
						"Extract 3 concise bullet points focusing on: (1) any numeric financial impact (revenue/earnings/guidance), "
						"(2) analyst actions or commentary, and (3) regulatory, macro or client-concerns. "
						"Return bullets only, 1-3 sentences each."
					)
					try:
						resp = self.llm.generate([{"role": "user", "content": prompt}])
						summary_text = getattr(resp, 'content', None) or (resp[0].text if isinstance(resp, (list, tuple)) and resp else str(resp))
					except Exception:
						summary_text = None
					if summary_text:
						news_lines.append(f"- {art_title} ({pub}): {summary_text}")
						n['summary'] = summary_text
					else:
						news_lines.append(f"- {art_title} ({pub}): {title}")
				else:
					news_lines.append(f"- {title} ({pub})")

			# RAG-retrieved reports
			rag_excerpts = []
			try:
				reports_for_sym = financial_reports.get(symbol) if financial_reports else None
				results = reports_for_sym or []
				for r in (results[:3] if results else []):
					excerpt = {
						"title": r.get('title') if isinstance(r, dict) else str(r),
						"score": r.get('score') if isinstance(r, dict) else None,
						"snippet": (r.get('text') or r.get('snippet') or '')[:1200] if isinstance(r, dict) else str(r),
						"source": r.get('source') or r.get('url') or r.get('link') if isinstance(r, dict) else None
					}
					rag_excerpts.append(excerpt)
			except Exception:
				results = []

			# Company profile
			company_profile = []
			try:
				info = stock_data.get(symbol, {}).get('info', {}) if stock_data else {}
				company_profile.append(f"Sector: {info.get('sector') or 'N/A'}")
				company_profile.append(f"Industry: {info.get('industry') or 'N/A'}")
				company_profile.append(f"Market Cap: {info.get('marketCap') or 'N/A'}")
			except Exception:
				pass

			# Financial trend bullets
			trend_lines = []
			try:
				kf = details.get('key_financials') or {}
				years = []
				if isinstance(kf, dict) and kf:
					try:
						entries = sorted(kf.items(), key=lambda kv: str(kv[0]), reverse=True)
						for k, v in entries[:4]:
							yr = v.get('Total Revenue') or v.get('revenue') if isinstance(v, dict) else None
							if yr is not None:
								years.append(float(yr))
					except Exception:
						pass
					if len(years) >= 2:
						trend = 'increasing' if years[0] > years[-1] else 'decreasing' if years[0] < years[-1] else 'flat'
						trend_lines.append(f"Revenue trend (recent): {trend} over {len(years)} periods")
			except Exception:
				pass

			# Competitor comparison
			competitor_lines = []
			try:
				sector_cfg = self.config.get('sectors', {}).get('allowed_sectors', [])
				competitors = []
				for s in sector_cfg:
					if isinstance(s.get('stocks'), list) and symbol in s.get('stocks'):
						competitors = [x for x in s.get('stocks') if x != symbol][:5]
				if competitors:
					a = state.get('analysis_summary', {})
					# base = a.get(symbol, {})
					for c in competitors:
						c_m = a.get(c, {})
						competitor_lines.append(f"{c}: CAGR {c_m.get('cagr')}, Sharpe {c_m.get('sharpe_ratio')}")
			except Exception:
				pass

			# Risks
			risk_lines = []
			for ex in (rag_excerpts or []):
				risk_lines.append(f"- {ex.get('title')}: {ex.get('snippet')[:300]}")
			for n in (news[:5] if news else []):
				if isinstance(n, dict) and n.get('summary'):
					risk_lines.append(f"- From news ({n.get('publisher') or n.get('source')}): {n.get('summary')}")

			# Numeric facts
			numeric_facts = []
			try:
				import re
				for n in (news or [])[:10]:
					if not isinstance(n, dict):
						continue
					txt = (n.get('summary') or n.get('snippet') or n.get('title') or '')
					for m in re.findall(r"[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?%", txt):
						numeric_facts.append({"type": "percent", "text": m, "source": n.get('publisher') or n.get('source')})
					for m in re.findall(r"(?:Rs\.?|INR\s?|USD\s?|\$)\s?[\d,]+(?:\.\d+)?", txt, flags=re.I):
						numeric_facts.append({"type": "currency", "text": m, "source": n.get('publisher') or n.get('source')})
			except Exception:
				numeric_facts = []

			# Web news highlights
			web_news_summary = None
			try:
				sd = stock_data.get(symbol, {}) if stock_data else {}
				web_news_summary = sd.get('web_news_summary')
			except Exception:
				web_news_summary = None

			body = "\n".join([
				"\n".join(company_profile),
				"".join(kf_lines),
				"\n".join(trend_lines),
				"\n".join(competitor_lines),
				"\n### Recent News\n",
				("\n".join(news_lines) if news_lines else "No recent news found."),
				(f"\n### Web News Highlights\n\n{web_news_summary}" if web_news_summary else ""),
				"\n### RAG Document Findings\n",
				("\n".join([f"- {ex.get('title')}: {ex.get('snippet')[:300]} (Source: {ex.get('source')})" for ex in rag_excerpts]) if rag_excerpts else "No RAG findings."),
				"\n### Key Numeric Facts\n",
				("\n".join([f"- {f['text']} (type: {f['type']}, source: {f['source']})" for f in numeric_facts]) if numeric_facts else "No numeric facts extracted."),
				"\n### Key Risks\n",
				("\n".join(risk_lines) if risk_lines else "No explicit risks found from RAG/news.")
			])
			if rag_excerpts:
				body += "\n\n### RAG Document Excerpts\n"
				for ex in rag_excerpts:
					body += f"- **{ex.get('title')}** (score: {ex.get('score')})\n\n{ex.get('snippet')}\n\nSource: {ex.get('source') or 'N/A'}\n\n"

			md.append(self._markdown_section(f"Analysis: {symbol}", body))

			# Aggregated news summary
			aggregated = {}
			try:
				if isinstance(news, list) and news:
					aggregated_text = None
					for n in news:
						if isinstance(n, dict) and n.get('summary'):
							aggregated_text = '\n'.join([str(x.get('summary')) for x in news if x.get('summary')][:3])
							break
					sd = stock_data.get(symbol, {}) if stock_data else {}
					agg_lvl = sd.get('news_aggregated_summary') or sd.get('news_aggregate')
					if not aggregated_text and agg_lvl:
						aggregated_text = agg_lvl
					if aggregated_text:
						aggregated['synthesized'] = aggregated_text
			except Exception:
				aggregated = {}

			report_struct['symbols'][symbol] = {
				'metrics': metrics,
				'key_financials': key_fin,
				'quarterly_financials': quarterly,
				'earnings': earnings,
				'yoy_revenue_change': yoy,
				'profitability_ratio': profit,
				'news': news,
				'numeric_facts': numeric_facts,
				'news_aggregated': aggregated,
				'rag_excerpts': rag_excerpts
			}

			header = f"**{company_name or symbol}** — {symbol}\n\n"
			md[-1] = header + md[-1]

		# Market & competitors high-level placeholder
		market_section = "Market context and competitors analysis not available locally. Consider enabling external web search or LLM summarization."
		md.append(self._markdown_section("Market & Competitors", market_section))

		# News & Analyst summary using LLM if news present
		summary_block = None
		try:
			all_news = []
			for sym, details in report_struct['symbols'].items():
				for n in (details.get('news') or []):
					all_news.append({
						"symbol": sym,
						"title": n.get('title'),
						"source": n.get('publisher') or n.get('source'),
						"link": n.get('link'),
						"snippet": n.get('snippet') or n.get('providerPublishedDate')
					})
			if all_news:
				prompt = "Summarize the following recent news items about these stocks. Provide 4-6 concise bullet points highlighting price action drivers, analyst commentary, and any regulatory or macro events. Do NOT output raw links; instead extract the key facts and the source name.\n\n"
				for it in all_news[:12]:
					item_text = it.get('snippet') or it.get('summary') or it.get('link') or ''
					prompt += f"- [{it['symbol']}] {it['title']} (source: {it.get('source')}) - {item_text}\n"
				try:
					resp = self.llm.generate([{"role": "user", "content": prompt}])
					summary_block = getattr(resp, 'content', None) or (resp[0].text if isinstance(resp, (list, tuple)) and resp else str(resp))
				except Exception:
					summary_block = None
		except Exception:
			summary_block = None

		if summary_block:
			md.append(self._markdown_section("News & Analyst Summary", summary_block))

		# Sources section
		source_names = set()
		for sym, details in report_struct['symbols'].items():
			for n in details.get('news', []) or []:
				if isinstance(n, dict):
					src = n.get('publisher') or n.get('source')
					if src:
						source_names.add(src)
			for ex in details.get('rag_excerpts', []) or []:
				if ex.get('source'):
					source_names.add(ex.get('source'))

		if source_names:
			md.append(self._markdown_section("Sources (publisher names)", "\n".join(f"- {s}" for s in sorted(source_names))))

		final_markdown = "\n".join(md)

		# If we have exactly one symbol, ask the LLM to produce a full, structured deep-dive
		if len(report_struct['symbols']) == 1:
			sym = next(iter(report_struct['symbols'].keys()))
			try:
				deep_report = self._generate_deep_company_report(sym, report_struct['symbols'][sym], stock_data.get(sym, {}))
				if deep_report:
					state["final_report"] = deep_report
					state["final_report_data"] = report_struct
					self.log_action("deep_company_report_generated", {"symbol": sym})
					return state
			except Exception:
				pass

		# Add an executive summary using the LLM if multiple symbols or no deep_report
		try:
			summary_prompt = (
				"Provide an executive summary (6-8 bullets) covering the main findings across the analyzed symbols. "
				"Use concise financial language and cite key drivers from the data provided.\n\n"
			)
			for sym, sec in report_struct['symbols'].items():
				summary_prompt += f"Symbol: {sym}\n"
				metrics = sec.get('metrics') or {}
				summary_prompt += (
					f"Metrics: CAGR={metrics.get('cagr')}, Sharpe={metrics.get('sharpe_ratio')}, "
					f"Volatility={metrics.get('volatility')}\n"
				)
				news = sec.get('news') or []
				if news:
					summary_prompt += f"Top news headline: {news[0].get('title')} ({news[0].get('publisher')})\n"
				rag = sec.get('rag_excerpts') or []
				if rag:
					summary_prompt += f"RAG excerpt: {rag[0].get('title')}\n"
				summary_prompt += "\n"
			resp = self.llm.generate([{"role": "user", "content": summary_prompt}])
			exec_summary = getattr(resp, 'content', None) or (resp[0].text if isinstance(resp, (list, tuple)) and resp else str(resp))
			if exec_summary:
				final_markdown = "## Executive Summary\n\n" + exec_summary + "\n\n" + final_markdown
				state["final_report"] = final_markdown
		except Exception:
			pass

		state["final_report"] = final_markdown
		state["final_report_data"] = report_struct
		self.log_action("report_generated", {"symbols": list(report_struct['symbols'].keys())})
		return state

	def _generate_deep_company_report(self, symbol: str, struct: Dict[str, Any], stock_info: Dict[str, Any]) -> str:
		"""Use LLM to generate a detailed company report in the user's requested format.

		The prompt below instructs the LLM to produce sections: Executive Summary, Financial Performance,
		TTM metrics, Business Model, Strategic Developments, Competitive Analysis, Technicals, Analyst
		Consensus & Valuation, Investment Thesis, Risks, and Conclusion.
		"""
		company_name = stock_info.get('info', {}).get('longName') or symbol
		# Collect available facts to include in the prompt
		facts = {
			"market_cap": stock_info.get('info', {}).get('marketCap'),
			"current_price": stock_info.get('prices')[-1] if stock_info.get('prices') else None,
			"52_week_high": stock_info.get('info', {}).get('fiftyTwoWeekHigh'),
			"52_week_low": stock_info.get('info', {}).get('fiftyTwoWeekLow'),
		}

		prompt = f"Produce a comprehensive, investor-quality report for {company_name} ({symbol}).\n"
		prompt += "Follow this section structure exactly: Executive Summary; Financial Performance Analysis; Trailing Twelve Months Performance; Business Model & Strategic Positioning; Recent Strategic Developments; Competitive Analysis; Technical Analysis; Analyst Consensus & Valuation; Investment Thesis; Key Catalysts; Critical Risks; Conclusion.\n"
		prompt += "Use available factual data where present, and clearly label estimated or missing data. Use real-sounding but conservative analyst tone; do NOT invent confidential data. If you don't have exact numbers, say 'data not available' instead of fabricating.\n\n"
		# Append known facts
		prompt += "Known facts (as JSON):\n"
		prompt += str(facts) + "\n\n"
		# Append RAG excerpts and news summaries if available
		if struct.get('rag_excerpts'):
			prompt += "Relevant RAG excerpts (short):\n"
			for ex in struct.get('rag_excerpts')[:5]:
				prompt += f"- {ex.get('title')}: {ex.get('snippet')[:400]}\n"
		# Prefer a symbol-level synthesized summary if present (produced by data collection aggregation)
		news_agg = struct.get('news_aggregated') or {}
		if news_agg and news_agg.get('synthesized'):
			prompt += "Recent synthesized news summary (from aggregated sources):\n"
			prompt += f"{news_agg.get('synthesized')}\n\n"
		# Also include raw per-article summaries/highlights if present
		if struct.get('news'):
			prompt += "Recent news summaries (per-article):\n"
			for n in struct.get('news')[:6]:
				if isinstance(n, dict) and n.get('summary'):
					prompt += f"- {n.get('title') or ''}: {n.get('summary')} (source: {n.get('publisher') or n.get('source')})\n"
				else:
					prompt += f"- {n.get('title')} (source: {n.get('publisher') or n.get('source')})\n"

		# Instruct LLM on output format: provide numeric tables and a final recommendation with target price
		prompt += "\nOutput: Provide the sections with bold headings, numeric tables where applicable, and finish with a short Recommendation paragraph including a target price or explicitly state 'price target not available' if missing. Use INR or local currency where relevant.\n"

		try:
			resp = self.llm.generate([{"role": "user", "content": prompt}])
			text = getattr(resp, 'content', None) or (resp[0].text if isinstance(resp, (list, tuple)) and resp else str(resp))
		except Exception:
			text = None

		return text
