# AkashChat Deployment Guide

This guide covers deploying AkashChat in various environments, from development to production.

## Development Deployment

### Local Development (Recommended)

1. **Prerequisites**
   - Python 3.10+
   - pip
   - Virtual environment tool

2. **Setup Steps**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd akashchat

   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

   # Set up environment
   cp .env.example .env
   # Edit .env with your OpenAI API key

   # Database setup
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser

   # Start development server
   python manage.py runserver
   ```

3. **Access Application**
   - URL: http://localhost:8000
   - Admin: http://localhost:8000/admin/

### Docker Development

1. **Prerequisites**
   - Docker
   - Docker Compose

2. **Setup Steps**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd akashchat

   # Set up environment
   cp .env.example .env
   # Edit .env with your OpenAI API key

   # Start services
   docker-compose -f docker-compose.dev.yml up --build

   # Create superuser (in another terminal)
   docker-compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
   ```

3. **Access Application**
   - URL: http://localhost:8000
   - Database: localhost:5432

## Production Deployment

### Docker Production (Recommended)

1. **Prerequisites**
   - Docker
   - Docker Compose
   - Domain name (optional)
   - SSL certificates (for HTTPS)

2. **Server Setup**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   sudo usermod -aG docker $USER

   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

3. **Application Deployment**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd akashchat

   # Set up production environment
   cp .env.example .env
   # Edit .env with production settings
   ```

4. **Environment Configuration**
   ```env
   # Production .env file
   SECRET_KEY=your-very-secure-secret-key-here
   DEBUG=False
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   DATABASE_URL=postgresql://akashchat:secure_password@db:5432/akashchat
   OPENAI_API_KEY=your-openai-api-key-here
   OPENAI_MODEL=gpt-4o
   MESSAGE_HISTORY_LIMIT=12
   ```

5. **Deploy Application**
   ```bash
   # Start production services
   docker-compose up -d --build

   # Run migrations
   docker-compose exec web python manage.py migrate

   # Create superuser
   docker-compose exec web python manage.py createsuperuser

   # Collect static files
   docker-compose exec web python manage.py collectstatic --noinput
   ```

6. **SSL Setup (Optional)**
   ```bash
   # Create SSL directory
   mkdir ssl

   # Copy your SSL certificates
   cp your-cert.pem ssl/cert.pem
   cp your-key.pem ssl/key.pem

   # Update nginx.conf to enable HTTPS
   # Uncomment the HTTPS server block in nginx.conf
   ```

### Manual Production Deployment

1. **Server Setup**
   ```bash
   # Install system dependencies
   sudo apt update
   sudo apt install python3 python3-pip python3-venv postgresql postgresql-contrib nginx redis-server

   # Create application user
   sudo adduser akashchat
   sudo usermod -aG sudo akashchat
   su - akashchat
   ```

2. **Database Setup**
   ```bash
   # Configure PostgreSQL
   sudo -u postgres psql
   CREATE DATABASE akashchat;
   CREATE USER akashchat WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE akashchat TO akashchat;
   \q
   ```

3. **Application Setup**
   ```bash
   # Clone and setup application
   git clone <repository-url>
   cd akashchat
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   # Configure environment
   cp .env.example .env
   # Edit .env with production settings

   # Run migrations
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   ```

4. **Gunicorn Setup**
   ```bash
   # Create systemd service
   sudo nano /etc/systemd/system/akashchat.service
   ```

   ```ini
   [Unit]
   Description=AkashChat Django Application
   After=network.target

   [Service]
   User=akashchat
   Group=akashchat
   WorkingDirectory=/home/akashchat/akashchat
   Environment="PATH=/home/akashchat/akashchat/venv/bin"
   ExecStart=/home/akashchat/akashchat/venv/bin/gunicorn --workers 3 --bind unix:/home/akashchat/akashchat/akashchat.sock akashchat_project.wsgi:application
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   # Enable and start service
   sudo systemctl daemon-reload
   sudo systemctl enable akashchat
   sudo systemctl start akashchat
   ```

5. **Nginx Setup**
   ```bash
   # Create Nginx configuration
   sudo nano /etc/nginx/sites-available/akashchat
   ```

   ```nginx
   server {
       listen 80;
       server_name yourdomain.com www.yourdomain.com;

       location = /favicon.ico { access_log off; log_not_found off; }
       
       location /static/ {
           root /home/akashchat/akashchat;
       }

       location / {
           include proxy_params;
           proxy_pass http://unix:/home/akashchat/akashchat/akashchat.sock;
       }
   }
   ```

   ```bash
   # Enable site
   sudo ln -s /etc/nginx/sites-available/akashchat /etc/nginx/sites-enabled
   sudo nginx -t
   sudo systemctl restart nginx
   ```

## Cloud Deployment

### AWS Deployment

1. **EC2 Instance Setup**
   - Launch EC2 instance (t3.medium or larger)
   - Configure security groups (ports 80, 443, 22)
   - Attach Elastic IP

2. **RDS Database**
   - Create PostgreSQL RDS instance
   - Configure security groups
   - Update DATABASE_URL in .env

3. **S3 for Static Files** (Optional)
   - Create S3 bucket
   - Configure Django settings for S3
   - Install django-storages

### Google Cloud Platform

1. **Compute Engine**
   - Create VM instance
   - Configure firewall rules
   - Follow manual deployment steps

2. **Cloud SQL**
   - Create PostgreSQL instance
   - Configure connection
   - Update DATABASE_URL

### DigitalOcean

1. **Droplet Setup**
   - Create Ubuntu droplet
   - Follow manual deployment steps

2. **Managed Database**
   - Create PostgreSQL cluster
   - Update DATABASE_URL

## Monitoring and Maintenance

### Health Checks

1. **Application Health**
   ```bash
   # Check application status
   curl -f http://localhost:8000/

   # Check with Docker
   docker-compose ps
   docker-compose logs web
   ```

2. **Database Health**
   ```bash
   # PostgreSQL
   docker-compose exec db pg_isready -U akashchat

   # Manual installation
   sudo -u postgres psql -c "SELECT 1;"
   ```

### Backup Strategy

1. **Database Backup**
   ```bash
   # Docker environment
   docker-compose exec db pg_dump -U akashchat akashchat > backup.sql

   # Manual installation
   sudo -u postgres pg_dump akashchat > backup.sql
   ```

2. **Application Backup**
   ```bash
   # Backup entire application
   tar -czf akashchat-backup-$(date +%Y%m%d).tar.gz akashchat/
   ```

### Log Management

1. **Application Logs**
   ```bash
   # Docker logs
   docker-compose logs -f web

   # Manual installation
   tail -f /var/log/akashchat/akashchat.log
   ```

2. **Nginx Logs**
   ```bash
   # Access logs
   tail -f /var/log/nginx/access.log

   # Error logs
   tail -f /var/log/nginx/error.log
   ```

### Performance Tuning

1. **Database Optimization**
   - Enable connection pooling
   - Optimize PostgreSQL settings
   - Regular VACUUM and ANALYZE

2. **Application Optimization**
   - Increase Gunicorn workers
   - Enable Redis caching
   - Optimize static file serving

3. **Nginx Optimization**
   - Enable gzip compression
   - Configure proper caching headers
   - Optimize worker processes

## Security Considerations

### Production Security Checklist

- [ ] Change default SECRET_KEY
- [ ] Set DEBUG=False
- [ ] Configure ALLOWED_HOSTS
- [ ] Use HTTPS with valid SSL certificates
- [ ] Enable firewall (ufw or cloud security groups)
- [ ] Regular security updates
- [ ] Strong database passwords
- [ ] Backup encryption
- [ ] Rate limiting configuration
- [ ] Content Security Policy headers

### SSL/TLS Setup

1. **Let's Encrypt (Free)**
   ```bash
   # Install Certbot
   sudo apt install certbot python3-certbot-nginx

   # Obtain certificate
   sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

   # Auto-renewal
   sudo crontab -e
   # Add: 0 12 * * * /usr/bin/certbot renew --quiet
   ```

2. **Custom SSL Certificate**
   - Purchase SSL certificate
   - Configure in nginx.conf
   - Update Docker volumes

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check DATABASE_URL format
   - Verify database service is running
   - Check network connectivity

2. **Static Files Not Loading**
   - Run `collectstatic` command
   - Check Nginx configuration
   - Verify file permissions

3. **OpenAI API Errors**
   - Verify API key is correct
   - Check API quota and billing
   - Review rate limiting

4. **Docker Issues**
   - Check Docker service status
   - Review container logs
   - Verify port availability

### Performance Issues

1. **Slow Response Times**
   - Check database query performance
   - Monitor OpenAI API response times
   - Review server resources

2. **High Memory Usage**
   - Optimize Gunicorn worker count
   - Check for memory leaks
   - Monitor database connections

## Scaling Considerations

### Horizontal Scaling

1. **Load Balancer Setup**
   - Configure multiple application servers
   - Use shared database
   - Implement session storage (Redis)

2. **Database Scaling**
   - Read replicas for read-heavy workloads
   - Connection pooling
   - Database sharding (advanced)

### Vertical Scaling

1. **Server Resources**
   - Increase CPU and RAM
   - Optimize worker processes
   - Monitor resource usage

2. **Database Resources**
   - Increase database instance size
   - Optimize queries and indexes
   - Regular maintenance

