import streamlit as st
from src.agents.router_agent import RouterAgent
from src.agents.base_agent import BaseAgent, Agent
from src.workflow.graph_builder import create_stock_analysis_graph

def process_user_query(query: str, placeholder):
    """Process user query through the agent system"""
    try:
        with placeholder:
            with st.status("Processing your request...", expanded=True) as status:
                st.write("🛡️ Checking sector guardrails...")
                router = RouterAgent(st.session_state.config)
                guardrails_result = router.check_guardrails(query)
                if not guardrails_result["allowed"]:
                    st.error("❌ Query outside allowed sectors")
                    response = guardrails_result["message"]
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response
                    })
                    st.markdown(response)
                    return
                st.write("✅ Guardrails passed - IT/Pharma query detected")
                st.write("🔀 Routing to analysis mode...")
                if st.session_state.analysis_mode == "basic":
                    st.write("🎯 Basic mode: Single LLM analysis")
                    response = process_basic_mode(query)
                else:
                    st.write("🔬 Deep research mode: Multi-agent analysis")
                    # pass the detected sector from guardrails to the deep research pipeline
                    response = process_deep_research_mode(query, status, guardrails_result.get('detected_sector'))
                status.update(label="✅ Analysis complete!", state="complete")
        st.session_state.messages.append({
            "role": "assistant",
            "content": response.get("content", ""),
            "metadata": response.get("metadata", {})
        })
        if "metadata" in response:
            # Use the package-style import path so imports work when running from repo root
            from app.component.agent_response import render_agent_response
            render_agent_response(response["content"], response["metadata"])
        else:
            st.markdown(response["content"])
    except Exception as e:
        st.session_state.logger.error(f"Error processing query: {str(e)}")
        st.error(f"An error occurred: {str(e)}")

def process_basic_mode(query: str) -> dict:
    """Process query in basic mode (single LLM)"""
    # Basic mode should be a single prompt -> single LLM completion.
    # Use the simple Agent wrapper to access its LLM client and make a one-shot call.
    agent = Agent()
    prompt = (
        f"You are a helpful financial assistant. Answer the user's query concisely and with clear actionable insights.\n\nUser query: {query}"
    )
    try:
        # Agent._call_llm expects a list of messages in the OpenAI chat format
        messages = [
            {"role": "system", "content": "You are a helpful financial assistant."},
            {"role": "user", "content": query}
        ]
        llm_response = agent._call_llm(messages)
        content = llm_response or "No response from LLM"
    except Exception as e:
        content = f"Error calling LLM: {e}"

    # Build a simple structured report payload so the UI can offer downloads in basic mode
    report_payload = {
        "query": query,
        "generated_at": __import__('datetime').datetime.utcnow().isoformat() + 'Z',
        "content": content
    }

    return {
        "content": content,
        "metadata": {"mode": "basic", "report_data": report_payload}
    }

def process_deep_research_mode(query: str, status, sector: str = None) -> dict:
    """Process query in deep research mode (multi-agent), logging agent/tool usage and surfacing all outputs."""
    graph = create_stock_analysis_graph(st.session_state.config)
    state = {
        "query": query,
        "chat_history": st.session_state.chat_history.messages,
        "mode": "deep_research",
        "sector_allowed": True,
        "sector": sector,
        "agent_trace": []
    }
    final_state = None
    try:
        # Planning Agent
        status.write("🧠 Planning Agent: Creating research plan...")
        from src.agents.planning_agent import PlanningAgent
        planning_agent = PlanningAgent(st.session_state.config)
        state = planning_agent.process(state)
        state["agent_trace"].append("PlanningAgent")
        # Data Collection Agent
        status.write("📊 Data Collection Agent: Fetching stock data (yfinance), web news (SerpApi/Tavily), and RAG docs...")
        from src.agents.data_collection_agent import DataCollectionAgent
        data_agent = DataCollectionAgent(st.session_state.config)
        state = data_agent.process(state)
        state["agent_trace"].append("DataCollectionAgent")
        # Analysis Agent
        status.write("🔍 Analysis Agent: Calculating metrics and performing analysis...")
        from src.agents.analysis_agent import AnalysisAgent
        analysis_agent = AnalysisAgent(st.session_state.config)
        state = analysis_agent.process(state)
        state["agent_trace"].append("AnalysisAgent")
        # Validation Agent
        status.write("✅ Validation Agent: Verifying results...")
        from src.agents.validation_agent import ValidationAgent
        validation_agent = ValidationAgent(st.session_state.config)
        state = validation_agent.process(state)
        state["agent_trace"].append("ValidationAgent")
        # Report Agent
        status.write("📝 Report Generation Agent: Creating final report...")
        from src.agents.report_agent import ReportAgent
        report_agent = ReportAgent(st.session_state.config)
        state = report_agent.process(state)
        state["agent_trace"].append("ReportAgent")
        final_state = state

        # Build richer metadata for the UI: top news, sources, company names
        analysis_results = final_state.get("analysis_results", {}) if final_state else {}
        plan = final_state.get("research_plan", {}) if final_state else {}
        validation_results = final_state.get("validation_results", {}) if final_state else {}
        agent_trace = final_state.get("agent_trace", [])

        # extract top news items across symbols
        top_news = []
        sources = set()
        company_names = {}
        for sym, det in (analysis_results or {}).items():
            news = det.get("news", []) if isinstance(det, dict) else []
            if news:
                for n in news[:2]:
                    title = n.get("title") or n.get("headline") or None
                    src = n.get("publisher") or n.get("source") or None
                    link = n.get("link") or n.get("url") or None
                    if title:
                        top_news.append({"symbol": sym, "title": title, "source": src, "link": link})
                    if src:
                        sources.add(src)
            # company name from stock_data if available
            try:
                info = (final_state.get("stock_data") or {}).get(sym, {}).get("info", {})
                if info:
                    company_names[sym] = info.get("longName") or info.get("shortName") or None
            except Exception:
                pass

        # Ensure we provide a structured `report_data` for the frontend to enable downloads.
        report_payload = None
        if final_state and final_state.get("final_report_data"):
            # final_report_data is structured dict; prefer that for machine-readable downloads
            report_payload = final_state.get("final_report_data")
        else:
            # fallback: include the markdown/plain final report string
            report_payload = {"report_markdown": final_state.get("final_report") if final_state else "Analysis completed"}

        return {
            "content": (final_state.get("final_report") if final_state else "Analysis completed"),
            "metadata": {
                "mode": "deep_research",
                "analysis_results": analysis_results,
                "plan": plan,
                "validation_results": validation_results,
                "top_news": top_news,
                "sources": sorted(list(sources)),
                "company_names": company_names,
                "report_data": report_payload,
                "agent_trace": agent_trace
            }
        }
    except Exception as e:
        st.session_state.logger.error(f"Error in deep research mode: {str(e)}")
        return {
            "content": f"Error during analysis: {str(e)}",
            "metadata": {"mode": "deep_research", "error": True}
        }
