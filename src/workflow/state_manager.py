class StateManager:
	"""Manages state transitions between agents"""
	def __init__(self):
		self.state = {}

	def update(self, key, value):
		self.state[key] = value

	def get(self, key, default=None):
		return self.state.get(key, default)

	def get_state(self):
		return self.state
