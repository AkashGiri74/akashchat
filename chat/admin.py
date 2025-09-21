from django.contrib import admin
from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'role', 'content_preview', 'created_at', 'edited', 'superseded')
    list_filter = ('role', 'created_at', 'edited', 'superseded')
    search_fields = ('content', 'conversation__title')
    readonly_fields = ('created_at', 'edited_at')
    ordering = ('-created_at',)

    def content_preview(self, obj):
        """Show a preview of the message content in admin list."""
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content Preview'
