# Deploy SM Assistant with Azure AI Foundry

## Quick CloudShell Deployment

1. **Open AWS CloudShell**: https://console.aws.amazon.com/cloudshell/
2. **Upload this folder** to CloudShell (drag & drop the `cloudshell-deploy-package` folder)
3. **Run the deployment**:
   ```bash
   cd cloudshell-deploy-package
   ./deploy.sh
   ```

## What This Does

- Connects your Lambda function to Azure AI Foundry
- Uses your configured agents: SM-Asst-BacklogIntelligence, SM-Asst-MeetingIntelligence, etc.
- Provides real AI responses instead of fallback templates
- Makes your public website behave like your local server

## After Deployment

Your public website will have full Azure AI Foundry capabilities:
- **Web Interface**: https://geekxx.github.io/sm-assistant-web/
- **API Endpoint**: https://7jo7sc6ja4.execute-api.us-east-1.amazonaws.com/prod

Test with any of the 5 agents:
- Backlog Intelligence: User story generation
- Meeting Intelligence: Meeting analysis  
- Flow Metrics: Delivery analytics
- Team Wellness: Sentiment analysis
- Agile Coaching: Strategic guidance
