from typing import TypedDict, Optional, Any

class AgentState(TypedDict):
    question: str
    relevancy: Optional[str]   # "relevant" | "not_relevant"
    tools: Optional[list[str]]
    tool_results: Optional[Any]
    answer: Optional[str]
    validation_passed: Optional[bool]  # True if response is valid, False if needs regeneration
    sql_attempts: Optional[int]  # Track number of SQL generation attempts