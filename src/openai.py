from openai import OpenAI
from datetime import datetime
from typing import List
import os
import logging
from src.models import Message


class DailyAgent:
    def __init__(self, openai_api_key: str = None):
        """Initialize DailyAgent with OpenAI client.

        Args:
            openai_api_key (str, optional): OpenAI API key for authentication.
                                          If None, gets from environment
        """
        self.logger = logging.getLogger()
        self.client = OpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
        self.logger.debug("DailyAgent initialized with OpenAI client")

    def create(self, chat_history: List[Message], model: str = None, **kwargs) -> str:
        """Process chat history and generate response using OpenAI.

        Args:
            chat_history (List[Message]): List of Message objects
            model (str, optional): OpenAI model to use. If None, uses DEFAULT_CHAT_MODEL
                     from environment
            **kwargs: Additional parameters for OpenAI API call

        Returns:
            List[Message]: Updated chat history including the assistant's response
        """
        model = model or os.getenv("DEFAULT_CHAT_MODEL", "gpt-4")
        self.logger.info(f"Using model: {model}")

        # Filter chat history to include only valid message types
        filtered_history = [
            {"role": msg.role, "content": msg.content}
            for msg in chat_history
            if msg.role in ["system", "assistant", "user"]
        ]
        self.logger.debug(f"Filtered chat history length: {len(filtered_history)}")

        # Generate response using OpenAI
        self.logger.info("Generating response from OpenAI")
        response = self.client.chat.completions.create(
            model=model, messages=filtered_history, **kwargs
        )

        response_content = response.choices[0].message.content
        self.logger.debug("Response received from OpenAI")

        # Create new Message object for the assistant's response
        assistant_message = Message(
            role="assistant", content=response_content, timestamp=datetime.now()
        )

        # Add assistant's response to chat history
        chat_history.append(assistant_message)
        self.logger.info("Assistant response added to chat history")

        return chat_history
