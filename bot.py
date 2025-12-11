"""
Main Telegram bot module.
Handles text and voice messages, creates embeddings, and stores them in the database.
"""

import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
import voyageai
from openai import OpenAI

import config
import db

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize API clients
voyage_client = voyageai.Client(api_key=config.VOYAGE_API_KEY)
openai_client = OpenAI(api_key=config.OPENAI_API_KEY)


def is_user_allowed(user_id: int) -> bool:
    """Check if user is allowed to use the bot."""
    if not config.ALLOWED_USERS:
        return True
    return user_id in config.ALLOWED_USERS


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /start command.
    Sends a welcome message to the user.
    """
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("hey, its not yours, go fuck yourself")
        return

    welcome_message = (
        "Welcome! I'm your personal memory bot.\n\n"
        "Send me text or voice messages, and I'll store them with embeddings for future retrieval.\n\n"
        "Commands:\n"
        "/start - Show this welcome message\n"
        "/count - Show total number of stored messages\n"
        "/search <query> - Search your stored messages"
    )
    await update.message.reply_text(welcome_message)


async def count_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /count command.
    Shows the total number of messages stored in the database.
    """
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("hey, its not yours, go fuck yourself")
        return

    try:
        count = db.get_message_count()
        await update.message.reply_text(f"Total messages stored: {count}")
    except Exception as e:
        logger.error(f"Error getting message count: {e}")
        await update.message.reply_text("Sorry, an error occurred while fetching the count.")


def trim_text(text: str, max_length: int = 150) -> tuple[str, bool]:
    """
    Trim text to max_length characters.

    Args:
        text: The text to trim
        max_length: Maximum length (default 150 for iPhone 15 Pro Max readability)

    Returns:
        Tuple of (trimmed_text, was_trimmed)
    """
    if len(text) <= max_length:
        return text, False

    # Trim and add ellipsis
    trimmed = text[:max_length].rsplit(' ', 1)[0] + '...'
    return trimmed, True


def format_search_results(results: list, offset: int = 0, batch_size: int = 3) -> tuple[str, list, bool]:
    """
    Format search results for display.

    Args:
        results: List of (id, text, timestamp, similarity) tuples
        offset: Starting offset for this batch
        batch_size: Number of results to include in this batch

    Returns:
        Tuple of (formatted_message, buttons_data, has_more)
        buttons_data is a list of (result_index, text, was_trimmed) tuples
    """
    batch = results[offset:offset + batch_size]
    has_more = len(results) > offset + batch_size

    lines = []
    buttons_data = []

    for i, (msg_id, text, timestamp, similarity) in enumerate(batch):
        result_index = offset + i
        trimmed_text, was_trimmed = trim_text(text)

        # Format timestamp as "YYYY-MM-DD HH:MM"
        time_str = timestamp.strftime("%Y-%m-%d %H:%M")

        # Add to message
        lines.append(f"{trimmed_text} ({time_str})")

        # Store button data
        buttons_data.append((result_index, text, timestamp, was_trimmed))

        # Log similarity score
        logger.info(f"Result {result_index}: similarity={similarity:.4f}")

    message = "\n\n".join(lines)
    return message, buttons_data, has_more


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /search command.
    Performs semantic search over stored messages.

    Usage: /search <query text>
    """
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("hey, its not yours, go fuck yourself")
        return

    try:
        # Extract query text
        if not context.args:
            await update.message.reply_text(
                "Please provide a search query.\n"
                "Usage: /search <your query>"
            )
            return

        query_text = ' '.join(context.args)
        logger.info(f"Search query: {query_text}")

        # Get embedding for query (use input_type="query" for search)
        query_embedding = get_embedding(query_text, input_type="query")

        # Perform similarity search (get more results for pagination)
        results = db.query_similar_messages(query_embedding, limit=12)

        if not results:
            await update.message.reply_text("No results found.")
            return

        logger.info(f"Found {len(results)} results")

        # Store results in user context for pagination
        context.user_data['search_results'] = results
        context.user_data['search_offset'] = 0

        # Format and send first batch
        message, buttons_data, has_more = format_search_results(results, offset=0)

        # Create inline keyboard
        keyboard = []
        for result_index, text, timestamp, was_trimmed in buttons_data:
            if was_trimmed:
                keyboard.append([
                    InlineKeyboardButton(
                        f"📄 Full text {result_index + 1}",
                        callback_data=f"full:{result_index}"
                    )
                ])

        if has_more:
            keyboard.append([
                InlineKeyboardButton("Show more", callback_data="more:3")
            ])

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await update.message.reply_text(message, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in search command: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, an error occurred while searching. Please try again."
        )


async def handle_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for inline button callbacks from search results.
    """
    query = update.callback_query
    await query.answer()

    if not is_user_allowed(update.effective_user.id):
        await query.message.reply_text("hey, its not yours, go fuck yourself")
        return

    try:
        callback_data = query.data
        action, value = callback_data.split(':', 1)

        if action == "full":
            # Show full text
            result_index = int(value)
            results = context.user_data.get('search_results', [])

            if result_index < len(results):
                msg_id, text, timestamp, similarity = results[result_index]

                # Format: TIMESTAMP\n{full text}
                time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                full_message = f"{time_str}\n{text}"

                await query.message.reply_text(full_message)
                logger.info(f"Showed full text for result {result_index}")
            else:
                await query.message.reply_text("Result not found.")

        elif action == "more":
            # Show more results
            offset = int(value)
            results = context.user_data.get('search_results', [])

            if offset < len(results):
                # Format next batch
                message, buttons_data, has_more = format_search_results(results, offset=offset)

                # Create inline keyboard
                keyboard = []
                for result_index, text, timestamp, was_trimmed in buttons_data:
                    if was_trimmed:
                        keyboard.append([
                            InlineKeyboardButton(
                                f"📄 Full text {result_index + 1}",
                                callback_data=f"full:{result_index}"
                            )
                        ])

                if has_more:
                    keyboard.append([
                        InlineKeyboardButton("Show more", callback_data=f"more:{offset + 3}")
                    ])

                reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

                # Send as new message
                await query.message.reply_text(message, reply_markup=reply_markup)
                logger.info(f"Showed more results starting from offset {offset}")
            else:
                await query.message.reply_text("No more results.")

    except Exception as e:
        logger.error(f"Error handling search callback: {e}", exc_info=True)
        await query.message.reply_text("Sorry, an error occurred.")


def get_embedding(text: str, input_type: str = "document") -> list:
    """
    Get embedding for text using Voyage AI.

    Args:
        text: The text to embed
        input_type: Either "document" (for storing) or "query" (for searching)

    Returns:
        Embedding vector as a list of floats

    Raises:
        Exception: If the API call fails
    """
    try:
        result = voyage_client.embed(
            texts=[text],
            model=config.VOYAGE_MODEL,
            input_type=input_type
        )
        return result.embeddings[0]
    except Exception as e:
        logger.error(f"Error getting embedding from Voyage AI: {e}")
        raise


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for text messages.
    Gets embedding and stores the message in the database.
    """
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("hey, its not yours, go fuck yourself")
        return

    try:
        # Get the message text
        text = update.message.text
        timestamp = update.message.date

        logger.info(f"Processing text message: {text[:50]}...")

        # Get embedding from Voyage AI
        embedding = get_embedding(text)

        # Store in database
        message_id = db.insert_message(
            text=text,
            embedding=embedding,
            timestamp=timestamp
        )

        logger.info(f"Text message stored with ID: {message_id}")

        # Reply to user
        await update.message.reply_text("✅ Logged")

    except Exception as e:
        logger.error(f"Error handling text message: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, an error occurred while processing your message. Please try again."
        )


async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for voice messages.
    Transcribes the audio, gets embedding, and stores in the database.
    """
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("hey, its not yours, go fuck yourself")
        return

    try:
        # Get voice message info
        voice = update.message.voice
        timestamp = update.message.date

        logger.info(f"Processing voice message (duration: {voice.duration}s)...")

        # Download the voice file
        voice_file = await context.bot.get_file(voice.file_id)
        voice_path = f"voice_{voice.file_id}.ogg"

        await voice_file.download_to_drive(voice_path)

        try:
            # Transcribe using OpenAI Whisper
            with open(voice_path, 'rb') as audio_file:
                transcript = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )

            transcribed_text = transcript.text
            logger.info(f"Transcribed text: {transcribed_text[:50]}...")

            # Get embedding from Voyage AI
            embedding = get_embedding(transcribed_text)

            # Store in database
            message_id = db.insert_message(
                text=transcribed_text,
                embedding=embedding,
                timestamp=timestamp
            )

            logger.info(f"Voice message stored with ID: {message_id}")

            # Reply to user
            await update.message.reply_text("✅ Logged")

        finally:
            # Clean up: delete the downloaded voice file
            if os.path.exists(voice_path):
                os.remove(voice_path)
                logger.info(f"Deleted temporary file: {voice_path}")

    except Exception as e:
        logger.error(f"Error handling voice message: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, an error occurred while processing your voice message. Please try again."
        )


async def handle_audio_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for audio messages (same as voice, but for audio files).
    Transcribes the audio, gets embedding, and stores in the database.
    """
    if not is_user_allowed(update.effective_user.id):
        await update.message.reply_text("hey, its not yours, go fuck yourself")
        return

    try:
        # Get audio message info
        audio = update.message.audio
        timestamp = update.message.date

        logger.info(f"Processing audio message (duration: {audio.duration}s)...")

        # Download the audio file
        audio_file_obj = await context.bot.get_file(audio.file_id)

        # Determine file extension
        file_ext = audio.mime_type.split('/')[-1] if audio.mime_type else 'mp3'
        audio_path = f"audio_{audio.file_id}.{file_ext}"

        await audio_file_obj.download_to_drive(audio_path)

        try:
            # Transcribe using OpenAI Whisper
            with open(audio_path, 'rb') as af:
                transcript = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=af
                )

            transcribed_text = transcript.text
            logger.info(f"Transcribed text: {transcribed_text[:50]}...")

            # Get embedding from Voyage AI
            embedding = get_embedding(transcribed_text)

            # Store in database
            message_id = db.insert_message(
                text=transcribed_text,
                embedding=embedding,
                timestamp=timestamp
            )

            logger.info(f"Audio message stored with ID: {message_id}")

            # Reply to user
            await update.message.reply_text("✅ Logged")

        finally:
            # Clean up: delete the downloaded audio file
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info(f"Deleted temporary file: {audio_path}")

    except Exception as e:
        logger.error(f"Error handling audio message: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, an error occurred while processing your audio message. Please try again."
        )


def main():
    """
    Main function to start the bot.
    """
    try:
        # Validate configuration
        config.validate_config()
        logger.info("Configuration validated successfully")

        # Initialize database
        db.initialize_pool()
        db.setup_database()
        logger.info("Database initialized successfully")

        # Create the Application
        application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

        # Register handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("count", count_command))
        application.add_handler(CommandHandler("search", search_command))
        application.add_handler(CallbackQueryHandler(handle_search_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
        application.add_handler(MessageHandler(filters.AUDIO, handle_audio_message))

        logger.info("Bot handlers registered")

        # Start the bot
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        # Clean up database connections
        db.close_pool()
        logger.info("Bot stopped")


if __name__ == '__main__':
    main()
