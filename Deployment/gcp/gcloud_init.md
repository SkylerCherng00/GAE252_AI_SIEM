# Initialize gcloud for operating GCP
0. Install gcloud cli
  - ref: https://cloud.google.com/sdk/docs/install-sdk

1. **Authenticate and Enable APIs**
```bash
gcloud auth login
gcloud config set project [your_project_name]

# Authorize the specific api in gcp
gcloud services enable artifactregistry.googleapis.com
```
