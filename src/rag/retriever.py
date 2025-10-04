from src.rag.embeddings import EmbeddingModel
from src.tools.vector_store import VectorStore
from typing import List, Dict

class FinancialReportRetriever:
	"""Retrieves relevant financial reports using embeddings and vector store"""
	def __init__(self, config):
		self.config = config
		self.embedding_model = EmbeddingModel()
		self.vector_store = VectorStore(config)

	def retrieve_reports(self, symbol: str, sector: str) -> List[Dict]:
		query = f"{symbol} {sector} financial report"
		query_embedding = self.embedding_model.embed([query])[0]
		results = self.vector_store.similarity_search(query_embedding)
		return results
