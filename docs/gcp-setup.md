# Google Cloud Setup

This document captures the manual setup and deployment commands for the RepoLens MVP foundation.

## Variables

Set these environment variables in your shell before running the commands:

```bash
PROJECT_ID="your-gcp-project-id"
PROJECT_NUMBER="your-gcp-project-number"
REGION="us-central1"
REPOSITORY="repolens"
SERVICE_NAME="repolens-backend"
IMAGE_NAME="backend"
FIREBASE_PROJECT_ID="your-firebase-project-id"
GEMINI_SECRET_NAME="gemini-api-key"
```

## Enable Required Services

```bash
gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable firebase.googleapis.com
```

## Create Artifact Registry Repository

```bash
gcloud artifacts repositories create "$REPOSITORY" \
  --repository-format=docker \
  --location="$REGION" \
  --description="RepoLens backend images"
```

## Create Firestore Database

```bash
gcloud firestore databases create \
  --location="$REGION" \
  --type=firestore-native
```

## Create Secret Manager Secret

```bash
printf "your-gemini-api-key" | gcloud secrets create "$GEMINI_SECRET_NAME" --data-file=-
```

To add a new secret version later:

```bash
printf "your-new-gemini-api-key" | gcloud secrets versions add "$GEMINI_SECRET_NAME" --data-file=-
```

## Build and Push the Backend Image

From the repository root:

```bash
gcloud builds submit \
  --tag "$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:latest" \
  ./backend
```

## Deploy the Backend to Cloud Run

```bash
gcloud run deploy "$SERVICE_NAME" \
  --image "$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE_NAME:latest" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-secrets "GEMINI_API_KEY=$GEMINI_SECRET_NAME:latest"
```

## Frontend Setup with Firebase Hosting

Authenticate and link the Firebase project:

```bash
firebase login
firebase use "$FIREBASE_PROJECT_ID"
```

Build and deploy the frontend once dependencies are installed:

```bash
cd frontend
npm install
npm run build
firebase deploy --only hosting
```

## Suggested Firestore Collections

- `repository_profiles`
- `interview_sessions`
- `study_plans`
- `repository_caches`

## Suggested Secret Names

- `gemini-api-key`
- `firebase-service-account-json`

## Deployment Notes

- Keep the backend stateless and session-aware through Firestore.
- Store API keys in Secret Manager rather than frontend configs.
- Add a dedicated service account for Cloud Run before production hardening.
- Add `cloudbuild.yaml`, Dockerfiles, and Firebase config files in the next infrastructure slice if you want repeatable command-free deploys.

