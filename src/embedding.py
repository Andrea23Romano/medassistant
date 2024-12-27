from typing import List, Optional
import os
from openai import OpenAI
import logging
import tiktoken


class EmbeddingGenerator:
    """
    Embedding generator with error handling and retry mechanism
    """

    def __init__(
        self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"
    ):
        """
        Initialize the embedding generator

        :param api_key: OpenAI API key (optional)
        :param model: Embedding model to use
        """
        self.logger = logging.getLogger(__name__)

        # Use API key from parameter or environment variable
        openai_key = api_key or os.getenv("OPENAI_API_KEY")

        if not openai_key:
            self.logger.critical("No OpenAI API key available")
            raise ValueError("Cannot initialize EmbeddingGenerator: Missing API key")

        self.client = OpenAI(api_key=openai_key)
        self.model = model

    def create(self, text: str) -> Optional[List[float]]:
        """
        Generate an embedding for the provided text

        :param text: Text to convert to embedding
        :return: List of embeddings or None in case of error
        """
        if not text or not text.strip():
            self.logger.warning("Attempt to generate embedding for empty text")
            return None

        # Initialize the tokenizer
        tokenizer = tiktoken.get_encoding("cl100k_base")
        max_tokens = 8191  # Replace with the actual max token length for your model

        # Tokenize and truncate the input text
        tokens = tokenizer.encode(text)
        if len(tokens) > max_tokens:
            self.logger.warning(
                f"Input text exceeds max token length of {max_tokens}. Truncating."
            )
            tokens = tokens[:max_tokens]

        truncated_text = tokenizer.decode(tokens)

        try:
            response = self.client.embeddings.create(
                input=truncated_text, model=self.model
            )
            embedding = response.data[0].embedding

            self.logger.info(
                f"Embedding generated successfully. Size: {len(embedding)}"
            )
            return embedding
        except Exception as e:
            self.logger.error(f"Error generating embedding: {e}")
            return None
