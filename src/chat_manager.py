from datetime import datetime, date, timedelta
from src.models import Message, ConversationEntry, SummaryEntry
from src.openai import DailyAgent
from src.CONSTANTS import (
    DEFAULT_SYSTEM_PROMPT,
    N_PREVIOUS_DAYS,
    FIRST_TIME_SYSTEM_PROMPT,
    FIRST_TIME_STARTING_MESSAGE,
    DEFAULT_STARTING_MESSAGE,
    MAX_CONV_TOKENS,
    CHAT_HISTORY_MODE,
    SUMMARIZATION_PROMPT,
)
import logging
from typing import List, Optional, Dict, Any, Literal
from src.mongo import MongoManager
from src.embedding import EmbeddingGenerator
import tiktoken

logger = logging.getLogger(__name__)


class ChatManager:
    """
    Manages chat interactions, message history, and conversation storage.

    Attributes:
        mongo_manager: Database manager for MongoDB operations
        embedder: Text embedding generator
        user_name (str): Name of the user
        session_id (str): Unique identifier for the chat session
        user_id (str): Unique identifier for the user
        messages (List[Message]): List of chat messages
    """

    def __init__(
        self,
        mongo_manager: MongoManager,
        embedding_generator: EmbeddingGenerator,
        user_name: str,
        session_id: str,
        user_id: str,
    ) -> None:
        """
        Initialize ChatManager with required components.

        Args:
            mongo_manager: Database manager instance
            embedder: Text embedding generator instance
            user_name: Name of the user
            session_id: Unique session identifier
            user_id: Unique user identifier
        """
        logger.info(
            f"Initializing ChatManager for user: {user_name}, session: {session_id}"
        )
        self.mongo_manager = mongo_manager
        self.embedding_generator = embedding_generator
        self.user_name = user_name
        self.session_id = session_id
        self.user_id = user_id
        self.messages: List[Message] = []

    def initialize_chat(self) -> None:
        """
        Initialize chat by setting up system prompts based on previous interactions.
        Retrieves historical summaries and sets appropriate initial messages.
        """
        if not self.messages:
            logger.info(f"Initializing chat for session: {self.session_id}")
            end_date = date.today()
            conversation_start_date = datetime.combine(end_date, datetime.min.time())

            # Retrieve summaries and previous sessions
            summaries: List[Dict[str, Any]] = (
                self.mongo_manager.get_last_summaries_by_user(
                    self.user_id, N_PREVIOUS_DAYS
                )
            )
            logger.debug(f"Found {len(summaries)} previous summaries")

            conversations = self.mongo_manager.get_conversations_by_date_range(
                self.user_id, conversation_start_date, end_date
            )
            conversations = [
                {
                    **conv,
                    "messages": [
                        msg
                        for msg in conv.get("messages", [])
                        if msg["role"] != "system" and msg.get("timestamp")
                    ],
                }
                for conv in conversations
            ]
            logger.debug(f"Found {len(conversations)} previous conversations")

            # Turn summaries into a summaries string block
            summaries_block = (
                "\n".join(
                    [
                        f"Day {s['day'].strftime('%Y-%m-%d')}:\n{s['summary']}"
                        for s in summaries
                    ]
                )
                if summaries
                else "Nessuna interazione ritrovata nei giorni precedenti."
            )

            # Turn previous sessions into a previous_sessions string block
            previous_sessions_block = (
                "\n".join(
                    [
                        f"[{msg['timestamp']}] {msg['role']}: {msg['content']}"
                        for conv in conversations
                        for msg in conv["messages"]
                    ]
                )
                if conversations
                else "Nessuna sessione precedente trovata."
            )

            # Format the correct system message
            if not summaries and not conversations:
                logger.info("First-time user detected, using first-time prompt")
                formatted_prompt = FIRST_TIME_SYSTEM_PROMPT.format(
                    patient=self.user_name.split(" ")[0],
                    current_time=datetime.now(),
                )
                starting_message_content = FIRST_TIME_STARTING_MESSAGE
            else:
                logger.info("Returning user detected, using default prompt")
                formatted_prompt = DEFAULT_SYSTEM_PROMPT.format(
                    patient=self.user_name.split(" ")[0],
                    n=N_PREVIOUS_DAYS,
                    summaries=summaries_block,
                    previous_sessions=previous_sessions_block,
                    current_time=datetime.now(),
                )
                starting_message_content = DEFAULT_STARTING_MESSAGE

            # Set self.messages
            self.messages = [
                Message(
                    role="system",
                    content=formatted_prompt,
                    timestamp=datetime.now(),
                ),
                Message(
                    role="assistant",
                    content=starting_message_content,
                    timestamp=datetime.now(),
                ),
            ]

    def handle_chat_input(self, prompt: str) -> Optional[Message]:
        """
        Process user input and generate assistant response.

        Args:
            prompt: User input text

        Returns:
            Optional[Message]: Assistant's response message or None if processing fails
        """
        if not prompt:
            logger.warning("Empty prompt received, ignoring")
            return None

        logger.info(f"Processing chat input for session: {self.session_id}")
        user_message = Message(role="user", content=prompt, timestamp=datetime.now())
        self.messages.append(user_message)

        try:
            agent = DailyAgent()
            logger.info("Current chat history: {}".format(self.messages))
            preprocessed_chat_history = self.preprocess_chat_history(
                self.messages, mode=CHAT_HISTORY_MODE
            )
            logger.info(
                "Preprocessed chat history, {} messages".format(
                    len(preprocessed_chat_history)
                )
            )
            logger.info("Current chat history: {}".format(self.messages))
            assistant_message = agent.create(
                chat_history=preprocessed_chat_history,
            )
            self.messages.append(assistant_message)
            logger.debug("Successfully generated assistant response")

            self._store_conversation()
            return assistant_message

        except Exception as e:
            logger.error(f"Error processing chat input: {str(e)}", exc_info=True)
            error_message = Message(role="system", content=f"Chat error: {str(e)}")
            self.messages.append(error_message)
            self._store_conversation()
            return None

    def _store_conversation(self) -> None:
        """
        Store or update the current conversation in the database.
        Generates embeddings and maintains conversation history.
        """
        logger.info(f"Storing conversation for session: {self.session_id}")

        conversation = ConversationEntry(
            session_id=self.session_id,
            user_id=self.user_id,
            messages=self.messages,
            text_content="\n".join(
                [msg.role + ": " + msg.content for msg in self.messages]
            ),
            embedding=self.embedding_generator.create(
                " ".join([msg.content for msg in self.messages])
            ),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        existing_conversation: Optional[Dict[str, Any]] = (
            self.mongo_manager.get_conversation_by_session_id(self.session_id)
        )
        if existing_conversation:
            logger.debug("Updating existing conversation")
            conversation.created_at = existing_conversation["created_at"]
            self.mongo_manager.update_conversation(
                self.session_id, conversation.model_dump()
            )
        else:
            logger.debug("Creating new conversation")
            self.mongo_manager.create_conversation(conversation)

    @staticmethod
    def preprocess_chat_history(
        chat_history: List[Message],
        mode: Literal["truncate", "summarize"] = "truncate",
    ) -> List[Message]:

        modes = {
            "summarize": ChatManager._summarize_conversation,
            "truncate": ChatManager._truncate_messages,
        }

        mode = "truncate"  # Default mode
        if not chat_history:
            return []

        return modes[mode](chat_history)

    @staticmethod
    def _summarize_conversation(messages: List[Message]) -> str:
        # Extract only the relevant message content
        conversation_text = []
        for msg in messages:
            if msg.role != "system":
                prefix = "User: " if msg.role == "user" else "Assistant: "
                conversation_text.append(f"{prefix}{msg.content}")

        # Create a summarized query
        latest_user_message = next(
            (msg for msg in reversed(messages) if msg.role == "user"), None
        )
        if not latest_user_message:
            return ""

        system_prompt = (
            "Based on the conversation history below, create a single query that "
            "captures the user's latest question with all necessary context. "
            "Use the conversation's language and style to rephrase the question.\n\n"
            "History:\n{}\n\nLatest question: {}"
        ).format("\n".join(conversation_text[:-1]), latest_user_message.content)

        agent = DailyAgent()
        reworded_query = agent.create([Message(role="system", content=system_prompt)])

        # Return synthetic chat history with just system message and reworded query
        return [
            Message(
                role="system", content=messages[0].content
            ),  # Keep original system message
            Message(
                role="user",
                content=(
                    reworded_query.content
                    if reworded_query
                    else latest_user_message.content
                ),
            ),
        ]

    @staticmethod
    def _truncate_messages(messages: List[Message]) -> List[Message]:
        encoding = tiktoken.encoding_for_model("gpt-4o")
        max_tokens = 100000  # Conservative limit for GPT-4

        # Always keep system message
        system_message = next((msg for msg in messages if msg.role == "system"), None)
        if not system_message:
            return messages

        other_messages = [msg for msg in messages if msg.role != "system"]
        current_tokens = len(encoding.encode(system_message.content))

        # Add messages from the end until we hit token limit
        included_messages = []
        for msg in reversed(other_messages):
            tokens = len(encoding.encode(msg.content))
            if current_tokens + tokens > max_tokens:
                break
            included_messages.insert(0, msg)
            current_tokens += tokens

        return [system_message] + included_messages


class SummaryManager:
    """
    Manages the generation and storage of conversation summaries.
    """

    def __init__(
        self, mongo_manager: MongoManager, embedding_generator: EmbeddingGenerator
    ) -> None:
        self.mongo_manager = mongo_manager
        self.embedding_generator = embedding_generator
        self.agent = DailyAgent()

    def create_daily_summaries(self, model: str = None) -> None:
        """
        Creates summaries for all conversations from the previous day.
        """
        summary_prompt = SUMMARIZATION_PROMPT
        yesterday = date.today() - timedelta(days=1)
        start_date = datetime.combine(yesterday, datetime.min.time())
        end_date = datetime.combine(yesterday, datetime.max.time())
        model = model or "o1-mini"

        # Get all users
        users = [user["user_id"] for user in self.mongo_manager.get_users()]
        for user in users:
            # Check if summary already exists for this user and date
            existing_summary = self.mongo_manager.get_summaries_by_date_range(
                user, yesterday, yesterday
            )
            if existing_summary:
                logger.info(f"Summary already exists for user {user} on {yesterday}")
                continue

            conversations = self.mongo_manager.get_conversations_by_date_range(
                user, start_date, end_date
            )

            if conversations:
                chat_history = []
                for conv in conversations:
                    chat_history.extend(
                        [Message(**msg) for msg in conv.get("messages", [])]
                    )
                logger.info(
                    f"Found {len(chat_history)} messages for user {user} on {yesterday}"
                )
                conv_block = "\n".join(
                    [
                        f"[{msg.timestamp}]{msg.role}: {msg.content}"
                        for msg in chat_history
                        if msg.role != "system"
                    ]
                )
                # Generate summary using the agent
                logger.info(f"Generating summary for user {user} on {yesterday}")
                logger.info(f"Conversation block:\n{conv_block}")
                summary_message = self.agent.create(
                    [
                        Message(
                            role="user",
                            content=summary_prompt.format(conv_block=conv_block),
                        )
                    ],
                    model=model,
                )

                if summary_message:
                    # Store the summary using existing method
                    summary_id = self.mongo_manager.create_summary(
                        SummaryEntry(
                            user_id=user,
                            day=datetime.combine(yesterday, datetime.min.time()),
                            created_at=datetime.now(),
                            summary=summary_message.content,
                            session_ids=[conv["session_id"] for conv in conversations],
                            embedding=self.embedding_generator.create(
                                summary_message.content
                            ),
                        )
                    )
                    logger.info(
                        f"Created summary for user {user} on {yesterday}: {summary_id}"
                    )
                else:
                    logger.error(f"Failed to generate summary for user {user}")
