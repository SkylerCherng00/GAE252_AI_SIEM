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

Configuration is read from config_qdrant_document_manager.ini file
"""

import os
import requests
from pathlib import Path
from typing import Dict, Any, Optional

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

# Change the working directory to the project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# HTTP Endpoint
CONFIG_URL = "http://localhost:10000/config/config_embed"

class QdrantDocManager:
    """
    A manager class for handling document processing, embedding, and storage in Qdrant.
    
    This class provides functionality to:
    - Process documents and store their embeddings in Qdrant collections
    - Search for similar documents using semantic search
    - Manage Qdrant collections and connection settings
    - Support multiple embedding providers (Ollama, Azure OpenAI, Google Gemini)
    
    Attributes:
        config (configparser.ConfigParser): Configuration parser for settings
        embeddings (Embeddings): The embedding model used for vectorization
        client (QdrantClient): Client for interacting with Qdrant
        text_splitter (RecursiveCharacterTextSplitter): Splitter for document chunking
    """

    def __init__(self):
        """
        Initialize the QdrantDocManager with configuration.
        
        Args:
            config_url (str, optional): URL to fetch configuration from.
                If provided, fetches configuration from URL instead of file.
        """
        try:
            # Fetch configuration from HTTP endpoint
            response = requests.get(CONFIG_URL, timeout=5)
            if response.status_code == 200:
                self.config = response.json().get('configs')
                print(f"✅ Configuration loaded from API: {CONFIG_URL}")
                
                # Initialize with the API config
                self._initialize_from_config()
            else:
                print(f"❌ Failed to fetch configuration from API: {response.status_code}")
        except Exception as e:
            print(f"❌ Error fetching configuration from API: {e}")
    
    def _initialize_from_config(self):
        """
        Initialize all required attributes from the loaded configuration.
        This is called after loading config from either file or API.
        """
        # Set up instance properties from config
        self.embedding_provider = self.config.get('GENERAL',0).get('embedding_provider', 'ollama')
        self.qdrant_url = self.config.get('QDRANT',0).get('url', 'http://localhost:6333')
        self.qdrant_api_key = self.config.get('QDRANT',0).get('api_key', '')
        self.chunk_size = int(self.config.get('CHUNKING',0).get('chunk_size', 400))
        self.chunk_overlap = int(self.config.get('CHUNKING',0).get('chunk_overlap', 200))
        
        # Initialize embeddings model based on provider
        self.embeddings = self._initialize_embeddings()
        
        # Initialize Qdrant client
        if self.qdrant_api_key:
            self.qdrant_client = QdrantClient(self.qdrant_url, api_key=self.qdrant_api_key)
        else:
            self.qdrant_client = QdrantClient(self.qdrant_url)
        
        # Text splitter for chunking documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
        )
     
    def _initialize_embeddings(self, provider: str = '') -> Embeddings:
        """
        Initialize the embeddings model based on the configured provider.
        
        This method sets up the appropriate embedding model based on the 
        configuration settings. It supports three embedding providers:
        - Ollama: Local embedding models
        - Azure OpenAI: Azure's hosted embedding models
        - Google Gemini: Google's Gemini embedding models
        
        Args:
            provider (str, optional): Override the configured provider.
                If provided, this overrides the provider in config.
                
        Returns:
            Embeddings: The initialized embedding model
            
        Raises:
            ValueError: If the provider is invalid or required configuration is missing
            ImportError: If required packages for Azure or Gemini are missing
        """
        if not provider:
            provider = self.embedding_provider
            
        if provider == "ollama":
            # Initialize Ollama embeddings
            ollama_base_url = self.config.get("OLLAMA",0).get("base_url", "http://localhost:11434")
            ollama_model = self.config.get("OLLAMA",0).get("embedding_model", "nomic-embed-text")
            
            if not ollama_base_url or not ollama_model:
                raise ValueError("Missing required Ollama configuration: base_url and/or embedding_model")
                
            print(f"🔄 Initializing Ollama embeddings with model: {ollama_model}")
            return OllamaEmbeddings(
                base_url=ollama_base_url,
                model=ollama_model
            )
            
        elif provider == "azure":
            # Initialize Azure OpenAI embeddings
            azure_api_key = self.config.get("AZURE",0).get("api_key", "")
            azure_api_base = self.config.get("AZURE",0).get("api_base", "")
            azure_api_version = self.config.get("AZURE",0).get("api_version", "2023-05-15")
            azure_deployment = self.config.get("AZURE",0).get("embedding_deployment", "")
            
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
                
        elif provider == "gemini":
            # Initialize Google Gemini embeddings
            gemini_api_key = self.config.get("GEMINI",0).get("api_key", "")
            gemini_model_name = self.config.get("GEMINI",0).get("model_name", "models/embedding-001")
            
            if not gemini_api_key or not gemini_model_name:
                raise ValueError("Missing required Gemini configuration: api_key and/or model_name")
                
            try:
                print(f"🔄 Initializing Google Gemini embeddings with model: {gemini_model_name}")
                return GoogleGenerativeAIEmbeddings(
                    model=gemini_model_name,
                    google_api_key=gemini_api_key,
                    output_dimensionality=self.config.getint("GEMINI",0).get("output_dimensionality", 768)
                )
            except (ImportError, ModuleNotFoundError):
                raise ImportError("Google Gemini embeddings require 'langchain_google_genai' package. Install with 'pip install langchain_google_genai'")
        
        else:
            raise ValueError(f"Unsupported embedding provider: {self.embedding_provider}. Supported options are: 'ollama', 'azure', 'gemini'.")
    
    def _get_loader(self, file_path: str) -> Any:
        """
        Get the appropriate document loader based on file extension.
        
        Args:
            file_path (str): Path to the file to load
            
        Returns:
            Any: An initialized document loader for the specific file type
            
        Raises:
            ValueError: If the file extension is not supported
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
        Generate a valid Qdrant collection name from a file path.
        
        Args:
            file_path (str): Path to the file
            
        Returns:
            str: A valid collection name derived from the filename
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
        """
        try:
            return self.qdrant_client.collection_exists(collection_name=collection_name)
        except Exception as e:
            print(f"Error checking if collection exists: {e}")
            return False
    
    def list_collections(self) -> list:
        """
        List all available collections in the Qdrant database.
        
        Returns:
            list: List of collection names
        """
        try:
            collections = self.qdrant_client.get_collections()
            collection_names = [collection.name for collection in collections.collections]
            print(f"Found {len(collection_names)} collections: {collection_names}")
            return collection_names
        except Exception as e:
            print(f"Error listing collections: {e}")
            return []
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection from Qdrant.
        
        Args:
            collection_name (str): Name of the collection to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            if not self._collection_exists(collection_name):
                print(f"Collection '{collection_name}' does not exist")
                return False
            
            self.qdrant_client.delete_collection(collection_name=collection_name)
            print(f"Successfully deleted collection: {collection_name}")
            return True
        except Exception as e:
            print(f"Error deleting collection {collection_name}: {e}")
            return False
    
    def update_connection(self, qdrant_url: str = None, qdrant_api_key: str = None) -> bool:
        """
        Update the Qdrant connection parameters and reconnect.
        
        Args:
            qdrant_url (str, optional): New Qdrant server URL
            qdrant_api_key (str, optional): New Qdrant API key
            
        Returns:
            bool: True if connection update was successful, False otherwise
        """
        try:
            # Update connection parameters if provided
            if qdrant_url:
                self.qdrant_url = qdrant_url
            if qdrant_api_key is not None:  # Allow empty string to remove API key
                self.qdrant_api_key = qdrant_api_key
            
            # Create new client with updated settings
            if self.qdrant_api_key:
                self.qdrant_client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
            else:
                self.qdrant_client = QdrantClient(url=self.qdrant_url)
            
            # Test connection
            return self.test_connection()
        except Exception as e:
            print(f"Error updating connection: {e}")
            return False
            
    def update_embedding_provider(self, 
                                 provider: str,
                                 config_override: Optional[Dict[str, Any]] = None) -> bool:
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
            
    def refresh_config_from_api(self, config_url: str = CONFIG_URL) -> bool:
        """
        Refresh configuration by fetching the latest from the API endpoint.
        
        Args:
            config_url (str, optional): URL to fetch configuration from.
                Default is "http://localhost:10000/config/config_embed".
                
        Returns:
            bool: True if configuration was successfully refreshed, False otherwise.
        """
        try:
            # Fetch configuration from HTTP endpoint
            response = requests.get(config_url, timeout=5)
            if response.status_code != 200:
                print(f"❌ Failed to fetch configuration from API: {response.status_code}")
                return False
                
            # Parse the JSON response
            new_config = response.json().get("configs")
            
            # Replace current config with new config
            self.config = new_config
            
            # Initialize all required components with the new configuration
            self._initialize_from_config()
            
            print(f"✅ Configuration successfully refreshed from API: {config_url}")
            return True
        except Exception as e:
            print(f"❌ Error refreshing configuration from API: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Tests the connection to the Qdrant server by attempting to retrieve the list of collections.
        Returns:
            bool: True if the connection is successful, False otherwise.
        Raises:
            Exception: If there is an error while connecting to the Qdrant server.
        """
        try:
            # Try to get collections to test connection
            collections = self.qdrant_client.get_collections()
            print(f"Connection successful! Server has {len(collections.collections)} collections")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def get_collection_points(self, collection_name: str, limit: int = 100, with_payload: bool = True, with_vectors: bool = False) -> list:
        """
        Retrieve points from a specified Qdrant collection with optional payload and vector data.
        Args:
            collection_name (str): Name of the Qdrant collection to retrieve points from.
            limit (int, optional): Maximum number of points to retrieve. Defaults to 100.
            with_payload (bool, optional): Whether to include payload data for each point. Defaults to True.
            with_vectors (bool, optional): Whether to include vector data for each point. Defaults to False.
        Returns:
            list: A list of dictionaries, each representing a point with the following structure:
                - id (str or int): Unique identifier of the point.
                - payload (dict): Payload data associated with the point (empty if not present).
                - vector (list or None): Vector data if requested and available, otherwise None.
                - vector_dimension (int or None): Dimension of the vector if present, otherwise None.
                - payload_summary (dict, optional): Summary of payload keys and a preview of content for text fields.
        Raises:
            Exception: If an error occurs during retrieval, prints the error and returns an empty list.
        Example:
            points = get_collection_points("my_collection", limit=10, with_payload=True, with_vectors=True)
        """
        try:
            if not self._collection_exists(collection_name):
                print(f"Collection '{collection_name}' does not exist")
                return []
            
            # Get points from the collection
            points = self.qdrant_client.scroll(
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
        Retrieves detailed information about a specific point from a Qdrant collection.
        Args:
            collection_name (str): The name of the Qdrant collection to search in.
            point_id (str): The unique identifier of the point to retrieve.
        Returns:
            dict: A dictionary containing detailed information about the point, including:
                - 'id': The point's unique identifier.
                - 'payload': The payload data associated with the point.
                - 'vector': The vector representation of the point (if available).
                - 'vector_dimension': The dimension of the vector (if available).
                - 'payload_analysis': Analysis of the payload, including:
                    - 'total_keys': Number of keys in the payload.
                    - 'key_types': Data types of each payload key.
                    - 'content_lengths': Lengths of string values in the payload.
                    - 'full_content': Full content of each payload key.
        Notes:
            - Returns an empty dictionary if the collection or point does not exist, or if an error occurs.
            - Prints informative messages for missing collections, points, or errors.
        """

        try:
            if not self._collection_exists(collection_name):
                print(f"Collection '{collection_name}' does not exist")
                return {}
            
            # Get specific point
            points = self.qdrant_client.retrieve(
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
    
    def process_document(self, file_path: str, force_recreate: bool = False) -> bool:
        """
        Process a document file and store its embeddings in Qdrant.
        
        This method:
        1. Loads the document using the appropriate loader
        2. Splits it into manageable chunks
        3. Creates embeddings for each chunk
        4. Stores the embeddings in a Qdrant collection
        
        Args:
            file_path (str): Path to the document file
            force_recreate (bool, optional): If True, deletes and recreates 
                the collection if it exists. Default is False.
                
        Returns:
            bool: True if processing was successful, False otherwise
        """
        try:
            print(f"Processing document: {file_path}")
            
            # Get collection name
            collection_name = self._get_collection_name(file_path)
            
            # Check if collection exists
            collection_exists = self._collection_exists(collection_name)
            
            if collection_exists and not force_recreate:
                print(f"Collection '{collection_name}' already exists. Updating documents...")
                return True  # Skip processing if collection exists and not forcing recreation
            elif collection_exists and force_recreate:
                print(f"Recreating collection '{collection_name}'...")
                self.qdrant_client.delete_collection(collection_name=collection_name)
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
                self.qdrant_client.create_collection(
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
    
    def process_directory(self, directory_path: str = '', force_recreate: bool = False) -> Dict[str, bool]:
        """
        Process all files in the specified directory by vectorizing and storing them in Qdrant.
        This method iterates through each file in the given directory, processes each document 
        using the process_document method, and collects the processing results.
        Parameters:
            directory_path (str): Path to the directory containing files to process.
                                  If not provided, uses the directory from configuration.
            force_recreate (bool): If True, forces re-processing of documents even if they
                                   have been processed before. Default is False.
        Returns:
            Dict[str, bool]: Dictionary mapping file paths to processing success status,
                             where True indicates successful processing and False indicates failure.
        Raises:
            Exception: Any exceptions during file processing are caught, logged, and the file is
                       marked as failed in the results.
        """
        if not directory_path:
            directory_path = self.config.get("PROCESSING",0).get("src_directory")
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


if __name__ == "__main__":
    try:
        # 1. Initialize the document manager
        # Initialize manager with default config URL from MsgCenter API
        print(f"🔄 Initializing QdrantDocManager with configuration from API: {CONFIG_URL}")
        manager = QdrantDocManager()
        print("✅ QdrantDocManager initialized successfully")

        # 2. Test connection
        print("\n" + "="*80)
        print("TESTING CONNECTION")
        print("="*80)
        connection_result = manager.test_connection()
        print(f"Connection test result: {'Success' if connection_result else 'Failed'}")
        
        if not connection_result:
            print("❌ Cannot proceed without a working connection. Please check your Qdrant server.")
            exit(1)
        
        # 3. Process a directory
        print("\n" + "="*80)
        print("PROCESSING A DIRECTORY")
        print("="*80)
        print(f"Testing directory processing with: src")

        dir_results = manager.process_directory(force_recreate=True)
        
        success_count = sum(1 for result in dir_results.values() if result)
        print(f"Directory processing results: {success_count}/{len(dir_results)} files processed successfully")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()