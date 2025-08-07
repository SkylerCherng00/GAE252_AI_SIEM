import requests
import json

class MessageCenterClient:
    def __init__(self, base_url="http://localhost:8001"):
        """
        Initialize the Message Center API client
        
        Args:
            base_url (str): The base URL of the Message Center API
        """
        self.base_url = base_url
        self.token = None
    
    def authenticate(self, username, password):
        """
        Authenticate with the API and get an access token
        
        Args:
            username (str): The username
            password (str): The password
            
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        auth_endpoint = f"{self.base_url}/token"
        
        # The OAuth2 token endpoint expects form data
        form_data = {
            "username": username,
            "password": password
        }
        
        try:
            response = requests.post(auth_endpoint, data=form_data)
            response.raise_for_status()
            
            # Save the token for subsequent requests
            token_data = response.json()
            self.token = token_data["access_token"]
            
            print(f"Authentication successful for {username}")
            return True
        
        except requests.exceptions.RequestException as e:
            print(f"Authentication failed: {e}")
            return False
    
    def get_headers(self):
        """Get headers for authenticated requests"""
        if not self.token:
            raise ValueError("Not authenticated. Call authenticate() first.")
        
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def get_embed_config(self):
        """
        Get the complete embed configuration
        
        Returns:
            dict: The embed configuration
        """
        endpoint = f"{self.base_url}/config/embed"
        
        try:
            response = requests.get(endpoint, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"Error getting embed config: {e}")
            return None
    
    def get_embed_config_section(self, section):
        """
        Get a specific section of the embed configuration
        
        Args:
            section (str): The section to retrieve
            
        Returns:
            dict: The configuration section
        """
        endpoint = f"{self.base_url}/config/embed/{section}"
        
        try:
            response = requests.get(endpoint, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"Error getting embed config section: {e}")
            return None
    
    def get_factory_config(self):
        """
        Get the complete factory configuration
        
        Returns:
            dict: The factory configuration
        """
        endpoint = f"{self.base_url}/config/factory"
        
        try:
            response = requests.get(endpoint, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"Error getting factory config: {e}")
            return None
    
    def get_factory_config_section(self, section):
        """
        Get a specific section of the factory configuration
        
        Args:
            section (str): The section to retrieve
            
        Returns:
            dict: The configuration section
        """
        endpoint = f"{self.base_url}/config/factory/{section}"
        
        try:
            response = requests.get(endpoint, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            print(f"Error getting factory config section: {e}")
            return None

# Example usage
if __name__ == "__main__":
    # Create the client
    client = MessageCenterClient("http://localhost:8001")
    
    # Authenticate
    if not client.authenticate("admin", "adminpassword"):
        print("Authentication failed, exiting.")
        exit(1)
    
    # Get configuration data
    print("\nGetting complete embed configuration...")
    embed_config = client.get_embed_config()
    print(json.dumps(embed_config, indent=2))
    
    print("\nGetting OLLAMA section from embed configuration...")
    ollama_config = client.get_embed_config_section("OLLAMA")
    print(json.dumps(ollama_config, indent=2))
    
    print("\nGetting complete factory configuration...")
    factory_config = client.get_factory_config()
    print(json.dumps(factory_config, indent=2))
    
    print("\nGetting AzureOpenAI section from factory configuration...")
    azure_config = client.get_factory_config_section("AzureOpenAI")
    print(json.dumps(azure_config, indent=2))
