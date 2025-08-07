from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import configparser
import os

# Create FastAPI app
app = FastAPI(
    title="Message Center API",
    description="API for accessing configuration information for the AI SIEM system",
    version="1.0.0",
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Define paths to configuration files
CURRENT_DIR = os.path.dirname(__file__)
CONFIG_DIR = os.path.join(CURRENT_DIR, "config")
CONFIG_EMBED_PATH = os.path.join(CONFIG_DIR, "config_embed.ini")
CONFIG_FACTORY_PATH = os.path.join(CONFIG_DIR, "config_factory.ini")
CONFIG_MONGODB_PATH = os.path.join(CONFIG_DIR, "config_mongodb.ini")
CONFIG_RAP_PATH = os.path.join(CONFIG_DIR, "config_rpa.ini")

# Pydantic models for response schemas
class ConfigResponse(BaseModel):
    """Response model for configuration data"""
    section: str
    config: Dict[str, Any]

class AllConfigResponse(BaseModel):
    """Response model for all configuration data from a file"""
    filename: str
    configs: Dict[str, Dict[str, Any]]
    
class ConfigUpdateRequest(BaseModel):
    """Request model for updating a specific section in a config file"""
    section: str
    config: Dict[str, Any]
    
class AllConfigUpdateRequest(BaseModel):
    """Request model for updating multiple sections in a config file"""
    configs: Dict[str, Dict[str, Any]]

def _load_config(config_path: str) -> configparser.ConfigParser:
    """
    Load configuration from an INI file
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        ConfigParser object with loaded configuration
        
    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        configparser.Error: If there's an error parsing the configuration file
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    config = configparser.ConfigParser()
    config.read(config_path)
    return config

def _config_to_dict(config: configparser.ConfigParser) -> Dict[str, Dict[str, Any]]:
    """
    Convert ConfigParser object to a dictionary
    
    Args:
        config: ConfigParser object
        
    Returns:
        Dictionary representation of the configuration
    """
    result = {}
    for section in config.sections():
        result[section] = {}
        for key, value in config[section].items():
            result[section][key] = value
    return result

def _save_config(config_path: str, config_data: Dict[str, Dict[str, Any]]) -> None:
    """
    Save configuration data to an INI file
    
    Args:
        config_path: Path to the configuration file
        config_data: Dictionary containing configuration data
        
    Raises:
        FileNotFoundError: If the directory for the configuration file doesn't exist
        PermissionError: If there's no write permission for the configuration file
    """
    # Create a new ConfigParser object
    config = configparser.ConfigParser()
    
    # Add sections and options from the provided dictionary
    for section, options in config_data.items():
        if not config.has_section(section):
            config.add_section(section)
        for key, value in options.items():
            config[section][key] = str(value)
    
    # Write the configuration to the file
    with open(config_path, 'w') as config_file:
        config.write(config_file)

@app.get("/config/config_embed", response_model=AllConfigResponse)
async def get_config_embed():
    """
    Get all sections from the embedding configuration file
    
    Returns:
        AllConfigResponse with all configuration sections from config_embed.ini
    
    Example Response:
        {
            "filename": "config_embed.ini",
            "configs": {
                "GENERAL": {
                    "embedding_provider": "ollama"
                },
                "OLLAMA": {
                    "base_url": "http://192.168.72.20:11434",
                    "embedding_model": "nomic-embed-text:v1.5"
                },
                ...
            }
        }
    
    Raises:
        HTTPException: If there's an error loading the configuration
    """
    try:
        config = _load_config(CONFIG_EMBED_PATH)
        return {
            "filename": "config_embed.ini",
            "configs": _config_to_dict(config)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading embedding configuration: {str(e)}")

@app.get("/config/config_factory", response_model=AllConfigResponse)
async def get_config_factory():
    """
    Get all sections from the factory configuration file
    
    Returns:
        AllConfigResponse with all configuration sections from config_factory.ini
    
    Example Response:
        {
            "filename": "config_factory.ini",
            "configs": {
                "AzureOpenAI": {
                    "API_KEY": "...",
                    "ENDPOINT": "https://.openai.azure.com/",
                    "VERSION": "2024-10-21",
                    "MODEL": "gpt-4.1"
                },
                ...
            }
        }
    
    Raises:
        HTTPException: If there's an error loading the configuration
    """
    try:
        config = _load_config(CONFIG_FACTORY_PATH)
        return {
            "filename": "config_factory.ini",
            "configs": _config_to_dict(config)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading factory configuration: {str(e)}")

@app.get("/config/config_mongodb", response_model=AllConfigResponse)
async def get_config_mongodb():
    """
    Get MongoDB connection string from the configuration file
    Returns:
        AllConfigResponse with MongoDB connection string from config_mongodb.ini
    Example Response:
        {
            "filename": "config_mongodb.ini",
            "configs": {
                "MONGODB": {
                    "connection_string": "mongodb://localhost:27017"
                }
            }
        }
    Raises:
        HTTPException: If there's an error loading the configuration
    """
    try:
        config = _load_config(CONFIG_MONGODB_PATH)
        return {
            "filename": "config_mongodb.ini",
            "configs": _config_to_dict(config)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading mongodb configuration: {str(e)}")

@app.get("/config/config_rpa", response_model=AllConfigResponse)
async def get_config_rpa():
    """
    Get RPA configuration from the configuration file
    
    Returns:
        AllConfigResponse with RPA configuration from config_rap.ini
    
    Example Response:
        {
            "filename": "config_rpa.ini",
            "configs": {
                "SLACK": {
                    "api_key": "your-rap-api-key",
                },

            }
        }
    
    Raises:
        HTTPException: If there's an error loading the configuration
    """
    try:
        config = _load_config(CONFIG_RAP_PATH)
        print(config)
        return {
            "filename": "config_rap.ini",
            "configs": _config_to_dict(config)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading RAP configuration: {str(e)}")

@app.put("/config/config_embed", response_model=AllConfigResponse, status_code=status.HTTP_200_OK)
async def update_config_embed(request: AllConfigUpdateRequest):
    """
    Update multiple sections in the embedding configuration file
    
    Args:
        request: AllConfigUpdateRequest containing the configuration data to update
        
    Returns:
        AllConfigResponse with the updated configuration
        
    Example Request:
        {
            "configs": {
                "GENERAL": {
                    "embedding_provider": "azure"
                },
                "AZURE": {
                    "api_key": "new-api-key",
                    "endpoint": "https://new-endpoint.openai.azure.com/",
                    "embedding_model": "text-embedding-ada-002"
                }
            }
        }
        
    Raises:
        HTTPException: If there's an error updating the configuration
    """
    try:
        # Load existing config
        config = _load_config(CONFIG_EMBED_PATH)
        current_config = _config_to_dict(config)
        
        # Update with new values
        for section, options in request.configs.items():
            if section not in current_config:
                current_config[section] = {}
            for key, value in options.items():
                current_config[section][key] = value
        
        # Save updated config
        _save_config(CONFIG_EMBED_PATH, current_config)
        
        return {
            "filename": "config_embed.ini",
            "configs": {"status": "updated successfully" if request.configs else "no changes made"}
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error updating embedding configuration: {str(e)}"
        )

@app.put("/config/config_factory", response_model=AllConfigResponse, status_code=status.HTTP_200_OK)
async def update_config_factory(request: AllConfigUpdateRequest):
    """
    Update multiple sections in the factory configuration file
    
    Args:
        request: AllConfigUpdateRequest containing the configuration data to update
        
    Returns:
        AllConfigResponse with the updated configuration
        
    Example Request:
        {
            "configs": {
                "AzureOpenAI": {
                    "API_KEY": "new-api-key",
                    "ENDPOINT": "https://new-endpoint.openai.azure.com/",
                    "VERSION": "2024-10-21",
                    "MODEL": "gpt-4.1"
                },
                "OpenAI": {
                    "API_KEY": "new-openai-key"
                }
            }
        }
        
    Raises:
        HTTPException: If there's an error updating the configuration
    """
    try:
        # Load existing config
        config = _load_config(CONFIG_FACTORY_PATH)
        current_config = _config_to_dict(config)
        
        # Update with new values
        for section, options in request.configs.items():
            if section not in current_config:
                current_config[section] = {}
            for key, value in options.items():
                current_config[section][key] = value
        
        # Save updated config
        _save_config(CONFIG_FACTORY_PATH, current_config)
        
        return {
            "filename": "config_factory.ini",
            "configs": {"status": "updated successfully" if request.configs else "no changes made"}
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error updating factory configuration: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
