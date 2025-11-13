"""
Configuration and logging setup for Osaka
"""

import logging
import os
from dotenv import load_dotenv

# Constants
BACKUP_DIR = ".osaka_backups"
DEFAULT_TIMEOUT = 30
MAX_TOKENS = 4096
MODEL_NAME = "claude-sonnet-4-5-20250929"

# System prompt for the AI agent
SYSTEM_PROMPT = (
    "You are a helpful coding assistant operating in a terminal environment. "
    "Output only plain text without markdown formatting, as your responses appear directly in the terminal."
    "Be concise but thorough, providing clear and practical advice with a friendly tone. "
    "Don't use any asterisk characters in your responses."
)


def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
        handlers=[logging.FileHandler("agent.log")],
    )
    
    # Suppress verbose HTTP logs
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def load_environment():
    """Load environment variables from .env file"""
    load_dotenv()


def get_api_key(cli_api_key=None):
    """
    Get API key from CLI argument or environment variable
    
    Args:
        cli_api_key: API key provided via command line
        
    Returns:
        str: The API key, or None if not found
    """
    return cli_api_key or os.environ.get("ANTHROPIC_API_KEY")