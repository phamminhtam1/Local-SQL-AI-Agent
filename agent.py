import os
from dotenv import load_dotenv
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from tools.list_tables_tool import ListTablesTool
from tools.query_sql_tool import SafeQuerySQLTool

load_dotenv()

DB_URI = os.getenv("DB_URI", "mysql+pymysql://root@127.0.0.1:3306/be_laravel")
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not DB_URI:
    raise ValueError("DB lỗi")

try:
    db = SQLDatabase.from_uri(DB_URI, sample_rows_in_table_info=2)
    print(f"Kết nối database thành công: {DB_URI}")
except Exception as e:
    print(f"Lỗi kết nối database: {e}")
    raise

tools = [
    ListTablesTool(db),
    SafeQuerySQLTool(db),
]

llm = ChatOpenAI(
    model=MODEL,
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY"),
)

prompt = PromptTemplate.from_template("""
You are a helpful SQL analyst assistant. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Rules:
- Only generate SQL statements starting with SELECT.
- Always LIMIT rows if result can be large (e.g. LIMIT 50).
- If the user requests write/update/delete actions, politely refuse.
- Use list_tables first to understand the database schema before writing queries.

Question: {input}
Thought: I need to understand the database structure first, then answer the user's question.
{agent_scratchpad}
""")

agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True, handle_parsing_errors=True)

def ask(question: str):
    return agent_executor.invoke({"input": question})
