# This Terraform configuration provisions an Azure Container App and related resources
# to replicate a Cloud Run multi-container service.

# Configure the Azure provider. The Azure CLI needs to be authenticated for this to work.
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }

  # This is a sample backend configuration for storing the Terraform state file.
  # It is highly recommended for production environments.
  # Replace "your_storage_account_name", "your_container_name", and "your_state_file_name.tfstate" with your own values.
  # backend "azurerm" {
  #   resource_group_name  = "your-tfstate-rg"
  #   storage_account_name = "yourstorageaccountname"
  #   container_name       = "your-container-name"
  #   key                  = "your-state-file-name.tfstate"
  # }
}

# Provider configuration.
provider "azurerm" {
  features {}
}

# --- Resource Group and Container Registry ---

# Create a resource group to hold all the resources.
# This acts as a logical container for your Azure services.
resource "azurerm_resource_group" "main" {
  name     = "ai-siem-rg"
  location = "East US"
}

# Create an Azure Container Registry to store your Docker images.
# This is the Azure equivalent of Google Artifact Registry.
resource "azurerm_container_registry" "main" {
  name                = "aisiemacr"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true
}

# --- Blob Storage for Volume Mounts ---

# Create an Azure Storage Account. This is required for creating blob containers.
# The `account_tier` and `account_replication_type` are important for performance and redundancy.
resource "azurerm_storage_account" "logs_storage" {
  name                     = "aisiemlogstorage"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# Create a blob container within the storage account.
# This will be mounted into your container app for log storage, similar to your gcsfuse setup.
resource "azurerm_storage_container" "logs_container" {
  name                  = "logs"
  storage_account_name  = azurerm_storage_account.logs_storage.name
  container_access_type = "private"
}

# --- Azure Container App Environment and App ---

# Create a Container App Environment. This is a secure, isolated environment
# where your container apps will run.
resource "azurerm_container_app_environment" "main" {
  name                = "aisiem-env"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_resource_group.main.id # Placeholder; use an actual Log Analytics Workspace ID in production.
}

# Deploy the Azure Container App.
resource "azurerm_container_app" "main" {
  name                         = "ai-siem-service"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  
  # Define the ingress settings for the public-facing service.
  # This corresponds to the HTTP port in your Knative Service.
  ingress {
    external_enabled = true
    target_port      = 10001
  }

  # Define the template for the container app, including the containers and their settings.
  template {
    # Set the container concurrency to 20, as defined in your Cloud Run spec.
    max_concurrent_requests = 20
    
    # Set the replica timeout, which maps to the Knative timeoutSeconds.
    replica_timeout_in_seconds = 300
    
    # Define the container for the 'agent' service.
    container {
      name    = "agent"
      image   = "${azurerm_container_registry.main.login_server}/your_image_name_on_acr_agent"
      cpu     = 1
      memory  = "1Gi" # Note: Azure Container Apps memory is in GiB. 512Mi is 0.5GiB, but 1GiB is the minimum for 1 CPU core.
      
      # Expose the container port.
      ports {
        name   = "http"
        internal = true
        container_port = 10001
      }

      # Mount the storage volume to the specified path.
      volume_mounts {
        name       = "logs-volume"
        mount_path = "/app/logs"
      }
    }

    # Define the container for the 'msgcenter' service.
    container {
      name   = "msgcenter"
      image  = "${azurerm_container_registry.main.login_server}/your_image_name_on_acr_msgcenter"
      cpu    = 1
      memory = "1Gi" # Note: 128Mi is 0.125GiB, but 1GiB is the minimum for 1 CPU core.
    }

    # Define the container for the 'rpa' service.
    container {
      name   = "rpa"
      image  = "${azurerm_container_registry.main.login_server}/your_image_name_on_acr_rpa"
      cpu    = 1
      memory = "1Gi" # Note: 128Mi is 0.125GiB, but 1GiB is the minimum for 1 CPU core.
    }
    
    # Define the volume that will be mounted.
    # This connects the blob storage to the volume mount in the container.
    volume {
      name       = "logs-volume"
      storage_type = "AzureFile" # Use AzureFile as a proxy for the gcsfuse behavior. Azure Blob doesn't have a direct mount driver.
      storage_name = azurerm_storage_account.logs_storage.name
      access_key   = azurerm_storage_account.logs_storage.primary_access_key
      share_name = azurerm_storage_container.logs_container.name
    }
  }
}
