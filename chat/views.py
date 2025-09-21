import json
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.utils.decorators import method_decorator
from django.conf import settings
from django.db import transaction

from .models import Conversation, Message
from .forms import CustomUserCreationForm, CustomAuthenticationForm, ConversationRenameForm, MessageEditForm
from .services import openai_service

logger = logging.getLogger(__name__)


# Authentication Views
def register_view(request):
    """User registration view."""
    if request.user.is_authenticated:
        return redirect('chat:conversation_list')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to AkashChat.')
            return redirect('chat:conversation_list')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'chat/auth/register.html', {'form': form})


class CustomLoginView(LoginView):
    """Custom login view with Bootstrap styling."""
    form_class = CustomAuthenticationForm
    template_name = 'chat/auth/login.html'
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        messages.success(self.request, f'Welcome back, {form.get_user().username}!')
        return super().form_valid(form)


login_view = CustomLoginView.as_view()


def logout_view(request):
    """User logout view."""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('chat:login')


# Conversation Views
@login_required
def conversation_list(request):
    """Display list of user's conversations."""
    conversations = Conversation.objects.filter(user=request.user)
    return render(request, 'chat/conversation_list.html', {
        'conversations': conversations
    })


@login_required
@require_POST
def create_conversation(request):
    """Create a new conversation."""
    conversation = Conversation.objects.create(
        user=request.user,
        title='New Conversation'
    )
    
    if request.headers.get('Content-Type') == 'application/json':
        return JsonResponse({
            'id': conversation.id,
            'title': conversation.title,
            'created_at': conversation.created_at.isoformat()
        })
    
    return redirect('chat:conversation_detail', conversation_id=conversation.id)


@login_required
def conversation_detail(request, conversation_id):
    """Display conversation detail with messages."""
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    messages_list = conversation.get_active_messages()
    
    return render(request, 'chat/conversation_detail.html', {
        'conversation': conversation,
        'messages': messages_list
    })


@login_required
@require_POST
def delete_conversation(request, conversation_id):
    """Delete a conversation and all its messages."""
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    conversation.delete()
    
    if request.headers.get('Content-Type') == 'application/json':
        return JsonResponse({'success': True})
    
    messages.success(request, 'Conversation deleted successfully.')
    return redirect('chat:conversation_list')


@login_required
@require_POST
def rename_conversation(request, conversation_id):
    """Rename a conversation."""
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        new_title = data.get('title', '').strip()
        
        if not new_title:
            return JsonResponse({'error': 'Title cannot be empty'}, status=400)
        
        conversation.title = new_title
        conversation.save()
        
        return JsonResponse({
            'success': True,
            'title': conversation.title
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error renaming conversation: {e}")
        return JsonResponse({'error': 'Failed to rename conversation'}, status=500)


# Message Views
@login_required
@require_POST
def send_message(request, conversation_id):
    """Send a user message and get AI response."""
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({'error': 'Message content cannot be empty'}, status=400)
        
        # Check if OpenAI API key is configured
        if not settings.OPENAI_API_KEY:
            return JsonResponse({
                'error': 'OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.'
            }, status=500)
        
        with transaction.atomic():
            # Create user message
            user_message = Message.objects.create(
                conversation=conversation,
                role='user',
                content=content
            )
            
            # Update conversation title if it's the first message
            conversation.update_title_from_first_message()
            
            # Get conversation history for OpenAI
            recent_messages = conversation.get_recent_messages_for_api(
                limit=settings.MESSAGE_HISTORY_LIMIT
            )
            
            # Convert to OpenAI format
            openai_messages = [msg.to_openai_format() for msg in recent_messages]
            
            # Generate AI response
            ai_response = openai_service.generate_chat_completion(openai_messages)
            
            if ai_response:
                # Create assistant message
                assistant_message = Message.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=ai_response,
                    parent_user_message=user_message
                )
                
                return JsonResponse({
                    'user_message': {
                        'id': user_message.id,
                        'content': user_message.content,
                        'created_at': user_message.created_at.isoformat(),
                        'edited': user_message.edited
                    },
                    'assistant_message': {
                        'id': assistant_message.id,
                        'content': assistant_message.content,
                        'created_at': assistant_message.created_at.isoformat(),
                        'superseded': assistant_message.superseded
                    }
                })
            else:
                return JsonResponse({
                    'error': 'Failed to generate AI response'
                }, status=500)
                
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return JsonResponse({'error': 'Failed to send message'}, status=500)


@login_required
@require_http_methods(["PATCH"])
def edit_message(request, message_id):
    """Edit a user message."""
    message = get_object_or_404(Message, id=message_id)
    
    # Check ownership through conversation
    if message.conversation.user != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # Only user messages can be edited
    if message.role != 'user':
        return JsonResponse({'error': 'Only user messages can be edited'}, status=400)
    
    try:
        data = json.loads(request.body)
        new_content = data.get('content', '').strip()
        
        if not new_content:
            return JsonResponse({'error': 'Message content cannot be empty'}, status=400)
        
        # Edit the message
        message.edit_content(new_content)
        
        return JsonResponse({
            'success': True,
            'message': {
                'id': message.id,
                'content': message.content,
                'edited': message.edited,
                'edited_at': message.edited_at.isoformat() if message.edited_at else None
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        return JsonResponse({'error': 'Failed to edit message'}, status=500)


@login_required
@require_POST
def regenerate_reply(request, conversation_id):
    """Regenerate assistant reply after user message edit."""
    conversation = get_object_or_404(Conversation, id=conversation_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        user_message_id = data.get('message_id')
        
        if not user_message_id:
            return JsonResponse({'error': 'message_id is required'}, status=400)
        
        user_message = get_object_or_404(
            Message, 
            id=user_message_id, 
            conversation=conversation,
            role='user'
        )
        
        # Check if OpenAI API key is configured
        if not settings.OPENAI_API_KEY:
            return JsonResponse({
                'error': 'OpenAI API key not configured. Please set OPENAI_API_KEY environment variable.'
            }, status=500)
        
        with transaction.atomic():
            # Find the current assistant reply to this user message
            current_assistant_reply = Message.objects.filter(
                parent_user_message=user_message,
                role='assistant',
                superseded=False
            ).first()
            
            # Get conversation history up to and including the user message
            messages_for_api = user_message.get_conversation_history_for_api()
            
            # Convert to OpenAI format
            openai_messages = [msg.to_openai_format() for msg in messages_for_api]
            
            # Generate new AI response
            ai_response = openai_service.generate_chat_completion(openai_messages)
            
            if ai_response:
                # Create new assistant message
                new_assistant_message = Message.objects.create(
                    conversation=conversation,
                    role='assistant',
                    content=ai_response,
                    parent_user_message=user_message
                )
                
                # Mark old assistant reply as superseded if it exists
                if current_assistant_reply:
                    current_assistant_reply.supersede_with_new_reply(new_assistant_message)
                
                return JsonResponse({
                    'success': True,
                    'assistant_message': {
                        'id': new_assistant_message.id,
                        'content': new_assistant_message.content,
                        'created_at': new_assistant_message.created_at.isoformat(),
                        'superseded': new_assistant_message.superseded
                    }
                })
            else:
                return JsonResponse({
                    'error': 'Failed to generate AI response'
                }, status=500)
                
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error regenerating reply: {e}")
        return JsonResponse({'error': 'Failed to regenerate reply'}, status=500)
