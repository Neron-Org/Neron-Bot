# Telegram Memory Bot

A Telegram bot that stores text and voice messages with embeddings for semantic search and retrieval. Uses Voyage AI for embeddings, OpenAI Whisper for transcription, and PostgreSQL with pgvector for storage.

## Features

- **Text Message Storage**: Automatically creates embeddings for text messages and stores them
- **Voice Message Transcription**: Transcribes voice messages using OpenAI Whisper, then creates and stores embeddings
- **Vector Database**: Uses PostgreSQL with pgvector extension for efficient similarity search
- **Connection Pooling**: Optimized database connections for better performance
- **Single-User Bot**: Designed for personal use

## Architecture

```
bot.py      - Main bot logic and message handlers
db.py       - Database operations (insert, query, schema management)
config.py   - Configuration and environment variable loading
```

## Prerequisites

1. **Python 3.8+**
2. **PostgreSQL 12+** with **pgvector extension**
3. **API Keys**:
   - Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
   - Voyage AI API Key (from [voyageai.com](https://www.voyageai.com/))
   - OpenAI API Key (from [platform.openai.com](https://platform.openai.com/))

## Installation

### 1. Install PostgreSQL and pgvector

**Ubuntu/Debian:**
```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Install pgvector
sudo apt install postgresql-15-pgvector
```

**macOS (using Homebrew):**
```bash
brew install postgresql@15
brew install pgvector
```

**Or compile pgvector from source:**
```bash
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### 2. Setup PostgreSQL Database

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE telegram_bot;
CREATE USER your_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE telegram_bot TO your_user;

# Exit psql
\q
```

### 3. Clone and Setup Project

```bash
# Clone or navigate to project directory
cd /path/to/Neron-Bot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual credentials
nano .env  # or use your preferred editor
```

Fill in the following values in `.env`:
- `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather
- `VOYAGE_API_KEY`: Your Voyage AI API key
- `OPENAI_API_KEY`: Your OpenAI API key
- `DB_PASSWORD`: Your PostgreSQL password
- Other DB settings as needed

### 5. Test Database Connection

```bash
# Test database setup
python db.py
```

You should see:
```
✓ Database setup successful!
```

### 6. Test Configuration

```bash
# Test configuration
python config.py
```

You should see:
```
✓ All required configuration variables are set
```

## Usage

### Start the Bot

```bash
python bot.py
```

You should see:
```
INFO - Starting bot...
INFO - Bot handlers registered
```

### Interact with the Bot

1. Open Telegram and find your bot
2. Send `/start` to see the welcome message
3. Send any text message - the bot will reply with "✅ Logged"
4. Send a voice message - the bot will transcribe it and reply with "✅ Logged"
5. Use `/count` to see how many messages are stored

## Bot Commands

- `/start` - Show welcome message and available commands
- `/count` - Display total number of stored messages

## Database Schema

```sql
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    text TEXT NOT NULL,
    embedding vector(1024) NOT NULL
);
```

## Project Structure

```
Neron-Bot/
├── bot.py              # Main bot application
├── db.py               # Database operations
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
├── .env               # Your actual environment variables (not in git)
└── README.md          # This file
```

## How It Works

### Text Messages
1. User sends a text message
2. Bot receives the message
3. Creates embedding using Voyage AI (`voyage-3-large` model)
4. Stores timestamp, text, and embedding in PostgreSQL
5. Replies "✅ Logged"

### Voice Messages
1. User sends a voice message
2. Bot downloads the audio file
3. Transcribes audio using OpenAI Whisper
4. Creates embedding of the transcribed text using Voyage AI
5. Stores timestamp, transcribed text, and embedding in PostgreSQL
6. Deletes temporary audio file
7. Replies "✅ Logged"

## Customization

### Modify Database Operations

All database code is in `db.py`. You can easily extend it with new functions:

```python
# Example: Add a function to search messages
def search_messages(query_text: str, limit: int = 5):
    query_embedding = get_embedding(query_text)
    return query_similar_messages(query_embedding, limit)
```

### Change Embedding Model

Edit `config.py`:
```python
VOYAGE_MODEL = 'voyage-3-large'  # or 'voyage-3', 'voyage-2', etc.
EMBEDDING_DIMENSION = 1024       # Update based on model
```

Note: If you change the dimension, you'll need to recreate the database table.

## Troubleshooting

### pgvector extension not found
```bash
# Make sure pgvector is installed
sudo apt install postgresql-15-pgvector

# Or compile from source (see Installation section)
```

### Database connection errors
- Check that PostgreSQL is running: `sudo systemctl status postgresql`
- Verify database credentials in `.env`
- Test connection: `psql -U your_user -d telegram_bot`

### API errors
- Verify API keys in `.env` are correct
- Check API rate limits and quotas
- Ensure you have credits/access for OpenAI and Voyage AI

### Bot not responding
- Check bot token is correct
- Ensure bot is started: `python bot.py`
- Check logs for error messages

## Security Notes

- Never commit `.env` file to version control
- Keep API keys secure
- Consider setting up firewall rules for PostgreSQL
- Use strong database passwords
- This is a single-user bot - do not expose it publicly without proper authentication

## Performance Tips

- Adjust connection pool size in `.env` based on your needs
- The vector index uses IVFFlat - consider adjusting `lists` parameter for larger datasets
- Monitor database size and consider adding cleanup jobs for old messages

## License

This project is provided as-is for personal use.

## Support

For issues related to:
- **Telegram Bot API**: https://core.telegram.org/bots/api
- **Voyage AI**: https://docs.voyageai.com/
- **OpenAI Whisper**: https://platform.openai.com/docs/guides/speech-to-text
- **pgvector**: https://github.com/pgvector/pgvector
