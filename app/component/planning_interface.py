import streamlit as st

def render_planning_interface():
    """Render planning interface for clarifying questions"""
    if st.session_state.current_plan:
        st.subheader("📋 Research Plan")
        st.json(st.session_state.current_plan)
        if "clarifying_questions" in st.session_state.current_plan:
            st.subheader("❓ Clarifying Questions")
            for i, question in enumerate(st.session_state.current_plan["clarifying_questions"]):
                response = st.text_input(f"Q{i+1}: {question}", key=f"clarify_{i}")
                if response:
                    st.session_state.current_plan["answers"] = st.session_state.current_plan.get("answers", {})
                    st.session_state.current_plan["answers"][f"q{i+1}"] = response
