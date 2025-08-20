import os
import sys
import re
import subprocess
import shutil
import json

def get_script_directory():
    """Get the directory where the script is located."""
    return os.path.dirname(os.path.abspath(__file__))

def change_to_script_directory():
    """Change the current working directory to the script directory."""
    script_dir = get_script_directory()
    os.chdir(script_dir)
    print(f"Changed working directory to: {script_dir}")

def update_endpoint_file(file_path, old_endpoint, new_endpoint):
    """Update endpoint URL in the specified file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        updated_content = content.replace(old_endpoint, new_endpoint)
        
        if content == updated_content:
            print(f"No changes needed in {file_path}")
            return False
        
        with open(file_path, 'w') as f:
            f.write(updated_content)
            
        print(f"Updated {file_path} with new endpoint: {new_endpoint}")
        return True
    except Exception as e:
        print(f"Error updating {file_path}: {str(e)}")
        return False

def update_local_endpoints():
    """Update endpoints for local testing environment."""
    aiagent_endpoint_path = os.path.join(get_script_directory(), "AIAgent", "utils", "endpoint.py")
    rpa_endpoint_path = os.path.join(get_script_directory(), "Rpa", "endpoint.py")
    
    # Define the expected local endpoints
    local_msgcenter_endpoint = "http://localhost:10000/config/"
    local_rpa_endpoint = "http://localhost:10002/alert"
    
    # Update AIAgent endpoint.py
    with open(aiagent_endpoint_path, 'r') as f:
        content = f.read()
    
    # Check and update AIAgent endpoints
    updated_msg = update_endpoint_file(
        aiagent_endpoint_path,
        re.search(r'endpoint_url\s*=\s*"([^"]+)"', content).group(1),
        local_msgcenter_endpoint
    )
    
    updated_rpa = update_endpoint_file(
        aiagent_endpoint_path,
        re.search(r'endpoint_rpa_url\s*=\s*"([^"]+)"', content).group(1),
        local_rpa_endpoint
    )
    
    # Update Rpa endpoint.py
    with open(rpa_endpoint_path, 'r') as f:
        content = f.read()
    
    updated_rpa_config = update_endpoint_file(
        rpa_endpoint_path,
        re.search(r'endpoint_url\s*=\s*"([^"]+)"', content).group(1),
        local_msgcenter_endpoint
    )
    
    return updated_msg or updated_rpa or updated_rpa_config

def update_docker_endpoints():
    """Update endpoints for docker deployment environment."""
    aiagent_endpoint_path = os.path.join(get_script_directory(), "AIAgent", "utils", "endpoint.py")
    rpa_endpoint_path = os.path.join(get_script_directory(), "Rpa", "endpoint.py")
    
    # Define the docker endpoints based on service names
    docker_msgcenter_endpoint = "http://msgcenter:10000/config/"
    docker_rpa_endpoint = "http://rpa:10002/alert"
    
    # Update AIAgent endpoint.py
    with open(aiagent_endpoint_path, 'r') as f:
        content = f.read()
    
    # Check and update AIAgent endpoints
    updated_msg = update_endpoint_file(
        aiagent_endpoint_path,
        re.search(r'endpoint_url\s*=\s*"([^"]+)"', content).group(1),
        docker_msgcenter_endpoint
    )
    
    updated_rpa = update_endpoint_file(
        aiagent_endpoint_path,
        re.search(r'endpoint_rpa_url\s*=\s*"([^"]+)"', content).group(1),
        docker_rpa_endpoint
    )
    
    # Update Rpa endpoint.py
    with open(rpa_endpoint_path, 'r') as f:
        content = f.read()
    
    updated_rpa_config = update_endpoint_file(
        rpa_endpoint_path,
        re.search(r'endpoint_url\s*=\s*"([^"]+)"', content).group(1),
        docker_msgcenter_endpoint
    )
    
    return updated_msg or updated_rpa or updated_rpa_config

def build_docker_containers():
    """Build and start docker containers using docker-compose."""
    try:
        print("Building and starting Docker containers...")
        subprocess.run(["docker", "compose", "up", "--build", "-d"], check=True)
        print("Docker containers built and started successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error building Docker containers: {str(e)}")
        return False
    except FileNotFoundError as e:
        print(f"Docker or docker compose not found. Please ensure Docker Desktop is installed and running. Error Message: {e}")
        return False

def check_cloud_cli(cloud_provider):
    """Check if the cloud CLI is installed and logged in."""
    try:
        if cloud_provider == 'azure':
            # Check if Azure CLI is installed
            result = subprocess.run(["az", "version"], capture_output=True, text=True)
            if result.returncode != 0:
                print("Azure CLI is not installed. Please install it first.")
                return False
                
            # Check if logged in
            result = subprocess.run(["az", "account", "show"], capture_output=True, text=True)
            if result.returncode != 0:
                print("You are not logged in to Azure. Please run 'az login' first.")
                return False
                
            print("Azure CLI is installed and logged in.")
            return True
            
        elif cloud_provider == 'gcp':
            # Check if Google Cloud CLI is installed
            result = subprocess.run(["gcloud", "version"], capture_output=True, text=True)
            if result.returncode != 0:
                print("Google Cloud SDK is not installed. Please install it first.")
                return False
                
            # Check if logged in
            result = subprocess.run(["gcloud", "auth", "list"], capture_output=True, text=True)
            if "No credentialed accounts." in result.stdout:
                print("You are not logged in to Google Cloud. Please run 'gcloud auth login' first.")
                return False
                
            print("Google Cloud SDK is installed and logged in.")
            return True
        
        else:
            print(f"Unsupported cloud provider: {cloud_provider}")
            return False
            
    except FileNotFoundError:
        print(f"The {cloud_provider} CLI is not installed or not in the PATH.")
        return False

def deploy_to_gcp():
    """Deploy to Google Cloud Platform."""
    print("Preparing to deploy to Google Cloud Platform...")
    print("Ready the images")
    update_local_endpoints()
    subprocess.run(["docker", "compose", "build"])

    repo_name = input("Enter the repository name for Artifact Registry (default: my-repo): ")
    if not repo_name:
        repo_name = "my-repo"
    location = input("Enter the deployment location (default: asia-east1): ")
    if not location:
        location = "asia-east1"

    try:
        project_id = subprocess.check_output(["gcloud", "config", "get-value", "project"]).decode("utf-8").strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Could not get GCP project ID. Make sure you are logged in and have a project set.")
        return False

    print(f"Using project ID: {project_id}")

    # Check if Artifact Registry repository exists
    repo_check_command = [
        "gcloud", "artifacts", "repositories", "describe", repo_name,
        f"--location={location}",
    ]
    repo_check_result = subprocess.run(repo_check_command, capture_output=True, text=True)

    if repo_check_result.returncode == 0:
        print(f"Artifact Registry repository '{repo_name}' already exists in '{location}'.")
    else:
        print(f"Creating Artifact Registry repository '{repo_name}' in '{location}'...")
        subprocess.run(
            [
                "gcloud",
                "artifacts",
                "repositories",
                "create",
                repo_name,
                f"--repository-format=docker",
                f"--location={location}",
                "--description=Docker repo for ai_siem images",
            ],
            check=True,
        )

    services = {
        "agent": "ai_siem/agent_image:1.0.0",
        "msgcenter": "ai_siem/msgcenter_image:1.0.0",
        "rpa": "ai_siem/rpa_image:1.0.0",
    }

    gcr_image_names = {}
    for service_name, image_name in services.items():
        print(f"Processing service: {service_name}")

        # Tag image
        gcr_image_name = f"{location}-docker.pkg.dev/{project_id}/{repo_name}/{image_name.split('/')[1]}"
        gcr_image_names[service_name] = gcr_image_name
        print(f"Tagging image {image_name} as {gcr_image_name}")
        subprocess.run(["docker", "tag", image_name, gcr_image_name], check=True)

        # Push image
        print(f"Pushing image {gcr_image_name}")
        subprocess.run(["docker", "push", gcr_image_name], check=True)

    # Get bucket name and create if not exists
    bucket_name = input("Enter the Cloud Storage bucket name for logs (default: ai-siem-logs): ")
    if not bucket_name:
        bucket_name = "ai-siem-logs"

    bucket_check_command = ["gcloud", "storage", "buckets", "describe", f"gs://{bucket_name}"]
    bucket_check_result = subprocess.run(bucket_check_command, capture_output=True, text=True)

    if bucket_check_result.returncode == 0:
        print(f"Cloud Storage bucket '{bucket_name}' already exists.")
    else:
        print(f"Creating Cloud Storage bucket '{bucket_name}'...")
        subprocess.run(["gcloud", "storage", "buckets", "create", f"gs://{bucket_name}", f"--project={project_id}", f"--location={location}"], check=True)
        print(f"Creating 'data' folder in bucket '{bucket_name}'...")
        with open("empty.txt", "w") as f:
            f.write("")
        subprocess.run(["gcloud", "storage", "cp", "empty.txt", f"gs://{bucket_name}/data/"], check=True)
        os.remove("empty.txt")

    # Check if Cloud Run service exists to get the volume name
    service_check_command = [
        "gcloud", "run", "services", "describe", "ai-siem-service",
        f"--platform=managed", f"--region={location}",
    ]
    service_check_result = subprocess.run(service_check_command, capture_output=True, text=True)

    volume_name = ""
    if service_check_result.returncode == 0:
        print("Cloud Run service 'ai-siem-service' already exists. Querying for volume name.")
        try:
            # Use a different command to get json output
            service_desc_command = [
                "gcloud", "run", "services", "describe", "ai-siem-service",
                f"--platform=managed", f"--region={location}", "--format=json"
            ]
            service_desc_result = subprocess.check_output(service_desc_command)
            service_desc = json.loads(service_desc_result)
            volume_name = service_desc['spec']['template']['spec']['volumes'][0]['name']
            print(f"Found existing volume name: {volume_name}")
        except (subprocess.CalledProcessError, KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"Could not determine existing volume name: {e}. Will generate a new name from the bucket name.")
            pass # Fallback to generating a new name
    
    if not volume_name:
        print("Generating volume name from bucket name.")
        volume_name = f"{bucket_name}-volume"

    print("\nUpdating service.yaml...")
    service_yaml_example_path = os.path.join(get_script_directory(), "Deployment", "gcp", "service.yaml.example")
    service_yaml_path = os.path.join(get_script_directory(), "Deployment", "gcp", "service.yaml")
    shutil.copyfile(service_yaml_example_path, service_yaml_path)
    with open(service_yaml_path, 'r') as f:
        service_yaml = f.read()

    for service_name, gcr_image_name in gcr_image_names.items():
        service_yaml = re.sub(
            f"image:.*{service_name.upper()}",
            f"image: {gcr_image_name}",
            service_yaml
        )
    
    service_yaml = service_yaml.replace("YOUR_BUCKET_NAME", bucket_name)
    service_yaml = service_yaml.replace("YOUR_VOLUME_NAME", volume_name)

    with open(service_yaml_path, 'w') as f:
        f.write(service_yaml)

    # Check if Cloud Run service exists
    service_check_command = [
        "gcloud", "run", "services", "describe", "ai-siem-service",
        f"--platform=managed", f"--region={location}",
    ]
    service_check_result = subprocess.run(service_check_command, capture_output=True, text=True)

    if service_check_result.returncode == 0:
        print("Cloud Run service 'ai-siem-service' already exists. It will be updated.")
    else:
        print("Cloud Run service 'ai-siem-service' does not exist. A new service will be created.")

    print("Deploying to GCP Cloud Run...")
    subprocess.run(
        [
            "gcloud",
            "run",
            "services",
            "replace",
            service_yaml_path,
            f"--region={location}",
        ],
        check=True
    )

    print("\nDeployment to GCP Cloud Run completed successfully.")
    print("Please check the service status on the GCP Cloud Run console.")
    return True

def deploy_to_azure():
    """Deploy to Azure Container Apps."""
    print("Preparing to deploy to Azure...")
    print("Ready the images")
    update_local_endpoints()
    subprocess.run(["docker", "compose", "build"], check=True)

    resource_group = input("Enter the resource group name (default: my-ai-siem-rg): ") or "my-ai-siem-rg"
    location = input("Enter the deployment location (default: eastasia): ") or "eastasia"
    acr_name = input("Enter the Azure Container Registry name (default: myaisiemacr): ") or "myaisiemacr"
    storage_account_name = input("Enter the Azure Storage Account name (default: myaisiemstorage): ") or "myaisiemstorage"
    file_share_name = input("Enter the Azure File Share name (default: ai-siem-logs): ") or "ai-siem-logs"
    container_app_env = f"{resource_group}-env"
    container_app_name = "ai-siem-app"

    # Check if resource group exists
    if subprocess.run(["az", "group", "show", "--name", resource_group], capture_output=True).returncode != 0:
        print(f"Creating resource group '{resource_group}' in '{location}'...")
        subprocess.run(["az", "group", "create", "--name", resource_group, "--location", location], check=True)
    else:
        print(f"Resource group '{resource_group}' already exists.")

    # Check if ACR exists
    if subprocess.run(["az", "acr", "show", "--name", acr_name, "--resource-group", resource_group], capture_output=True).returncode != 0:
        print(f"Creating Azure Container Registry '{acr_name}'...")
        subprocess.run(["az", "acr", "create", "--resource-group", resource_group, "--name", acr_name, "--sku", "Basic", "--admin-enabled", "true"], check=True)
    else:
        print(f"Azure Container Registry '{acr_name}' already exists.")

    # Login to ACR
    print(f"Logging in to Azure Container Registry '{acr_name}'...")
    subprocess.run(["az", "acr", "login", "--name", acr_name], check=True)

    services = {
        "agent": "ai_siem/agent_image:1.0.0",
        "msgcenter": "ai_siem/msgcenter_image:1.0.0",
        "rpa": "ai_siem/rpa_image:1.0.0",
    }
    
    acr_login_server = subprocess.check_output(["az", "acr", "show", "--name", acr_name, "--query", "loginServer", "-o", "tsv"]).decode("utf-8").strip()
    
    acr_image_names = {}
    for service_name, image_name in services.items():
        print(f"Processing service: {service_name}")
        acr_image_name = f"{acr_login_server}/{image_name.split('/')[1]}"
        acr_image_names[service_name] = acr_image_name
        print(f"Tagging image {image_name} as {acr_image_name}")
        subprocess.run(["docker", "tag", image_name, acr_image_name], check=True)
        print(f"Pushing image {acr_image_name}")
        subprocess.run(["docker", "push", acr_image_name], check=True)

    # # Check if storage account exists
    # if subprocess.run(["az", "storage", "account", "show", "--name", storage_account_name, "--resource-group", resource_group], capture_output=True).returncode != 0:
    #     print(f"Creating Azure Storage Account '{storage_account_name}'...")
    #     subprocess.run(["az", "storage", "account", "create", "--name", storage_account_name, "--resource-group", resource_group, "--location", location, "--sku", "Standard_LRS"], check=True)
    # else:
    #     print(f"Azure Storage Account '{storage_account_name}' already exists.")

    # storage_account_key = subprocess.check_output(["az", "storage", "account", "keys", "list", "--resource-group", resource_group, "--account-name", storage_account_name, "--query", "[0].value", "-o", "tsv"]).decode("utf-8").strip()

    # # Check if file share exists
    # if '"exists": false' in subprocess.check_output(["az", "storage", "share", "exists", "--name", file_share_name, "--account-name", storage_account_name, "--account-key", storage_account_key]).decode("utf-8"):
    #     print(f"Creating Azure File Share '{file_share_name}'...")
    #     subprocess.run(["az", "storage", "share", "create", "--name", file_share_name, "--account-name", storage_account_name, "--account-key", storage_account_key], check=True)
    # else:
    #     print(f"Azure File Share '{file_share_name}' already exists.")

    # Create Container App Environment
    # if subprocess.run(["az", "containerapp", "env", "show", "--name", container_app_env, "--resource-group", resource_group], capture_output=True).returncode != 0:
    #     print(f"Creating Container App Environment '{container_app_env}'...")
    #     subprocess.run(["az", "containerapp", "env", "create", "--name", container_app_env, "--resource-group", resource_group, "--location", location], check=True)
    # else:
    #     print(f"Container App Environment '{container_app_env}' already exists.")

    # Create or Update Container App
    print(f"Creating or updating container app '{container_app_name}'...")

  
    return True

def deploy_to_cloud(cloud_provider:str):
    """Deploy to the selected cloud provider."""
    if not check_cloud_cli(cloud_provider):
        return False

    if cloud_provider.lower() == 'azure':
        return deploy_to_azure()

    elif cloud_provider.lower() == 'gcp':
        return deploy_to_gcp()

    return False


def main():
    """Main function for the deployment script."""
    # Ensure we're in the correct directory
    change_to_script_directory()
    
    while True:
        print("\n=== AI SIEM Deployment Tool ===")
        print("Choose deployment environment:")
        print("a. Test (Local)")
        print("b. Docker on-premise")
        print("c. Public Cloud")
        print("q. Quit")
        
        choice = input("Enter your choice [a/b/c/q]: ").strip().lower()
        
        if choice == 'a':
            print("\nPreparing local test environment...")
            if update_local_endpoints():
                print("Local environment endpoints configured successfully.")
            else:
                print("Local environment endpoints were already properly configured.")
                
            print("\nLocal test environment is ready. You can start your services manually.")
            break
            
        elif choice == 'b':
            print("\nPreparing Docker on-premise environment...")
            if update_docker_endpoints():
                print("Docker environment endpoints configured successfully.")
            else:
                print("Docker environment endpoints were already properly configured.")
                
            if build_docker_containers():
                print("\nDocker on-premise environment is up and running.")
            else:
                print("\nFailed to start Docker on-premise environment.")
            break
            
        elif choice == 'c':
            while True:
                print("\nChoose cloud provider:")
                print("1. Google Cloud Platform (GCP)")
                # print("2. Azure")
                print("b. Back to main menu")
                
                # cloud_choice = input("Enter your choice [1/2/b]: ").strip().lower()
                cloud_choice = input("Enter your choice [1/b]: ").strip().lower()
                
                if cloud_choice == '1':
                    deploy_to_cloud('gcp')
                    break
                elif cloud_choice == '2':
                    deploy_to_cloud('azure')
                    break
                elif cloud_choice == 'b':
                    break
                else:
                    print("Invalid choice. Please try again.")
            
            if cloud_choice in ['1', '2']:
                break
                
        elif choice == 'q':
            print("Exiting deployment tool.")
            sys.exit(0)
            
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        sys.exit(1)
