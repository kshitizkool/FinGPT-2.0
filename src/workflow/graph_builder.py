import networkx as nx
import importlib
import re
from typing import Dict, Any

class WorkflowGraphBuilder:
	"""Builds workflow graph for agentic pipeline"""
	def __init__(self):
		self.graph = nx.DiGraph()

	def add_agent(self, agent_name):
		self.graph.add_node(agent_name)

	def add_edge(self, from_agent, to_agent):
		self.graph.add_edge(from_agent, to_agent)

	def get_graph(self):
		return self.graph

def create_stock_analysis_graph(config=None):
	"""Creates a default agent workflow graph for stock analysis

	Returns a WorkflowGraph wrapper that exposes `invoke(state)` so higher-level
	code can run the workflow. The optional `config` is passed to each agent
	on construction (agent __init__(config, agent_name)).
	"""
	builder = WorkflowGraphBuilder()
	# Add agents in logical order
	builder.add_agent("RouterAgent")
	builder.add_agent("PlanningAgent")
	builder.add_agent("DataCollectionAgent")
	builder.add_agent("AnalysisAgent")
	builder.add_agent("ValidationAgent")
	builder.add_agent("ReportAgent")
	# Add edges to represent workflow
	builder.add_edge("RouterAgent", "PlanningAgent")
	builder.add_edge("PlanningAgent", "DataCollectionAgent")
	builder.add_edge("DataCollectionAgent", "AnalysisAgent")
	builder.add_edge("AnalysisAgent", "ValidationAgent")
	builder.add_edge("ValidationAgent", "ReportAgent")

	class WorkflowGraph:
		"""Thin wrapper around a networkx DiGraph that provides invoke(state).

		Behavior:
		- Imports agent classes dynamically from `src.agents.<module>` where
		  `<module>` is the snake_case form of the agent class name (e.g.
		  RouterAgent -> router_agent).
		- Instantiates each agent with (config, agent_name) and calls
		  `process(state)`; if the agent returns a dict, it replaces the
		  current state.
		- Runs agents in topological order; if topological sort fails,
		  falls back to insertion order of nodes.
		- Non-fatal import/process errors are printed and the workflow continues.
		"""

		def __init__(self, nx_graph: nx.DiGraph, config: Dict[str, Any] = None):
			self.graph = nx_graph
			self.config = config or {}

		def _agent_module_name(self, agent_name: str) -> str:
			# Convert CamelCase -> snake_case (RouterAgent -> router_agent)
			s = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', agent_name)
			s = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s).lower()
			return s

		def invoke(self, state: Dict[str, Any]):
			try:
				order = list(nx.topological_sort(self.graph))
			except Exception:
				order = list(self.graph.nodes())

			current_state = state
			for node in order:
				module_name = self._agent_module_name(node)
				full_module = f"src.agents.{module_name}"
				try:
					mod = importlib.import_module(full_module)
					AgentClass = getattr(mod, node)
				except Exception as e:
					print(f"Warning: could not import agent {node} from {full_module}: {e}")
					continue

				# Try to instantiate with a single `config` arg (most concrete agents expect this)
				try:
					agent = AgentClass(self.config)
				except TypeError:
					# Fallback: some agents may expect (config, agent_name)
					try:
						agent = AgentClass(self.config, node)
					except Exception as e:
						print(f"Warning: could not construct agent {node}: {e}")
						continue
				except Exception as e:
					print(f"Error constructing agent {node}: {e}")
					continue

				# At this point the agent was instantiated successfully. Call its process() method
				if hasattr(agent, 'process') and callable(agent.process):
					try:
						result = agent.process(current_state)
						if isinstance(result, dict):
							current_state = result
					except Exception as e:
						print(f"Error running agent {node}: {e}")
						# continue to next agent despite the error
				else:
					print(f"Warning: agent {node} has no callable process() method")

			return current_state

	return WorkflowGraph(builder.get_graph(), config)
