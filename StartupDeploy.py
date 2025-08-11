import os
import sys
import re
import subprocess

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

def deploy_to_cloud(cloud_provider:str):
    """Deploy to the selected cloud provider."""
    if not check_cloud_cli(cloud_provider):
        return False
        
    if cloud_provider.lower() == 'azure':
        print("Preparing to deploy to Azure...")
        # Placeholder for Azure deployment logic
        # You would typically use Azure CLI commands or Azure SDK here
        print("Azure deployment not implemented yet.")
        return False
        
    elif cloud_provider.lower() == 'gcp':
        print("Preparing to deploy to Google Cloud Platform...")
        # Placeholder for GCP deployment logic
        # You would typically use Google Cloud SDK commands or APIs here
        print("Google Cloud Platform deployment not implemented yet.")
        return False
        
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
                print("1. Azure")
                print("2. Google Cloud Platform (GCP)")
                print("b. Back to main menu")
                
                cloud_choice = input("Enter your choice [1/2/b]: ").strip().lower()
                
                if cloud_choice == '1':
                    deploy_to_cloud('azure')
                    break
                elif cloud_choice == '2':
                    deploy_to_cloud('gcp')
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
