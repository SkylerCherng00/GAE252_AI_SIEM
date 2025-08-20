import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from .endpoint import endpoint_url

# HTTP Endpoint
CONFIG_EMBED_URL = endpoint_url + "config_embed"

class EmbeddingModel(ABC):
    """Abstract base class for embedding models"""
    @abstractmethod
    def get_model(self, **kwargs):
        """Get the underlying embedding model object"""
        pass

class OllamaEmbedding(EmbeddingModel):
    """Embedding model for Ollama using LangChain"""
    
    def __init__(self, config: Dict[str, Any]):
        self.base_url = config.get('base_url', 'http://localhost:11434')
        self.model = config.get('embedding_model', 'nomic-embed-text')
        self.current_model = self.model
        self._embeddings = None
    
    def _initialize_embeddings(self):
        try:
            from langchain_ollama import OllamaEmbeddings
            
            self._embeddings = OllamaEmbeddings(
                base_url=self.base_url,
                model=self.current_model
            )
        except Exception as e:
            print(f"- ERROR - factory_embedding.py OllamaEmbedding._initialize_embeddings() - Error initializing Ollama embeddings: {str(e)}")
            self._embeddings = None
    
    def get_model(self, **kwargs):
        """Get the underlying OllamaEmbeddings model object"""
        if kwargs.get('model') and kwargs.get('model') != self.current_model:
            self.current_model = kwargs.get('model')
            self._initialize_embeddings()
        
        if not self._embeddings:
            self._initialize_embeddings()
            
        return self._embeddings
        
    def embed_query(self, text: str) -> List[float]:
        """Generate embeddings for a single text query"""
        try:
            embeddings = self.get_model()
            
            if not embeddings:
                print(f"- ERROR - factory_embedding.py OllamaEmbedding.embed_query() - Failed to initialize Ollama embeddings")
                return []
                
            return embeddings.embed_query(text)
        except Exception as e:
            print(f"- ERROR - factory_embedding.py OllamaEmbedding.embed_query() - Error generating embeddings from Ollama: {str(e)}")
            return []
    
    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of documents"""
        try:
            embeddings = self.get_model()
            
            if not embeddings:
                print(f"- ERROR - factory_embedding.py OllamaEmbedding.embed_documents() - Failed to initialize Ollama embeddings")
                return []
                
            return embeddings.embed_documents(documents)
        except Exception as e:
            print(f"- ERROR - factory_embedding.py OllamaEmbedding.embed_documents() - Error generating document embeddings from Ollama: {str(e)}")
            return []
            
    def is_available(self) -> bool:
        """Check if the embedding model is available"""
        try:
            model = self.get_model()
            return model is not None
        except:
            return False

class AzureOpenAIEmbedding(EmbeddingModel):
    """Embedding model for Azure OpenAI using LangChain"""
    
    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get('api_key', '')
        self.api_base = config.get('api_base', '')
        self.api_version = config.get('api_version', '')
        self.deployment = config.get('embedding_deployment', '')
        self.current_deployment = self.deployment
        self._embeddings = None
    
    def _initialize_embeddings(self):
        try:
            from langchain_openai import AzureOpenAIEmbeddings
            
            self._embeddings = AzureOpenAIEmbeddings(
                azure_deployment=self.current_deployment,
                openai_api_version=self.api_version,
                azure_endpoint=self.api_base,
                api_key=self.api_key
            )
        except Exception as e:
            print(f"- ERROR - factory_embedding.py AzureOpenAIEmbedding._initialize_embeddings() - Error initializing Azure OpenAI embeddings: {str(e)}")
            self._embeddings = None
    
    def get_model(self, **kwargs):
        """Get the underlying AzureOpenAIEmbeddings model object"""
        if kwargs.get('deployment') and kwargs.get('deployment') != self.current_deployment:
            self.current_deployment = kwargs.get('deployment')
            self._initialize_embeddings()
        
        if not self._embeddings:
            self._initialize_embeddings()
            
        return self._embeddings
        
    def embed_query(self, text: str) -> List[float]:
        """Generate embeddings for a single text query"""
        try:
            embeddings = self.get_model()
            
            if not embeddings:
                print(f"- ERROR - factory_embedding.py AzureOpenAIEmbedding.embed_query() - Failed to initialize Azure OpenAI embeddings")
                return []
                
            return embeddings.embed_query(text)
        except Exception as e:
            print(f"- ERROR - factory_embedding.py AzureOpenAIEmbedding.embed_query() - Error generating embeddings from Azure OpenAI: {str(e)}")
            return []
    
    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of documents"""
        try:
            embeddings = self.get_model()
            
            if not embeddings:
                print(f"- ERROR - factory_embedding.py AzureOpenAIEmbedding.embed_documents() - Failed to initialize Azure OpenAI embeddings")
                return []
                
            return embeddings.embed_documents(documents)
        except Exception as e:
            print(f"- ERROR - factory_embedding.py AzureOpenAIEmbedding.embed_documents() - Error generating document embeddings from Azure OpenAI: {str(e)}")
            return []
            
    def is_available(self) -> bool:
        """Check if the embedding model is available"""
        return bool(self.api_key and self.api_base and self.deployment)
 
class GeminiEmbedding(EmbeddingModel):
    """Embedding model for Google's Gemini API using LangChain"""
    
    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get('api_key', '')
        self.model_name = config.get('model_name', 'models/embedding-001')
        # Convert string to int if necessary
        output_dim = config.get('output_dimensionality', 768)
        self.output_dimensionality = int(output_dim) if isinstance(output_dim, str) else output_dim
        self.current_model = self.model_name
        self._embeddings = None
    
    def _initialize_embeddings(self):
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            
            self._embeddings = GoogleGenerativeAIEmbeddings(
                model=self.current_model,
                google_api_key=self.api_key,
                output_dimensionality=self.output_dimensionality
            )
        except Exception as e:
            print(f"- ERROR - factory_embedding.py GeminiEmbedding._initialize_embeddings() - Error initializing Gemini embeddings: {str(e)}")
            self._embeddings = None
    
    def get_model(self, **kwargs):
        """Get the underlying GoogleGenerativeAIEmbeddings model object"""
        if kwargs.get('model') and kwargs.get('model') != self.current_model:
            self.current_model = kwargs.get('model')
            self._initialize_embeddings()
        
        if not self._embeddings:
            self._initialize_embeddings()
            
        return self._embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embeddings for a single text query"""
        try:
            embeddings = self.get_model()
            
            if not embeddings:
                print(f"- ERROR - factory_embedding.py GeminiEmbedding.embed_query() - Failed to initialize Gemini embeddings")
                return []
                
            return embeddings.embed_query(text)
        except Exception as e:
            print(f"- ERROR - factory_embedding.py GeminiEmbedding.embed_query() - Error generating embeddings from Gemini: {str(e)}")
            return []
    
    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of documents"""
        try:
            embeddings = self.get_model()
            
            if not embeddings:
                print(f"- ERROR - factory_embedding.py GeminiEmbedding.embed_documents() - Failed to initialize Gemini embeddings")
                return []
                
            return embeddings.embed_documents(documents)
        except Exception as e:
            print(f"- ERROR - factory_embedding.py GeminiEmbedding.embed_documents() - Error generating document embeddings from Gemini: {str(e)}")
            return []
    
    def is_available(self) -> bool:
        return bool(self.api_key)

class EmbeddingModelFactory:
    """Factory class to produce embedding model objects based on configuration (Singleton)"""
    
    _instance = None
    
    def __new__(cls):
        """
        Create a singleton instance of the factory
        """
        if cls._instance is None:
            cls._instance = super(EmbeddingModelFactory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        Initialize the factory with configuration
        """
        # Only initialize once
        if self._initialized:
            return

        try:
            # Fetch configuration from HTTP endpoint
            response = requests.get(CONFIG_EMBED_URL, timeout=5)
            if response.status_code == 200:
                self.config = response.json().get('configs')
                print(f"- INFO - factory_embedding.py EmbeddingModelFactory.__init__() - Configuration loaded from API: {CONFIG_EMBED_URL}")
                
            else:
                print(f"- ERROR - factory_embedding.py EmbeddingModelFactory.__init__() - Failed to fetch configuration from API: {response.status_code}")
                self.config = {}
        except Exception as e:
            print(f"- ERROR - factory_embedding.py EmbeddingModelFactory.__init__() - Error fetching configuration from API: {e}")
            self.config = {}

        # Default embedding model to use if available
        # Handle the case where config is a nested dictionary
        if isinstance(self.config, dict) and 'GENERAL' in self.config:
            self.default_provider = self.config['GENERAL'].get('embedding_provider', '')
        else:
            self.default_provider = ''
        self._initialized = True
    
    def get_current_model(self) -> Optional[str]:
        """
        Get the current embedding model name from configuration
        
        Returns:
            The name of the current embedding model or None if not available
        """
        return self.default_provider
    
    def get_qdrant_config(self) -> Optional[Dict[str, Any]]:
        """
        Fetch Qdrant configuration from the configured endpoint
        
        Returns:
            Dictionary containing Qdrant configuration or None if not available
        """
        return self.config.get('QDRANT', {})
    
    def create_embedding_model(self, provider_type=None) -> Optional[EmbeddingModel]:
        """
        Create an embedding model of the specified type
        
        Args:
            provider_type: Type of embedding provider to create ('ollama', 'gemini', 'azure'). 
                          If None, tries to create the default provider or the first available one.
        
        Returns:
            An embedding model instance or None if no model could be created
        """
        # Use the specified provider or the default
        if provider_type is None:
            provider_type = self.default_provider
        
        provider_map = {
            'ollama': self._create_ollama_embedding,
            'gemini': self._create_gemini_embedding,
            'azure': self._create_azure_openai_embedding
        }
        
        # Try to create the specified provider
        if provider_type in provider_map:
            model = provider_map[provider_type]()
            if model and getattr(model, 'is_available', lambda: True)():
                return model
        
        # If specified provider couldn't be created, try the default
        if provider_type != self.default_provider and self.default_provider in provider_map:
            model = provider_map[self.default_provider]()
            if model and getattr(model, 'is_available', lambda: True)():
                return model
                
        # If default provider couldn't be created, try any available provider
        for provider_func in provider_map.values():
            model = provider_func()
            if model and getattr(model, 'is_available', lambda: True)():
                return model
        
        return None
    
    def _create_ollama_embedding(self) -> Optional[EmbeddingModel]:
        """Create an Ollama embedding model if configuration exists"""
        if 'OLLAMA' in self.config:
            config_dict = self.config['OLLAMA']
            return OllamaEmbedding(config_dict)
        return OllamaEmbedding({})  # Use defaults
    
    def _create_gemini_embedding(self) -> Optional[EmbeddingModel]:
        """Create a Gemini embedding model if configuration exists"""
        if 'GEMINI' in self.config:
            config_dict = self.config['GEMINI']
            return GeminiEmbedding(config_dict)
        return None
    
    def _create_azure_openai_embedding(self) -> Optional[EmbeddingModel]:
        """Create an Azure OpenAI embedding model if configuration exists"""
        if 'AZURE' in self.config:
            config_dict = self.config['AZURE']
            # No need to convert to uppercase as the class handles lowercase keys
            return AzureOpenAIEmbedding(config_dict)
        return None
    

# Example usage:
if __name__ == "__main__":
    # Create the factory (singleton)
    factory = EmbeddingModelFactory()
    
    # Get the default embedding model
    embedding_model = factory.create_embedding_model()
    
    if embedding_model is None:
        print(f"- ERROR - factory_embedding.py __main__ - No embedding model could be created. Please check your configuration.")
        print(f"- INFO - factory_embedding.py __main__ - Make sure at least one embedding service is properly configured and available.")
        # Try each provider explicitly
        for provider in ['azure', 'gemini', 'ollama']:
            print(f"- INFO - factory_embedding.py __main__ - Trying to create {provider} embedding model...")
            embedding_model = factory.create_embedding_model(provider)
            if embedding_model is not None:
                break
        
    if embedding_model is not None:
        # Get the underlying model object
        model = embedding_model.get_model()
        print(f"- INFO - factory_embedding.py __main__ - Embedding model type: {type(model).__name__}")

        # Example usage for a single query
        query_text = "This is a test query for embeddings"
        query_embedding = embedding_model.embed_query(query_text)
        print(f"- INFO - factory_embedding.py __main__ - Query embedding dimensions: {len(query_embedding) if query_embedding else 0}")
        
        # Example usage for multiple documents
        documents = [
            "This is the first document",
            "This is the second document",
            "This is the third document"
        ]
        doc_embeddings = embedding_model.embed_documents(documents)
        print(f"- INFO - factory_embedding.py __main__ - Number of document embeddings: {len(doc_embeddings) if doc_embeddings else 0}")
        if doc_embeddings and len(doc_embeddings) > 0:
            print(f"- INFO - factory_embedding.py __main__ - Dimensions of first document embedding: {len(doc_embeddings[0])}")
    else:
        print(f"- ERROR - factory_embedding.py __main__ - Error: No embedding model is available. Please check your configuration and ensure at least one service is running.")
