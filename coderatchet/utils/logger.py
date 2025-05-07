"""
Logging configuration for the coderatchet package.
"""

import logging
import sys

# Configure the logger
logger = logging.getLogger("coderatchet")
logger.setLevel(logging.INFO)

# Create console handler with formatting
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(handler)
