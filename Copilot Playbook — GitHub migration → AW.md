Copilot Playbook — GitHub migration → AWS deploy using Azure AI Foundry Agents (aligned to ARCHITECTURE.md)

0) Move the codebase to GitHub

Create a private repo sm-assistant → push current project (keep history if you have it).

git init
cat > .gitignore <<'EOF'
node_modules/
.next/
out/
dist/
.venv/
__pycache__/
*.pyc
.terraform/
*.tfstate*
.DS_Store
.idea/
.vscode/
EOF
git add -A
git commit -m "Initial import"
git branch -M main
git remote add origin https://github.com/<org-or-user>/<repo>.git
git push -u origin main

(Optional) set up Git LFS for large binaries.

⸻

1) Repo layout (match the architecture)

sm-assistant/
  frontend/              # Enhanced chat UI (Next.js/React)
  backend/               # FastAPI handlers (mapped to /agents/* and /health)
  infra/terraform/       # S3+CloudFront, API Gateway HTTP API, Lambda, Secrets, (DynamoDB optional)
  README.md
  ARCHITECTURE.md


⸻

2) AWS GitHub OIDC (no long-lived keys)

Create IAM role gha-deploy-scrummaster trusted by token.actions.githubusercontent.com for your repo main branch. Add repo secrets:
	•	AWS_ROLE_TO_ASSUME, AWS_REGION
	•	(after first infra deploy) SITE_BUCKET, CF_DIST_ID

Start with AdministratorAccess then tighten later.

⸻

3) Terraform (infra/terraform)

Provision:
	•	S3 (static website, private) + CloudFront (OAI) for frontend/
	•	API Gateway (HTTP) → Lambda for REST routes
	•	Secrets Manager: azure-ai-foundry-creds
	•	(Optional) DynamoDB conversations for context memory in /agents/*
	•	(Optional) API Gateway WebSocket + Lambda for streaming later

Variables needed:
	•	site_bucket_name, acm_cert_arn, aws_region
	•	azure_tenant_id, azure_client_id, azure_client_secret
	•	azure_agent_base, azure_api_version
	•	Agent IDs to mirror your doc’s agents:
agent_router_id, agent_meeting_id, agent_backlog_id, agent_flow_id, agent_wellness_id
	•	lambda_zip_path

Store all Azure values in Secrets Manager (not in GitHub):
AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET,
AZURE_AGENT_BASE, AZURE_API_VERSION,
AGENT_ROUTER_ID, AGENT_MEETING_ID, AGENT_BACKLOG_ID, AGENT_FLOW_ID, AGENT_WELLNESS_ID.

Outputs:
	•	api_base_url
	•	cloudfront_domain
	•	site_bucket_name
	•	distribution_id

Commit and push Terraform; add CI (.github/workflows/deploy-infra.yml) to run terraform init/plan/apply via OIDC.

⸻

4) Backend (FastAPI) aligned to your endpoints

We’ll deploy FastAPI on AWS Lambda using the AWS Lambda Web Adapter so you keep FastAPI semantics and route names exactly as in ARCHITECTURE.md.

backend/pyproject.toml (or requirements.txt)

fastapi
uvicorn
httpx
boto3
pydantic

backend/app.py (route skeletons mapped to your doc)

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import os, json, time
import httpx
import boto3

app = FastAPI()
secrets_client = boto3.client("secretsmanager")
_cached = {"secrets": None, "token": None, "exp": 0}

class ChatPayload(BaseModel):
    messages: list
    sessionId: str | None = None
    manualAgentKey: str | None = None   # used by /agents/chat
    metadata: dict | None = None

def _get_secrets():
    if _cached["secrets"]:
        return _cached["secrets"]
    sid = os.environ["SECRET_ID"]
    res = secrets_client.get_secret_value(SecretId=sid)
    _cached["secrets"] = json.loads(res["SecretString"])
    return _cached["secrets"]

async def _get_token(secrets):
    now = time.time()
    if _cached["token"] and _cached["exp"] > now + 60:
        return _cached["token"]
    form = {
        "client_id": secrets["AZURE_CLIENT_ID"],
        "client_secret": secrets["AZURE_CLIENT_SECRET"],
        "grant_type": "client_credentials",
        "scope": "https://cognitiveservices.azure.com/.default",
    }
    token_url = f"https://login.microsoftonline.com/{secrets['AZURE_TENANT_ID']}/oauth2/v2.0/token"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(token_url, data=form)
        r.raise_for_status()
        data = r.json()
    _cached["token"] = data["access_token"]
    _cached["exp"] = now + int(data["expires_in"])
    return _cached["token"]

def _agent_id_for_key(key: str, secrets: dict) -> str:
    # Map manual keys in your UI to agent IDs from ARCHITECTURE.md
    mapping = {
        "router": secrets["AGENT_ROUTER_ID"],
        "meeting": secrets["AGENT_MEETING_ID"],
        "backlog": secrets["AGENT_BACKLOG_ID"],
        "flow": secrets["AGENT_FLOW_ID"],
        "wellness": secrets["AGENT_WELLNESS_ID"],
    }
    return mapping[key]

async def _call_agent(agent_id: str, payload: dict, secrets: dict):
    token = await _get_token(secrets)
    base = secrets["AZURE_AGENT_BASE"]  # e.g. https://<hub>.<region>.azure.ai/agents
    api_version = secrets["AZURE_API_VERSION"]
    url = f"{base}/agents/{agent_id}/sessions?api-version={api_version}"
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload)
        # Adjust path/body to the exact Azure AI Foundry Agent op you're using (send message / run).
        # If your agent API exposes a “responses” or “messages” endpoint, modify accordingly.
        if r.status_code >= 400:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()

@app.get("/health")
async def health():
    try:
        secrets = _get_secrets()
        token = await _get_token(secrets)
        return {
            "ok": True,
            "usesAzureAgentService": True,
            "agentIds": {
                "router": secrets.get("AGENT_ROUTER_ID"),
                "meeting": secrets.get("AGENT_MEETING_ID"),
                "backlog": secrets.get("AGENT_BACKLOG_ID"),
                "flow": secrets.get("AGENT_FLOW_ID"),
                "wellness": secrets.get("AGENT_WELLNESS_ID"),
            }
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/agents")
async def list_agents():
    # Surface what UI needs for manual selection
    secrets = _get_secrets()
    return [
        {"key": "meeting", "name": "MeetingIntelligenceAgent", "id": secrets.get("AGENT_MEETING_ID")},
        {"key": "backlog", "name": "BacklogIntelligenceAgent", "id": secrets.get("AGENT_BACKLOG_ID")},
        {"key": "flow", "name": "FlowMetricsAgent", "id": secrets.get("AGENT_FLOW_ID")},
        {"key": "wellness", "name": "TeamWellnessAgent", "id": secrets.get("AGENT_WELLNESS_ID")},
    ]

@app.post("/agents/smart-chat")
async def smart_chat(payload: ChatPayload):
    secrets = _get_secrets()
    # Router agent decides which agent to invoke; simplest: first call router, then dispatch
    router_id = secrets["AGENT_ROUTER_ID"]
    route_result = await _call_agent(router_id, payload.dict(), secrets)
    # parse route_result to select target agent key/id; for now, assume it returns {"target":"meeting"}
    target_key = route_result.get("target", "meeting")
    target_id = _agent_id_for_key(target_key, secrets)
    final = await _call_agent(target_id, payload.dict(), secrets)
    return {"routedTo": target_key, "result": final}

@app.post("/agents/chat")
async def manual_chat(payload: ChatPayload):
    if not payload.manualAgentKey:
        raise HTTPException(400, "manualAgentKey is required")
    secrets = _get_secrets()
    agent_id = _agent_id_for_key(payload.manualAgentKey, secrets)
    result = await _call_agent(agent_id, payload.dict(), secrets)
    return {"agent": payload.manualAgentKey, "result": result}

@app.post("/agents/clear-conversation")
async def clear_conversation(payload: dict):
    # If you use DynamoDB for memory, clear by sessionId here.
    # No-op placeholder for now.
    return {"cleared": True}

Packaging for Lambda (Web Adapter):
	•	Add aws_lambda_powertools or use the Lambda Web Adapter (recommended).
	•	Build a zip with your backend/ code + adapter; set handler to the adapter entrypoint.

Environment variables for Lambda:
	•	SECRET_ID=azure-ai-foundry-creds
	•	(optional) ALLOWED_ORIGIN=https://<your-cloudfront-domain>

⸻

5) Frontend (Next.js) mapped to your endpoints

Calls:
	•	GET /health → show “Connected to Azure Agents” + list agent IDs
	•	GET /agents → populate manual agent dropdown (meeting/backlog/flow/wellness)
	•	POST /agents/smart-chat → Smart mode
	•	POST /agents/chat (with manualAgentKey) → Manual mode
	•	POST /agents/clear-conversation → reset context

frontend/.env.production

NEXT_PUBLIC_API_BASE=https://<api-id>.execute-api.<region>.amazonaws.com

Example client wrapper

export async function apiGet(path: string) {
  const r = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}${path}`, { credentials: "include" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
export async function apiPost(path: string, body: any) {
  const r = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

Render Smart / Manual tabs per your doc; keep continuous conversation history in local state keyed by sessionId. If you enable DynamoDB later, pass sessionId through and reload from the API.

⸻

6) CI/CD workflows (GitHub Actions)

A) .github/workflows/deploy-infra.yml — Terraform apply via OIDC
B) .github/workflows/deploy-backend.yml — package FastAPI + Web Adapter, update Lambda code
C) .github/workflows/deploy-frontend.yml — build Next.js → sync to S3 → CloudFront invalidate

(Use the YAMLs I provided earlier; update names/paths to infra/terraform, backend, and frontend.)

⸻

7) Seed Secrets and First Deploy

Run Terraform once locally (or via workflow with protected env vars) to create Secrets Manager content:

cd infra/terraform
terraform init
terraform apply \
  -var="aws_region=us-west-2" \
  -var="site_bucket_name=<your-site-bucket>" \
  -var="acm_cert_arn=arn:aws:acm:..." \
  -var="azure_tenant_id=..." \
  -var="azure_client_id=..." \
  -var="azure_client_secret=..." \
  -var="azure_agent_base=https://<hub>.<region>.azure.ai/agents" \
  -var="azure_api_version=2024-xx-xx-preview" \
  -var="agent_router_id=<router-id>" \
  -var="agent_meeting_id=<meeting-id>" \
  -var="agent_backlog_id=<backlog-id>" \
  -var="agent_flow_id=<flow-id>" \
  -var="agent_wellness_id=<wellness-id>" \
  -var="lambda_zip_path=../backend.zip"

Then run Deploy Backend and Deploy Frontend workflows.

⸻

8) Verify “AWS UI → Azure Agents” end-to-end
	•	Open the CloudFront site.
	•	GET /health should return { ok: true, usesAzureAgentService: true, agentIds: {...} }.
	•	Try Smart Mode (POST /agents/smart-chat); confirm response includes "routedTo": "<agent>".
	•	Try Manual Mode with manualAgentKey one of: meeting, backlog, flow, wellness.
	•	In CloudWatch Logs, verify outbound call to your Azure Agent endpoint with 200/2xx.

⸻

9) Optional Enhancements
	•	Context memory: add DynamoDB conversations table; /agents/* read/write by sessionId.
	•	Auth: add Cognito authorizer for POST routes; keep GET /health public.
	•	Streaming: later add API Gateway WebSocket and a small WS Lambda; or implement SSE via ALB + Fargate if you want true streaming responses from Azure through your backend.

⸻

Notes that tie back to ARCHITECTURE.md
	•	Endpoints exactly match: /agents/smart-chat, /agents/chat, /agents/clear-conversation, /agents, /health.
	•	“Smart/Manual mode selection” is preserved in UI.
	•	“Continuous conversation history” supported via sessionId now; DynamoDB option aligns with “context memory”.
	•	“API Gateway & Router (FastAPI with WebSocket support)” preserved—FastAPI is kept; WS added later if/when needed.

If you want me to auto-generate the concrete files (FastAPI app, Terraform modules, and the three GitHub Actions workflows) as ready-to-commit PRs, say the word and I’ll produce them exactly with the names/paths above.