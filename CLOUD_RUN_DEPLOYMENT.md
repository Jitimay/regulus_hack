# Regulus — Cloud Run Deployment

## Prerequisites

- Google Cloud project with billing enabled
- `gcloud` CLI installed and authenticated
- Docker (for local container build) or Cloud Build

---

## 1. Enable required APIs

```bash
export PROJECT_ID=your-project-id

gcloud config set project $PROJECT_ID

gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  pubsub.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

---

## 2. Create Firestore database

```bash
gcloud firestore databases create \
  --location=us-central1 \
  --type=firestore-native
```

---

## 3. Create Pub/Sub topic and subscription

```bash
gcloud pubsub topics create regulus-runs

gcloud pubsub subscriptions create regulus-runs-sub \
  --topic=regulus-runs \
  --ack-deadline=600
```

---

## 4. Create service account

```bash
gcloud iam service-accounts create regulus-backend \
  --display-name="Regulus Backend Service Account"

export SA_EMAIL=regulus-backend@${PROJECT_ID}.iam.gserviceaccount.com

# Firestore
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/datastore.user"

# Pub/Sub
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/pubsub.subscriber"

# Secret Manager (for production secrets)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

# Gemini / Vertex AI
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user"
```

---

## 5. Store Gemini API key in Secret Manager

```bash
echo -n "your-gemini-api-key" | \
  gcloud secrets create GEMINI_API_KEY \
  --data-file=-

gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"
```

---

## 6. Build and push container

### Using Cloud Build (recommended)

```bash
cd backend

gcloud builds submit \
  --tag gcr.io/${PROJECT_ID}/regulus-api:latest \
  .
```

### Using local Docker

```bash
cd backend

docker build -t gcr.io/${PROJECT_ID}/regulus-api:latest .
docker push gcr.io/${PROJECT_ID}/regulus-api:latest
```

---

## 7. Deploy to Cloud Run

```bash
gcloud run deploy regulus-api \
  --image gcr.io/${PROJECT_ID}/regulus-api:latest \
  --region us-central1 \
  --service-account ${SA_EMAIL} \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 10 \
  --memory 1Gi \
  --cpu 1 \
  --timeout 900 \
  --set-env-vars "ENVIRONMENT=production" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
  --set-env-vars "GOOGLE_CLOUD_REGION=us-central1" \
  --set-env-vars "GEMINI_MODEL=gemini-3.6-flash-exp" \
  --set-env-vars "FIRESTORE_DATABASE=(default)" \
  --set-env-vars "PUBSUB_TOPIC=regulus-runs" \
  --set-env-vars "PUBSUB_SUBSCRIPTION=regulus-runs-sub" \
  --set-env-vars "ALLOWED_ORIGIN=https://your-app.vercel.app" \
  --set-env-vars "SIMULATION_COUNT=2000" \
  --set-env-vars "USE_MOCK_RESEARCH=false" \
  --set-env-vars "USE_MOCK_FIRESTORE=false" \
  --set-env-vars "USE_MOCK_PUBSUB=false"
```

Note the deployed URL from the output — you'll need it for the frontend.

---

## 8. Configure Pub/Sub push delivery

For production, configure Pub/Sub to push messages to your Cloud Run service:

```bash
# Get the Cloud Run URL
CLOUD_RUN_URL=$(gcloud run services describe regulus-api \
  --region us-central1 \
  --format 'value(status.url)')

# Create a push subscription
gcloud pubsub subscriptions delete regulus-runs-sub

gcloud pubsub subscriptions create regulus-runs-sub \
  --topic=regulus-runs \
  --push-endpoint="${CLOUD_RUN_URL}/internal/pubsub/push" \
  --push-auth-service-account=${SA_EMAIL} \
  --ack-deadline=600
```

> **Note:** For the hackathon demo with a single Cloud Run instance, the in-process asyncio queue (`USE_MOCK_PUBSUB=false` + real Pub/Sub) can also be used. The worker is already running inside the same container.

---

## 9. Health check

```bash
CLOUD_RUN_URL=$(gcloud run services describe regulus-api \
  --region us-central1 \
  --format 'value(status.url)')

curl ${CLOUD_RUN_URL}/api/v1/health
# Expected: {"status":"ok","service":"regulus-api"}
```

---

## 10. Smoke test

```bash
curl -s -X POST ${CLOUD_RUN_URL}/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "decision_question": "How should we allocate $50000 for water access?",
    "budget_usd": 50000,
    "communities": [{"name": "Kijani"}, {"name": "Mtoni"}, {"name": "Amani"}],
    "objective": "Maximize reliable water access",
    "interventions": ["solar_pumping", "pump_expansion"],
    "demo_mode": true
  }' | python3 -m json.tool
```

Poll the returned `run_id` until status is `completed`:

```bash
RUN_ID=<run_id from above>

watch -n 2 "curl -s ${CLOUD_RUN_URL}/api/v1/runs/${RUN_ID} | python3 -m json.tool | grep status"
```

---

## Cost estimate (hackathon / demo scale)

| Resource | Estimated cost |
|---|---|
| Cloud Run (1 vCPU, 1GB RAM, ~100 runs) | < $1 |
| Firestore (< 1GB reads/writes) | < $0.10 |
| Pub/Sub (< 1000 messages) | < $0.01 |
| Gemini API (depends on model/tier) | Check current pricing |
| **Total demo** | **< $5** |

---

## Updating the deployment

```bash
cd backend

# Rebuild and push
gcloud builds submit --tag gcr.io/${PROJECT_ID}/regulus-api:latest .

# Redeploy (same env vars retained)
gcloud run deploy regulus-api \
  --image gcr.io/${PROJECT_ID}/regulus-api:latest \
  --region us-central1
```

---

## Troubleshooting

**Run stays in QUEUED** — Worker is not consuming the Pub/Sub message. Check that `USE_MOCK_PUBSUB=false` and the Pub/Sub subscription is correctly configured. For the demo, setting `USE_MOCK_PUBSUB=true` uses the in-process queue which always works.

**Firestore permission denied** — Service account is missing `roles/datastore.user`. Run the IAM binding command from step 4.

**Gemini authentication failed** — The service account needs `roles/aiplatform.user` or a valid API key via Secret Manager.

**CORS errors in browser** — `ALLOWED_ORIGIN` does not match the Vercel domain. Update via `gcloud run services update`.
