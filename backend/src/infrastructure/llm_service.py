"""
LLM Service with OpenRouter support
"""

from typing import Optional, Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.language_models import BaseChatModel
from infrastructure.config.settings import get_settings
import logging

logger = logging.getLogger(__name__)


class LLMService:
    """Service for managing LLM interactions with OpenRouter"""

    def __init__(self):
        self.settings = get_settings()
        self._llm: Optional[BaseChatModel] = None
        self._vision_llm: Optional[BaseChatModel] = None

    def get_llm(self, model_type: str = "chat") -> BaseChatModel:
        """Get configured LLM instance"""
        if model_type == "vision":
            if self._vision_llm is None:
                self._vision_llm = self._create_llm(is_vision=True)
            return self._vision_llm
        else:
            if self._llm is None:
                self._llm = self._create_llm(is_vision=False)
            return self._llm

    def _create_llm(self, is_vision: bool = False) -> BaseChatModel:
        """Create LLM instance with OpenRouter"""
        model = self.settings.vision_model if is_vision else self.settings.chat_model

        logger.info(f"Using OpenRouter with model: {model}")

        default_headers = {
            "HTTP-Referer": self.settings.openrouter_app_url or "https://construction-agent.local",
            "X-Title": self.settings.openrouter_app_title or self.settings.app_name,
        }

        llm = ChatOpenAI(
            api_key=self.settings.openrouter_api_key,
            base_url=self.settings.openrouter_base_url,
            model=model,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
            default_headers=default_headers
        )

        return llm

    def get_model_info(self) -> Dict[str, Any]:
        """Get current model configuration info"""
        return {
            "provider": "OpenRouter",
            "model": self.settings.chat_model,
            "chat_model": self.settings.chat_model,
            "vision_model": self.settings.vision_model,
            "base_url": self.settings.openrouter_base_url,
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens
        }

    def chat(self, messages: List[BaseMessage]) -> str:
        """Simple chat completion"""
        llm = self.get_llm()
        response = llm.invoke(messages)
        return response.content

    def stream_chat(self, messages: List[BaseMessage]):
        """Stream chat completion"""
        llm = self.get_llm()
        for chunk in llm.stream(messages):
            yield chunk.content

    @staticmethod
    def create_messages(
        system_prompt: Optional[str] = None,
        user_message: str = ""
    ) -> List[BaseMessage]:
        """Helper to create message list"""
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        if user_message:
            messages.append(HumanMessage(content=user_message))
        return messages


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get LLM service singleton"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
