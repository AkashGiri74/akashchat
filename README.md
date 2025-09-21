# AkashChat

A modern ChatGPT-style web application built with Django and Bootstrap, featuring user authentication, conversation management, message editing, and AI reply regeneration with archiving.

## Features

- **User Authentication**: Complete registration, login, and logout system
- **Multi-user Support**: Each user has their own private conversations
- **Conversation Management**: Create, rename, delete, and organize conversations
- **Real-time Chat Interface**: Modern chat UI with message bubbles and typing indicators
- **Message Editing**: Edit user messages with version history
- **Reply Regeneration**: Regenerate AI responses with automatic archiving of previous versions
- **OpenAI Integration**: Server-side integration with OpenAI GPT models
- **Content Moderation**: Built-in content filtering using OpenAI's moderation API
- **Responsive Design**: Mobile-friendly interface using Bootstrap 5
- **Docker Support**: Complete containerization for development and production
- **Comprehensive Testing**: Full test suite covering models, views, and integrations

## Tech Stack

- **Backend**: Django 5.2.6, Django REST Framework
- **Frontend**: HTML5, CSS3, JavaScript (ES6+), Bootstrap 5
- **Database**: SQLite (development), PostgreSQL (production)
- **AI Integration**: OpenAI GPT-4
- **Containerization**: Docker, Docker Compose
- **Web Server**: Nginx (production), Gunicorn
- **Testing**: Django TestCase, unittest.mock

## Project Structure

```
akashchat/
├── akashchat_project/          # Django project settings
│   ├── __init__.py
│   ├── settings.py             # Main settings file
│   ├── urls.py                 # URL routing
│   └── wsgi.py                 # WSGI configuration
├── chat/                       # Main chat application
│   ├── migrations/             # Database migrations
│   ├── __init__.py
│   ├── admin.py                # Django admin configuration
│   ├── forms.py                # Django forms
│   ├── models.py               # Database models
│   ├── services.py             # OpenAI service integration
│   ├── tests.py                # Test suite
│   ├── urls.py                 # App URL routing
│   └── views.py                # View controllers
├── templates/                  # HTML templates
│   ├── base.html               # Base template
│   └── chat/                   # Chat-specific templates
│       ├── auth/               # Authentication templates
│       ├── conversation_list.html
│       └── conversation_detail.html
├── static/                     # Static files
│   ├── css/
│   │   └── style.css           # Custom styles
│   └── js/
│       └── app.js              # JavaScript functionality
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Production Docker Compose
├── docker-compose.dev.yml      # Development Docker Compose
├── nginx.conf                  # Nginx configuration
├── .env.example                # Environment variables template
└── README.md                   # This file
```

## Quick Start

### Prerequisites

- Python 3.10+
- Docker and Docker Compose (optional)
- OpenAI API key

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd akashchat
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file and add your OpenAI API key
   ```

5. **Run database migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Open http://localhost:8000 in your browser
   - Register a new account or login
   - Start chatting!

### Docker Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd akashchat
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file and add your OpenAI API key
   ```

3. **Start with Docker Compose**
   ```bash
   docker-compose -f docker-compose.dev.yml up --build
   ```

4. **Access the application**
   - Open http://localhost:8000 in your browser

### Production Deployment

1. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Configure production settings in .env
   ```

2. **Deploy with Docker Compose**
   ```bash
   docker-compose up -d --build
   ```

3. **Access the application**
   - Open http://localhost in your browser

## Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Django Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here

# Database Configuration (for production)
DATABASE_URL=postgresql://user:password@localhost:5432/akashchat

# Optional: OpenAI Model Configuration
OPENAI_MODEL=gpt-4o
MESSAGE_HISTORY_LIMIT=12
```

## API Endpoints

### Authentication
- `GET /auth/login/` - Login page
- `POST /auth/login/` - Login user
- `GET /auth/register/` - Registration page
- `POST /auth/register/` - Register user
- `GET /auth/logout/` - Logout user

### Conversations
- `GET /conversations/` - List conversations
- `POST /conversations/` - Create conversation
- `GET /conversations/<id>/` - Conversation detail
- `POST /conversations/<id>/delete/` - Delete conversation
- `POST /conversations/<id>/rename/` - Rename conversation

### Messages
- `POST /conversations/<id>/messages/` - Send message
- `PATCH /messages/<id>/edit/` - Edit message
- `POST /conversations/<id>/regenerate/` - Regenerate AI reply

## Database Models

### Conversation Model
```python
class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default='New Conversation')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Message Model
```python
class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    previous_content = models.TextField(blank=True)
    superseded = models.BooleanField(default=False)
    replaced_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    parent_user_message = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
```

## Testing

Run the complete test suite:

```bash
# Run all tests
python manage.py test

# Run specific test class
python manage.py test chat.tests.ConversationModelTest

# Run with verbose output
python manage.py test --verbosity=2

# Run with coverage (install coverage first: pip install coverage)
coverage run --source='.' manage.py test
coverage report
coverage html
```

## OpenAI Integration

### Features
- **Chat Completion**: Uses OpenAI's chat completion API
- **Content Moderation**: Automatic content filtering
- **Token Management**: Smart message history trimming
- **Error Handling**: Graceful handling of API errors and rate limits

### Configuration
- Set `OPENAI_API_KEY` in environment variables
- Configure model with `OPENAI_MODEL` (default: gpt-4o)
- Adjust message history limit with `MESSAGE_HISTORY_LIMIT` (default: 12)

### Message History Trimming
The application automatically trims conversation history to stay within token limits:
- Keeps the most recent messages that fit within the limit
- Estimates ~4 characters per token
- Default limit: 12 messages or ~3000 tokens

## Security Features

- **CSRF Protection**: Django's built-in CSRF protection
- **Content Security**: OpenAI content moderation
- **Rate Limiting**: Nginx-based rate limiting
- **Input Validation**: Server-side validation for all inputs
- **Authentication**: Session-based authentication
- **Authorization**: User-specific data access

## Performance Optimizations

- **Database Indexing**: Optimized database queries
- **Static File Serving**: Nginx for static files in production
- **Gzip Compression**: Enabled for all text content
- **Browser Caching**: Appropriate cache headers
- **Connection Pooling**: PostgreSQL connection pooling

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue on GitHub or contact the development team.

## Changelog

### v1.0.0 (Initial Release)
- User authentication system
- Conversation management
- Message editing and regeneration
- OpenAI integration
- Docker support
- Comprehensive test suite
- Production-ready deployment configuration

