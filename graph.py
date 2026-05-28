from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.contact_finder import contact_finder_agent
from agents.copywriter import copywriter_agent
from agents.fit_analyzer import fit_analyzer_agent
from agents.hook_finder import hook_finder_agent
from agents.qualifier import qualifier_agent
from agents.recommender import recommender_agent
from agents.researcher import researcher_agent
from models import SwarmState, ensure_complete_state


def should_proceed(state: SwarmState) -> str:
    state = ensure_complete_state(state)
    if state["qualified"]:
        return "contact_finder"
    return "recommender"


async def finalize_state(state: SwarmState) -> SwarmState:
    return ensure_complete_state(state)


def build_graph():
    graph = StateGraph(SwarmState)

    graph.add_node("researcher", researcher_agent)
    graph.add_node("fit_analyzer", fit_analyzer_agent)
    graph.add_node("qualifier", qualifier_agent)
    graph.add_node("contact_finder", contact_finder_agent)
    graph.add_node("recommender", recommender_agent)
    graph.add_node("hook_finder", hook_finder_agent)
    graph.add_node("copywriter", copywriter_agent)
    graph.add_node("finalize", finalize_state)

    graph.set_entry_point("researcher")
    graph.add_edge("researcher", "fit_analyzer")
    graph.add_edge("fit_analyzer", "qualifier")
    graph.add_conditional_edges(
        "qualifier",
        should_proceed,
        {
            "contact_finder": "contact_finder",
            "recommender": "recommender",
        },
    )
    graph.add_edge("contact_finder", "hook_finder")
    graph.add_edge("recommender", "finalize")
    graph.add_edge("hook_finder", "copywriter")
    graph.add_edge("copywriter", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


swarm_graph = build_graph()

