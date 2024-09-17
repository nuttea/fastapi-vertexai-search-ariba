# Fastapi for Vertex AI Search Datastore Retriever

## Prerequisite

- Python 3.10 (check with command "python3.10 --version")
- Google Cloud Project ID with IAM permission to enable services (Agent Builder, Cloud Run, set IAM, create Service Account)
- Install runme extension to run this README.md interactively

## Development

Set up gcloud and environment variables

Google Vertex AI Search Retriver parameters reference
https://python.langchain.com/v0.2/docs/integrations/retrievers/google_vertex_ai_search/

```bash
export PROJECT_ID=[Enter your project id]
echo "PROJECT_ID set to $PROJECT_ID"
```

```bash
VERTEXAI_PROJECT_ID=$PROJECT_ID
LOCATION="us-central1"
SEARCH_ENGINE_ID="gov-way_1725522863016"
DATA_STORE_LOCATION="global"
CLOUDRUN_SA="cloud-run-sa"

set -o allexport
source .env
set +o allexport
```

Authenticate to Google Cloud for login and application default login credential

```bash
gcloud auth login
gcloud config set project $VERTEXAI_PROJECT_ID
gcloud auth application-default login
```

Creat Service Account for Cloud Run

```bash
# Create the service account for Cloud Run
gcloud iam service-accounts create $CLOUDRUN_SA \
    --display-name "Cloud Run Service Account for Vertex AI Search" \
    --project $PROJECT_ID

# Add IAM permission
gcloud projects add-iam-policy-binding --no-user-output-enabled $PROJECT_ID \
    --member serviceAccount:$CLOUDRUN_SA_EMAIL \
    --role roles/storage.objectViewer
gcloud projects add-iam-policy-binding --no-user-output-enabled $PROJECT_ID \
    --member serviceAccount:$CLOUDRUN_SA_EMAIL \
    --role roles/secretmanager.secretAccessor
gcloud projects add-iam-policy-binding --no-user-output-enabled $PROJECT_ID \
    --member serviceAccount:$CLOUDRUN_SA_EMAIL \
    --role roles/discoveryengine.viewer
```

Enable required services

```bash
gcloud services enable aiplatform.googleapis.com --project $PROJECT_ID
gcloud services enable run.googleapis.com --project $PROJECT_ID
gcloud services enable cloudresourcemanager.googleapis.com --project $PROJECT_ID
gcloud services enable discoveryengine.googleapis.com --project $PROJECT_ID
gcloud services enable storage.googleapis.com --project $PROJECT_ID
```

## Testing

Then run app locally, listen on port 8080

You will need to wait until FastAPI completely started and ready to servce requests.


```bash
python3.10 -m venv venv
source venv/bin/activate
#pip install pip-tools
#pip-compile requirements.in
pip install --quiet -r requirements.txt

python main.py
```

You can open FastAPI docs on http://localhost:8080/docs/

Or open Vertex AI Search Widget on http://localhost:8080/

## Deploy to Cloud Run

Deploy to Cloud Run by using current directory as source to build.
Then the built container will deploy to Cloud Run with Required Environment Variables, and attached Service Account created at the beginning.

```bash {"id":"01J1HSJRA7J0D6P6QC6QYZ0VG3"}
gcloud run deploy fastapi-vertexai-search \
  --source . \
  --project $PROJECT_ID \
  --region $LOCATION \
  --allow-unauthenticated \
  --set-env-vars="PROJECT_ID=${PROJECT_ID},LOCATION=${LOCATION},SEARCH_ENGINE_ID=${SEARCH_ENGINE_ID},DATA_STORE_LOCATION=${DATA_STORE_LOCATION}" \
  --service-account $CLOUDRUN_SA_EMAIL 
```