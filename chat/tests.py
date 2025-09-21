import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from .models import Conversation, Message
from .services import OpenAIService


class ConversationModelTest(TestCase):
    """Test cases for the Conversation model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.conversation = Conversation.objects.create(
            user=self.user,
            title='Test Conversation'
        )

    def test_conversation_creation(self):
        """Test conversation creation."""
        self.assertEqual(self.conversation.user, self.user)
        self.assertEqual(self.conversation.title, 'Test Conversation')
        self.assertIsNotNone(self.conversation.created_at)
        self.assertIsNotNone(self.conversation.updated_at)

    def test_conversation_str_method(self):
        """Test conversation string representation."""
        expected = f"{self.user.username} - {self.conversation.title}"
        self.assertEqual(str(self.conversation), expected)

    def test_get_active_messages(self):
        """Test getting active (non-superseded) messages."""
        # Create messages
        msg1 = Message.objects.create(
            conversation=self.conversation,
            role='user',
            content='Hello'
        )
        msg2 = Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            content='Hi there!'
        )
        msg3 = Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            content='Updated response',
            superseded=True
        )
        
        active_messages = self.conversation.get_active_messages()
        self.assertEqual(active_messages.count(), 2)
        self.assertIn(msg1, active_messages)
        self.assertIn(msg2, active_messages)
        self.assertNotIn(msg3, active_messages)

    def test_update_title_from_first_message(self):
        """Test auto-updating conversation title from first message."""
        # Create a conversation with default title
        conversation = Conversation.objects.create(
            user=self.user,
            title='New Conversation'  # Default title that should be updated
        )
        
        # Create a user message
        Message.objects.create(
            conversation=conversation,
            role='user',
            content='This is a very long message that should be truncated when used as title'
        )
        
        # Update title
        conversation.update_title_from_first_message()
        
        # Check that title was updated and truncated
        self.assertTrue(conversation.title.startswith('This is a very long message'))
        self.assertTrue(len(conversation.title) <= 53)  # 50 chars + '...'


class MessageModelTest(TestCase):
    """Test cases for the Message model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.conversation = Conversation.objects.create(
            user=self.user,
            title='Test Conversation'
        )

    def test_message_creation(self):
        """Test message creation."""
        message = Message.objects.create(
            conversation=self.conversation,
            role='user',
            content='Test message'
        )
        
        self.assertEqual(message.conversation, self.conversation)
        self.assertEqual(message.role, 'user')
        self.assertEqual(message.content, 'Test message')
        self.assertFalse(message.edited)
        self.assertFalse(message.superseded)

    def test_edit_content(self):
        """Test editing message content."""
        message = Message.objects.create(
            conversation=self.conversation,
            role='user',
            content='Original content'
        )
        
        # Edit the message
        message.edit_content('Updated content')
        
        self.assertEqual(message.content, 'Updated content')
        self.assertEqual(message.previous_content, 'Original content')
        self.assertTrue(message.edited)
        self.assertIsNotNone(message.edited_at)

    def test_edit_content_non_user_message(self):
        """Test that only user messages can be edited."""
        message = Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            content='Assistant message'
        )
        
        with self.assertRaises(ValueError):
            message.edit_content('Updated content')

    def test_supersede_with_new_reply(self):
        """Test superseding assistant message with new reply."""
        user_message = Message.objects.create(
            conversation=self.conversation,
            role='user',
            content='User message'
        )
        
        old_reply = Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            content='Old reply',
            parent_user_message=user_message
        )
        
        new_reply = Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            content='New reply',
            parent_user_message=user_message
        )
        
        # Supersede old reply
        old_reply.supersede_with_new_reply(new_reply)
        
        self.assertTrue(old_reply.superseded)
        self.assertEqual(old_reply.replaced_by, new_reply)

    def test_to_openai_format(self):
        """Test converting message to OpenAI format."""
        message = Message.objects.create(
            conversation=self.conversation,
            role='user',
            content='Test message'
        )
        
        openai_format = message.to_openai_format()
        expected = {
            'role': 'user',
            'content': 'Test message'
        }
        
        self.assertEqual(openai_format, expected)


class AuthenticationViewTest(TestCase):
    """Test cases for authentication views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_register_view_get(self):
        """Test GET request to register view."""
        response = self.client.get(reverse('chat:register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Join AkashChat')

    def test_register_view_post_valid(self):
        """Test POST request to register view with valid data."""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'first_name': 'New',
            'last_name': 'User'
        }
        
        response = self.client.post(reverse('chat:register'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful registration
        
        # Check user was created
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_login_view_get(self):
        """Test GET request to login view."""
        response = self.client.get(reverse('chat:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome Back')

    def test_login_view_post_valid(self):
        """Test POST request to login view with valid credentials."""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        response = self.client.post(reverse('chat:login'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful login

    def test_logout_view(self):
        """Test logout view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('chat:logout'))
        self.assertEqual(response.status_code, 302)  # Redirect after logout


class ConversationViewTest(TestCase):
    """Test cases for conversation views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.conversation = Conversation.objects.create(
            user=self.user,
            title='Test Conversation'
        )

    def test_conversation_list_view(self):
        """Test conversation list view."""
        response = self.client.get(reverse('chat:conversation_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Conversation')

    def test_create_conversation_view(self):
        """Test creating a new conversation."""
        response = self.client.post(
            reverse('chat:create_conversation'),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('id', data)
        self.assertEqual(data['title'], 'New Conversation')

    def test_conversation_detail_view(self):
        """Test conversation detail view."""
        response = self.client.get(
            reverse('chat:conversation_detail', args=[self.conversation.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Conversation')

    def test_delete_conversation_view(self):
        """Test deleting a conversation."""
        response = self.client.post(
            reverse('chat:delete_conversation', args=[self.conversation.id]),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Check conversation was deleted
        self.assertFalse(Conversation.objects.filter(id=self.conversation.id).exists())

    def test_rename_conversation_view(self):
        """Test renaming a conversation."""
        data = {'title': 'Updated Title'}
        response = self.client.post(
            reverse('chat:rename_conversation', args=[self.conversation.id]),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['title'], 'Updated Title')
        
        # Check conversation was updated
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.title, 'Updated Title')


class MessageViewTest(TestCase):
    """Test cases for message views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.conversation = Conversation.objects.create(
            user=self.user,
            title='Test Conversation'
        )

    @patch('chat.services.openai_service.generate_chat_completion')
    def test_send_message_view(self, mock_generate):
        """Test sending a message."""
        mock_generate.return_value = 'AI response'
        
        data = {'content': 'Hello, AI!'}
        response = self.client.post(
            reverse('chat:send_message', args=[self.conversation.id]),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertIn('user_message', response_data)
        self.assertIn('assistant_message', response_data)
        self.assertEqual(response_data['user_message']['content'], 'Hello, AI!')
        self.assertEqual(response_data['assistant_message']['content'], 'AI response')

    def test_edit_message_view(self):
        """Test editing a message."""
        message = Message.objects.create(
            conversation=self.conversation,
            role='user',
            content='Original content'
        )
        
        data = {'content': 'Updated content'}
        response = self.client.patch(
            reverse('chat:edit_message', args=[message.id]),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['message']['content'], 'Updated content')
        self.assertTrue(response_data['message']['edited'])

    @patch('chat.services.openai_service.generate_chat_completion')
    def test_regenerate_reply_view(self, mock_generate):
        """Test regenerating an assistant reply."""
        mock_generate.return_value = 'New AI response'
        
        user_message = Message.objects.create(
            conversation=self.conversation,
            role='user',
            content='User message'
        )
        
        old_reply = Message.objects.create(
            conversation=self.conversation,
            role='assistant',
            content='Old AI response',
            parent_user_message=user_message
        )
        
        data = {'message_id': user_message.id}
        response = self.client.post(
            reverse('chat:regenerate_reply', args=[self.conversation.id]),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['assistant_message']['content'], 'New AI response')
        
        # Check old reply was superseded
        old_reply.refresh_from_db()
        self.assertTrue(old_reply.superseded)


class OpenAIServiceTest(TestCase):
    """Test cases for OpenAI service."""
    
    def setUp(self):
        self.service = OpenAIService()

    def test_estimate_tokens(self):
        """Test token estimation."""
        text = "This is a test message"
        tokens = self.service.estimate_tokens(text)
        self.assertGreater(tokens, 0)
        self.assertEqual(tokens, len(text) // 4)

    def test_trim_messages_by_token_limit(self):
        """Test trimming messages by token limit."""
        messages = [
            {'role': 'user', 'content': 'Short message'},
            {'role': 'assistant', 'content': 'Another short message'},
            {'role': 'user', 'content': 'A' * 1000},  # Long message
            {'role': 'assistant', 'content': 'Final message'}
        ]
        
        trimmed = self.service.trim_messages_by_token_limit(messages, max_tokens=100)
        
        # Should keep only the most recent messages that fit
        self.assertLess(len(trimmed), len(messages))
        self.assertEqual(trimmed[-1]['content'], 'Final message')

    @patch('openai.OpenAI')
    def test_check_moderation(self, mock_openai):
        """Test content moderation check."""
        # Mock the moderation response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.results = [MagicMock()]
        mock_response.results[0].flagged = False
        mock_response.results[0].categories.model_dump.return_value = {}
        
        mock_client.moderations.create.return_value = mock_response
        
        service = OpenAIService()
        result = service.check_moderation("This is a safe message")
        
        self.assertFalse(result['flagged'])
        self.assertEqual(result['categories'], {})

    @patch('openai.OpenAI')
    def test_generate_chat_completion(self, mock_openai):
        """Test chat completion generation."""
        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock the chat completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AI response"
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Mock moderation check
        mock_moderation = MagicMock()
        mock_moderation.results = [MagicMock()]
        mock_moderation.results[0].flagged = False
        mock_client.moderations.create.return_value = mock_moderation
        
        service = OpenAIService()
        messages = [{'role': 'user', 'content': 'Hello'}]
        result = service.generate_chat_completion(messages)
        
        self.assertEqual(result, "AI response")


class IntegrationTest(TestCase):
    """Integration tests for the complete workflow."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

    @patch('chat.services.openai_service.generate_chat_completion')
    def test_complete_conversation_workflow(self, mock_generate):
        """Test the complete conversation workflow."""
        mock_generate.return_value = 'AI response'
        
        # Create conversation
        response = self.client.post(
            reverse('chat:create_conversation'),
            content_type='application/json'
        )
        conversation_data = json.loads(response.content)
        conversation_id = conversation_data['id']
        
        # Send message
        data = {'content': 'Hello, AI!'}
        response = self.client.post(
            reverse('chat:send_message', args=[conversation_id]),
            data=json.dumps(data),
            content_type='application/json'
        )
        message_data = json.loads(response.content)
        user_message_id = message_data['user_message']['id']
        
        # Edit message
        edit_data = {'content': 'Hello, updated AI!'}
        response = self.client.patch(
            reverse('chat:edit_message', args=[user_message_id]),
            data=json.dumps(edit_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Regenerate reply
        mock_generate.return_value = 'Updated AI response'
        regen_data = {'message_id': user_message_id}
        response = self.client.post(
            reverse('chat:regenerate_reply', args=[conversation_id]),
            data=json.dumps(regen_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify the workflow
        conversation = Conversation.objects.get(id=conversation_id)
        messages = conversation.get_active_messages()
        
        # Should have user message and new assistant reply
        self.assertEqual(messages.count(), 2)
        user_msg = messages.filter(role='user').first()
        assistant_msg = messages.filter(role='assistant').first()
        
        self.assertEqual(user_msg.content, 'Hello, updated AI!')
        self.assertTrue(user_msg.edited)
        self.assertEqual(assistant_msg.content, 'Updated AI response')
        self.assertFalse(assistant_msg.superseded)
