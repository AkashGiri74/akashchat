from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Conversation(models.Model):
    """
    Represents a conversation between a user and the AI assistant.
    Each user can have multiple conversations.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=255, default='New Conversation')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def get_active_messages(self):
        """
        Returns all non-superseded messages in chronological order.
        This is used to display the conversation history.
        """
        return self.messages.filter(superseded=False).order_by('created_at')

    def get_recent_messages_for_api(self, limit=12):
        """
        Returns the most recent non-superseded messages for OpenAI API.
        Limits the number of messages to avoid token overflow.
        """
        messages = self.get_active_messages()
        if messages.count() > limit:
            return messages[messages.count() - limit:]
        return messages

    def update_title_from_first_message(self):
        """
        Auto-generates conversation title from the first user message.
        """
        first_message = self.messages.filter(role='user', superseded=False).first()
        if first_message and self.title == 'New Conversation':
            # Take first 50 characters of the message as title
            title = first_message.content[:50]
            if len(first_message.content) > 50:
                title += '...'
            self.title = title
            self.save()


class Message(models.Model):
    """
    Represents a message in a conversation.
    Can be from user, assistant, or system.
    Supports editing and versioning.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Editing support
    edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    previous_content = models.TextField(blank=True, help_text="Stores the previous version when edited")
    
    # Superseding support for assistant replies
    superseded = models.BooleanField(default=False)
    replaced_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='replaces')
    
    # Link assistant replies to the user message they respond to
    parent_user_message = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                                          related_name='assistant_replies')

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."

    def edit_content(self, new_content):
        """
        Edits the message content and stores the previous version.
        """
        if self.role != 'user':
            raise ValueError("Only user messages can be edited")
        
        self.previous_content = self.content
        self.content = new_content
        self.edited = True
        self.edited_at = timezone.now()
        self.save()

        # Update conversation timestamp
        self.conversation.updated_at = timezone.now()
        self.conversation.save()

    def supersede_with_new_reply(self, new_reply):
        """
        Marks this assistant message as superseded by a new reply.
        """
        if self.role != 'assistant':
            raise ValueError("Only assistant messages can be superseded")
        
        self.superseded = True
        self.replaced_by = new_reply
        self.save()

    def get_conversation_history_for_api(self):
        """
        Returns the conversation history up to this message for OpenAI API.
        Used when regenerating assistant replies.
        """
        conversation = self.conversation
        messages = conversation.get_active_messages()
        
        # Find the position of this message
        message_list = list(messages)
        try:
            current_index = message_list.index(self)
            # Return messages up to and including this message
            return message_list[:current_index + 1]
        except ValueError:
            # If message not found (shouldn't happen), return all messages
            return message_list

    def to_openai_format(self):
        """
        Converts the message to OpenAI API format.
        """
        return {
            "role": self.role,
            "content": self.content
        }
