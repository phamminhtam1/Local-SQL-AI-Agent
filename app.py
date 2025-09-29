import streamlit as st
from agent import ask, db

st.set_page_config(page_title="MySQL AI Agent")
st.title("Local SQL AI Agent")

with st.expander("Database schema preview"):
    st.code(db.get_table_info(), language="sql")

query = st.text_area(
    "Đặt câu hỏi:",
    placeholder="Ví dụ: Liệt kê 10 bảng có nhiều cột nhất"
)

if st.button("Run") and query.strip():
    with st.spinner("Đang xử lý..."):
        result = ask(query)
    st.subheader("Kết quả")
    st.write(result["output"])
