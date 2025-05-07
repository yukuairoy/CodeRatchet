"""
Logging configuration for the coderatchet package.
"""

import sys

from loguru import logger

# Remove default handler
logger.remove()

# Add custom handler with formatting
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# Export the configured logger
__all__ = ["logger"]
