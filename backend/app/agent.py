from typing import TypedDict, List, Annotated
import operator

from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import BaseMessage, SystemMessage

from app.config import OLLAMA_BASE_URL, LLM_MODEL
from app.tools import search_web, read_pdf, tarot_reading


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]


base_tools = [search_web, read_pdf, tarot_reading]


def build_graph(extra_tools: list | None = None):
    all_tools = base_tools + (extra_tools or [])
    pdf_safe_tools = [read_pdf, tarot_reading] + (extra_tools or [])

    tool_node = ToolNode(all_tools)

    llm = ChatOllama(
        base_url=OLLAMA_BASE_URL,
        model=LLM_MODEL,
        temperature=0.7,
    )
    llm_with_tools = llm.bind_tools(all_tools)
    llm_pdf_safe = llm.bind_tools(pdf_safe_tools)

    def _has_pdf_context(state: AgentState) -> bool:
        for m in state["messages"]:
            if isinstance(m, SystemMessage) and "DO NOT call search_web" in m.content:
                return True
        return False

    def call_model(state: AgentState) -> dict:
        if _has_pdf_context(state):
            result = llm_pdf_safe.invoke(state["messages"])
        else:
            result = llm_with_tools.invoke(state["messages"])
        return {"messages": [result]}

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "continue"
        return "end"

    graph = StateGraph(AgentState)

    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {"continue": "tools", "end": END},
    )
    graph.add_edge("tools", "agent")

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)
