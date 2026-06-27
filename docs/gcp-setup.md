# Google Cloud Setup

This document is the deployment source of truth for the RepoLens MVP architecture:
- Backend on Cloud Run
- Frontend on Firebase Hosting
- Firestore for persisted session/report/cache data
- Secret Manager for API credentials
- Artifact Registry + Cloud Build for CI/CD

## 1) Required Variables

```bash
PROJECT_ID="your-gcp-project-id"
REGION="us-central1"
REPOSITORY="repolens"
SERVICE_NAME="repolens-backend"
FIREBASE_PROJECT_ID="your-firebase-project-id"
OPENAI_SECRET_NAME="openai-api-key"
```

## 2) Enable Services

```bash
gcloud config set project "$PROJECT_ID"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com firestore.googleapis.com firebase.googleapis.com
```

## 3) Bootstrap Data + Registry

Artifact Registry:
```bash
gcloud artifacts repositories create "$REPOSITORY" \
  --repository-format=docker \
  --location="$REGION" \
  --description="RepoLens backend images"
```

Firestore (native mode):
```bash
gcloud firestore databases create --location="$REGION" --type=firestore-native
```

## 4) Secret Manager

Create OpenAI key secret:
```bash
printf "your-openai-key" | gcloud secrets create "$OPENAI_SECRET_NAME" --data-file=-
```

Add new version later:
```bash
printf "your-new-openai-key" | gcloud secrets versions add "$OPENAI_SECRET_NAME" --data-file=-
```

Grant Cloud Run runtime SA access:
```bash
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
RUNTIME_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud secrets add-iam-policy-binding "$OPENAI_SECRET_NAME" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

## 5) Backend Deploy (Cloud Build + Cloud Run)

The repo includes [cloudbuild.backend.yaml](/C:/Users/GIGABYTE/Documents/RepoLens/cloudbuild.backend.yaml) and [backend/Dockerfile](/C:/Users/GIGABYTE/Documents/RepoLens/backend/Dockerfile).

Run:
```bash
gcloud builds submit \
  --config cloudbuild.backend.yaml \
  --substitutions=_REGION="$REGION",_REPOSITORY="$REPOSITORY",_SERVICE_NAME="$SERVICE_NAME",_OPENAI_SECRET="$OPENAI_SECRET_NAME" \
  .
```

## 6) Frontend Deploy (Firebase Hosting + Cloud Build)

Initialize Firebase project mapping once in `.firebaserc` and update project id:
- [.firebaserc](/C:/Users/GIGABYTE/Documents/RepoLens/.firebaserc)
- [firebase.json](/C:/Users/GIGABYTE/Documents/RepoLens/firebase.json)

Create CI token secret:
```bash
# Generate token locally once: firebase login:ci
printf "your-firebase-ci-token" | gcloud secrets create firebase-ci-token --data-file=-
```

Deploy via Cloud Build pipeline [cloudbuild.frontend.yaml](/C:/Users/GIGABYTE/Documents/RepoLens/cloudbuild.frontend.yaml):
```bash
BACKEND_URL="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')"
gcloud builds submit \
  --config cloudbuild.frontend.yaml \
  --substitutions=_FIREBASE_PROJECT_ID="$FIREBASE_PROJECT_ID",_API_BASE_URL="$BACKEND_URL" \
  .
```

## 7) Architecture Notes for Judging

- **Cloud Run** backend is stateless and horizontally scalable.
- **Firebase Hosting** serves static SPA with rewrite routing.
- **Secret Manager** injects sensitive keys at deploy/runtime (no secrets in frontend bundles).
- **Artifact Registry + Cloud Build** provide reproducible image/build pipelines.
- **Firestore** is provisioned for session/report/cache persistence and can be wired without changing deployment topology.

## 8) Recommended Production Tightening

- Use dedicated service accounts for Cloud Run and Cloud Build with least privilege.
- Add Cloud Run min instances and request concurrency tuning.
- Add Cloud Logging dashboards and error-rate alerts.
- Add Firestore TTL/index policies once persistence layer is enabled.
