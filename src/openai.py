from openai import OpenAI
from datetime import datetime
from typing import List
import os
import json
import logging
from src.models import Message, ConversationEntry


class DailyAgent:
    def __init__(self, openai_api_key: str = None, tools: list[dict] = None):
        """Initialize DailyAgent with OpenAI client.

        Args:
            openai_api_key (str, optional): OpenAI API key for authentication.
                                          If None, gets from environment
            tools (list[dict], optional): List of tool configurations
        """
        self.logger = logging.getLogger()
        self.client = OpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
        self.tools = tools or []
        self.logger.debug("DailyAgent initialized with OpenAI client")

    def create(
        self, chat_history: List[Message], model: str = None, **kwargs
    ) -> Message:
        """Process chat history and generate response using OpenAI.

        Args:
            chat_history (List[Message]): List of Message objects
            model (str, optional): OpenAI model to use. If None, uses DEFAULT_CHAT_MODEL
                     from environment
            **kwargs: Additional parameters for OpenAI API call

        Returns:
            List[Message]: Updated chat history including the assistant's response
        """
        model = model or os.getenv("DEFAULT_CHAT_MODEL", "gpt-4o")
        self.logger.info(f"Using model: {model}")

        # Filter chat history to include only valid message types
        filtered_history = [
            {"role": msg.role, "content": msg.content}
            for msg in chat_history
            if msg.role in ["system", "assistant", "developer", "tool", "user"]
        ]
        self.logger.debug(f"Filtered chat history length: {len(filtered_history)}")

        # Generate response using OpenAI
        self.logger.info("Generating response from OpenAI")
        if self.tools:
            response = self.client.chat.completions.create(
                model=model, messages=filtered_history, tools=self.tools, **kwargs
            )
        else:
            response = self.client.chat.completions.create(
                model=model, messages=filtered_history, **kwargs
            )

        if response_content := response.choices[0].message.content:
            self.logger.debug("Response received from OpenAI - text content")

            # Create new Message object for the assistant's response
            assistant_message = Message(
                role="assistant", content=response_content, timestamp=datetime.now()
            )
        elif response.choices[0].message.tools_calls:
            response_list = []
            self.logger.debug("Response received from OpenAI - tool call")
            assistant_message = Message(
                role="assistant",
                content=json.dumps(response.choices[0].message.tools_calls),
                timestamp=datetime.now(),
            )
            response_list.append(assistant_message)
            for tool_call in response.choices[0].message.tools_calls:
                # Call the relevant tool and return the result as a Message object
                pass

        return assistant_message
