import fitz  # PyMuPDF

class PDFProcessor:
	"""Processes PDF files for extracting text"""
	def extract_text(self, pdf_path):
		doc = fitz.open(pdf_path)
		text = ""
		for page in doc:
			text += page.get_text()
		return text
