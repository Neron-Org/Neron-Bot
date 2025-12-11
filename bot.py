"""
Main Telegram bot module.
Handles text and voice messages, creates embeddings, and stores them in the database.
"""

import logging
import os
from datetime import datetime
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
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


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /start command.
    Sends a welcome message to the user.
    """
    welcome_message = (
        "Welcome! I'm your personal memory bot.\n\n"
        "Send me text or voice messages, and I'll store them with embeddings for future retrieval.\n\n"
        "Commands:\n"
        "/start - Show this welcome message\n"
        "/count - Show total number of stored messages"
    )
    await update.message.reply_text(welcome_message)


async def count_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for /count command.
    Shows the total number of messages stored in the database.
    """
    try:
        count = db.get_message_count()
        await update.message.reply_text(f"Total messages stored: {count}")
    except Exception as e:
        logger.error(f"Error getting message count: {e}")
        await update.message.reply_text("Sorry, an error occurred while fetching the count.")


def get_embedding(text: str) -> list:
    """
    Get embedding for text using Voyage AI.

    Args:
        text: The text to embed

    Returns:
        Embedding vector as a list of floats

    Raises:
        Exception: If the API call fails
    """
    try:
        result = voyage_client.embed(
            texts=[text],
            model=config.VOYAGE_MODEL,
            input_type="document"
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
