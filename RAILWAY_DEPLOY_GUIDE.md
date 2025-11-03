# SM Assistant - Railway Deployment Guide

## Deploy via Railway Web Interface (Recommended)

1. **Visit**: https://railway.app
2. **Sign up/Login** with GitHub
3. **Click**: "Deploy from GitHub repo"  
4. **Select**: This repository
5. **Set Environment Variables**:
   ```
   AZURE_OPENAI_ENDPOINT = https://your-openai-resource.openai.azure.com/
   AZURE_OPENAI_API_KEY = your-api-key
   AZURE_OPENAI_DEPLOYMENT_NAME = gpt-4.1
   ```
6. **Click**: Deploy

Railway will:
- Automatically detect your Dockerfile
- Build the container
- Deploy both frontend and backend
- Provide a public URL

## Your Environment Variables

Make sure you have these from your Azure OpenAI resource:

```bash
# Find these in Azure Portal → Your OpenAI Resource → Keys and Endpoint
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1  # or whatever your deployment is named
```

## Alternative Platforms

If Railway doesn't work, try these (same GitHub integration):

### Render.com
1. Visit: https://render.com
2. "New Web Service" 
3. Connect GitHub repo
4. Set environment variables
5. Deploy

### Heroku
1. Visit: https://heroku.com
2. Create new app
3. Connect GitHub repo  
4. Set Config Vars (environment variables)
5. Deploy

All three platforms will automatically:
- Detect your Dockerfile
- Build the container
- Deploy your app
- Give you a public URL for demos

The app will be available at: `https://your-app-name.railway.app` (or similar for other platforms)