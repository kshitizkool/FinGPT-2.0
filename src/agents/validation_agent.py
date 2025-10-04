from src.agents.base_agent import BaseAgent
from typing import Dict, Any
import logging
import numpy as np

logger = logging.getLogger(__name__)

class ValidationAgent(BaseAgent):
	"""Validates data accuracy and analytical integrity"""
	def __init__(self, config: Dict):
		super().__init__(config, "validation_agent")

	def detect_outliers(self, values):
		"""Detect statistical outliers using z-score"""
		if not values or len(values) < 2:
			return []
		arr = np.array(values)
		mean = np.mean(arr)
		std = np.std(arr)
		if std == 0:
			return []
		z_scores = np.abs((arr - mean) / std)
		return np.where(z_scores > 3)[0].tolist()

	def validate_stock_data(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
		"""Cross-reference and validate stock data"""
		validation_results = {}
		for symbol, data in stock_data.items():
			prices = data.get("prices", [])
			outliers = self.detect_outliers(prices)
			validation_results[symbol] = {
				"outliers": outliers,
				"valid": len(outliers) == 0 and prices != []
			}
		return validation_results

	def process(self, state: Dict) -> Dict:
		"""Process validation phase"""
		stock_data = state.get("stock_data", {})
		if not stock_data:
			state["error"] = "No stock data available for validation"
			return state
		validation = self.validate_stock_data(stock_data)
		state["validation_results"] = validation
		self.log_action("data_validated", {"count": len(validation)})
		return state
