import logging
import os
import dotenv

dotenv.load_dotenv()

log_file_path = os.environ.get('LOG_FILE_PATH')

logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(log_file_path, mode='a')

file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

logger.addHandler(file_handler)