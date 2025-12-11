"""
Configuration module for loading environment variables.
All API keys and configuration settings are loaded from .env file.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# API Keys
VOYAGE_API_KEY = os.getenv('VOYAGE_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Database Configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'postgres')
DB_USER = os.getenv('DB_USER', 'neron_bot')
DB_PASSWORD = os.getenv('DB_PASSWORD')

# Database Connection Pool Settings
DB_MIN_CONNECTIONS = int(os.getenv('DB_MIN_CONNECTIONS', '2'))
DB_MAX_CONNECTIONS = int(os.getenv('DB_MAX_CONNECTIONS', '10'))

# Voyage AI Configuration
VOYAGE_MODEL = 'voyage-3-large'
EMBEDDING_DIMENSION = 1024

# User Access Control
# If empty list, no restrictions. If populated, only these user_ids can use the bot.
ALLOWED_USERS = [1890816031]

# Validate required environment variables
def validate_config():
    """Validate that all required environment variables are set."""
    required_vars = {
        'TELEGRAM_BOT_TOKEN': TELEGRAM_BOT_TOKEN,
        'VOYAGE_API_KEY': VOYAGE_API_KEY,
        'OPENAI_API_KEY': OPENAI_API_KEY,
        'DB_PASSWORD': DB_PASSWORD,
    }

    missing_vars = [var for var, value in required_vars.items() if not value]

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            f"Please check your .env file."
        )

if __name__ == '__main__':
    # Quick test when running directly
    try:
        validate_config()
        print("✓ All required configuration variables are set")
    except ValueError as e:
        print(f"✗ Configuration error: {e}")
