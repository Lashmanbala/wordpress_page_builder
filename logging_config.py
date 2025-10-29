# import logging
# import os
# import dotenv

# dotenv.load_dotenv()

# log_file_path = os.environ.get('LOG_FILE_PATH')

# logger = logging.getLogger(__name__)

# logger.setLevel(logging.INFO)

# file_handler = logging.FileHandler(log_file_path, mode='a')

# file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

# logger.addHandler(file_handler)



import logging
import os
import dotenv
from logging.handlers import TimedRotatingFileHandler

# Load environment variables
dotenv.load_dotenv()

log_file_path = os.environ.get('LOG_FILE_PATH', 'app.log')

log_dir = os.path.dirname(log_file_path)
if log_dir:
    os.makedirs(log_dir, exist_ok=True)


# Configure logger
logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO)

file_handler = TimedRotatingFileHandler(
    filename=log_file_path,
    when='midnight',       # rotate every midnight
    interval=1,
    encoding='utf-8',
    utc=False              # set True if your server uses UTC
)

file_handler.suffix = "%Y-%m-%d"

file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

# Add handler if not already added
if not logger.handlers:
    logger.addHandler(file_handler)

logger.info("✅ Logging initialized successfully.")
