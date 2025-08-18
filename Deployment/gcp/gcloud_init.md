# Preparing Your Google Cloud Environment for Deployment

This guide will walk you through the necessary steps to prepare your Google Cloud environment for deploying the AI SIEM application using the `StartupDeploy.py` script.

## 1. Install the Google Cloud SDK

If you haven't already, you'll need to install the Google Cloud SDK (which includes the `gcloud` command-line tool). 

Follow the official instructions for your operating system: [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)

## 2. Initialize the gcloud CLI

Once the SDK is installed, you need to initialize it. This will involve logging into your Google Cloud account and selecting a project.

```bash
# This command will open a browser window for you to log in.
gcloud init
```

During the `gcloud init` process, you will be prompted to:
*   Log in with your Google Cloud account.
*   Choose a Google Cloud project to use. If you don't have one, you'll need to create one in the [Google Cloud Console](https://console.cloud.google.com/).
*   Set a default region and zone.

**Important:** Make sure that the project you select has billing enabled.

## 3. Enable Required APIs

The deployment script requires the following APIs to be enabled for your project. You can enable them with the following commands:

```bash
# Enable the Artifact Registry API to store your Docker images
gcloud services enable artifactregistry.googleapis.com

# Enable the Cloud Run API to deploy your services
gcloud services enable run.googleapis.com

# Enable the Cloud Storage API for logging and data storage
gcloud services enable storage.googleapis.com

# Enable the Cloud Build API, which is used by Cloud Run
gcloud services enable cloudbuild.googleapis.com
```

## 4. Verify Your Configuration

After completing the steps above, you can verify your configuration by running:

```bash
# Check your logged-in account
gcloud auth list

# Check your current project configuration
gcloud config list
```

Once you have completed these steps, you are ready to run the `StartupDeploy.py` script to deploy the application to Google Cloud.