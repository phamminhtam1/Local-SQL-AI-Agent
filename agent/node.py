import json
from langchain_openai import ChatOpenAI
from .state import AgentState
from .tools import list_tables_tool, query_sql_tool
import logging
logger = logging.getLogger(__name__)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 1. Kiểm tra câu hỏi có liên quan DB không
def check_relevancy(state: AgentState) -> AgentState:
    q = state["question"]
    prompt = f"""
    You are a classifier. User question: "{q}"
    If related to SQL/Database, respond 'relevant', else 'not_relevant'.
    """
    resp = llm.invoke(prompt).content.strip().lower()
    logger.info(f"Relevancy: {resp}")
    return {**state, "relevancy": "relevant" if "relevant" in resp else "not_relevant"}

# 2. Chọn tool
def select_tools(state: AgentState) -> AgentState:
    q = state["question"].lower()
    # Nếu hỏi về schema/tables thì dùng list_tables
    if any(word in q for word in ["table", "schema", "structure", "show tables"]):
        logger.info(f"Selecting list_tables")
        return {**state, "tools": ["list_tables"]}
    # Nếu hỏi về dữ liệu cụ thể thì dùng query_sql
    else:
        logger.info(f"Selecting query_sql")
        return {**state, "tools": ["query_sql"]}

# 3. Thực thi tool
def execute_tools(state: AgentState) -> AgentState:
    results = []
    # Cache schema info để tránh gọi nhiều lần
    schema_info = None
    
    for t in state.get("tools", []):
        if t == "list_tables":
            results.append(list_tables_tool._run())
        elif t == "query_sql":
            # Lấy thông tin schema để LLM tạo SQL chính xác hơn (chỉ gọi 1 lần)
            if schema_info is None:
                try:
                    schema_info = list_tables_tool._run()
                except Exception as e:
                    schema_info = f"Could not retrieve schema: {str(e)}"
            
            # Gọi LLM để sinh SQL từ question với schema info
            prompt = f"""
                You are a SQL generator. Convert the user question to a valid SQL SELECT query.
                
                Database Schema Information:
                {schema_info}
                
                Rules:
                - Only use SELECT statements
                - No UPDATE, DELETE, DROP, or INSERT
                - Use the exact table and column names from the schema above
                - For "list all [table_name]" → SELECT * FROM [exact_table_name]
                - Be precise with column names and table names from the schema
                - If schema shows table names, use those exact names
                
                User question: "{state['question']}"
                
                Return ONLY the SQL query without explanations or markdown formatting.
                """
            sql = llm.invoke(prompt).content.strip()
            # Remove any markdown formatting if present
            if sql.startswith("```sql"):
                sql = sql.replace("```sql", "").replace("```", "").strip()
            elif sql.startswith("```"):
                sql = sql.replace("```", "").strip()
            
            # Debug: print the generated SQL
            logger.info(f"Generated SQL: {sql}")
            try:
                result = query_sql_tool._run(sql)
                results.append(result)
            except Exception as e:
                results.append(f"❌ SQL Error: {str(e)}")
    return {**state, "tool_results": results}

# 4. Sinh câu trả lời
def generate_answer(state: AgentState) -> AgentState:
    context = state.get("tool_results", "")
    q = state["question"]
    prompt = f"User asked: {q}\nDatabase results: {context}\nGive a concise answer."
    answer = llm.invoke(prompt).content
    logger.info(f"Generated Answer: {answer}")
    return {**state, "answer": answer}

# 5. Funny response khi không liên quan DB
def funny_response(state: AgentState) -> AgentState:
    q = state["question"]
    return {**state, "answer": f"😂 Câu hỏi '{q}' không liên quan database rồi!"}