# Meta Rayban Glasses + Gemini Integration Project

This project integrates the Meta Rayban Glasses with a WhatsApp bot, leveraging the power of Google Gemini, Redis for data management, Notion for note-taking, and Google Calendar for event and reminder management. This README guides you through setting up the project environment, including necessary configurations and API integrations.

For optimal performance and scalability, consider hosting this project on GB Cloud. Visit [GB Cloud](https://www.gbcloud.net) for more information.

For the best web hosting and domain registration services, visit [GB Network Solutions](https://www.gbnetwork.my). Explore more products available on their website.

## Features

### WhatsApp Notifications

- Text messages
- Image sharing
- AI-powered responses

### Calendar Management

The system provides natural language commands for managing your calendar:

#### Checking Schedule
You can check your schedule using various commands:

1. Single Day Queries:
   - "Check my meeting today"
   - "Check my meeting tomorrow"
   - "What meetings do I have today"

2. General Schedule Queries:
   - "What's my schedule"
   - "Show my schedule"
   - "Tell me my schedule"
   (These will show both today's and tomorrow's schedules)

3. Weekly Schedule Queries:
   - "What's my schedule this week"
   - "What meetings do I have next week"
   - "Show me this week's schedule"

#### Creating Events
You can create different types of calendar events:

1. Regular Meetings:
   - "Schedule a meeting with the team tomorrow at 2pm"
   - "Add a client meeting next Monday at 10am for 2 hours"
   - "Create a meeting with vendors on Friday at 3pm"

2. Reminders:
   - "Add a reminder for gym tomorrow at 7am"
   - "Set a reminder for medicine at 9pm"
   - "Remind me about project deadline next Tuesday at 5pm"

3. Time Blocks:
   - "Block 3 hours for project work tomorrow at 1pm"
   - "Add time block for studying from 9am to 12pm"
   - "Schedule focus time today at 4pm for 2 hours"

You can include additional details in your commands:
- Location: "...at Starbucks KLCC"
- Description: "...to discuss Q4 planning"
- Duration: "...for 45 minutes" (default is 1 hour if not specified)

Events are color-coded in your calendar:
- Green (default): Regular meetings and appointments
- Purple: Important meetings and deadlines
- Green Teal: Personal appointments and breaks
- Pink: Social events and celebrations
- Red: Urgent or high-priority meetings
- Yellow: Reminders and tasks

### Home Assistant Integration

- Automation support
- Camera snapshots
- Device state notifications

### Additional Services

- Notion note-taking
- Home automation control

### API Endpoints

- `POST /send-notification`: Send WhatsApp notifications with optional images
- `GET /webhook`: WhatsApp webhook verification
- `POST /webhook`: WhatsApp message processing
- `GET /auth/google`: Initiate Google OAuth flow (requires x-api-key header)
- `GET /auth/callback`: Handle OAuth callback (requires x-api-key header)

### Services Integration

- **WhatsApp**: Message handling and notifications
- **Google Gemini**: AI processing and responses
- **Redis**: Data and session management
- **Notion**: Note-taking and data organization
- **Google Calendar**: Event and reminder management
- **Home Assistant**: Home automation control

## Getting Started

### Prerequisites

- Python 3.x
- pip for Python package installation

### Installation

1. Clone this repository to your local machine.
2. Navigate to the project directory.
3. Install the required Python packages:

  ```sh
  pip install -r requirements.txt
  ```
4. Run the project:

  ```sh
  uvicorn main:app --reload
  ```

### Docker Installation

You can also run this project using Docker. Pull the Docker image from GitHub Container Registry:

```sh
docker pull ghcr.io/lowkey88/meta-glasses-gemini:master
```

Run the Docker container:

```sh
docker run -d -p 8000:8000 --env-file .env ghcr.io/lowkey88/meta-glasses-gemini:master
```

You can also use Docker Compose to manage the services. Create a `docker-compose.yml` file in the project directory with the following content:

```yaml
version: '3.8'

services:
  app:
    container_name: raybanmeta
    image: ghcr.io/lowkey88/meta-glasses-gemini:master
    restart: always
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - cache
    volumes:
      - ./creds:/app/creds

  cache:
    container_name: redismeta
    image: redis:7.2.5
    restart: always
    ports:
      - "6379:6379"
    environment:
      - REDIS_PASSWORD=${REDIS_DB_PASSWORD}
    volumes:
      - ./db:/data/
```

To start the services, run:

```sh
docker-compose up -d
```

### Environment Variables

You need to set the following environment variables in a `.env` file within the project directory:

```dotenv
WHATSAPP_AUTH_TOKEN=
WHATSAPP_PHONE_NUMBER=
WHATSAPP_PHONE_ID=
WHATSAPP_WEBHOOK_VERIFICATION_TOKEN=
REDIS_DB_HOST=
REDIS_DB_PORT=
REDIS_DB_PASSWORD=
GEMINI_API_KEY=
CLOUD_STORAGE_BUCKET_NAME=
NOTION_INTEGRATION_SECRET=
NOTION_DATABASE_ID=
NOTION_FOOD_DATABASE_ID=
SERPER_DEV_API_KEY=
CRAWLBASE_API_KEY=
OAUTH_CREDENTIALS_ENCODED=
HOME_ASSISTANT_TOKEN=
HOME_ASSISTANT_URL=
HOME_ASSISTANT_AGENT_ID=
APP_URL=
API_SECRET_KEY=
```

- `WHATSAPP_AUTH_TOKEN`: Create an app at [Meta for Developers](https://developers.facebook.com/) and retrieve the WhatsApp authentication token.
- `WHATSAPP_PHONE_NUMBER`: The sender's phone number associated with your WhatsApp API. This is the number from which the bot sends messages to your WhatsApp account.
- `WHATSAPP_PHONE_ID`: The unique identifier associated with your WhatsApp Business phone number.
- `WHATSAPP_WEBHOOK_VERIFICATION_TOKEN`: Set a verification token of your choice and use it in the Meta for Developers dashboard to verify the webhook.
- `REDIS_DB_HOST`, `REDIS_DB_PORT`, `REDIS_DB_PASSWORD`: Credentials for your Redis database. This project uses Redis for managing data, including storing images for analysis.
- `GEMINI_API_KEY`: Obtain this from the Google Gemini API for image analysis and AI capabilities.
- `CLOUD_STORAGE_BUCKET_NAME`: The name of your Google Cloud Storage bucket for storing images and data.
- `NOTION_INTEGRATION_SECRET`, `NOTION_DATABASE_ID`, `NOTION_FOOD_DATABASE_ID`: Create a Notion integration and databases with fields (Title, Category, Content, Created At, Completed). Share the databases with the integration.
- `SERPER_DEV_API_KEY`, `CRAWLBASE_API_KEY`: Obtain these API keys from the respective websites to enable advanced search and data retrieval functionalities.
- `OAUTH_CREDENTIALS_ENCODED`: Base64 encode your Google OAuth credentials and set them here.
- `HOME_ASSISTANT_TOKEN`: The token for authenticating with your Home Assistant instance.
- `HOME_ASSISTANT_URL`: The URL of your Home Assistant instance.
- `HOME_ASSISTANT_AGENT_ID`: The ID of the agent in Home Assistant that will handle the integration.
- `APP_URL`: The base URL of your application, used for OAuth redirects and callbacks.
- `API_SECRET_KEY`: A secure random key used to protect OAuth endpoints. This key must be provided in the x-api-key header when accessing OAuth-related endpoints.

### Additional Configuration

- **Google Cloud Platform Credentials**: Place your `google-credentials.json` file in the project root. This file should contain credentials for your GCP project.
- **Google OAuth Token**: Ensure you have a `credentials.json` file for OAuth to enable Google Calendar integrations. Follow the Google Calendar API documentation to obtain this token.
- **Create a Meta App**: Create an app at [Meta for Developers](https://developers.facebook.com/) to obtain the WhatsApp API credentials, and set up the webhook to your URL.

### Home Assistant Integration

**Configuration**

Add to `configuration.yaml`:

```yaml
rest_command:
  whatsapp_notify:
  url: "https://your-api/send-notification"
  method: POST
  content_type: "application/json"
  payload: >-
    {"message": "{{ message }}"
    {%- if image_url is defined -%}
    , "image_url": "{{ image_url }}"
    {%- endif -%}}
```

**Example Automations**

1. Text Notification

```yaml
automation:
  - alias: "Door Alert"
  trigger:
    - platform: state
    entity_id: binary_sensor.front_door
    to: "on"
  action:
    - service: rest_command.whatsapp_notify
    data:
      message: "Front door opened"
```

2. Camera Notification

```yaml
automation:
  - alias: "Camera Alert"
  trigger:
    - platform: state
    entity_id: binary_sensor.motion_sensor
    to: "on"
  action:
    - service: camera.snapshot
    target:
      entity_id: camera.front_door
    data:
      filename: "/config/www/snapshot.jpg"
    - service: rest_command.whatsapp_notify
    data:
      message: "Motion detected"
      image_url: "https://your-ha-instance.com/local/snapshot.jpg?t={{ now().timestamp() | int }}"
```

### Contributing

Pull requests are welcome. For major changes, please open an issue first.

### Credits

I would like to thank and credit the following repositories from which this project is forked:

- [Meta Glasses Gemini by marcpata](https://github.com/marcpata/meta-glasses-gemini)
- [Meta Glasses Gemini by josancamon19](https://github.com/josancamon19/meta-glasses-gemini)
