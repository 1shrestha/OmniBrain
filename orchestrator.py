from langgraph.graph import StateGraph, END
import re
from typing import Dict, Any, List, TypedDict, Literal

# Import agents
from retrieval import MultiModalVectorStore
from agents.search_agent import SearchAgent
from agents.sql_agent import SQLAgent
from agents.vision_agent import VisionAgent
from config import IS_MOCK

# Define AgentState structure
class AgentState(TypedDict):
    query: str
    next_node: str
    intermediate_steps: List[str]
    search_result: Dict[str, Any]
    sql_result: Dict[str, Any]
    vision_result: Dict[str, Any]
    image_path: str
    final_answer: str
    citations: List[Dict[str, Any]]

def route_next(state: AgentState) -> str:
    """Routing function for the StateGraph."""
    return state.get("next_node", "response_synthesizer")

class OmniBrainOrchestrator:
    def __init__(self, vector_store: MultiModalVectorStore, is_mock: bool = IS_MOCK):
        self.is_mock = is_mock
        self.search_agent = SearchAgent(vector_store)
        self.sql_agent = SQLAgent(is_mock=is_mock)
        self.vision_agent = VisionAgent(is_mock=is_mock)
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("supervisor", self.supervisor_node)
        workflow.add_node("search_agent", self.search_node)
        workflow.add_node("sql_agent", self.sql_node)
        workflow.add_node("vision_agent", self.vision_node)
        workflow.add_node("response_synthesizer", self.synthesizer_node)
        
        # Set entry point
        workflow.set_entry_point("supervisor")
        
        # Add conditional transitions
        workflow.add_conditional_edges(
            "supervisor",
            route_next,
            {
                "search_agent": "search_agent",
                "sql_agent": "sql_agent",
                "vision_agent": "vision_agent",
                "response_synthesizer": "response_synthesizer"
            }
        )
        
        # Add standard transitions back to supervisor
        workflow.add_edge("search_agent", "supervisor")
        workflow.add_edge("sql_agent", "supervisor")
        workflow.add_edge("vision_agent", "supervisor")
        
        # Finish path
        workflow.add_edge("response_synthesizer", END)
        
        return workflow.compile()

    def supervisor_node(self, state: AgentState) -> Dict[str, Any]:
        """Analyzes query and past actions to decide routing."""
        query = state["query"].lower()
        steps = state.get("intermediate_steps", [])
        
        # Safeguard against infinite loops
        if len(steps) >= 3:
            return {"next_node": "response_synthesizer"}
            
        if self.is_mock:
            # Rule-based routing logic for testing offline
            if ("price" in query or "stock" in query or "ticker" in query or "share" in query) and "sql_agent" not in steps:
                return {"next_node": "sql_agent"}
            if ("chart" in query or "table" in query or "image" in query or "balance" in query or "revenue" in query) and "vision_agent" not in steps:
                return {"next_node": "vision_agent"}
            if ("search" in query or "document" in query or "fact" in query or "report" in query or "news" in query) and "search_agent" not in steps:
                return {"next_node": "search_agent"}
            
            # Default fallbacks if not matched
            if "search_agent" not in steps and len(steps) == 0:
                return {"next_node": "search_agent"}
                
            return {"next_node": "response_synthesizer"}
        else:
            try:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(temperature=0)
                prompt = (
                    "You are a supervisor agent orchestrating a financial analysis. "
                    "Determine the next agent to call based on the user's query and completed steps.\n\n"
                    f"User Query: {state['query']}\n"
                    f"Steps Completed: {steps}\n\n"
                    "Select one of the following exact options: 'search_agent', 'sql_agent', 'vision_agent', 'response_synthesizer'.\n"
                    "Provide ONLY the string of your choice."
                )
                response = llm.invoke(prompt)
                choice = response.content.strip().lower()
                
                # Validation of response
                if choice in ["search_agent", "sql_agent", "vision_agent", "response_synthesizer"]:
                    return {"next_node": choice}
                return {"next_node": "response_synthesizer"}
            except Exception:
                # Force fallback to mock routing if real LLM fails
                self.is_mock = True
                return self.supervisor_node(state)

    def search_node(self, state: AgentState) -> Dict[str, Any]:
        """Node for semantic retrieval search agent."""
        res = self.search_agent.run(state["query"])
        steps = state.get("intermediate_steps", []) + ["search_agent"]
        return {
            "search_result": res,
            "intermediate_steps": steps
        }

    def sql_node(self, state: AgentState) -> Dict[str, Any]:
        """Node for Text-to-SQL stock pricing agent."""
        res = self.sql_agent.run(state["query"])
        steps = state.get("intermediate_steps", []) + ["sql_agent"]
        return {
            "sql_result": res,
            "intermediate_steps": steps
        }

    def vision_node(self, state: AgentState) -> Dict[str, Any]:
        """Node for visual balance sheet / chart agent."""
        image_path = state.get("image_path", "balance_sheet.png")
        res = self.vision_agent.run(image_path)
        steps = state.get("intermediate_steps", []) + ["vision_agent"]
        return {
            "vision_result": res,
            "intermediate_steps": steps
        }

    def synthesizer_node(self, state: AgentState) -> Dict[str, Any]:
        """Synthesizes memo output combining retrieved content and details."""
        search_res = state.get("search_result", {})
        sql_res = state.get("sql_result", {})
        vision_res = state.get("vision_result", {})
        
        memo = [
            "==================================================",
            "                INVESTMENT MEMORANDUM             ",
            "==================================================",
            f"Original Query: {state['query']}\n"
        ]
        
        citations = []
        
        if search_res and search_res.get("answer"):
            memo.append("--- Semantics & News Context ---")
            memo.append(search_res["answer"])
            citations.extend(search_res.get("citations", []))
            
        if sql_res and sql_res.get("answer"):
            memo.append("--- Quantitative Stock Data ---")
            memo.append(sql_res["answer"])
            
        if vision_res and vision_res.get("answer"):
            memo.append("--- Financial Chart Analysis ---")
            memo.append(vision_res["answer"])
            
        memo.append("==================================================")
        
        final_answer = "\n\n".join(memo)
        
        return {
            "final_answer": final_answer,
            "citations": citations
        }

    def run(self, query: str, image_path: str = None) -> Dict[str, Any]:
        initial_state = {
            "query": query,
            "next_node": "supervisor",
            "intermediate_steps": [],
            "search_result": {},
            "sql_result": {},
            "vision_result": {},
            "image_path": image_path or "",
            "final_answer": "",
            "citations": []
        }
        return self.graph.invoke(initial_state)
