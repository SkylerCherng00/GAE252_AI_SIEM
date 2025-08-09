from fastapi import FastAPI, HTTPException, Body, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from pydantic import BaseModel, Field
from typing import Any, Optional, List, Dict, Union
from qdrant_client import QdrantClient
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage
from langchain_qdrant import QdrantVectorStore
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from pathlib import Path
from contextlib import asynccontextmanager
import threading
import json
import datetime
import os
# Change the working directory to the project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from utils.factory_llm import LLMExecutorFactory, LLMExecutor
from utils.factory_embedding import EmbeddingModelFactory, EmbeddingModel
from utils.util_mongodb import MongoDBHandler

# Application state management
class AppState:
    """
    Manage shared application state.
    
    Attributes:
        factory_llm: Factory for creating LLM executors
        factory_embedding: Factory for creating embedding models
        current_executor: The currently active LLM executor instance
        current_executor_type: The type of the currently active LLM executor
        sysmsg_logpreviewer: System prompt for log previewing tasks
        sysmsg_loganalyzer: System prompt for log analysis safety checks
        sysmsg_qrt: System prompt for quick response team execution
        llm: The current LLM executor instance used for analysis tasks
        mongo_handler: MongoDB handler instance for database operations
    """
    def __init__(self):
        self.factory_llm: None = None
        self.factory_embedding: None = None
        self.current_executor: None = None
        self.current_executor_type: str = ''
        self.sysmsg_logpreviewer: str | None = None
        self.sysmsg_loganalyzer: str | None = None
        self.sysmsg_qrt: str | None = None
        self.llm: None = None
        self.mongo_handler: None = None
APP_STATE = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan event handler for startup and shutdown.
    
    Initializes resources on application startup and cleans up on shutdown
    
    Args:
        app (FastAPI): The FastAPI application instance.
    """
    try:
        # Initialize the LLM and embedding factories
        APP_STATE.factory_llm = LLMExecutorFactory()
        APP_STATE.factory_embedding = EmbeddingModelFactory()

        # Set the current executor and type based on the embedding factory
        APP_STATE.current_executor = None
        APP_STATE.current_executor_type = APP_STATE.factory_embedding.get_current_model()

        # Load system prompt messages
        def _load_system_message(path: Path) -> str:
            """
            Load a system prompt message from the specified file path.
            
            Args:
                path (Path): The path to the system message file.
            
            Returns:
                str: The content of the system message file.
            
            Raises:
                FileNotFoundError: If the file does not exist.
                ValueError: If there is an error reading the file.
            """
            if not path.is_file():
                raise FileNotFoundError(f"System message file does not exist at: {path}")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                raise ValueError(f"Error loading system message file '{path}': {e}")

        # Define paths for configuration and system messages
        base_dir = Path(__file__).parent
        sysmsg_LogPreviewer = base_dir / "sysmsg" / "LogPreviewer.txt"
        sysmsg_LoganAlyzer = base_dir / "sysmsg" / "LogAnalyzer.txt"
        sysmsg_QRT = base_dir / "sysmsg" / "QuickRespTeam.txt"

        # Load system messages from files
        APP_STATE.sysmsg_logpreviewer = _load_system_message(sysmsg_LogPreviewer)
        APP_STATE.sysmsg_loganalyzer = _load_system_message(sysmsg_LoganAlyzer)
        APP_STATE.sysmsg_qrt = _load_system_message(sysmsg_QRT)
        print("System prompt messages loaded.")
    except Exception as e:
        print(f"Error: Failed to load system prompt messages: {e}")
        raise RuntimeError("Failed to load system prompt messages, application cannot start.") from e
        
    # Initialize LLM for analysis tasks
    # Get the executor and then get the actual LangChain model from it
    APP_STATE.llm = _get_executor(APP_STATE.current_executor_type).get_model()
    print("Agent executors initialized.")

    # Initialize MongoDB handler
    APP_STATE.mongo_handler = MongoDBHandler()  # Initialize MongoDB handler
    print("MongoDB handler initialized.")
    yield

# Initialize FastAPI application with metadata
app = FastAPI(title="AI SIEM Log Analysis API", 
              description="API for analyzing logs using different LLM models", 
              version="1.0.2",
              lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only, restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LogAnalysisRequest(BaseModel):
    """
    Request model for log analysis
    
    Attributes:
        logs: The raw log data to be analyzed by the LLM
        collection_name: Optional Qdrant collection name to search in
        top_k: Optional number of similar documents to retrieve from Qdrant
    """
    logs: str = Field(..., description="The logs to analyze")
    collection_name: Optional[str] = Field(None, description="The Qdrant collection name to search in")
    top_k: Optional[int] = Field(3, description="The number of similar documents to retrieve from Qdrant")
    
class ModelInfo(BaseModel):
    """
    Information about an available model type
    
    Attributes:
        name: The identifier of the model (e.g., 'ollama', 'gemini', 'azure')
        description: Human-readable description of the model
        is_current: Whether this model is currently active
    """
    name: str
    description: str
    is_current: bool

class APIResponse(BaseModel):
    """
    Standard API response model for consistent return formats
    
    Attributes:
        success: Whether the operation was successful
        message: A descriptive message about the result
        data: Optional data payload returned by the operation
    """
    success: bool
    message: str
    data: Optional[Any] = None

def _get_executor(model_type: Optional[str] = None) -> LLMExecutor:
    """
    Get the appropriate LLM executor based on the requested model type
    
    This function implements a singleton-like pattern by caching the current executor
    and only creating a new one when necessary. It also handles fallback logic when
    a requested model is not available.
    
    Args:
        model_type: The type of model to use ('ollama', 'gemini', 'azure', or None for default)
        
    Returns:
        An instance of LLMExecutor ready to process requests
        
    Raises:
        HTTPException: If the requested model is not available or cannot be initialized
    """
    # If no model specified, use the current one
    if model_type is None:
        model_type = APP_STATE.current_executor_type
    
    # If requesting the current model and we have it cached, return it
    if model_type == APP_STATE.current_executor_type and APP_STATE.current_executor is not None:
        return APP_STATE.current_executor

    # Otherwise, try to create the requested executor
    executor = APP_STATE.factory_llm.create_executor(model_type)
    
    if executor is None:
        available = APP_STATE.factory_llm.get_available_executors()
        available_str = ", ".join(available) if available else "None"
        raise HTTPException(
            status_code=400,
            detail=f"Requested model '{model_type}' is not available. Available models: {available_str}"
        )
    
    # Update the cache
    APP_STATE.current_executor = executor
    APP_STATE.current_executor_type = model_type
    
    return executor

def _get_embedding_model() -> EmbeddingModel:
    """
    Get the appropriate embedding model based on the requested model type
    
    This function implements a singleton-like pattern by caching the current embedding model
    and only creating a new one when necessary.
        
    Returns:
        An instance of EmbeddingModel ready to process embeddings
        
    Raises:
        HTTPException: If the requested model is not available or cannot be initialized
    """
    embedding_model = APP_STATE.factory_embedding.create_embedding_model()

    if embedding_model is None:
        raise HTTPException(
            status_code=400,
            detail=f"Requested embedding model is not available."
        )
    
    return embedding_model

def _get_qdrant_client() -> QdrantClient:
    """
    Get the Qdrant client for vector similarity search
    
    This function initializes a Qdrant client using the configuration from the embedding factory
    and caches it for future use.
    
    Returns:
        An instance of QdrantClient ready to perform vector searches
        
    Raises:
        HTTPException: If the Qdrant client cannot be initialized
    """
    try:
        # Get Qdrant configuration from the embedding factory
        qdrant_config = APP_STATE.factory_embedding.get_qdrant_config()
        
        # Initialize Qdrant client
        qdrant_url = qdrant_config.get('url', 'http://localhost:6333')
        qdrant_api_key = qdrant_config.get('api_key', '')
        
        if qdrant_api_key:
            qdrant_client = QdrantClient(qdrant_url, api_key=qdrant_api_key)
        else:
            qdrant_client = QdrantClient(qdrant_url)
        
        return qdrant_client
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize Qdrant client: {str(e)}"
        )

def _get_retriever_instance(collection_name: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieve similar documents from Qdrant using the provided query.

    Args:
        query (str): The query string to search for similar documents.
        collection_name (str): The name of the Qdrant collection to search in.
        top_k (int, optional): The number of top similar documents to retrieve. Defaults to 3.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the similar documents.

    Raises:
        HTTPException: If there is an error initializing Qdrant or retrieving documents.
    """
    try:
        qdrant = QdrantVectorStore(
            client=_get_qdrant_client(),
            collection_name=collection_name,
            embedding=_get_embedding_model().get_model()
        )
        return qdrant.as_retriever(search_kwargs={'k': top_k})
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to convert to Retriever: {str(e)}"
        )

def _write_to_mongodb(collection_name: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> bool:
    """
    Write data to MongoDB using the MongoDBHandler.
    
    Args:
        collection_name (str): The name of the MongoDB collection to write to.
        data (Union[Dict[str, Any], List[Dict[str, Any]]]): The data to insert, either a single document (dict) 
                                                             or multiple documents (list of dicts).
    
    Returns:
        bool: True if the write operation was successful, False otherwise.
    """
    try:
        # Ensure the collection exists
        if not APP_STATE.mongo_handler.create_collection(collection_name):
            print(f"Failed to create or verify collection: {collection_name}")
            return False
        
        # Insert the data
        result = APP_STATE.mongo_handler.insert_data(collection_name, data)
        
        if result:
            print(f"Successfully wrote data to MongoDB collection: {collection_name}")
        else:
            print(f"Failed to write data to MongoDB collection: {collection_name}")
            
        return result
    except Exception as e:
        print(f"Error writing to MongoDB: {str(e)}")
        return False

def _comparison_report(report: str, language_code: Optional[str] = 'zh', analyzing_time:float = 0, file_name: str = '') -> None:
    preview_prompt = ChatPromptTemplate.from_messages([
        SystemMessage('''
You are an expert cybersecurity analyst tasked with reviewing and critiquing a security report generated by an LLM. Your role is to act as a judge, comparing the LLM-produced report against a provided "answer key" or "gold standard" report.

Your core function is to:
1.  **Analyze the LLM's report for accuracy and completeness.** Carefully compare every finding, vulnerability, and recommendation in the LLM's report to the information in the provided answer key.
2.  **Identify discrepancies, errors, and omissions.** Point out where the LLM's report deviates from the correct information. This includes incorrect vulnerability names, misstated severity levels, inaccurate descriptions, and missing crucial details or recommendations.
3.  **Evaluate the report's structure and clarity.** Assess if the LLM's report is well-organized, easy to read, and professionally presented. Does it follow a logical flow? Is the language clear and concise?
4.  **Provide detailed, constructive comments.** For each identified issue, provide a specific, actionable comment. These comments should explain *what* is wrong and *why* it's wrong, referencing the correct information from the answer key.
5.  **Assign a final verdict or score.** Based on your analysis, provide a summary judgment on the quality of the LLM's report. You may use a scoring system (e.g., a scale of 1-10) or a categorical judgment (e.g., "Pass," "Needs Improvement," "Fail") and justify your decision.

**Your output must be structured as follows:**

-   **Summary Judgment:** Start with a brief, high-level summary of the report's quality.
-   **Specific Findings and Comments:**
    -   Use a bulleted or numbered list.
    -   For each point, clearly state the issue. For example: "Incorrect Vulnerability Name," "Missing Remediation Step," "Inaccurate CVSS Score."
    -   Follow each point with your detailed comment, explaining the error and providing the correct information from the answer key.
-   **Overall Recommendation:** Conclude with a final recommendation on how the LLM's report could be improved. This should be a synthesis of your specific comments.

Your tone should be professional and objective, focusing on the technical accuracy and quality of the report. The goal is to provide feedback that can be used to improve the LLM's performance in generating future security reports.
Summarize the report in {lang} language.
'''),
        ("human", "Compare the input report:\n\n{input} with anser report:\n\n{answer} them summize the correctness of input report in {lang} language.")
    ])
    preview_chain = preview_prompt | APP_STATE.llm
    # Read the file content if file_path is provided
    

    result = preview_chain.invoke({"input": report, "answer": ,"lang": language_code})
    data = {'input_report': report,
            'comparison_result': result.content,
            'analyzing_time': analyzing_time,
            'use_model': APP_STATE.current_executor_type
            }
    _write_to_mongodb(collection_name='DebugComparisonReport', data=data)

def _analyze_logs(logs: str, collection_name: Optional[str] = "SecurityCriteria", top_k: Optional[int] = 5, language_code: Optional[str] = 'zh', file_name:str='') -> str:
    '''
    Analyze logs using the LLM executor and return the results.
    Args:
        logs (str): The raw log data to analyze.
        collection_name (str): The name of the Qdrant collection to search in for similar logs.
        top_k (int): The number of similar documents to retrieve from Qdrant.
        language_code (str): The language in which the report should be generated (default is 'zh' for Traditional Chinese and 'en' for English).
    Returns:
        str: The analysis results from the LLM.
    '''
    try:
        # Record the start time for performance measurement
        start_time = datetime.datetime.now()

        # Preview the logs before analysis
        preview_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(APP_STATE.sysmsg_logpreviewer),
            ("human", "Preview the following logs:\n\n{input}")
        ])
        preview_chain = preview_prompt | APP_STATE.llm
        preview_result = preview_chain.invoke({"input": logs})

        # Integrate with Qdrant for similarity search if a collection is specified
        # Create a chat prompt template for the agent
        agent_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(APP_STATE.sysmsg_loganalyzer),
            ("human", '''Analyze the following logs based on the provided context.\n
             Context:\n{context}\n
             Logs:\n{input}\n
             Please provide a detailed analysis in {lang} language.'''),
        ])
        
        # Create a document chain that can process the retrieved documents
        document_chain = create_stuff_documents_chain(
            llm=APP_STATE.llm, # Use the base LLM, not the agent
            prompt=agent_prompt
        )
        
        # Get the retriever for security criteria
        retriever = _get_retriever_instance(collection_name=collection_name, top_k=top_k)
        
        # Create a proper retrieval chain that will combine documents with the query
        rag_chain = create_retrieval_chain(retriever, document_chain)
        
        # The invoke method expects a dict with the 'input' key
        agent_reply = rag_chain.invoke({"input": preview_result.content, "lang": language_code})
        result = agent_reply.get('answer', 'No answer found').strip('`json')  # string
        print(f"Log analysis result: {result}\n")

        # Write the analysis result to MongoDB
        result_json = json.loads(result)
        
        # Comparison report for the analysis result
        _comparison_report(result_json.get('analysis_report', 'EMPTY analysis report'),
                           language_code=language_code,
                           processing_time=(datetime.datetime.now() - start_time).total_seconds(),
                           file_name=file_name)


        # print(f"Log analysis result: {result_json}\n")
        # _write_to_mongodb(collection_name='DebugLogAnalysisResults', data=result_json)
        
        # The result will be a dict with an "answer" key containing the processed response
        # print(f"Log preview result: {preview_result.content}\n")
        # print(f"Agent reply type: {type(agent_reply)} keys:{agent_reply.keys()}\n")
        # print(f"Agent reply input: {agent_reply.get('input', 'Non input found')}\n")
        # print(f"Agent reply context: {agent_reply.get('context', 'No context found')}\n")
        # print(f"Agent reply answer type: {type(agent_reply.get('answer', 'No answer found'))}\n") # str
        # print(f"Agent reply answer: {agent_reply.get('answer', 'No answer found')}\n")

        # Return just the answer string, not the whole dict
        return None
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to decode JSON from analysis result: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze logs: {str(e)}"
        )

@app.get("/agent/health")
async def health_check():
    """
    Health check endpoint for monitoring and status verification
    
    This endpoint provides information about the API's health status, including
    which LLM models are currently available and which one is active. It's useful
    for monitoring systems and service discovery.
    
    Returns:
        dict: A dictionary with the health status and relevant information
    """
    try:
        available_models = APP_STATE.factory_llm.get_available_executors()

        return {
            "status": "healthy",
            "available_models": available_models,
            "current_model": APP_STATE.current_executor_type
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/agent/models", response_model=APIResponse)
async def list_models():
    """
    List all available LLM models/executors
    
    This endpoint returns information about all LLM models that are currently
    available for use, including which one is active. This helps clients
    understand their options for model switching.
    
    Returns:
        APIResponse: A standardized response with the list of available models
    """
    try:
        # available = LLM_FACTORY.get_available_executors()
        available = APP_STATE.factory_llm.get_available_executors()
        
        models_info = []
        for model in available:
            models_info.append(ModelInfo(
                name=model,
                description=f"LLM executor for {model.capitalize()}",
                is_current=(model == APP_STATE.current_executor_type)
            ))
        
        return APIResponse(
            success=True,
            message="Available models retrieved successfully",
            data=models_info
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"Error retrieving models: {str(e)}",
            data=None
        )

@app.post("/agent/switch-model", response_model=APIResponse)
async def switch_model(model_type: str = Body(..., embed=True)):
    """
    Switch the active LLM model to a different type
    
    This endpoint allows the client to change which LLM model/service is used for analysis.
    It validates that the requested model is available before switching and provides
    appropriate error messages if the model cannot be used.
    
    Args:
        model_type: The type of model to switch to ('ollama', 'gemini', 'azure')
        
    Returns:
        APIResponse: A standardized response indicating success or failure
    """
    # global CURRENT_EXECUTOR, APP_STATE
    try:
        # Validate the requested model type
        if model_type not in ['ollama', 'gemini', 'azure']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model type '{model_type}'. Supported models: 'ollama', 'gemini', 'azure'."
            )

        # Try to get the executor for the requested model
        APP_STATE.current_executor = _get_executor(model_type)
        APP_STATE.current_executor_type = model_type
        APP_STATE.llm = APP_STATE.current_executor.get_model()  # Update the LLM
        
        return APIResponse(
            success=True,
            message=f"Successfully switched to model: {model_type}",
            data={"model_type": model_type}
        )
    except HTTPException as e:
        return APIResponse(
            success=False,
            message=e.detail,
            data=None
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"Error switching model: {str(e)}",
            data=None
        )

@app.post("/agent/analyze-logs", response_model=APIResponse)
async def analyze_logs(request: LogAnalysisRequest, language_code: Optional[str] = 'zh'):
    """
    Analyze logs using the specified LLM model, with optional Qdrant similarity search
    
    This is the main endpoint for log analysis. It takes log data from the client,
    optionally performs a similarity search in Qdrant, and then uses the LLM to
    analyze the logs and provide insights. The client can specify which model to use
    and whether to use Qdrant for similarity comparison.
    
    Args:
        request: The LogAnalysisRequest object containing logs and optional model preferences
        
    Returns:
        APIResponse: A standardized response with the analysis results or error details
    """
    try:
        if language_code not in ['zh', 'en']:
            raise HTTPException(
                status_code=400,
                detail="Invalid report language specified. Supported languages are 'zh' (Traditional Chinese) and 'en' (English)."
            )
        
        return {
            "success": True,
            "message": "Log analysis started",
            "data": _analyze_logs(request.logs,language_code=language_code,)
        }

    except HTTPException as e:
        return APIResponse(
            success=False,
            message=e.detail,
            data=None
        )

@app.post("/agent/analyze-logs/upload", response_model=APIResponse)
async def analyze_logs_upload(file: UploadFile = File(...), language_code: Optional[str] = 'zh'):
    """
    Analyze logs with file upload support
    This endpoint allows clients to upload log files for analysis. It checks the file
    extension, saves the file to a designated directory, and then reads the contents
    for analysis using the LLM. It supports common log file formats like .txt, .csv,
    .json, and .log.

    Args:
        file: The log file to be uploaded and analyzed. Must be one of the allowed formats.
    
    Returns:
        APIResponse: A standardized response indicating success or failure of the upload and analysis
    """
    # Validate the language code
    if language_code not in ['zh', 'en']:
        raise HTTPException(
            status_code=400,
            detail="Invalid report language specified. Supported languages are 'zh' (Traditional Chinese) and 'en' (English)."
        )
    
    # Check file extension
    allowed_extensions = ['.txt', '.csv', '.json', '.log']
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file extension: {file_extension}. Allowed: {', '.join(allowed_extensions)}"
        )
    try:
        # Create docs directory if it doesn't exist
        docs_dir = Path("logs")
        docs_dir.mkdir(exist_ok=True)
        
        # Save file to docs directory
        file_path = docs_dir / file.filename
        print(f"Saving file to: {file_path}")
        
        # The crucial step: write the contents of the UploadFile to the new file
        # Using a sync operation with a thread pool to avoid blocking the event loop
        import shutil
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Open the file and read its contents
        with open(file_path, "r", encoding="utf-8") as f:
            logs = f.read()

        return {
            "success": True,
            "message": "Log analysis started",
            "data": _analyze_logs(logs, language_code=language_code, file_name=file.filename)
        }
    except Exception as e:
        # Catch and handle exceptions, making sure to include the original error message
        # for better debugging.
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("agent:app", host="0.0.0.0", port=8000)
