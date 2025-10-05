import streamlit as st
import logging
import sys
import pandas as pd
from orchestrator import orchestrate
import asyncio


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ui")

st.set_page_config(page_title="Multi-Agent Orchestrator", page_icon="🤖")
st.title("🤖 Multi-Agent Orchestrator Demo")
st.caption("Database + Search Agents with Smart Orchestration")

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Nhập câu hỏi (database, search, hoặc cả hai)..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Đang xử lý với Multi-Agent Orchestrator..."):
            result = asyncio.run(orchestrate(
                question=prompt,
                chat_history=st.session_state["chat_history"]
            ))
            
            answer = result.get("final_answer", "❌ No answer")
            relevance = result.get("relevance", "unknown")
            
            # Cập nhật chat_history từ orchestrator result
            if "chat_history" in result:
                st.session_state["chat_history"] = result["chat_history"]

            st.markdown(answer)
            st.session_state["messages"].append(
                {"role": "assistant", "content": answer}
            )
