#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import configparser
import re
from pathlib import Path
import socket

# Define paths
CURRENT_DIR = Path(__file__).parent
CONFIG_TEMPLATE_DIR = CURRENT_DIR / "ConfigTemplate"
TARGET_CONFIG_DIR = CURRENT_DIR / "MsgCenter" / "config"

# Ensure the target directory exists
os.makedirs(TARGET_CONFIG_DIR, exist_ok=True)

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"{title.center(60)}")
    print("=" * 60 + "\n")

def is_valid_url(url):
    """Validate if the string is a URL."""
    if not url:
        return False
    pattern = re.compile(
        r'^(http|https)://'  # http:// or https://
        r'([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+'  # domain
        r'[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?'  # domain
        r'(:[0-9]+)?'  # optional port
        r'(/[a-zA-Z0-9._~:/?#[\]@!$&\'()*+,;=]*)?$'  # path
    )
    return bool(pattern.match(url))

def is_valid_api_key(api_key):
    """Validate if the string could be an API key."""
    if not api_key:
        return False
    # Most API keys are alphanumeric and at least 20 chars
    return len(api_key) >= 20 and re.match(r'^[A-Za-z0-9\-_]+$', api_key) is not None

def is_valid_mongodb_connection(conn_str):
    """Validate MongoDB connection string."""
    if not conn_str:
        return False
    # Basic pattern for MongoDB connection strings
    pattern = re.compile(
        r'^mongodb(\+srv)?://'  # mongodb:// or mongodb+srv://
    )
    return bool(pattern.match(conn_str))

def is_valid_host(host, port):
    """Check if a host:port is reachable."""
    if not host or not port:
        return False
    try:
        # Convert port to integer
        port = int(port)
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)  # 2 seconds timeout
        # Try to connect
        s.connect((host, port))
        s.close()
        return True
    except (socket.error, ValueError):
        return False
    except Exception:
        return False

def extract_host_port(url):
    """Extract host and port from URL."""
    if not url:
        return None, None
    try:
        # Remove protocol
        if '://' in url:
            url = url.split('://', 1)[1]
        # Split host and path
        host_part = url.split('/', 1)[0]
        # Split host and port
        if ':' in host_part:
            host, port = host_part.rsplit(':', 1)
            return host, int(port)
        else:
            return host_part, 80 if url.startswith('http:') else 443
    except Exception:
        return None, None

def validate_embed_config(config):
    """Validate embedding configuration."""
    issues = []
    
    provider = config.get('GENERAL', 'embedding_provider', fallback='').lower()
    if not provider or provider not in ['ollama', 'azure', 'gemini']:
        issues.append("Invalid or missing embedding provider in [GENERAL] section")
    
    if provider == 'ollama':
        base_url = config.get('OLLAMA', 'base_url', fallback='')
        if not is_valid_url(base_url):
            issues.append("Invalid or missing base_url in [OLLAMA] section")
        else:
            host, port = extract_host_port(base_url)
            if not is_valid_host(host, port):
                issues.append(f"Ollama server at {base_url} is not reachable")
        
        if not config.get('OLLAMA', 'embedding_model', fallback=''):
            issues.append("Missing embedding_model in [OLLAMA] section")
    
    elif provider == 'azure':
        if not is_valid_api_key(config.get('AZURE', 'api_key', fallback='')):
            issues.append("Invalid or missing api_key in [AZURE] section")
        if not is_valid_url(config.get('AZURE', 'api_base', fallback='')):
            issues.append("Invalid or missing api_base in [AZURE] section")
        if not config.get('AZURE', 'embedding_deployment', fallback=''):
            issues.append("Missing embedding_deployment in [AZURE] section")
    
    elif provider == 'gemini':
        if not is_valid_api_key(config.get('GEMINI', 'api_key', fallback='')):
            issues.append("Invalid or missing api_key in [GEMINI] section")
        if not config.get('GEMINI', 'model_name', fallback=''):
            issues.append("Missing model_name in [GEMINI] section")
    
    # Validate Qdrant settings
    qdrant_url = config.get('QDRANT', 'url', fallback='')
    if qdrant_url and not is_valid_url(qdrant_url):
        issues.append("Invalid url in [QDRANT] section")
    
    # Validate chunk settings
    try:
        chunk_size = int(config.get('CHUNKING', 'chunk_size', fallback='0'))
        chunk_overlap = int(config.get('CHUNKING', 'chunk_overlap', fallback='0'))
        if chunk_size <= 0:
            issues.append("Invalid chunk_size in [CHUNKING] section")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            issues.append("Invalid chunk_overlap in [CHUNKING] section")
    except ValueError:
        issues.append("Invalid numeric values in [CHUNKING] section")
    
    return issues

def validate_factory_config(config):
    """Validate factory configuration."""
    issues = []
    
    # Check at least one LLM provider is properly configured
    azure_key = config.get('AzureOpenAI', 'API_KEY', fallback='')
    azure_endpoint = config.get('AzureOpenAI', 'ENDPOINT', fallback='')
    azure_model = config.get('AzureOpenAI', 'MODEL', fallback='')
    
    ollama_host = config.get('Ollama', 'HOST', fallback='')
    ollama_model = config.get('Ollama', 'MODEL', fallback='')
    
    gemini_key = config.get('Gemini', 'API_KEY', fallback='')
    gemini_model = config.get('Gemini', 'MODEL', fallback='')
    
    # Check if at least one provider is properly configured
    azure_valid = (is_valid_api_key(azure_key) and 
                   is_valid_url(azure_endpoint) and 
                   azure_model)
    
    ollama_valid = (is_valid_url(ollama_host) and ollama_model)
    
    gemini_valid = (is_valid_api_key(gemini_key) and gemini_model)
    
    if not (azure_valid or ollama_valid or gemini_valid):
        issues.append("At least one LLM provider must be properly configured")
    
    return issues

def validate_mongodb_config(config):
    """Validate MongoDB configuration."""
    issues = []
    
    conn_str = config.get('Mongodb', 'connection_string', fallback='')
    if not is_valid_mongodb_connection(conn_str):
        issues.append("Invalid or missing MongoDB connection string")
    
    return issues

def validate_rpa_config(config):
    """Validate RPA configuration."""
    issues = []
    
    # Check if at least one messaging platform is configured
    slack_token = config.get('Slack', 'SLACK_BOT_TOKEN', fallback='')
    teams_token = config.get('Teams', 'TEAMS_BOT_TOKEN', fallback='')
    
    if not slack_token and not teams_token:
        issues.append("At least one messaging platform (Slack or Teams) should be configured")
    
    # Validate tokens if provided
    if slack_token and slack_token == 'your_slack_bot_token_here':
        issues.append("Please provide a valid Slack bot token")
        
    if teams_token and teams_token == 'your_teams_bot_token_here':
        issues.append("Please provide a valid Teams bot token")
    
    return issues

def configure_file(template_path, output_path, validator_func):
    """Configure a single file based on its template."""
    if not os.path.exists(template_path):
        print(f"Error: Template file not found: {template_path}")
        return False
    
    # Create a new config file
    config = configparser.ConfigParser()
    
    # Read the example file to get the structure
    with open(template_path, 'r') as f:
        example_content = f.read()
    
    # Parse the example file
    example_config = configparser.ConfigParser()
    example_config.read_string(example_content)
    
    # Copy the structure
    for section in example_config.sections():
        if not config.has_section(section):
            config.add_section(section)
        for key, value in example_config.items(section):
            config.set(section, key, value)
    
    # Get user input for each section and key
    print_header(f"Configuring {os.path.basename(output_path)}")
    print(f"Using template from: {os.path.basename(template_path)}")
    print("Please provide values for the following settings:")
    print("(Press Enter to keep the default/example value in brackets)\n")
    
    for section in config.sections():
        print(f"\n[{section}]")
        for key, value in config.items(section):
            # Skip lines with comments
            if key.startswith('#'):
                continue
                
            prompt = f"{key} [{value}]: "
            user_value = input(prompt).strip()
            
            # If user entered a value, use it; otherwise keep the example value
            if user_value:
                config.set(section, key, user_value)
    
    # Validate the configuration
    issues = validator_func(config)
    if issues:
        print("\nValidation issues found:")
        for issue in issues:
            print(f" - {issue}")
        
        retry = input("\nDo you want to fix these issues? (y/n): ").lower()
        if retry == 'y':
            return configure_file(template_path, output_path, validator_func)
        else:
            save_anyway = input("Save the configuration anyway? (y/n): ").lower()
            if save_anyway != 'y':
                return False
    
    # Save the configuration
    with open(output_path, 'w') as f:
        config.write(f)
    
    print(f"\nConfiguration saved to: {output_path}")
    return True

def initialize_qdrant():
    """Initialize Qdrant database by copying config and running qdrant_embed_local.py."""
    clear_screen()
    print_header("Qdrant Database Initialization")
    
    # Check if embed config exists
    embed_config_path = TARGET_CONFIG_DIR / "config_embed.ini"
    if not os.path.exists(embed_config_path):
        print("Error: config_embed.ini not found. Please configure it first.")
        input("\nPress Enter to continue...")
        return False
    
    # Define Qdrant directory and script path
    qdrant_dir = CURRENT_DIR / "Qrant"
    qdrant_script = qdrant_dir / "qdrant_embed_local.py"
    qdrant_config = qdrant_dir / "config_embed.ini"
    qdrant_src_dir = qdrant_dir / "src"
    
    # Check if Qdrant directory exists
    if not os.path.exists(qdrant_dir):
        print(f"Error: Qdrant directory not found at {qdrant_dir}")
        input("\nPress Enter to continue...")
        return False
    
    # Check if script exists
    if not os.path.exists(qdrant_script):
        print(f"Error: Qdrant script not found at {qdrant_script}")
        input("\nPress Enter to continue...")
        return False
    
    # Check if src directory exists
    if not os.path.exists(qdrant_src_dir):
        print(f"Warning: Source directory not found at {qdrant_src_dir}")
        print("Creating source directory...")
        os.makedirs(qdrant_src_dir, exist_ok=True)
        print("Please place your documents in this directory before continuing.")
        choice = input("\nDo you want to proceed anyway? (y/n): ").lower()
        if choice != 'y':
            print("\nQdrant initialization cancelled.")
            input("\nPress Enter to continue...")
            return False
    else:
        # Check if src directory is empty
        if not os.listdir(qdrant_src_dir):
            print(f"Warning: Source directory {qdrant_src_dir} is empty.")
            print("No documents will be processed.")
            choice = input("\nDo you want to proceed anyway? (y/n): ").lower()
            if choice != 'y':
                print("\nQdrant initialization cancelled.")
                input("\nPress Enter to continue...")
                return False
    
    # Ask for confirmation
    print("\nThis will initialize the Qdrant database with documents in the src directory.")
    print("The process may take some time depending on the number and size of documents.")
    choice = input("\nDo you want to proceed? (y/n): ").lower()
    
    if choice != 'y':
        print("\nQdrant initialization cancelled.")
        input("\nPress Enter to continue...")
        return False
    
    try:
        # Copy config_embed.ini to Qdrant directory
        print("\nCopying configuration to Qdrant directory...")
        shutil.copy2(embed_config_path, qdrant_config)
        
        # Run the qdrant_embed_local.py script
        print("\nInitializing Qdrant database...")
        print("This may take a while. Please wait...")
        
        # Get the current directory to change back to it later
        current_dir = os.getcwd()
        
        # Change to the Qdrant directory to run the script
        os.chdir(qdrant_dir)
        
        # Run the script
        result = os.system(f"{sys.executable} qdrant_embed_local.py")
        
        # Change back to the original directory
        os.chdir(current_dir)
        
        # Check if the script ran successfully
        if result == 0:
            print("\nQdrant database initialized successfully!")
        else:
            print(f"\nError initializing Qdrant database. Exit code: {result}")
        
        # Clean up by removing the copied config file
        if os.path.exists(qdrant_config):
            os.remove(qdrant_config)
            print("\nTemporary configuration file removed.")
        
        input("\nPress Enter to continue...")
        return result == 0
    
    except Exception as e:
        print(f"\nAn error occurred during Qdrant initialization: {e}")
        
        # Clean up if the config file was copied
        if os.path.exists(qdrant_config):
            try:
                os.remove(qdrant_config)
                print("\nTemporary configuration file removed.")
            except:
                pass
        
        input("\nPress Enter to continue...")
        return False

def manual_configuration():
    """Guide user to manually copy and modify configuration templates."""
    clear_screen()
    print_header("Manual Configuration")
    
    print("This option helps you manually create configuration files from templates.")
    print("You will need to copy the template files to the config directory and modify them.")
    
    # List all available template files
    print("\nAvailable configuration templates:")
    for i, template in enumerate(os.listdir(CONFIG_TEMPLATE_DIR), 1):
        if template.endswith('.example'):
            print(f"{i}. {template}")
    
    print("\nFollow these steps to complete the configuration:")
    print("1. Copy the template files from the ConfigTemplate directory to MsgCenter/config")
    print("2. Open each file and modify the settings according to your environment")
    
    # Show paths
    print(f"\nTemplate directory: {CONFIG_TEMPLATE_DIR}")
    print(f"Target directory: {TARGET_CONFIG_DIR}")
    
    # Check if config directory exists, create if not
    if not os.path.exists(TARGET_CONFIG_DIR):
        os.makedirs(TARGET_CONFIG_DIR, exist_ok=True)
        print("\nTarget directory created.")
    
    # Check if config directory is not empty
    existing_configs = []
    if os.path.exists(TARGET_CONFIG_DIR):
        existing_configs = [f for f in os.listdir(TARGET_CONFIG_DIR) if f.endswith('.ini')]
        if existing_configs:
            print("\nWarning: The following configuration files already exist:")
            for i, config_file in enumerate(existing_configs, 1):
                print(f"{i}. {config_file}")
            print("\nProceeding with copy might overwrite these files.")
    
    # Provide options to help with copying
    print("\nWould you like help with copying the template files?")
    print("1. Copy all template files to config directory")
    print("2. Copy specific template file")
    print("3. Return to main menu")
    
    choice = input("\nEnter your choice (1-3): ")
    
    if choice == '1':
        # Copy all template files
        if existing_configs:
            overwrite = input("\nOverwrite existing configuration files? (y/n): ").lower()
            if overwrite != 'y':
                print("\nCopy operation cancelled.")
                input("\nPress Enter to continue...")
                return
        
        copied = 0
        for file in os.listdir(CONFIG_TEMPLATE_DIR):
            if file.endswith('.example'):
                src = os.path.join(CONFIG_TEMPLATE_DIR, file)
                # Create destination path with .ini extension (removing .example)
                dst_name = file.replace('.example', '')
                dst = os.path.join(TARGET_CONFIG_DIR, dst_name)
                
                # Check if file exists
                if os.path.exists(dst) and not (existing_configs and overwrite == 'y'):
                    print(f"Skipping: {dst_name} (already exists)")
                    continue
                
                try:
                    shutil.copy2(src, dst)
                    copied += 1
                    print(f"Copied and renamed: {file} -> {dst_name}")
                except Exception as e:
                    print(f"Error copying {file}: {e}")
        
        print(f"\n{copied} files copied to {TARGET_CONFIG_DIR}")
        print("Please edit these files to configure your settings.")
        
    elif choice == '2':
        # Copy specific file
        print("\nSelect a template file to copy:")
        templates = [f for f in os.listdir(CONFIG_TEMPLATE_DIR) if f.endswith('.example')]
        for i, template in enumerate(templates, 1):
            print(f"{i}. {template}")
        
        try:
            file_choice = int(input("\nEnter file number: "))
            if 1 <= file_choice <= len(templates):
                selected_file = templates[file_choice - 1]
                src = os.path.join(CONFIG_TEMPLATE_DIR, selected_file)
                
                # Create destination path with .ini extension (removing .example)
                dst_name = selected_file.replace('.example', '')
                dst = os.path.join(TARGET_CONFIG_DIR, dst_name)
                
                # Check if file exists
                if os.path.exists(dst):
                    overwrite = input(f"\n{dst_name} already exists. Overwrite? (y/n): ").lower()
                    if overwrite != 'y':
                        print("\nCopy operation cancelled.")
                        input("\nPress Enter to continue...")
                        return
                
                try:
                    shutil.copy2(src, dst)
                    print(f"\nCopied and renamed: {selected_file} -> {dst_name}")
                    print(f"File saved to: {dst}")
                    print("Please edit this file to configure your settings.")
                except Exception as e:
                    print(f"Error copying {selected_file}: {e}")
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    input("\nPress Enter to continue...")

def main():
    clear_screen()
    print_header("GAE252 AI SIEM Configuration Setup")
    
    print("This utility will help you set up configuration files for the AI SIEM system.")
    print("You'll be guided through configuring each required component.")
    
    print("\nWhat would you like to do?")
    print("1. Configure all components")
    print("2. Initialize Qdrant database")
    print("3. Manual configuration (copy templates to config folder)")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ")
    
    if choice == '2':
        initialize_qdrant()
        return
    elif choice == '3':
        manual_configuration()
        return
    elif choice == '4':
        clear_screen()
        print_header("Setup Cancelled")
        print("Thank you for using the GAE252 AI SIEM Configuration Utility.")
        return
    
    input("\nPress Enter to continue with configuration setup...")
    
    # Define configuration mapping (template file, output file, validator function)
    configs = [
        (
            CONFIG_TEMPLATE_DIR / "config_embed.ini.example",
            TARGET_CONFIG_DIR / "config_embed.ini",
            validate_embed_config
        ),
        (
            CONFIG_TEMPLATE_DIR / "config_factory.ini.example",
            TARGET_CONFIG_DIR / "config_factory.ini",
            validate_factory_config
        ),
        (
            CONFIG_TEMPLATE_DIR / "config_mongodb.ini.example",
            TARGET_CONFIG_DIR / "config_mongodb.ini",
            validate_mongodb_config
        ),
        (
            CONFIG_TEMPLATE_DIR / "config_rpa.ini.example",
            TARGET_CONFIG_DIR / "config_rpa.ini",
            validate_rpa_config
        )
    ]
    
    # Process each configuration file
    success_count = 0
    for template_path, output_path, validator_func in configs:
        clear_screen()
        if configure_file(template_path, output_path, validator_func):
            success_count += 1
        input("\nPress Enter to continue...")
    
    # Summary
    clear_screen()
    print_header("Configuration Summary")
    
    if success_count == len(configs):
        print("All configuration files have been successfully created!")
        print(f"Files are located in: {TARGET_CONFIG_DIR}")
    else:
        print(f"Created {success_count} out of {len(configs)} configuration files.")
        print("Some configurations may be incomplete or have validation issues.")
    
    print("\nWhat would you like to do next?")
    print("1. Review all configurations")
    print("2. Initialize Qdrant database")
    print("3. Manual configuration (copy templates to config folder)")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ")
    
    if choice == '1':
        for _, output_path, _ in configs:
            if os.path.exists(output_path):
                clear_screen()
                print_header(f"Review: {os.path.basename(output_path)}")
                
                with open(output_path, 'r') as f:
                    print(f.read())
                
                input("\nPress Enter to continue...")
    elif choice == '2':
        initialize_qdrant()
    elif choice == '3':
        manual_configuration()
    
    clear_screen()
    print_header("Setup Complete")
    print("Thank you for configuring the GAE252 AI SIEM system.")
    print("You can re-run this script at any time to update your configuration.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nConfiguration interrupted. Exiting...")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nAn error occurred: {e}")
        sys.exit(1)
