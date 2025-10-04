import sqlite3
from typing import Any, Dict

class DatabaseManager:
	"""Manages SQLite database for stock and metrics data"""
	def __init__(self, db_path):
		self.conn = sqlite3.connect(db_path)

	def insert_stock(self, symbol, date, open_, high, low, close, volume, sector):
		query = "INSERT INTO stocks (symbol, date, open, high, low, close, volume, sector) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
		self.conn.execute(query, (symbol, date, open_, high, low, close, volume, sector))
		self.conn.commit()

	def insert_metrics(self, symbol, date, cagr, sharpe_ratio, volatility):
		query = "INSERT INTO metrics (symbol, date, cagr, sharpe_ratio, volatility) VALUES (?, ?, ?, ?, ?)"
		self.conn.execute(query, (symbol, date, cagr, sharpe_ratio, volatility))
		self.conn.commit()

	def fetch_stock(self, symbol):
		query = "SELECT * FROM stocks WHERE symbol = ?"
		return self.conn.execute(query, (symbol,)).fetchall()
