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
import configparser
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

    def __init__(self, config_path: str = None):
        """
        Initialize the QdrantDocManager with configuration.
        
        Args:
            config_path (str, optional): Path to the configuration file.
                If None, uses default path in the same directory.
        """
        # Load configuration
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, 'config_embed.ini')
        
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        
        # Set up instance properties from config
        self.embedding_provider = self.config.get('GENERAL', 'embedding_provider', fallback='ollama')
        self.qdrant_url = self.config.get('QDRANT', 'url', fallback='http://localhost:6333')
        self.qdrant_api_key = self.config.get('QDRANT', 'api_key', fallback='')
        self.chunk_size = self.config.getint('CHUNKING', 'chunk_size', fallback=1000)
        self.chunk_overlap = self.config.getint('CHUNKING', 'chunk_overlap', fallback=200)
        
        # Initialize embeddings model based on provider
        self.embeddings = self._initialize_embeddings()
        
        # Initialize Qdrant client
        print(self.qdrant_url)
        if self.qdrant_api_key:
            self.client = QdrantClient(self.qdrant_url, api_key=self.qdrant_api_key)
        else:
            self.client = QdrantClient(self.qdrant_url)
        
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
        print(provider)
            
        if provider == "ollama":
            # Initialize Ollama embeddings
            ollama_base_url = self.config.get("OLLAMA", "base_url", fallback="http://localhost:11434")
            ollama_model = self.config.get("OLLAMA", "embedding_model", fallback="nomic-embed-text")
            
            if not ollama_base_url or not ollama_model:
                raise ValueError("Missing required Ollama configuration: base_url and/or embedding_model")
                
            print(f"🔄 Initializing Ollama embeddings with model: {ollama_model}")
            return OllamaEmbeddings(
                base_url=ollama_base_url,
                model=ollama_model
            )
            
        elif provider == "azure":
            # Initialize Azure OpenAI embeddings
            azure_api_key = self.config.get("AZURE", "api_key", fallback="")
            azure_api_base = self.config.get("AZURE", "api_base", fallback="")
            azure_api_version = self.config.get("AZURE", "api_version", fallback="2023-05-15")
            azure_deployment = self.config.get("AZURE", "embedding_deployment", fallback="")
            
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
            gemini_api_key = self.config.get("GEMINI", "api_key", fallback="")
            gemini_model_name = self.config.get("GEMINI", "model_name", fallback="models/embedding-001")
            
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
            return self.client.collection_exists(collection_name=collection_name)
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
            collections = self.client.get_collections()
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
            
            self.client.delete_collection(collection_name=collection_name)
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

        try:
            # Try to get collections to test connection
            collections = self.client.get_collections()
            print(f"Connection successful! Server has {len(collections.collections)} collections")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def get_collection_points(self, collection_name: str, limit: int = 100, with_payload: bool = True, with_vectors: bool = False) -> list:

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
        Search for documents similar to the query in the specified collection.
        
        Args:
            query (str): The search query text
            collection_name (str): Name of the collection to search in
            k (int, optional): Number of results to return. Default is 3.
            
        Returns:
            list: List of dictionaries containing search results with scores and metadata
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
    
    def process_directory(self, directory_path: str = '', force_recreate: bool = False) -> Dict[str, bool]:
        
        if not directory_path:
            directory_path = self.config.get("PROCESSING", "src_directory")
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
        # Initialize manager with default config
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
        
        # 3. List existing collections
        print("\n" + "="*80)
        print("LISTING EXISTING COLLECTIONS")
        print("="*80)
        existing_collections = manager.list_collections()
        
        # 4. Process a sample document
        print("\n" + "="*80)
        print("PROCESSING A SAMPLE DOCUMENT")
        print("="*80)
        
        # Use a markdown file from the repository as a test document
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        sample_file = os.path.join(parent_dir, "README.md")
        
        if not os.path.exists(sample_file):
            # Fallback to creating a temporary test file
            print(f"README.md not found at {sample_file}, creating a temporary test file...")
            sample_file = os.path.join(current_dir, "temp_test_file.md")
            with open(sample_file, "w") as f:
                f.write("# Test Document\n\nThis is a temporary test document for Qdrant Document Manager.\n\n" +
                       "It contains multiple paragraphs to test chunking and embedding functionality.\n\n" +
                       "The document manager should process this file, split it into chunks, and store the embeddings in Qdrant.")
            print(f"Created temporary test file at {sample_file}")
        
        # Process the document with force_recreate=True to ensure clean test
        process_result = manager.process_document(sample_file, force_recreate=True)
        print(f"Document processing result: {'Success' if process_result else 'Failed'}")
        
        # 5. Process a directory
        print("\n" + "="*80)
        print("PROCESSING A DIRECTORY")
        print("="*80)
        
        # Use the current directory or parent directory for the test
        # test_dir = current_dir
        # if not os.listdir(test_dir) or all(os.path.isdir(os.path.join(test_dir, f)) for f in os.listdir(test_dir)):
        #     test_dir = os.path.dirname(test_dir)
        
        # print(f"Testing directory processing with: {test_dir}")
        print(f"Testing directory processing with: src")

        dir_results = manager.process_directory(force_recreate=False)
        
        success_count = sum(1 for result in dir_results.values() if result)
        print(f"Directory processing results: {success_count}/{len(dir_results)} files processed successfully")
        
        # 6. List collections after processing
        print("\n" + "="*80)
        print("LISTING COLLECTIONS AFTER PROCESSING")
        print("="*80)
        updated_collections = manager.list_collections()
        
        new_collections = set(updated_collections) - set(existing_collections)
        print(f"New collections created: {new_collections}")
        
        # 7. Get collection points
        print("\n" + "="*80)
        print("RETRIEVING COLLECTION POINTS")
        print("="*80)
        
        if updated_collections:
            test_collection = updated_collections[0]
            print(f"Testing with collection: {test_collection}")
            
            points = manager.get_collection_points(test_collection, limit=5)
            print(f"Retrieved {len(points)} points from collection {test_collection}")
            
            # 8. Get point details for first point
            if points:
                print("\n" + "="*80)
                print("RETRIEVING POINT DETAILS")
                print("="*80)
                
                point_id = points[0]['id']
                point_details = manager.get_point_details(test_collection, point_id)
                print(f"Retrieved details for point {point_id}")
                
                # 9. Search similar documents
                print("\n" + "="*80)
                print("SEARCHING FOR SIMILAR DOCUMENTS")
                print("="*80)
                
                # Extract some text from the point to use as a search query
                if 'payload' in point_details and 'page_content' in point_details['payload']:
                    search_text = point_details['payload']['page_content'][:100]  # Use first 100 chars
                    print(f"Search query: {search_text}")
                    
                    search_results = manager.search_similar(search_text, test_collection, k=2)
                    print(f"Search returned {len(search_results)} results")
                else:
                    print("No content available in point details for search")
            else:
                print("No points available for testing point details and search")
        else:
            print("No collections available for testing")
        
        # 10. Update embedding provider
        print("\n" + "="*80)
        print("TESTING EMBEDDING PROVIDER UPDATE")
        print("="*80)
        
        # Just test if the method runs without errors using the same provider
        current_provider = manager.embedding_provider
        print(f"Current embedding provider: {current_provider}")
        
        update_result = manager.update_embedding_provider(current_provider)
        print(f"Embedding provider update result: {'Success' if update_result else 'Failed'}")
        
        # 11. Test deleting a collection
        print("\n" + "="*80)
        print("TESTING COLLECTION DELETION")
        print("="*80)
        
        if new_collections:
            # Delete the first new collection created during the test
            collection_to_delete = list(new_collections)[0]
            print(f"Deleting test collection: {collection_to_delete}")
            
            delete_result = manager.delete_collection(collection_to_delete)
            print(f"Collection deletion result: {'Success' if delete_result else 'Failed'}")
            
            # Verify deletion
            final_collections = manager.list_collections()
            if collection_to_delete not in final_collections:
                print(f"Verified: Collection {collection_to_delete} was successfully deleted")
            else:
                print(f"Verification failed: Collection {collection_to_delete} still exists")
        else:
            print("No new collections created during test to delete")
        
        # 12. Test connection update
        print("\n" + "="*80)
        print("TESTING CONNECTION UPDATE")
        print("="*80)
        
        # Use same URL to just test if the method runs
        same_url = manager.qdrant_url
        print(f"Current Qdrant URL: {same_url}")
        
        update_conn_result = manager.update_connection(qdrant_url=same_url)
        print(f"Connection update result: {'Success' if update_conn_result else 'Failed'}")
        
        # Clean up temporary test file if created
        if os.path.exists(os.path.join(current_dir, "temp_test_file.md")):
            os.remove(os.path.join(current_dir, "temp_test_file.md"))
            print("Temporary test file removed")
        
        print("\n" + "="*80)
        print("TEST EXECUTION COMPLETE")
        print("="*80)
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()