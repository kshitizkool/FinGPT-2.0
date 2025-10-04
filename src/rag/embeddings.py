from sentence_transformers import SentenceTransformer
from typing import List

class EmbeddingModel:
	"""Generates embeddings for text chunks"""
	def __init__(self, model_name="sentence-transformers/all-mpnet-base-v2"):
		self.model = SentenceTransformer(model_name)

	def embed(self, texts: List[str]) -> List[List[float]]:
		return self.model.encode(texts, convert_to_numpy=True).tolist()
