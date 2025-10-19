# Test Data for SM Assistant

This folder contains test data for validating the functionality of the SM Assistant's 5 AI agents.

## Folder Structure

### 📋 `backlogs/`
- Sample product backlogs in JSON format
- User story templates and examples
- Backlog refinement scenarios

### 🎤 `meeting_transcripts/`
- Daily standup transcripts
- Sprint planning meeting recordings
- Retrospective meeting notes
- Demo/review session transcripts

### 📝 `user_stories/`
- Well-formatted user stories with acceptance criteria
- Epic breakdown examples
- Story refinement templates

### 💬 `team_communications/`
- Slack/Teams chat exports
- Email threads
- Team sentiment analysis examples

### 📊 `metrics_data/`
- Velocity tracking data
- Cycle time measurements
- Burndown chart data
- Flow metrics examples

## Agent Testing Coverage

Each folder supports specific SM Assistant agents:

- **BacklogIntelligenceAgent**: Uses `backlogs/` and `user_stories/`
- **MeetingIntelligenceAgent**: Uses `meeting_transcripts/`
- **FlowMetricsAgent**: Uses `metrics_data/`
- **TeamWellnessAgent**: Uses `team_communications/`
- **AgileCoachingAgent**: Uses data from all folders for holistic insights

## Usage

1. Add sample data files to appropriate folders
2. Reference these files in agent tests
3. Use for demonstration scenarios
4. Validate agent responses against known test cases

## File Formats

- **JSON**: Structured data (backlogs, metrics)
- **TXT/MD**: Transcripts and communications
- **CSV**: Tabular metrics data