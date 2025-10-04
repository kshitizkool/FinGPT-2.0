def validate_stock_symbol(symbol):
	return symbol.endswith(".NS") or symbol.endswith(".BO")

def validate_prices(prices):
	return isinstance(prices, list) and all(isinstance(p, (int, float)) for p in prices)
