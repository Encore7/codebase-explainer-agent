# app/services/agent.py

from typing import Annotated, Any, Dict, List, TypedDict

import chromadb
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import OpenAI

from app.core.config import settings
from app.core.telemetry import get_logger
from app.utils.trace import _trace_attrs

logger = get_logger(__name__)


class AgentState(TypedDict, total=False):
    """State schema for the agent.
    This defines the structure of the state that will be passed between tools.
    Attributes:
        repo_id: Unique identifier for the repository.
        question: The question or query to answer.
        chunks: List of code chunks retrieved from ChromaDB.
        summaries: List of summaries generated from the code chunks.
        stream: Stream for the final answer composition.
    """

    repo_id: str
    question: str
    chunks: List[Dict[str, Any]]
    summaries: List[str]
    stream: Any


_graph = StateGraph(state_schema=AgentState)


@tool
async def retrieve(state: Annotated[AgentState, Any]) -> Annotated[AgentState, Any]:
    """Retrieve code chunks from ChromaDB based on the question.
    Args:
        state: The current state of the agent, containing repo_id and question.
    Returns:
        state: Updated state with retrieved chunks.
    Raises:
        ValueError: If the state does not contain repo_id or question.
    """
    repo_id = state["repo_id"]
    question = state["question"]
    client = chromadb.Client()
    collection = client.get_collection(name=repo_id)
    results = collection.query(
        query_texts=[question],
        n_results=5,
        include=["documents", "metadatas"],
    )
    docs, metas = results["documents"][0], results["metadatas"][0]
    state["chunks"] = [{"text": d, **m} for d, m in zip(docs, metas)]
    logger.debug(
        "Chunks retrieved from vector DB",
        extra={"repo_id": repo_id, "count": len(docs), **_trace_attrs()},
    )
    return state


@traceable(run_type="tool", name="summarise")
@tool
async def summarise(state: Annotated[AgentState, Any]) -> Annotated[AgentState, Any]:
    """Summarise each code chunk using GPT-4o.
    Args:
        state: The current state of the agent, containing chunks.
    Returns:
        state: Updated state with summaries of each chunk.
    Raises:
        ValueError: If the state does not contain chunks.
    """
    raw_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    embedder = wrap_openai(raw_client)
    summaries: List[str] = []
    for chunk in state.get("chunks", []):
        prompt = (
            f"Here is a code diff:\n{chunk['text']}\n\n"
            "Explain in plain English what changed."
        )
        resp = await embedder.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        summaries.append(resp.choices[0].message.content)
    state["summaries"] = summaries
    logger.debug(
        "Summarised all chunks",
        extra={"count": len(summaries), **_trace_attrs()},
    )
    return state


@traceable(run_type="tool", name="compose")
@tool
async def compose(state: Annotated[AgentState, Any]) -> Annotated[AgentState, Any]:
    """Compose the final answer from summaries.
    Args:
        state: The current state of the agent, containing summaries and question.
    Returns:
        state: Updated state with a stream for the final answer.
    Raises:
        ValueError: If the state does not contain summaries or question.
    """
    raw_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    embedder = wrap_openai(raw_client)
    bullets = "\n".join(f"- {s}" for s in state.get("summaries", []))
    prompt = (
        f"Question: {state['question']}\n\n"
        f"Summaries:\n{bullets}\n\n"
        "Please provide a concise final answer, citing commits."
    )
    resp = await embedder.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        stream=True,
    )
    state["stream"] = resp.choices[0].delta_stream()
    logger.info("Answer composition stream ready", extra=_trace_attrs())
    return state


_graph.add_node("retrieve", retrieve)
_graph.add_node("summarise", summarise)
_graph.add_node("compose", compose)

_graph.set_entry_point("retrieve")
_graph.add_edge("retrieve", "summarise")
_graph.add_edge("summarise", "compose")
_graph.add_edge("compose", END)

_agent = _graph.compile()


def get_agent_for_repo(repo_id: str):
    """Create a new agent instance for the given repository ID.
    Args:
        repo_id: The unique identifier for the repository.
    Returns:
        An instance of the agent configured for the specified repository.
    Raises:
        ValueError: If the repo_id is not provided.
    """
    agent = _agent.reset()
    agent.initial_state = {"repo_id": repo_id}
    logger.debug("Agent instance created", extra={"repo_id": repo_id, **_trace_attrs()})
    return agent
