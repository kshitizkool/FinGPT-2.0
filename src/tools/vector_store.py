import numpy as np

class VectorStore:
	"""Simple in-memory vector store for similarity search"""
	def __init__(self, config):
		self.vectors = []
		self.documents = []

	def add(self, embedding, document):
		self.vectors.append(np.array(embedding))
		self.documents.append(document)

	def similarity_search(self, query_embedding, top_k=5):
		query_vec = np.array(query_embedding)
		scores = [np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec)) for vec in self.vectors]
		top_indices = np.argsort(scores)[-top_k:][::-1]
		return [self.documents[i] for i in top_indices]
