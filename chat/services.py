import openai
import logging
from django.conf import settings
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class OpenAIService:
    """
    Service class for handling OpenAI API interactions.
    """
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
    
    def check_moderation(self, text: str) -> Dict:
        """
        Check if text violates OpenAI's usage policies.
        Returns moderation result.
        """
        try:
            response = self.client.moderations.create(input=text)
            return {
                'flagged': response.results[0].flagged,
                'categories': response.results[0].categories.model_dump() if response.results[0].flagged else {}
            }
        except Exception as e:
            logger.error(f"Moderation check failed: {e}")
            # If moderation fails, allow the message but log the error
            return {'flagged': False, 'categories': {}}
    
    def generate_chat_completion(self, messages: List[Dict]) -> Optional[str]:
        """
        Generate a chat completion using OpenAI API.
        
        Args:
            messages: List of message dictionaries in OpenAI format
            
        Returns:
            Generated response text or None if failed
        """
        try:
            # Check moderation for user messages
            for message in messages:
                if message['role'] == 'user':
                    moderation = self.check_moderation(message['content'])
                    if moderation['flagged']:
                        logger.warning(f"Message flagged by moderation: {moderation['categories']}")
                        return "I'm sorry, but I can't respond to that message as it violates our usage policies. Please rephrase your message."
            
            # Make the API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            return response.choices[0].message.content
            
        except openai.RateLimitError:
            logger.error("OpenAI rate limit exceeded")
            return "I'm currently experiencing high demand. Please try again in a moment."
            
        except openai.AuthenticationError:
            logger.error("OpenAI authentication failed")
            return "There's an issue with the AI service configuration. Please contact support."
            
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return "I'm experiencing technical difficulties. Please try again later."
            
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI service: {e}")
            return "An unexpected error occurred. Please try again."
    
    def estimate_tokens(self, text: str) -> int:
        """
        Rough estimation of token count for a text.
        This is a simple approximation: ~4 characters per token.
        """
        return len(text) // 4
    
    def trim_messages_by_token_limit(self, messages: List[Dict], max_tokens: int = 3000) -> List[Dict]:
        """
        Trim messages to stay within token limit.
        Keeps the most recent messages that fit within the limit.
        """
        total_tokens = 0
        trimmed_messages = []
        
        # Process messages in reverse order (most recent first)
        for message in reversed(messages):
            message_tokens = self.estimate_tokens(message['content'])
            if total_tokens + message_tokens <= max_tokens:
                trimmed_messages.insert(0, message)
                total_tokens += message_tokens
            else:
                break
        
        return trimmed_messages


# Global instance
openai_service = OpenAIService()

