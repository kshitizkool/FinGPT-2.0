import os
import fitz
from typing import List

class DocumentProcessor:
	"""Processes PDF documents for RAG system"""
	def __init__(self, chunk_size=1000, chunk_overlap=200, separators=None):
		self.chunk_size = chunk_size
		self.chunk_overlap = chunk_overlap
		self.separators = separators or ["\n\n", "\n", " ", ""]

	def extract_text(self, pdf_path: str) -> str:
		doc = fitz.open(pdf_path)
		text = ""
		for page in doc:
			text += page.get_text()
		return text

	def chunk_text(self, text: str) -> List[str]:
		chunks = []
		start = 0
		while start < len(text):
			end = min(start + self.chunk_size, len(text))
			chunk = text[start:end]
			chunks.append(chunk)
			start += self.chunk_size - self.chunk_overlap
		return chunks
