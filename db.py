"""
Database module for PostgreSQL operations with pgvector support.
Handles all database connections, schema creation, and data operations.
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple
from psycopg2 import pool
from psycopg2.extras import execute_values
import psycopg2

import config

# Setup logging
logger = logging.getLogger(__name__)

# Global connection pool
connection_pool: Optional[pool.ThreadedConnectionPool] = None


def initialize_pool():
    """
    Initialize the PostgreSQL connection pool.
    Should be called once when the application starts.
    """
    global connection_pool

    try:
        connection_pool = pool.ThreadedConnectionPool(
            config.DB_MIN_CONNECTIONS,
            config.DB_MAX_CONNECTIONS,
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            user=config.DB_USER,
            password=config.DB_PASSWORD
        )
        logger.info(f"Database connection pool initialized with {config.DB_MIN_CONNECTIONS}-{config.DB_MAX_CONNECTIONS} connections")
    except Exception as e:
        logger.error(f"Failed to initialize database connection pool: {e}")
        raise


def get_connection():
    """Get a connection from the pool."""
    if connection_pool is None:
        raise RuntimeError("Connection pool not initialized. Call initialize_pool() first.")
    return connection_pool.getconn()


def return_connection(conn):
    """Return a connection to the pool."""
    if connection_pool is not None:
        connection_pool.putconn(conn)


def close_pool():
    """Close all connections in the pool."""
    global connection_pool
    if connection_pool is not None:
        connection_pool.closeall()
        logger.info("Database connection pool closed")


def setup_database():
    """
    Setup database schema and enable pgvector extension.
    Creates the neron table if it doesn't exist.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Enable pgvector extension
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        logger.info("pgvector extension enabled")

        # Create neron table
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS neron (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                text TEXT NOT NULL,
                embedding vector({config.EMBEDDING_DIMENSION}) NOT NULL
            );
        """)
        logger.info("Neron table created/verified")

        # Create index for vector similarity search (optional but recommended)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS neron_embedding_idx
            ON neron USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """)
        logger.info("Vector index created/verified")

        conn.commit()
        cursor.close()

    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            return_connection(conn)


def insert_message(text: str, embedding: List[float], timestamp: Optional[datetime] = None) -> int:
    """
    Insert a message with its embedding into the database.

    Args:
        text: The text content of the message
        embedding: The embedding vector (should be 1024 dimensions for voyage-3-large)
        timestamp: Optional timestamp (defaults to current time)

    Returns:
        The ID of the inserted message

    Raises:
        Exception: If the insert operation fails
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Validate embedding dimension
        if len(embedding) != config.EMBEDDING_DIMENSION:
            raise ValueError(
                f"Embedding dimension mismatch: expected {config.EMBEDDING_DIMENSION}, "
                f"got {len(embedding)}"
            )

        # Insert the message
        if timestamp is None:
            cursor.execute(
                """
                INSERT INTO neron (text, embedding)
                VALUES (%s, %s)
                RETURNING id;
                """,
                (text, embedding)
            )
        else:
            cursor.execute(
                """
                INSERT INTO neron (timestamp, text, embedding)
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (timestamp, text, embedding)
            )

        message_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()

        logger.info(f"Message inserted with ID: {message_id}")
        return message_id

    except Exception as e:
        logger.error(f"Error inserting message: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            return_connection(conn)


def query_similar_messages(
    query_embedding: List[float],
    limit: int = 10,
    similarity_threshold: Optional[float] = None
) -> List[Tuple[int, str, datetime, float]]:
    """
    Query messages similar to the given embedding using cosine similarity.

    Args:
        query_embedding: The embedding vector to search for
        limit: Maximum number of results to return
        similarity_threshold: Optional minimum similarity score (0-1, higher is more similar)

    Returns:
        List of tuples: (id, text, timestamp, similarity_score)

    Raises:
        Exception: If the query operation fails
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Validate embedding dimension
        if len(query_embedding) != config.EMBEDDING_DIMENSION:
            raise ValueError(
                f"Embedding dimension mismatch: expected {config.EMBEDDING_DIMENSION}, "
                f"got {len(query_embedding)}"
            )

        # Query using cosine similarity
        # Note: 1 - (embedding <=> %s) converts distance to similarity score
        if similarity_threshold is not None:
            cursor.execute(
                """
                SELECT id, text, timestamp, 1 - (embedding <=> %s) as similarity
                FROM neron
                WHERE 1 - (embedding <=> %s) >= %s
                ORDER BY embedding <=> %s
                LIMIT %s;
                """,
                (query_embedding, query_embedding, similarity_threshold, query_embedding, limit)
            )
        else:
            cursor.execute(
                """
                SELECT id, text, timestamp, 1 - (embedding <=> %s) as similarity
                FROM neron
                ORDER BY embedding <=> %s
                LIMIT %s;
                """,
                (query_embedding, query_embedding, limit)
            )

        results = cursor.fetchall()
        cursor.close()

        logger.info(f"Found {len(results)} similar messages")
        return results

    except Exception as e:
        logger.error(f"Error querying similar messages: {e}")
        raise
    finally:
        if conn:
            return_connection(conn)


def get_message_count() -> int:
    """
    Get the total number of messages in the database.

    Returns:
        Total count of messages
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM neron;")
        count = cursor.fetchone()[0]
        cursor.close()

        return count

    except Exception as e:
        logger.error(f"Error getting message count: {e}")
        raise
    finally:
        if conn:
            return_connection(conn)


if __name__ == '__main__':
    # Test database connection and setup
    logging.basicConfig(level=logging.INFO)

    try:
        print("Initializing database connection pool...")
        initialize_pool()

        print("Setting up database schema...")
        setup_database()

        print(f"Current message count: {get_message_count()}")
        print("✓ Database setup successful!")

    except Exception as e:
        print(f"✗ Database setup failed: {e}")
    finally:
        close_pool()
