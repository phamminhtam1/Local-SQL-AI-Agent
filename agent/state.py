from typing import TypedDict, Optional, Any

class AgentState(TypedDict):
    question: str
    relevancy: Optional[str]   # "relevant" | "not_relevant"
    tools: Optional[list[str]]
    tool_results: Optional[Any]
    answer: Optional[str]