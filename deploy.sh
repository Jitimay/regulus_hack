#!/usr/bin/env bash
# Regulus — one-shot deploy script (Cloud Run + Vercel)
# Usage: PROJECT_ID=your-project GEMINI_API_KEY=your-key VERCEL_FRONTEND_URL=https://xxx.vercel.app ./deploy.sh
set -euo pipefail

: "${PROJECT_ID:?Set PROJECT_ID}"
: "${GEMINI_API_KEY:?Set GEMINI_API_KEY}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="regulus-api"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"
SA_EMAIL="${SERVICE_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
FRONTEND_URL="${VERCEL_FRONTEND_URL:-http://localhost:3000}"

echo "==> 1. Setting project"
gcloud config set project "$PROJECT_ID"

echo "==> 2. Enabling APIs"
gcloud services enable \
  run.googleapis.com \
  firestore.googleapis.com \
  pubsub.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  --quiet

echo "==> 3. Firestore (skip if exists)"
gcloud firestore databases create --location="$REGION" --type=firestore-native --quiet 2>/dev/null || true

echo "==> 4. Pub/Sub topic"
gcloud pubsub topics create regulus-runs --quiet 2>/dev/null || true

echo "==> 5. Service account"
gcloud iam service-accounts create "$SERVICE_NAME" \
  --display-name="Regulus Backend" --quiet 2>/dev/null || true

for ROLE in roles/datastore.user roles/pubsub.publisher roles/pubsub.subscriber roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${SA_EMAIL}" --role="$ROLE" --quiet
done

echo "==> 6. Store Gemini API key"
echo -n "$GEMINI_API_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=- --quiet 2>/dev/null || \
  echo -n "$GEMINI_API_KEY" | gcloud secrets versions add GEMINI_API_KEY --data-file=-
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/secretmanager.secretAccessor" --quiet

echo "==> 7. Build container"
cd "$(dirname "$0")/backend"
gcloud builds submit --tag "$IMAGE" . --quiet

echo "==> 8. Deploy to Cloud Run"
gcloud run deploy "$SERVICE_NAME" \
  --image "$IMAGE" \
  --region "$REGION" \
  --service-account "$SA_EMAIL" \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 900 \
  --min-instances 0 \
  --max-instances 5 \
  --set-env-vars "ENVIRONMENT=production" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
  --set-env-vars "GOOGLE_CLOUD_REGION=${REGION}" \
  --set-env-vars "GEMINI_MODEL=gemini-2.5-flash" \
  --set-env-vars "FIRESTORE_DATABASE=(default)" \
  --set-env-vars "PUBSUB_TOPIC=regulus-runs" \
  --set-env-vars "USE_MOCK_RESEARCH=false" \
  --set-env-vars "USE_MOCK_FIRESTORE=false" \
  --set-env-vars "USE_MOCK_PUBSUB=true" \
  --set-env-vars "SIMULATION_COUNT=1000" \
  --set-env-vars "ALLOWED_ORIGIN=${FRONTEND_URL}" \
  --set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest" \
  --quiet

CLOUD_RUN_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --region "$REGION" --format 'value(status.url)')

echo ""
echo "✅ Backend deployed: ${CLOUD_RUN_URL}"
echo "   Health: curl ${CLOUD_RUN_URL}/api/v1/health"
echo ""
echo "==> 9. Frontend — set NEXT_PUBLIC_API_BASE_URL=${CLOUD_RUN_URL} in Vercel dashboard"
echo "   Then: cd frontend && npx vercel deploy --prod"
