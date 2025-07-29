#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Document Embedder for Qdrant Vector Database

This script processes documents in the src directory, creates embeddings using
the configured embedding provider (Ollama, Azure OpenAI, or Google Gemini),
and stores them in Qdrant collections. Each document gets its own collection.

Supported Embedding Providers:
- Ollama: Local embedding models like nomic-embed-text
- Azure OpenAI: Azure's hosted embedding models
- Google Gemini: Google's Gemini embedding models

Configuration is read from config_qdrant_document_manager.ini file which should have sections:
[GENERAL]
embedding_provider = ollama  # Options: ollama, azure, gemini

[OLLAMA]
base_url = http://localhost:11434
embedding_model = nomic-embed-text:v1.5

[AZURE]
api_key = your-api-key
api_base = https://your-endpoint.openai.azure.com
api_version = 2023-05-15
embedding_deployment = text-embedding-ada-002

[GEMINI]
api_key = your-api-key
model_name = models/embedding-001

[QDRANT]
url = http://localhost:6333
api_key = your-api-key-optional

[CHUNKING]
chunk_size = 800
chunk_overlap = 400

[PROCESSING]
src_directory = src
force_recreate = false
"""

import os
import sys
import configparser
from pathlib import Path
from typing import Dict, Any, Optional, Union

# Langchain imports
from langchain.embeddings.base import Embeddings
from langchain_ollama import OllamaEmbeddings
from langchain_community.document_loaders import (
    TextLoader, 
    PyPDFLoader, 
    UnstructuredMarkdownLoader
)
from langchain_community.vectorstores import Qdrant
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Azure imports
from langchain_openai import AzureOpenAIEmbeddings

# Google imports
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Qdrant imports
from qdrant_client import QdrantClient
from qdrant_client.http import models


def _load_config(config_path=None):
    """
    Load configuration from the .ini file.
    
    Args:
        config_path (str, optional): Path to the config file.
        
    Returns:
        dict: Configuration dictionary with all settings
        
    Note:
        If the config file doesn't exist, returns default values.
    """
    config = configparser.ConfigParser()
    
    # Default configuration values
    default_config = {
        "GENERAL": {
            "embedding_provider": "ollama"  # Default to ollama, options: ollama, azure, gemini
        },
        "OLLAMA": {
            "base_url": "http://localhost:11434",
            "embedding_model": "nomic-embed-text:v1.5"
        },
        "AZURE": {
            "api_key": "",
            "api_base": "",
            "api_version": "2023-05-15",
            "embedding_deployment": "text-embedding-ada-002"
        },
        "GEMINI": {
            "api_key": "",
            "model_name": "models/embedding-001"
        },
        "QDRANT": {
            "url": "http://localhost:6333",
            "api_key": ""
        },
        "CHUNKING": {
            "chunk_size": "400",
            "chunk_overlap": "200"
        },
        "PROCESSING": {
            "src_directory": "src",
            "force_recreate": "false"
        }
    }
    
    # If no path provided, use default path relative to the script
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "config_qdrant_doc_manager.ini"
        )
    
    # Try to read the config file
    try:
        if os.path.exists(config_path):
            config.read(config_path)
            print(f"✅ Loaded configuration from: {config_path}")
        else:
            print(f"⚠️ Config file not found at: {config_path}")
            print("   Using default configuration values.")
            
            # Create sections and default values
            for section, values in default_config.items():
                config[section] = values
            
            # Save default config file
            try:
                with open(config_path, 'w') as configfile:
                    config.write(configfile)
                print(f"📝 Created default configuration file at: {config_path}")
            except Exception as e:
                print(f"⚠️ Could not create default config file: {e}")
    except Exception as e:
        print(f"⚠️ Error loading configuration: {e}")
        print("   Using default configuration values.")
        
        # Create sections and default values
        for section, values in default_config.items():
            config[section] = values
    
    # Convert configuration to dictionary
    config_dict = {
        "embedding_provider": config.get("GENERAL", "embedding_provider", fallback=default_config["GENERAL"]["embedding_provider"]).lower(),
        
        # Ollama settings
        "ollama_base_url": config.get("OLLAMA", "base_url", fallback=default_config["OLLAMA"]["base_url"]),
        "ollama_embedding_model": config.get("OLLAMA", "embedding_model", fallback=default_config["OLLAMA"]["embedding_model"]),
        
        # Azure settings
        "azure_api_key": config.get("AZURE", "api_key", fallback=default_config["AZURE"]["api_key"]),
        "azure_api_base": config.get("AZURE", "api_base", fallback=default_config["AZURE"]["api_base"]),
        "azure_api_version": config.get("AZURE", "api_version", fallback=default_config["AZURE"]["api_version"]),
        "azure_embedding_deployment": config.get("AZURE", "embedding_deployment", fallback=default_config["AZURE"]["embedding_deployment"]),
        
        # Gemini settings
        "gemini_api_key": config.get("GEMINI", "api_key", fallback=default_config["GEMINI"]["api_key"]),
        "gemini_model_name": config.get("GEMINI", "model_name", fallback=default_config["GEMINI"]["model_name"]),
        
        # Qdrant settings
        "qdrant_url": config.get("QDRANT", "url", fallback=default_config["QDRANT"]["url"]),
        "qdrant_api_key": config.get("QDRANT", "api_key", fallback=default_config["QDRANT"]["api_key"]) or None,
        
        # Chunking settings
        "chunk_size": config.getint("CHUNKING", "chunk_size", fallback=int(default_config["CHUNKING"]["chunk_size"])),
        "chunk_overlap": config.getint("CHUNKING", "chunk_overlap", fallback=int(default_config["CHUNKING"]["chunk_overlap"])),
        
        # Processing settings
        "src_directory": config.get("PROCESSING", "src_directory", fallback=default_config["PROCESSING"]["src_directory"]),
        "force_recreate": config.getboolean("PROCESSING", "force_recreate", fallback=default_config["PROCESSING"]["force_recreate"] == "true"),
    }
    
    return config_dict

class QdrantDocumentManager:
    """
    A comprehensive document management system for Qdrant Vector Database.
    
    This class provides complete functionality for document processing, embedding generation,
    vector storage, and collection management in Qdrant. It integrates with Ollama for 
    embeddings and supports various document formats (PDF, Markdown, Text, CSV, JSON, XML).
    
    Key Features:
        - Document processing and chunking
        - Embedding generation using Ollama models
        - Qdrant collection management (create, delete, list)
        - Point retrieval and analysis
        - Connection management and testing
        - Batch directory processing
    
    Supported File Formats:
        - PDF (.pdf)
        - Markdown (.md)
        - Text files (.txt)
        - CSV files (.csv)
        - JSON files (.json)
        - XML files (.xml)
    
    Attributes:
        ollama_base_url (str): URL of the Ollama server for embeddings
        qdrant_url (str): URL of the Qdrant vector database server
        qdrant_api_key (str): API key for Qdrant authentication (optional)
        embedding_model (str): Name of the Ollama embedding model
        chunk_size (int): Size of text chunks for processing
        chunk_overlap (int): Overlap between consecutive chunks
        embeddings (OllamaEmbeddings): Initialized embedding model instance
        client (QdrantClient): Qdrant client instance
        text_splitter (RecursiveCharacterTextSplitter): Text chunking utility
    
    Example Usage:
        # Initialize the manager
        manager = QdrantDocumentManager(
            ollama_base_url="http://localhost:11434",
            qdrant_url="http://localhost:6333",
            embedding_model="nomic-embed-text:v1.5"
        )
        
        # Test connection
        if manager.test_connection():
            print("Connected successfully!")
        
        # Process a single document
        success = manager.process_document("/path/to/document.pdf")
        
        # List all collections
        collections = manager.list_collections()
        
        # Get points from a collection
        points = manager.get_collection_points("my_collection", limit=10)
        
        # Process entire directory
        results = manager.process_directory("/path/to/documents/")
    """
    def __init__(
        self, 
        qdrant_url: str = "http://localhost:6333",
        qdrant_api_key: Optional[str] = None,
        embedding_provider: str = "ollama",
        chunk_size: int = 400,
        chunk_overlap: int = 200,
        config_override: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the QdrantDocumentManager.
        
        Args:
            qdrant_url (str, optional): URL of the Qdrant server. Defaults to "http://localhost:6333".
            qdrant_api_key (str, optional): API key for Qdrant authentication. Defaults to None.
            embedding_provider (str, optional): Which embedding provider to use ('ollama', 'azure', or 'gemini'). Defaults to "ollama".
            chunk_size (int, optional): Size of text chunks for processing. Defaults to 400.
            chunk_overlap (int, optional): Overlap between consecutive chunks. Defaults to 200.
            config_override (Dict[str, Any], optional): Override specific config values. Defaults to None.
            
        Returns:
            None: Constructor method, returns instance of QdrantDocumentManager
            
        Example Usage:
            # Basic initialization
            manager = QdrantDocumentManager()
            
            # With Ollama embeddings
            manager = QdrantDocumentManager(
                embedding_provider="ollama",
                qdrant_url="https://my-qdrant-cloud.io:6333",
                qdrant_api_key="your-api-key-here",
                chunk_size=512,
                chunk_overlap=128
            )
            
            # With Azure OpenAI embeddings
            manager = QdrantDocumentManager(
                embedding_provider="azure",
                config_override={
                    "azure_api_key": "your-azure-api-key",
                    "azure_api_base": "https://your-resource-name.openai.azure.com",
                    "azure_embedding_deployment": "your-embedding-deployment-name"
                }
            )
            
            # With Google Gemini embeddings
            manager = QdrantDocumentManager(
                embedding_provider="gemini",
                config_override={"gemini_api_key": "your-gemini-api-key"}
            )
            
        Note:
            Automatically initializes embeddings based on provider and Qdrant client.
            Creates text splitter with specified chunk parameters.
        """
        # Load configuration
        config = _load_config()
        
        # Apply config overrides if provided
        if config_override:
            for key, value in config_override.items():
                config[key] = value
        
        # Set Qdrant parameters
        self.qdrant_url = config.get("qdrant_url", qdrant_url)
        self.qdrant_api_key = config.get("qdrant_api_key", qdrant_api_key)
        self.chunk_size = config.get("chunk_size", chunk_size)
        self.chunk_overlap = config.get("chunk_overlap", chunk_overlap)
        
        # Set embedding provider (use parameter or config file)
        self.embedding_provider = embedding_provider.lower() if embedding_provider else config.get("embedding_provider", "ollama").lower()
        
        # Store all config for reference
        self.config = config
        
        # Initialize embeddings model based on provider
        self.embeddings = self._initialize_embeddings()
        
        # Initialize Qdrant client
        if self.qdrant_api_key:
            self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
        else:
            self.client = QdrantClient(url=self.qdrant_url)
        
        # Text splitter for chunking documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
        )
    
    def _initialize_embeddings(self, provider:str='') -> Embeddings:
        """
        Initialize the appropriate embedding model based on the configured provider.
        
        Returns:
            Embeddings: The initialized embedding model
            
        Raises:
            ValueError: If the embedding provider is not supported or configuration is missing
        """
        if self.embedding_provider == ("ollama" if not provider else provider.lower()):
            # Initialize Ollama embeddings
            ollama_base_url = self.config.get("ollama_base_url")
            ollama_model = self.config.get("ollama_embedding_model")
            
            if not ollama_base_url or not ollama_model:
                raise ValueError("Missing required Ollama configuration: base_url and/or embedding_model")
                
            print(f"🔄 Initializing Ollama embeddings with model: {ollama_model}")
            return OllamaEmbeddings(
                base_url=ollama_base_url,
                model=ollama_model
            )
            
        elif self.embedding_provider == ("azure" if not provider else provider.lower()):
            # Initialize Azure OpenAI embeddings
            azure_api_key = self.config.get("azure_api_key")
            azure_api_base = self.config.get("azure_api_base")
            azure_api_version = self.config.get("azure_api_version")
            azure_deployment = self.config.get("azure_embedding_deployment")
            
            if not azure_api_key or not azure_api_base or not azure_deployment:
                raise ValueError("Missing required Azure configuration: api_key, api_base, and/or embedding_deployment")
                
            try:
                print(f"🔄 Initializing Azure OpenAI embeddings with deployment: {azure_deployment}")
                return AzureOpenAIEmbeddings(
                    azure_deployment=azure_deployment,
                    openai_api_version=azure_api_version,
                    azure_endpoint=azure_api_base,
                    api_key=azure_api_key
                )
            except (ImportError, ModuleNotFoundError):
                raise ImportError("Azure OpenAI embeddings require 'langchain_openai' package. Install with 'pip install langchain_openai'")
                
        elif self.embedding_provider == ("gemini" if not provider else provider.lower()):
            # Initialize Google Gemini embeddings
            gemini_api_key = self.config.get("gemini_api_key")
            gemini_model_name = self.config.get("gemini_model_name")
            
            if not gemini_api_key or not gemini_model_name:
                raise ValueError("Missing required Gemini configuration: api_key and/or model_name")
                
            try:
                print(f"🔄 Initializing Google Gemini embeddings with model: {gemini_model_name}")
                return GoogleGenerativeAIEmbeddings(
                    model=gemini_model_name,
                    google_api_key=gemini_api_key
                )
            except (ImportError, ModuleNotFoundError):
                raise ImportError("Google Gemini embeddings require 'langchain_google_genai' package. Install with 'pip install langchain_google_genai'")
        
        else:
            raise ValueError(f"Unsupported embedding provider: {self.embedding_provider}. Supported options are: 'ollama', 'azure', 'gemini'.")
    
    def _get_loader(self, file_path: str) -> Any:
        """
        Get appropriate document loader based on file extension.
        
        Args:
            file_path (str): Path to the document
            
        Returns:
            Any: Document loader instance (PyPDFLoader, UnstructuredMarkdownLoader, or TextLoader)
            
        Example Return:
            For PDF file: PyPDFLoader('/path/to/document.pdf')
            For Markdown file: UnstructuredMarkdownLoader('/path/to/document.md')
            For text file: TextLoader('/path/to/document.txt')
            
        Raises:
            ValueError: If file extension is not supported
        """
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension == '.pdf':
            return PyPDFLoader(file_path)
        elif file_extension == '.md':
            return UnstructuredMarkdownLoader(file_path)
        elif file_extension in ['.txt', '.csv', '.json', '.xml']:
            return TextLoader(file_path)
        else:
            raise ValueError(f"Unsupported file extension: {file_extension}")
    
    def _get_collection_name(self, file_path: str) -> str:
        """
        Generate a collection name based on the file path.
        
        Args:
            file_path (str): Path to the document
            
        Returns:
            str: Collection name for Qdrant (alphanumeric with underscores)
            
        Example Return:
            Input: '/path/to/my document.pdf'
            Output: 'my_document'
            
            Input: '/data/user-guide_v2.txt'
            Output: 'user_guide_v2'
        """
        # Use the filename without extension as the collection name
        file_name = Path(file_path).stem
        
        # Replace spaces and special characters
        collection_name = ''.join(c if c.isalnum() else '_' for c in file_name)
        
        return collection_name
    
    def _collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists in Qdrant.
        
        Args:
            collection_name (str): Name of the collection to check
            
        Returns:
            bool: True if the collection exists, False otherwise
            
        Example Return:
            True  # Collection 'my_document' exists
            False # Collection 'non_existent' does not exist
            
        Note:
            Returns False if there's an error during the check operation.
        """
        try:
            return self.client.collection_exists(collection_name=collection_name)
        except Exception as e:
            print(f"Error checking if collection exists: {e}")
            return False
    
    def list_collections(self) -> list:
        """
        List all collections in Qdrant.
        
        Returns:
            list: List of collection names as strings
            
        Example Return:
            ['document1', 'user_guide', 'technical_specs', 'meeting_notes']
            
            # Empty database
            []
            
        Note:
            Returns empty list if there's an error or no collections exist.
            Prints collection count and names to console.
        """
        try:
            collections = self.client.get_collections()
            collection_names = [collection.name for collection in collections.collections]
            print(f"Found {len(collection_names)} collections: {collection_names}")
            return collection_names
        except Exception as e:
            print(f"Error listing collections: {e}")
            return []
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a specific collection from Qdrant.
        
        Args:
            collection_name (str): Name of the collection to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
            
        Example Return:
            True  # Collection 'old_docs' successfully deleted
            False # Collection 'non_existent' doesn't exist or deletion failed
            
        Note:
            Returns False if collection doesn't exist or if deletion fails.
            Prints success/failure messages to console.
        """
        try:
            if not self._collection_exists(collection_name):
                print(f"Collection '{collection_name}' does not exist")
                return False
            
            self.client.delete_collection(collection_name=collection_name)
            print(f"Successfully deleted collection: {collection_name}")
            return True
        except Exception as e:
            print(f"Error deleting collection {collection_name}: {e}")
            return False
    
    def update_connection(self, qdrant_url: str = None, qdrant_api_key: str = None) -> bool:
        """
        Update Qdrant connection settings and test the connection.
        
        Args:
            qdrant_url (str, optional): New Qdrant server URL. If None, keeps current URL.
            qdrant_api_key (str, optional): New API key. If None, keeps current key.
            
        Returns:
            bool: True if connection update and test successful, False otherwise
            
        Example Return:
            True  # Successfully updated to new URL and connection tested
            False # Failed to connect with new settings
            
        Note:
            Automatically tests the new connection after updating settings.
            Updates instance variables with new connection parameters.
        """
        try:
            # Update connection parameters if provided
            if qdrant_url:
                self.qdrant_url = qdrant_url
            if qdrant_api_key is not None:  # Allow empty string to remove API key
                self.qdrant_api_key = qdrant_api_key
            
            # Create new client with updated settings
            if self.qdrant_api_key:
                self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
            else:
                self.client = QdrantClient(url=self.qdrant_url)
            
            # Test connection
            return self.test_connection()
        except Exception as e:
            print(f"Error updating connection: {e}")
            return False
            
    def update_embedding_provider(self, 
                                 provider: str,
                                 config_override: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update the embedding provider and related settings.
        
        Args:
            provider (str): New embedding provider ('ollama', 'azure', or 'gemini')
            config_override (Dict[str, Any], optional): Override specific config values. Defaults to None.
            
        Returns:
            bool: True if update successful, False otherwise
            
        Example Return:
            True  # Successfully updated embedding provider
            False # Failed to update provider (invalid provider or missing configuration)
            
        Example Usage:
            # Switch to Azure OpenAI
            manager.update_embedding_provider('azure', {
                'azure_api_key': 'your-api-key',
                'azure_api_base': 'https://your-endpoint.openai.azure.com',
                'azure_embedding_deployment': 'text-embedding-ada-002'
            })
            
            # Switch to Gemini
            manager.update_embedding_provider('gemini', {
                'gemini_api_key': 'your-api-key'
            })
        """
        try:
            # Update provider
            if provider not in ['ollama', 'azure', 'gemini']:
                print(f"Invalid embedding provider: {provider}")
                print("Supported providers: 'ollama', 'azure', 'gemini'")
                return False
            
            self.embedding_provider = provider.lower()
            
            # Apply config overrides if provided
            if config_override:
                for key, value in config_override.items():
                    self.config[key] = value
                    
            # Re-initialize embeddings
            self.embeddings = self._initialize_embeddings(provider=provider)
            print(f"✅ Successfully updated embedding provider to: {self.embedding_provider}")
            return True
        except Exception as e:
            print(f"❌ Error updating embedding provider: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Test the connection to Qdrant server.
        
        Returns:
            bool: True if connection is successful, False otherwise
            
        Example Return:
            True  # Connection successful, server responded
            False # Connection failed, server unreachable or authentication failed
            
        Note:
            Tests connection by attempting to retrieve collections list.
            Prints connection status and collection count to console.
        """
        try:
            # Try to get collections to test connection
            collections = self.client.get_collections()
            print(f"Connection successful! Server has {len(collections.collections)} collections")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def get_collection_points(self, collection_name: str, limit: int = 100, with_payload: bool = True, with_vectors: bool = False) -> list:
        """
        Get points and their payload from a specific collection.
        
        Args:
            collection_name (str): Name of the collection to retrieve points from
            limit (int, optional): Maximum number of points to retrieve. Defaults to 100.
            with_payload (bool, optional): Whether to include payload data. Defaults to True.
            with_vectors (bool, optional): Whether to include vector data. Defaults to False.
            
        Returns:
            list: List of dictionaries containing detailed point data with payload information
            
        Example Return:
            [
                {
                    'id': 'point_123',
                    'payload': {
                        'page_content': 'This is the document content...',
                        'filename': 'document.pdf',
                        'source': '/path/to/document.pdf'
                    },
                    'vector': [0.1, 0.2, 0.3, ...] or None,
                    'vector_dimension': 384 or None,
                    'payload_summary': {
                        'keys': ['page_content', 'filename', 'source'],
                        'content_preview': {
                            'page_content': 'This is the document content...',
                            'filename': 'document.pdf',
                            'source': '/path/to/document.pdf'
                        }
                    }
                },
                {
                    'id': 'point_456',
                    'payload': {...},
                    ...
                }
            ]
            
            # Empty collection or collection doesn't exist
            []
            
        Note:
            Returns empty list if collection doesn't exist or on error.
            Prints detailed summary and sample point structure to console.
        """
        try:
            if not self._collection_exists(collection_name):
                print(f"Collection '{collection_name}' does not exist")
                return []
            
            # Get points from the collection
            points = self.client.scroll(
                collection_name=collection_name,
                limit=limit,
                with_payload=with_payload,
                with_vectors=with_vectors
            )
            
            points_list = points[0]  # First element contains the points
            print(f"Retrieved {len(points_list)} points from collection '{collection_name}'")
            
            # Transform points into detailed dictionaries
            detailed_points = []
            for point in points_list:
                point_data = {
                    'id': point.id,
                    'payload': dict(point.payload) if point.payload else {},
                    'vector': point.vector if with_vectors and point.vector else None,
                    'vector_dimension': len(point.vector) if with_vectors and point.vector else None
                }
                
                # Add detailed payload information
                if point.payload:
                    point_data['payload_summary'] = {
                        'keys': list(point.payload.keys()),
                        'content_preview': {}
                    }
                    
                    # Add preview of payload content (first 100 chars for text fields)
                    for key, value in point.payload.items():
                        if isinstance(value, str):
                            point_data['payload_summary']['content_preview'][key] = (
                                value[:100] + "..." if len(value) > 100 else value
                            )
                        else:
                            point_data['payload_summary']['content_preview'][key] = str(value)
                
                detailed_points.append(point_data)
            
            # Print summary of points
            if detailed_points:
                print(f"Sample point structure:")
                sample_point = detailed_points[0]
                print(f"  - ID: {sample_point['id']}")
                if sample_point['payload']:
                    print(f"  - Payload keys: {sample_point['payload_summary']['keys']}")
                    print(f"  - Content preview available for: {list(sample_point['payload_summary']['content_preview'].keys())}")
                if sample_point['vector_dimension']:
                    print(f"  - Vector dimension: {sample_point['vector_dimension']}")
                
                # Print detailed payload information for first point as example
                if sample_point['payload']:
                    print(f"\n  Detailed payload example (first point):")
                    for key, preview in sample_point['payload_summary']['content_preview'].items():
                        print(f"    - {key}: {preview}")
            
            return detailed_points
        except Exception as e:
            print(f"Error getting points from collection {collection_name}: {e}")
            return []
    
    def get_point_details(self, collection_name: str, point_id: str) -> dict:
        """
        Get detailed information about a specific point.
        
        Args:
            collection_name (str): Name of the collection containing the point
            point_id (str): ID of the specific point to retrieve
            
        Returns:
            dict: Dictionary containing comprehensive point information
            
        Example Return:
            {
                'id': 'point_123',
                'payload': {
                    'page_content': 'This is the full document content that was embedded...',
                    'filename': 'user_manual.pdf',
                    'source': '/documents/user_manual.pdf'
                },
                'vector': [0.123, -0.456, 0.789, ...],  # 384-dimensional vector
                'vector_dimension': 384,
                'payload_analysis': {
                    'total_keys': 3,
                    'key_types': {
                        'page_content': 'str',
                        'filename': 'str', 
                        'source': 'str'
                    },
                    'content_lengths': {
                        'page_content': 1247,
                        'filename': 16,
                        'source': 28
                    },
                    'full_content': {
                        'page_content': 'This is the full document content...',
                        'filename': 'user_manual.pdf',
                        'source': '/documents/user_manual.pdf'
                    }
                }
            }
            
            # Point not found or collection doesn't exist
            {}
            
        Note:
            Returns empty dict if point not found, collection doesn't exist, or on error.
            Includes complete payload analysis with types and content lengths.
        """
        try:
            if not self._collection_exists(collection_name):
                print(f"Collection '{collection_name}' does not exist")
                return {}
            
            # Get specific point
            points = self.client.retrieve(
                collection_name=collection_name,
                ids=[point_id],
                with_payload=True,
                with_vectors=True
            )
            
            if not points:
                print(f"Point with ID '{point_id}' not found in collection '{collection_name}'")
                return {}
            
            point = points[0]
            
            # Create detailed point information
            point_details = {
                'id': point.id,
                'payload': dict(point.payload) if point.payload else {},
                'vector': point.vector if point.vector else None,
                'vector_dimension': len(point.vector) if point.vector else None,
                'payload_analysis': {}
            }
            
            # Analyze payload content
            if point.payload:
                payload_analysis = {
                    'total_keys': len(point.payload),
                    'key_types': {},
                    'content_lengths': {},
                    'full_content': {}
                }
                
                for key, value in point.payload.items():
                    payload_analysis['key_types'][key] = type(value).__name__
                    if isinstance(value, str):
                        payload_analysis['content_lengths'][key] = len(value)
                    payload_analysis['full_content'][key] = value
                
                point_details['payload_analysis'] = payload_analysis
            
            print(f"Retrieved detailed information for point '{point_id}' from collection '{collection_name}'")
            return point_details
            
        except Exception as e:
            print(f"Error getting point details for {point_id} from collection {collection_name}: {e}")
            return {}
    
    def search_similar(self, query: str, collection_name: str, k: int = 3) -> list:
        """
        Search for similar documents in a collection using cosine similarity.
        
        Args:
            query (str): The query text to compare against documents in the collection
            collection_name (str): Name of the collection to search in
            k (int, optional): Number of results to return. Defaults to 3.
            
        Returns:
            list: List of dictionaries containing the top k most similar points with scores
            
        Example Return:
            [
                {
                    'id': 'point_123',
                    'score': 0.89,
                    'payload': {
                        'page_content': 'This is the most similar document content...',
                        'filename': 'document1.pdf',
                        'source': '/path/to/document1.pdf'
                    },
                    'metadata': {
                        'filename': 'document1.pdf',
                        'similarity_score': 0.89
                    }
                },
                {
                    'id': 'point_456',
                    'score': 0.75,
                    'payload': {...},
                    'metadata': {...}
                },
                ...
            ]
            
            # Empty collection or collection doesn't exist or no matches
            []
            
        Note:
            Uses cosine similarity for comparison.
            Returns empty list if collection doesn't exist or on error.
            Prints search results summary to console.
        """
        try:
            if not self._collection_exists(collection_name):
                print(f"Collection '{collection_name}' does not exist")
                return []
            
            print(f"Searching for similar documents to query: '{query[:50]}...' (truncated)" if len(query) > 50 else f"Searching for similar documents to query: '{query}'")
            
            # Generate embeddings for the query
            query_embedding = self.embeddings.embed_query(query)
            
            # Search for similar points in the collection
            search_results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=k,
                with_payload=True
            )
            
            # Transform search results into detailed dictionaries
            result_points = []
            for point in search_results:
                result_point = {
                    'id': point.id,
                    'score': point.score,
                    'payload': dict(point.payload) if point.payload else {},
                    'metadata': {
                        'similarity_score': point.score
                    }
                }
                
                # Add filename to metadata if available
                if point.payload and "filename" in point.payload:
                    result_point['metadata']['filename'] = point.payload["filename"]
                
                result_points.append(result_point)
            
            # Print search results summary
            print(f"Found {len(result_points)} similar documents in collection '{collection_name}'")
            
            if result_points:
                print("Top results:")
                for i, point in enumerate(result_points):
                    content_preview = "N/A"
                    if "page_content" in point['payload']:
                        content = point['payload']['page_content']
                        content_preview = (content[:60] + "...") if len(content) > 60 else content
                    
                    print(f"  {i+1}. Score: {point['score']:.4f}, ID: {point['id']}, Content: {content_preview}")
            
            return result_points
            
        except Exception as e:
            print(f"Error searching similar documents in collection {collection_name}: {e}")
            return []
    
    def process_document(self, file_path: str, force_recreate: bool = False) -> bool:
        """
        Process a document and store it in Qdrant.
        
        Args:
            file_path (str): Path to the document to process
            force_recreate (bool, optional): Whether to recreate the collection if it exists. Defaults to False.
            
        Returns:
            bool: True if document processing was successful, False otherwise
            
        Example Return:
            True  # Document successfully processed and stored in Qdrant
            False # Failed to process document (file not found, unsupported format, etc.)
            
        Process Flow:
            1. Generate collection name from file path
            2. Check if collection exists
            3. Load document using appropriate loader
            4. Split document into chunks
            5. Create embeddings and store in Qdrant
            
        Note:
            Creates a new collection if it doesn't exist.
            Adds filename metadata to each document chunk.
            Prints processing status and chunk count to console.
        """
        try:
            print(f"Processing document: {file_path}")
            
            # Get collection name
            collection_name = self._get_collection_name(file_path)
            
            # Check if collection exists
            collection_exists = self._collection_exists(collection_name)
            
            if collection_exists and not force_recreate:
                print(f"Collection '{collection_name}' already exists. Updating documents...")
            elif collection_exists and force_recreate:
                print(f"Recreating collection '{collection_name}'...")
                self.client.delete_collection(collection_name=collection_name)
                collection_exists = False
            
            # Load the document
            loader = self._get_loader(file_path)
            documents = loader.load()
            
            # Add source information to metadata
            for doc in documents:
                doc.metadata["filename"] = Path(file_path).name
            
            # Split text into chunks
            chunks = self.text_splitter.split_documents(documents)
            
            if not chunks:
                print(f"No content found in document: {file_path}")
                return False
            
            # Get embedding dimensions from the first chunk
            sample_text = chunks[0].page_content
            sample_embedding = self.embeddings.embed_query(sample_text)
            vector_size = len(sample_embedding)
            
            # Create collection if it doesn't exist
            if not collection_exists:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size, 
                        distance=models.Distance.COSINE
                    ),
                )
                print(f"Created collection: {collection_name}")
            
            # Store documents in Qdrant
            Qdrant.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                url=self.qdrant_url,
                collection_name=collection_name,
                api_key=self.qdrant_api_key,
                force_recreate=False  # We handle recreation manually
            )
            
            print(f"Successfully processed document: {file_path}")
            print(f"Created {len(chunks)} chunks in collection '{collection_name}'")
            return True
            
        except Exception as e:
            print(f"Error processing document {file_path}: {e}")
            return False
    
    def process_directory(self, directory_path: str, force_recreate: bool = False) -> Dict[str, bool]:
        """
        Process all documents in a directory.
        
        Args:
            directory_path (str): Path to the directory containing documents
            force_recreate (bool, optional): Whether to recreate collections if they exist. Defaults to False.
            
        Returns:
            Dict[str, bool]: Dictionary mapping file paths to processing success status
            
        Example Return:
            {
                '/docs/manual.pdf': True,
                '/docs/guide.txt': True, 
                '/docs/specs.md': False,
                '/docs/readme.docx': False  # Unsupported format
            }
            
            # Empty directory
            {}
            
        Process Flow:
            1. List all files in the directory
            2. Process each file individually using process_document()
            3. Collect success/failure status for each file
            
        Note:
            Only processes files (ignores subdirectories).
            Continues processing even if individual files fail.
            Prints error messages for failed files.
        """
        results = {}
        
        # Get all files in the directory
        files = [
            os.path.join(directory_path, f) 
            for f in os.listdir(directory_path) 
            if os.path.isfile(os.path.join(directory_path, f))
        ]
        
        # Process each file
        for file_path in files:
            try:
                success = self.process_document(file_path, force_recreate=force_recreate)
                results[file_path] = success
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                results[file_path] = False
        
        return results


def basic_usage_example(config_path=None):
    """
    Basic usage example showing the most common operations.
    
    Args:
        config_path (str, optional): Path to configuration file. If None, uses default path.
    """
    print("🚀 Basic Usage Example")
    print("-" * 30)
    
    # Load configuration from file
    config = _load_config(config_path)
    
    # Initialize manager - the provider is automatically selected based on config
    manager = QdrantDocumentManager(
        qdrant_url=config["qdrant_url"],
        qdrant_api_key=config["qdrant_api_key"],
        embedding_provider=config["embedding_provider"]
    )
    
    # Test connection
    if not manager.test_connection():
        print("❌ Connection failed")
        return
    
    # Process a document
    # success = manager.process_document("/path/to/your/document.pdf")
    # print(f"Document processing: {'✅' if success else '❌'}")
    
    # List collections
    collections = manager.list_collections()
    print(f"Found {len(collections)} collections")
    
    # Get points from a collection (if any exist)
    if collections:
        points = manager.get_collection_points(collections[0], limit=5)
        print(f"Retrieved {len(points)} points")
        
        # Example of similarity search
        print("\n📊 Similarity Search Example")
        print("-" * 30)
        query = "Example search query for similar documents"
        similar_docs = manager.search_similar(
            query=query,
            collection_name=collections[0],
            k=3  # Return top 3 results
        )
        print(f"Found {len(similar_docs)} documents similar to the query.")


if __name__ == "__main__":
    import sys
    import argparse
    
    # Setup argument parser
    parser = argparse.ArgumentParser(description="QdrantDocumentManager - Document processing and vector storage utility")
    parser.add_argument('--basic', action='store_true', help="Run basic usage example")
    parser.add_argument('--config', type=str, help="Path to configuration file", default=None)
    parser.add_argument('--provider', type=str, choices=['ollama', 'azure', 'gemini'], 
                       help="Override the embedding provider specified in the config file")
    
    # Provider-specific arguments
    provider_group = parser.add_argument_group('Embedding Provider Options')
    
    # Ollama options
    ollama_group = provider_group.add_argument_group('Ollama Options')
    ollama_group.add_argument('--ollama-url', type=str, help="Ollama server URL")
    ollama_group.add_argument('--ollama-model', type=str, help="Ollama embedding model name")
    
    # Azure options
    azure_group = provider_group.add_argument_group('Azure Options')
    azure_group.add_argument('--azure-key', type=str, help="Azure OpenAI API key")
    azure_group.add_argument('--azure-base', type=str, help="Azure OpenAI API base URL")
    azure_group.add_argument('--azure-deployment', type=str, help="Azure embedding deployment name")
    
    # Gemini options
    gemini_group = provider_group.add_argument_group('Gemini Options')
    gemini_group.add_argument('--gemini-key', type=str, help="Google Gemini API key")
    gemini_group.add_argument('--gemini-model', type=str, help="Google Gemini embedding model name")
    
    # Parse arguments
    args = parser.parse_args()
    
    if args.basic:
        basic_usage_example(config_path=args.config)
    elif '--help' in sys.argv:
        parser.print_help()
    else:
        # Default behavior - process documents from src directory
        print("🚀 QdrantDocumentManager - Default Document Processing")
        print("-" * 50)
        
        # Load configuration from file
        config = _load_config(args.config)
        
        # Apply command line overrides to config
        config_override = {}
        
        # Override embedding provider if specified
        if args.provider:
            config_override["embedding_provider"] = args.provider
            
        # Override provider-specific settings
        if args.provider == 'ollama' or config.get("embedding_provider") == 'ollama':
            if args.ollama_url:
                config_override["ollama_base_url"] = args.ollama_url
            if args.ollama_model:
                config_override["ollama_embedding_model"] = args.ollama_model
        
        if args.provider == 'azure' or config.get("embedding_provider") == 'azure':
            if args.azure_key:
                config_override["azure_api_key"] = args.azure_key
            if args.azure_base:
                config_override["azure_api_base"] = args.azure_base
            if args.azure_deployment:
                config_override["azure_embedding_deployment"] = args.azure_deployment
        
        if args.provider == 'gemini' or config.get("embedding_provider") == 'gemini':
            if args.gemini_key:
                config_override["gemini_api_key"] = args.gemini_key
            if args.gemini_model:
                config_override["gemini_model_name"] = args.gemini_model
        
        # Apply overrides to config
        for key, value in config_override.items():
            config[key] = value
        
        # Create manager
        manager = QdrantDocumentManager(
            qdrant_url=config["qdrant_url"],
            qdrant_api_key=config["qdrant_api_key"],
            embedding_provider=config["embedding_provider"],
            chunk_size=config["chunk_size"],
            chunk_overlap=config["chunk_overlap"],
            config_override=config_override
        )
        
        # Test connection
        if not manager.test_connection():
            print("❌ Failed to connect to Qdrant. Please check your configuration.")
            sys.exit(1)
        
        # Process documents from src directory
        src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config["src_directory"])
        
        if os.path.exists(src_path):
            print(f"📂 Processing documents from: {src_path}")
            print(f"   Force recreate: {'✓' if config['force_recreate'] else '✗'}")
            results = manager.process_directory(
                directory_path=src_path,
                force_recreate=config["force_recreate"]
            )
            
            # Print summary
            print("\n📊 Processing Summary")
            print("-" * 20)
            success_count = sum(1 for success in results.values() if success)
            print(f"✅ Successfully processed: {success_count}/{len(results)} documents")
            
            if len(results) > success_count:
                print("\n❌ Failed documents:")
                for file_path, success in results.items():
                    if not success:
                        print(f"  - {os.path.basename(file_path)}")
        else:
            print(f"📂 Source directory '{src_path}' not found.")
            print("💡 Use --demo to see the manager in action!")
    ...
