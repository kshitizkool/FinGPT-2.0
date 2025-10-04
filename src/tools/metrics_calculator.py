import numpy as np

class MetricsCalculator:
	"""Calculates financial metrics for stock analysis"""
	def calculate_all(self, prices):
		metrics = {}
		metrics["cagr"] = self.calculate_cagr(prices)
		metrics["sharpe_ratio"] = self.calculate_sharpe_ratio(prices)
		metrics["volatility"] = self.calculate_volatility(prices)
		metrics["sortino_ratio"] = self.calculate_sortino_ratio(prices)
		metrics["max_drawdown"] = self.calculate_max_drawdown(prices)
		# Add more metrics as needed
		return metrics

	def calculate_cagr(self, prices):
		if not prices or len(prices) < 2:
			return None
		start, end = prices[0], prices[-1]
		years = len(prices) / 252  # trading days per year
		return (end / start) ** (1 / years) - 1

	def calculate_sharpe_ratio(self, prices, risk_free_rate=0.03):
		returns = np.diff(prices) / prices[:-1]
		mean_return = np.mean(returns)
		std_return = np.std(returns)
		if std_return == 0:
			return None
		return (mean_return - risk_free_rate / 252) / std_return * np.sqrt(252)

	def calculate_volatility(self, prices):
		returns = np.diff(prices) / prices[:-1]
		return np.std(returns) * np.sqrt(252)

	def calculate_sortino_ratio(self, prices, risk_free_rate=0.03):
		"""Calculate Sortino ratio using downside deviation"""
		if not prices or len(prices) < 2:
			return None
		returns = np.diff(prices) / prices[:-1]
		mean_return = np.mean(returns)
		# downside returns relative to 0 (or risk-free rate monthly adjusted)
		neg_returns = returns[returns < 0]
		if len(neg_returns) == 0:
			return None
		downside_deviation = np.sqrt(np.mean(neg_returns ** 2))
		if downside_deviation == 0:
			return None
		# annualize
		return (mean_return - risk_free_rate / 252) / downside_deviation * np.sqrt(252)

	def calculate_max_drawdown(self, prices):
		"""Calculate maximum drawdown from price series"""
		if not prices or len(prices) < 2:
			return None
		arr = np.array(prices)
		cum_max = np.maximum.accumulate(arr)
		drawdowns = (arr - cum_max) / cum_max
		max_dd = float(np.min(drawdowns)) if drawdowns.size else None
		return max_dd
