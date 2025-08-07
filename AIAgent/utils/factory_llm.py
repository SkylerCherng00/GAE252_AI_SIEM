import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from .endpoint import endpoint_url

# HTTP Endpoint
CONFIG_FACTORY_URL = endpoint_url + "config_factory"

class LLMExecutor(ABC):
    """Abstract base class for LLM executors"""
    
    @abstractmethod
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate a response from the LLM based on the prompt"""
        pass

    @abstractmethod
    def get_model(self, **kwargs):
        """Get the underlying LLM model object"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM is available for use"""
        pass

class OllamaExecutor(LLMExecutor):
    """LLM executor for Ollama using LangChain"""
    
    def __init__(self, config: Dict[str, Any]):
        self.host = config.get('HOST', 'http://localhost:11434')
        self.model = config.get('MODEL', 'llama2')
        self.current_model = self.model
        self._llm = None
    
    def _initialize_llm(self):
        try:
            from langchain_ollama import OllamaLLM
            
            self._llm = OllamaLLM(
                base_url=self.host,
                model=self.current_model,
                temperature=0
            )
        except Exception as e:
            print(f"Error initializing Ollama LLM: {str(e)}")
            self._llm = None
    
    def get_model(self, **kwargs):
        """Get the underlying OllamaLLM model object"""
        if kwargs.get('model') and kwargs.get('model') != self.current_model:
            self.current_model = kwargs.get('model')
            self._initialize_llm()
        
        if not self._llm:
            self._initialize_llm()
            
        return self._llm
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        try:
            llm = self.get_model(**kwargs)
            
            if not llm:
                return "Failed to initialize Ollama LLM"
                
            response = llm.invoke(prompt)
            return response
        except Exception as e:
            return f"Error generating response from Ollama: {str(e)}"
    
    def is_available(self) -> bool:
        try:
            import requests
            response = requests.get(f"{self.host}/api/tags", timeout=3)
            return response.status_code == 200
        except Exception:
            return False

class GeminiExecutor(LLMExecutor):
    """LLM executor for Google's Gemini API using LangChain"""
    
    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get('API_KEY', '')
        self.model = config.get('MODEL', 'gemini-pro')
        self.current_model = self.model
        self._llm = None
    
    def _initialize_llm(self):
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            self._llm = ChatGoogleGenerativeAI(
                model=self.current_model,
                google_api_key=self.api_key,
                temperature=0                
            )
        except Exception as e:
            print(f"Error initializing Gemini LLM: {str(e)}")
            self._llm = None
    
    def get_model(self, **kwargs):
        """Get the underlying ChatGoogleGenerativeAI model object"""
        if kwargs.get('model') and kwargs.get('model') != self.current_model:
            self.current_model = kwargs.get('model')
            self._initialize_llm()
        
        if not self._llm:
            self._initialize_llm()
            
        return self._llm
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        try:
            llm = self.get_model(**kwargs)
            
            if not llm:
                return "Failed to initialize Gemini LLM"
                
            from langchain.schema import HumanMessage
            
            response = llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            return f"Error generating response from Gemini: {str(e)}"
    
    def is_available(self) -> bool:
        return bool(self.api_key)

class AzureOpenAIExecutor(LLMExecutor):
    """LLM executor for Azure OpenAI using LangChain"""
    
    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get('API_KEY', '')
        self.endpoint = config.get('ENDPOINT', '')
        self.api_version = config.get('VERSION', '2023-05-15')
        self.model = config.get('MODEL', 'gpt-4')
        self.current_model = self.model
        self._llm = None
    
    def _initialize_llm(self):
        try:
            from langchain_openai import AzureChatOpenAI
            
            self._llm = AzureChatOpenAI(
                azure_endpoint=self.endpoint,
                azure_deployment=self.current_model,
                api_key=self.api_key,
                api_version=self.api_version,
                temperature=0,
                max_retries=3
            )
        except Exception as e:
            print(f"Error initializing Azure OpenAI LLM: {str(e)}")
            self._llm = None
    
    def get_model(self, **kwargs):
        """Get the underlying AzureChatOpenAI model object"""
        if kwargs.get('model') and kwargs.get('model') != self.current_model:
            self.current_model = kwargs.get('model')
            self._initialize_llm()
        
        if not self._llm:
            self._initialize_llm()
            
        return self._llm
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        try:
            llm = self.get_model(**kwargs)
            
            if not llm:
                return "Failed to initialize Azure OpenAI LLM"
                
            from langchain.schema import HumanMessage
            
            response = llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception as e:
            return f"Error generating response from Azure OpenAI: {str(e)}"
    
    def is_available(self) -> bool:
        return bool(self.api_key and self.endpoint)

class LLMExecutorFactory:
    """Factory class to produce LLM executor objects based on configuration (Singleton)"""
    
    _instance = None
    
    def __new__(cls):
        """
        Create a singleton instance of the factory
        
        """
        if cls._instance is None:
            cls._instance = super(LLMExecutorFactory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        Initialize the factory with configuration
        
        Args:
            config_path: Path to the configuration file. If None, looks for config_factory.ini in the same directory
        """
        # Only initialize once
        if self._initialized:
            return

        try:
            # Fetch configuration from HTTP endpoint
            response = requests.get(CONFIG_FACTORY_URL, timeout=3)
            if response.status_code == 200:
                self.config = response.json().get('configs')
                print(f"✅ Configuration loaded from API: {CONFIG_FACTORY_URL}")
                
            else:
                print(f"❌ Failed to fetch configuration from API: {response.status_code}")
        except Exception as e:
            print(f"❌ Error fetching configuration from API: {e}")

        # Default executor to use if available
        self.default_executor = 'ollama'
        self._initialized = True
    
    def create_executor(self, executor_type: str = None) -> Optional[LLMExecutor]:
        """
        Create an LLM executor of the specified type
        
        Args:
            executor_type: Type of executor to create ('ollama', 'gemini', 'azure'). 
                          If None, tries to create the default executor or the first available one.
        
        Returns:
            An LLM executor instance or None if no executor could be created
        """
        if executor_type is None:
            executor_type = self.default_executor
        
        executor_map = {
            'ollama': self._create_ollama_executor,
            'gemini': self._create_gemini_executor,
            'azure': self._create_azure_openai_executor
        }
        
        # Try to create the specified executor
        if executor_type in executor_map:
            executor = executor_map[executor_type]()
            if executor and executor.is_available():
                return executor
        
        # If the specified executor is not available, try each one in order
        if executor_type != 'auto':
            return self.create_executor('auto')
        
        # Try each executor in order
        for create_func in executor_map.values():
            executor = create_func()
            if executor and executor.is_available():
                return executor
        
        return None
    
    def _create_ollama_executor(self) -> Optional[LLMExecutor]:
        """Create an Ollama executor if configuration exists"""
        if 'Ollama' in self.config:
            config_dict = self.config['Ollama']
            # Convert lowercase keys to uppercase for API compatibility
            config_dict = {k.upper(): v for k, v in config_dict.items()}
            return OllamaExecutor(config_dict)
        return OllamaExecutor({})  # Use defaults
    
    def _create_gemini_executor(self) -> Optional[LLMExecutor]:
        """Create a Gemini executor if configuration exists"""
        if 'Gemini' in self.config:
            config_dict = self.config['Gemini']
            # Convert lowercase keys to uppercase for API compatibility
            config_dict = {k.upper(): v for k, v in config_dict.items()}
            return GeminiExecutor(config_dict)
        return None
    
    def _create_azure_openai_executor(self) -> Optional[LLMExecutor]:
        """Create an Azure OpenAI executor if configuration exists"""
        if 'AzureOpenAI' in self.config:
            config_dict = self.config['AzureOpenAI']
            # Convert lowercase keys to uppercase for API compatibility
            config_dict = {k.upper(): v for k, v in config_dict.items()}
            return AzureOpenAIExecutor(config_dict)
        return None
    
    def get_available_executors(self) -> List[str]:
        """
        Get a list of available executor types
        
        Returns:
            List of available executor type names
        """
        available = []
        
        executor_types = {
            'ollama': self._create_ollama_executor,
            'gemini': self._create_gemini_executor,
            'azure': self._create_azure_openai_executor
        }
        
        for name, create_func in executor_types.items():
            try:
                executor = create_func()
                if executor and executor.is_available():
                    available.append(name)
            except Exception:
                pass
        
        return available

# Example usage:
if __name__ == "__main__":
    # Create the factory (singleton)
    factory = LLMExecutorFactory()
    
    # Get available executors first
    available_executors = factory.get_available_executors()
    print(f"Available executors: {available_executors}")
    
    # Get the first available executor
    # executor = factory.create_executor(executor_type='ollama')
    # executor = factory.create_executor(executor_type="gemini")
    executor = factory.create_executor(executor_type='azure')
    
    if executor is None:
        print("No executor could be created. Please check your configuration.")
        print("Make sure at least one LLM service is properly configured and available.")
        # Try to create any available executor
        executor = factory.create_executor('auto')
        
    if executor is not None:
        # Get the underlying model object
        model = executor.get_model()
        print(f"Model type: {type(model).__name__}")

        # Example usage with a prompt
        from langchain.prompts import PromptTemplate
        prompt_template = PromptTemplate.from_template(
            "請列出三個{obj}的名字，並用逗號,隔開。"
        )
        chain = prompt_template | model 
        output = chain.invoke({"obj":"城市"})
        print(f"Output: {output}")
        
        # You can now work directly with the model object
        # For example, with AzureChatOpenAI:
        # from langchain.schema import HumanMessage
        # response = model.invoke([HumanMessage(content="What is the capital of France?")])
        # print(f"Response: {response.content}")
        
        # Or use the generate_response method
        response = executor.generate_response("What is the capital of France?")
        print(f"Response: {response}")
    else:
        print("Error: No LLM executor is available. Please check your configuration and ensure at least one service is running.")