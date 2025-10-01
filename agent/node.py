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
    schema_info = None
    
    for t in state.get("tools", []):
        if t == "list_tables":
            results.append(list_tables_tool._run())
        elif t == "query_sql":
            if schema_info is None:
                try:
                    schema_info = list_tables_tool._run()
                except Exception as e:
                    schema_info = f"Could not retrieve schema: {str(e)}"
            
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
            if sql.startswith("```sql"):
                sql = sql.replace("```sql", "").replace("```", "").strip()
            elif sql.startswith("```"):
                sql = sql.replace("```", "").strip()
            
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

# 5. Kiểm tra response có chuẩn với câu hỏi hay không
def validate_response(state: AgentState) -> AgentState:
    question = state["question"]
    answer = state.get("answer", "")
    tool_results = state.get("tool_results", [])
    
    # Tạo prompt để LLM đánh giá response
    validation_prompt = f"""
    You are a response validator. Evaluate if the generated answer properly addresses the user's question.
    
    User Question: "{question}"
    Database Results: {tool_results}
    Generated Answer: "{answer}"
    
    Check if:
    1. The answer directly addresses the user's question
    2. The answer uses the database results appropriately
    3. The answer is complete and informative
    4. The answer doesn't contain errors or misleading information
    
    Respond with ONLY: "valid" or "invalid"
    If invalid, also provide a brief reason why.
    """
    
    validation_result = llm.invoke(validation_prompt).content.strip().lower()
    is_valid = "valid" in validation_result
    
    logger.info(f"Response validation: {validation_result}")
    logger.info(f"Validation passed: {is_valid}")
    
    return {**state, "validation_passed": is_valid}

# 6. Ép sinh SQL lại nếu response không chuẩn
def regenerate_sql(state: AgentState) -> AgentState:
    question = state["question"]
    current_attempts = state.get("sql_attempts", 0)
    max_attempts = 3
    
    if current_attempts >= max_attempts:
        logger.warning(f"Max SQL regeneration attempts reached ({max_attempts})")
        return {**state, "validation_passed": True}
    
    try:
        schema_info = list_tables_tool._run()
    except Exception as e:
        schema_info = f"Could not retrieve schema: {str(e)}"
    
    improved_prompt = f"""
    You are an expert SQL generator. The previous attempt failed validation. 
    Generate a better SQL query based on the feedback.
    
    Database Schema Information:
    {schema_info}
    
    User question: "{question}"
    Previous attempt number: {current_attempts + 1}
    
    Rules:
    - Only use SELECT statements
    - No UPDATE, DELETE, DROP, or INSERT
    - Use exact table and column names from schema
    - Be more precise and comprehensive
    - Consider all relevant tables and relationships
    - For "list all [table_name]" → SELECT * FROM [exact_table_name]
    
    Return ONLY the SQL query without explanations or markdown formatting.
    """
    
    sql = llm.invoke(improved_prompt).content.strip()
    if sql.startswith("```sql"):
        sql = sql.replace("```sql", "").replace("```", "").strip()
    elif sql.startswith("```"):
        sql = sql.replace("```", "").strip()
    
    logger.info(f"Regenerated SQL (attempt {current_attempts + 1}): {sql}")
    
    try:
        result = query_sql_tool._run(sql)
        new_tool_results = [result]
        logger.info(f"Regenerated SQL executed successfully")
        
        # Tạo answer mới với kết quả SQL mới
        context = new_tool_results
        answer_prompt = f"User asked: {question}\nDatabase results: {context}\nGive a concise answer."
        new_answer = llm.invoke(answer_prompt).content
        
        return {
            **state, 
            "tool_results": new_tool_results,
            "answer": new_answer,
            "sql_attempts": current_attempts + 1,
            "validation_passed": None
        }
    except Exception as e:
        logger.error(f"Regenerated SQL failed: {str(e)}")
        return {
            **state, 
            "sql_attempts": current_attempts + 1,
            "validation_passed": None
        }

# 5. Funny response khi không liên quan DB
def funny_response(state: AgentState) -> AgentState:
    q = state["question"]
    return {**state, "answer": f"😂 Câu hỏi '{q}' không liên quan database rồi!"}