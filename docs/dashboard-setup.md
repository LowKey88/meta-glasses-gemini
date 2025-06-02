# Meta Glasses Admin Dashboard

A comprehensive web-based administration interface for managing your Meta Glasses Gemini system.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Web Browser   │────▶│  Admin Dashboard │────▶│   FastAPI       │
│   (React UI)    │     │   (Container 3)  │     │  (Container 1)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                │                          │
                                └──────────┬───────────────┘
                                           ▼
                                    ┌─────────────┐
                                    │    Redis    │
                                    │(Container 2)│
                                    └─────────────┘
```

## Features

### 1. Memory Management
- View, search, and filter all memories
- Edit memory content and types
- Delete memories with confirmation
- Bulk operations for cleanup
- Memory analytics and insights

### 2. Redis Database Monitor
- Real-time key browsing and search
- View key values, types, and TTL
- Memory usage statistics
- Export/import functionality

### 3. Calendar Integration
- View upcoming events and reminders
- Manual calendar sync trigger
- Event history and logs
- Reminder management

### 4. WhatsApp Activity
- Real-time message logs
- Message type analytics
- Response time tracking
- Error monitoring

### 5. System Health
- API uptime monitoring
- Container resource usage
- Integration status
- Error logs and alerts

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and navigate to project:**
```bash
cd /path/to/meta-glasses-gemini
```

2. **Create environment file:**
```bash
cp dashboard/.env.example dashboard/.env
# Edit dashboard/.env with your settings
```

3. **Start all services:**
```bash
docker-compose up -d --build
```

4. **Access the dashboard:**
- Dashboard UI: http://localhost:3000
- API: http://localhost:8111
- Default password: `meta-admin-2024`

### Manual Setup

1. **Install dashboard dependencies:**
```bash
cd dashboard
npm install
```

2. **Build the dashboard:**
```bash
npm run build
```

3. **Start the dashboard:**
```bash
npm start
```

## API Endpoints

### Authentication
- `POST /api/dashboard/login` - Login with password

### Memory Management
- `GET /api/dashboard/memories` - List memories
- `PUT /api/dashboard/memories/{id}` - Update memory
- `DELETE /api/dashboard/memories/{id}` - Delete memory

### Redis Monitoring
- `GET /api/dashboard/redis/keys` - List Redis keys
- `GET /api/dashboard/redis/key/{key}` - Get key value

### System Stats
- `GET /api/dashboard/stats` - Overall statistics
- `GET /api/dashboard/messages/recent` - Recent messages
- `GET /api/dashboard/reminders` - Active reminders

## Configuration

### Environment Variables

```env
# Dashboard Settings
DASHBOARD_PASSWORD=meta-admin-2024
DASHBOARD_JWT_SECRET=your-secret-key

# API Connection
API_URL=http://api:8080
DEFAULT_USER_ID=60122873632

# Redis Connection
REDIS_HOST=redis
REDIS_PORT=6379
```

### Security

1. **Change default password** in production
2. **Use HTTPS** for public deployment
3. **Set strong JWT secret**
4. **Configure firewall rules**

## Development

### Project Structure
```
api/
├── dashboard/
│   ├── __init__.py
│   ├── routes.py      # API endpoints
│   └── config.py      # Configuration
dashboard/
├── pages/             # Next.js pages
├── components/        # React components
├── lib/              # Utilities
└── public/           # Static assets
```

### Adding New Features

1. **Backend**: Add endpoints in `api/dashboard/routes.py`
2. **Frontend**: Create components in `dashboard/components/`
3. **Update** Docker images after changes

## Troubleshooting

### Common Issues

1. **Cannot connect to API**
   - Check if all containers are running: `docker ps`
   - Verify network connectivity: `docker network ls`

2. **Authentication fails**
   - Check password in environment variables
   - Verify JWT token generation

3. **Redis connection errors**
   - Ensure Redis container is running
   - Check Redis host/port configuration

### Logs

View logs for debugging:
```bash
# API logs
docker logs raybanmeta

# Dashboard logs
docker logs metadashboard

# Redis logs
docker logs redismeta
```

## Production Deployment

1. **Use reverse proxy** (Nginx/Caddy) with SSL
2. **Set secure passwords** and secrets
3. **Configure backups** for Redis data
4. **Monitor resource usage**
5. **Set up alerts** for errors

## Support

For issues or questions:
1. Check logs first
2. Review configuration
3. Open issue on GitHub