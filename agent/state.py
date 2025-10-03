from typing import TypedDict, Optional, Any, List, Dict

class AgentState(TypedDict):
    question: str
    relevancy: Optional[str]   # "relevant" | "not_relevant"
    
    # Chat History
    chat_history: Optional[List[Dict]]  # Lịch sử trò chuyện: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    
    # Planner LLM
    selected_tool: Optional[str]  # Tool được chọn bởi Planner
    tool_metadata: Optional[Dict]  # Metadata của tool được chọn
    
    # Executor
    tool_results: Optional[List[Any]]  # Kết quả từ các tool đã thực thi
    execution_history: Optional[List[Dict]]  # Lịch sử thực thi tools
    
    # Evaluator LLM
    is_complete: Optional[bool]  # Đánh giá kết quả có đủ chưa
    evaluation_reason: Optional[str]  # Lý do đánh giá
    
    # Final Answer Generator
    final_answer: Optional[str]  # Câu trả lời cuối cùng
    reasoning: Optional[str]  # Natural language reasoning
    
    # Loop control
    iteration_count: Optional[int]  # Số lần lặp
    max_iterations: Optional[int]  # Số lần lặp tối đa