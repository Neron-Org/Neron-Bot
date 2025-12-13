# Neron Bot

A private Telegram bot that stores text, voice, and audio messages with vector embeddings for intelligent semantic search and retrieval. Built with Voyage AI for embeddings, OpenAI Whisper for transcription, and PostgreSQL with pgvector for vector similarity search.

## Features

- **Text Message Storage**: Automatically creates embeddings for text messages and stores them in the database
- **Voice & Audio Transcription**: Transcribes voice and audio messages using OpenAI Whisper API, then creates and stores embeddings
- **Semantic Search**: Search through all your stored messages using natural language queries with vector similarity
- **Smart Pagination**: Search results are displayed in batches with "Show more" buttons for easy navigation
- **Full Text Display**: Trimmed results can be expanded to show full message content with timestamps
- **Vector Database**: PostgreSQL with pgvector extension for fast similarity search using cosine distance
- **Connection Pooling**: Thread-safe connection pool with automatic retry logic for reliability
- **User Access Control**: Private bot with configurable allowed user list for security

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

# Create user with password
CREATE USER neron_bot WITH PASSWORD 'your_secure_password_here';

# Grant necessary privileges on the default postgres database
GRANT ALL PRIVILEGES ON DATABASE postgres TO neron_bot;

# Connect to postgres database to grant schema privileges
\c postgres

# Grant schema privileges
GRANT ALL ON SCHEMA public TO neron_bot;

# Exit psql
\q
```

**Note**: This bot uses the default `postgres` database. The table is called `neron` and will be created automatically when you first run the bot.

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
4. Send a voice or audio message - the bot will transcribe it and reply with "✅ Logged"
5. Use `/count` to see how many messages are stored
6. Use `/search <query>` to search through your stored messages

## Bot Commands

- `/start` - Show welcome message and available commands
- `/count` - Display total number of stored messages
- `/search <query>` - Search your messages using semantic similarity (e.g., `/search meeting notes from last week`)

## Database Schema

The bot automatically creates this table on first run:

```sql
CREATE TABLE neron (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    text TEXT NOT NULL,
    embedding vector(1024) NOT NULL
);
```

- **Table name**: `neron`
- **Database**: `postgres` (default PostgreSQL database)
- **Vector dimension**: 1024 (for voyage-3-large model)
- **Similarity metric**: Cosine distance (`<=>` operator)

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
3. Creates embedding using Voyage AI (`voyage-3-large` model, `input_type="document"`)
4. Stores timestamp, text, and 1024-dimensional embedding vector in PostgreSQL
5. Replies "✅ Logged"

### Voice & Audio Messages
1. User sends a voice or audio message
2. Bot downloads the audio file to temporary storage
3. Transcribes audio using OpenAI Whisper (`whisper-1` model)
4. Creates embedding of the transcribed text using Voyage AI
5. Stores timestamp, transcribed text, and embedding in PostgreSQL
6. Deletes temporary audio file from disk
7. Replies "✅ Logged"

### Semantic Search
1. User sends `/search <query>` command
2. Bot creates embedding for the query using Voyage AI (`input_type="query"`)
3. Performs cosine similarity search against all stored message embeddings
4. Returns up to 12 most similar results, ranked by similarity score
5. Displays results in batches of 3 with:
   - Trimmed text (max 150 chars for readability)
   - Timestamp (YYYY-MM-DD HH:MM format)
   - "Full text" button for expanded results (if trimmed)
   - "Show more" button for pagination (if more results available)
6. User can click buttons to view full messages or load additional results

## Customization

### User Access Control

By default, the bot is restricted to specific users. Edit `config.py` to configure access:

```python
# Allow only specific user IDs (get your user_id by messaging the bot)
ALLOWED_USERS = [1890816031]  # Replace with your Telegram user ID

# Or allow anyone (NOT RECOMMENDED for private data):
ALLOWED_USERS = []  # Empty list = no restrictions
```

To find your Telegram user ID, you can:
- Use [@userinfobot](https://t.me/userinfobot)
- Check bot logs when you send a message (user ID will be logged)

### Change Embedding Model

Edit `config.py`:
```python
VOYAGE_MODEL = 'voyage-3-large'  # or 'voyage-3', 'voyage-2', etc.
EMBEDDING_DIMENSION = 1024       # Update based on model (voyage-3-large = 1024)
```

**Important**: If you change the dimension, you must recreate the database table:
```sql
DROP TABLE neron;
-- Restart the bot to recreate with new dimension
```

### Adjust Search Results

Modify search behavior in `bot.py`:

```python
# Change number of results fetched (line 165)
results = db.query_similar_messages(query_embedding, limit=12)  # Change 12 to desired limit

# Change batch size for pagination (line 178)
message, buttons_data, has_more = format_search_results(results, offset=0)  # Default batch_size=3

# Change text trimming length (line 80)
def trim_text(text: str, max_length: int = 150):  # Change 150 to desired length
```

### Database Connection Pool

Adjust pool size in `.env` based on your load:
```env
DB_MIN_CONNECTIONS=2   # Minimum idle connections
DB_MAX_CONNECTIONS=10  # Maximum total connections
```

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
- Test connection: `psql -U neron_bot -d postgres`
- Ensure the `neron_bot` user has proper privileges (see Installation section)

### API errors
- Verify API keys in `.env` are correct
- Check API rate limits and quotas
- Ensure you have credits/access for OpenAI and Voyage AI

### Bot not responding
- Check bot token is correct
- Ensure bot is started: `python bot.py`
- Check logs for error messages

## Security Notes

- **Never commit `.env` file to version control** (already in `.gitignore`)
- Keep API keys secure and rotate them periodically
- Configure `ALLOWED_USERS` in `config.py` to restrict access to your Telegram user ID only
- Use strong database passwords (minimum 16 characters recommended)
- Consider setting up firewall rules for PostgreSQL if exposed to network
- The bot stores all messages in plain text - ensure your server and database are secure
- Unauthorized users receive a rejection message when trying to use the bot

## Performance Tips

- **Connection pooling**: Adjust `DB_MIN_CONNECTIONS` and `DB_MAX_CONNECTIONS` in `.env` based on expected load
- **No index for small datasets**: By default, no vector index is created for better accuracy with small datasets (< 1000 messages)
- **Add IVFFlat index for large datasets**: If you have 1000+ messages, uncomment the index creation code in `db.py` (lines 150-154) for faster searches
- **Monitor database size**: The `neron` table grows with each message. Consider adding cleanup jobs for old messages if needed
- **Batch operations**: The bot uses connection pooling with retry logic to handle temporary database issues
- **Search limits**: Default search fetches 12 results total, displaying 3 at a time. Adjust if needed for your use case

## Running as a System Service

To keep the bot running in the background, create a systemd service:

1. Create service file:
```bash
sudo nano /etc/systemd/system/neron-bot.service
```

2. Add the following content (adjust paths as needed):
```ini
[Unit]
Description=Neron Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/home/Neron-Bot
Environment="PATH=/home/Neron-Bot/venv/bin"
ExecStart=/home/Neron-Bot/venv/bin/python3 /home/Neron-Bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable neron-bot
sudo systemctl start neron-bot
```

4. Check status:
```bash
sudo systemctl status neron-bot
```

5. View logs:
```bash
sudo journalctl -u neron-bot -f
```

## Logs

The bot creates a `bot.log` file in the project directory with detailed logging information. To monitor:
```bash
tail -f /home/Neron-Bot/bot.log
```

## License

This project is provided as-is for personal use.

## Dependencies

- **python-telegram-bot** (21.0.1): Telegram Bot API wrapper
- **voyageai** (0.2.3): Voyage AI embeddings API client
- **openai** (1.54.3): OpenAI API client (Whisper transcription)
- **psycopg2-binary** (2.9.10): PostgreSQL database adapter
- **python-dotenv** (1.0.1): Environment variable management

## Support & Resources

For issues related to:
- **Telegram Bot API**: https://core.telegram.org/bots/api
- **Voyage AI Embeddings**: https://docs.voyageai.com/
- **OpenAI Whisper**: https://platform.openai.com/docs/guides/speech-to-text
- **pgvector Extension**: https://github.com/pgvector/pgvector
- **PostgreSQL**: https://www.postgresql.org/docs/

## Technical Details

- **Embedding Model**: voyage-3-large (1024 dimensions)
- **Transcription Model**: whisper-1 (OpenAI)
- **Vector Similarity**: Cosine distance (pgvector `<=>` operator)
- **Database**: PostgreSQL with pgvector extension
- **Message Types Supported**: Text, Voice (OGG), Audio (MP3, etc.)
- **Search Algorithm**: K-nearest neighbors with cosine similarity
