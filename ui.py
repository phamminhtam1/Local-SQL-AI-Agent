import streamlit as st
import logging
import sys
import pandas as pd
from app import build_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ui")
app = build_app()

st.set_page_config(page_title="LangGraph SQL Agent", page_icon="🤖")
st.title("🗄️ LangGraph SQL Agent Demo")

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Nhập câu hỏi về database..."):
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Đang xử lý..."):
            # Truyền chat_history vào agent state
            result = app.invoke({
                "question": prompt,
                "chat_history": st.session_state["chat_history"]
            })
            answer = result.get("final_answer", "❌ No answer")
            
            # Cập nhật chat_history từ agent result
            if "chat_history" in result:
                st.session_state["chat_history"] = result["chat_history"]
            
            # tool_results = result.get("tool_results")
            # if isinstance(tool_results, list):
            #     for r in tool_results:
            #         if isinstance(r, list):
            #             try:
            #                 df = pd.DataFrame(r)
            #                 if not df.empty:
            #                     st.dataframe(df)
            #             except Exception as e:
            #                 logger.error(f"Error converting result to DataFrame: {e}")

            st.markdown(answer)
            st.session_state["messages"].append(
                {"role": "assistant", "content": answer}
            )
