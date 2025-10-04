import logging
import os

def setup_logging(log_file=None, level=logging.INFO):
	# Ensure logs directory exists
	logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
	os.makedirs(logs_dir, exist_ok=True)
	
	# Default log file path
	if log_file is None:
		log_file = os.path.join(logs_dir, 'app.log')
	
	logging.basicConfig(
		filename=log_file,
		level=level,
		format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
	)

	# Return a configured logger instance for callers
	logger = logging.getLogger('stock_analysis')
	logger.setLevel(level)
	# If no handlers are attached (e.g., basicConfig used), add a StreamHandler for console output
	if not logger.handlers:
		ch = logging.StreamHandler()
		ch.setLevel(level)
		formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
		ch.setFormatter(formatter)
		logger.addHandler(ch)

	return logger
