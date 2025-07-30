# 🛡️ AI Security Expert
An interactive AI-powered security analysis platform that conducts comprehensive security interviews and provides tailored security recommendations for technology stacks.

## ✨ Features

- **Interactive Security Interview**: AI-driven 5-question interview process to gather critical security information
- **Comprehensive Analysis**: Detailed security reports with vulnerability assessments and actionable recommendations
- **Multiple Interfaces**: Both FastAPI REST API and Streamlit web interface
- **Session Management**: Track analysis history and maintain conversation context
- **Technology Agnostic**: Supports analysis of web apps, mobile apps, cloud-native stacks, AI/ML applications, and enterprise systems

## 🏗️ Architecture

- **Frontend**: Streamlit web interface with custom styling
- **Backend**: FastAPI REST API with SQLite database
- **AI Engine**: CrewAI framework with Google Gemini LLM
- **Search**: Optional Serper API integration for enhanced research
- **Database**: SQLite for analysis history and session management

## 🚀 Quick Start

### Prerequisites

- Python 3.10-3.13
- Google Gemini API key
- (Optional) Serper API key for enhanced research capabilities

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd security-expert
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   # Create .env file
   echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
   echo "SERPER_API_KEY=your_serper_api_key_here" >> .env  # Optional
   ```

4. **Run the applications**
   
   **Streamlit Interface (Recommended)**:
   ```bash
   streamlit run app.py
   ```
   
   **FastAPI REST API**:
   ```bash
   uvicorn api:app --host 0.0.0.0 --port 8000 --reload
   ```

## 🐳 Docker Deployment

### Dockerfile

The application includes a production-ready Dockerfile:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "api:app", "--bind", "0.0.0.0:8000"]
```

### Build and Run Locally

```bash
# Build the Docker image
docker build -t security-expert .

# Run the container
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key_here security-expert
```

## ☁️ Google Cloud Platform Deployment

### Prerequisites

- Google Cloud SDK installed and configured
- Docker installed locally
- GCP project with billing enabled

### Step-by-Step GCP Deployment

1. **Authenticate with Google Cloud**
   ```bash
   gcloud auth login
   ```

2. **List and set your GCP project**
   ```bash
   gcloud projects list
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Enable required services**
   ```bash
   gcloud services enable cloudbuild.googleapis.com artifactregistry.googleapis.com run.googleapis.com
   ```

4. **Create Artifact Registry repository**
   ```bash
   # Set variables
   $REPO_NAME = "security-expert-repo"
   $REGION = "us-central1"  # Change to your preferred region
   
   # Create repository
   gcloud artifacts repositories create $REPO_NAME `
       --repository-format=docker `
       --location=$REGION `
       --description="Security Expert Docker Repository"
   ```

5. **Build and push Docker image**
   ```bash
   # Get project ID and create image tag
   $PROJECT_ID = $(gcloud config get-value project)
   $IMAGE_TAG = "$($REGION)-docker.pkg.dev/$($PROJECT_ID)/$($REPO_NAME)/security-expert:latest"
   
   # Build and push image to Artifact Registry
   gcloud builds submit --tag $IMAGE_TAG
   ```

6. **Deploy to Cloud Run**
   ```bash
   $SERVICE_NAME = "security-expert-service"
   
   gcloud run deploy $SERVICE_NAME `
       --image=$IMAGE_TAG `
       --platform=managed `
       --region=$REGION `
       --allow-unauthenticated `
       --set-env-vars="GEMINI_API_KEY=your_gemini_api_key_here,SERPER_API_KEY=your_serper_api_key_here" `
       --memory=2Gi `
       --cpu=2 `
       --max-instances=10
   ```

### Alternative Deployment with Environment File

If you prefer to use a `.env` file for environment variables:

```bash
# Deploy with env file
gcloud run deploy $SERVICE_NAME `
    --image=$IMAGE_TAG `
    --platform=managed `
    --region=$REGION `
    --allow-unauthenticated `
    --env-vars-file=.env.yaml
```

Create `.env.yaml`:
```yaml
GEMINI_API_KEY: "your_gemini_api_key_here"
SERPER_API_KEY: "your_serper_api_key_here"
```

### Verify Deployment

After deployment, Cloud Run will provide a service URL. Test your deployment:

```bash
# Get service URL
gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)"

# Test the API
curl https://your-service-url/health
```

## 📚 API Documentation

Once deployed, access the interactive API documentation:

- **Swagger UI**: `https://your-service-url/docs`
- **ReDoc**: `https://your-service-url/redoc`

### Key Endpoints

- `POST /interview/start` - Start security interview
- `POST /interview/continue` - Continue interview process
- `POST /analysis/perform` - Generate security analysis
- `GET /history/{session_id}` - Retrieve analysis history
- `GET /health` - Health check

## 🛠️ Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key for AI processing |
| `SERPER_API_KEY` | No | Serper API key for enhanced web search |

### Database

The application uses SQLite by default. The database file (`security_analysis.db`) is created automatically on first run.

## 🔧 Development

### Project Structure

```
security-expert/
├── src/security_expert/
│   ├── config/
│   │   ├── agents.yaml      # AI agent configurations
│   │   └── tasks.yaml       # Task definitions
│   ├── crew.py              # CrewAI orchestration
│   └── main.py              # CLI entry point
├── api.py                   # FastAPI application
├── app.py                   # Streamlit interface
├── Dockerfile               # Docker configuration
├── requirements.txt         # Python dependencies
├── pyproject.toml          # Project configuration
└── knowledge/              # Knowledge base files
```

### Adding New Features

1. **New AI Agents**: Add configurations to `src/security_expert/config/agents.yaml`
2. **New Tasks**: Define in `src/security_expert/config/tasks.yaml`
3. **API Endpoints**: Extend `api.py` with new FastAPI routes
4. **UI Components**: Modify `app.py` for Streamlit interface changes

## 🧪 Testing

### Local Testing

```bash
# Test the FastAPI application
python -m pytest tests/  # If you have tests

# Manual testing
curl -X POST "http://localhost:8000/interview/start" \
     -H "Content-Type: application/json" \
     -d '{"tech_stack": "React, Node.js, MongoDB"}'
```

### Cloud Testing

```bash
# Test deployed service
curl -X GET "https://your-service-url/health"
```

## 📊 Monitoring and Logging

### Cloud Run Metrics

Monitor your deployment through Google Cloud Console:

1. Navigate to Cloud Run
2. Select your service
3. View metrics: CPU utilization, memory usage, request count, response time

### Logs

View application logs:

```bash
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME" --limit=50
```

## 🔒 Security Considerations

- **API Keys**: Store sensitive keys in Google Secret Manager for production
- **Authentication**: Consider adding authentication for production deployments
- **CORS**: Review CORS settings in `api.py` for production use
- **Rate Limiting**: Implement rate limiting for public APIs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
- Create an issue in the repository
- Check the documentation at `/docs` endpoint
- Review the logs for debugging information
