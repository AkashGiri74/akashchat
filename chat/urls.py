from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Main conversation views
    path('', views.conversation_list, name='conversation_list'),
    path('conversations/', views.conversation_list, name='conversation_list'),
    path('conversations/new/', views.create_conversation, name='create_conversation'),
    path('conversations/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('conversations/<int:conversation_id>/delete/', views.delete_conversation, name='delete_conversation'),
    path('conversations/<int:conversation_id>/rename/', views.rename_conversation, name='rename_conversation'),
    
    # Message-related API endpoints
    path('conversations/<int:conversation_id>/messages/', views.send_message, name='send_message'),
    path('conversations/<int:conversation_id>/regenerate/', views.regenerate_reply, name='regenerate_reply'),
    path('messages/<int:message_id>/edit/', views.edit_message, name='edit_message'),
    
    # Authentication views
    path('auth/register/', views.register_view, name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
]

