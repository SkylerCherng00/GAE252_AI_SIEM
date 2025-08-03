from fastapi import FastAPI, HTTPException, Body, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Any, Optional, Dict, List
from llm_factory import LLMExecutorFactory, LLMExecutor
import uvicorn
import requests
import os
import shutil
from pathlib import Path

# Initialize FastAPI application with metadata
app = FastAPI(title="AI SIEM Log Analysis API", 
              description="API for analyzing logs using different LLM models", 
              version="1.0.0")

# Initialize the LLM Factory singleton to manage model creation
llm_factory = LLMExecutorFactory()

# Cache for the current executor to avoid recreating model instances
CURRENT_EXECUTOR = None
CURRENT_EXECUTOR_TYPE = "ollama"  # Default to ollama as requested

# Qdrant configuration settings
QDRANT_CONFIG_URL = "http://localhost:10000/config/config_embed"
CURRENT_COLLECTION = "logs"  # Default collection name for log analysis

class LogAnalysisRequest(BaseModel):
    """
    Request model for log analysis
    
    Attributes:
        logs: The raw log data to be analyzed by the LLM
        model_type: Optional type of model to use (e.g., 'ollama', 'gemini', 'azure')
        model_name: Optional specific model name if the executor supports multiple models
        use_rag: Whether to use RAG with Qdrant for analysis
        collection_name: Optional collection name to use for RAG (defaults to CURRENT_COLLECTION)
    """
    logs: str = Field(..., description="The logs to analyze")
    model_type: Optional[str] = Field(None, description="The model type to use for analysis")
    model_name: Optional[str] = Field(None, description="The specific model name to use (if supported by the executor)")
    use_rag: bool = Field(False, description="Whether to use RAG with Qdrant for analysis")
    collection_name: Optional[str] = Field(None, description="Collection name to use for RAG")
    
class RemoteLogRequest(BaseModel):
    """
    Request model for retrieving and analyzing logs from a remote server
    
    Attributes:
        url: The URL of the remote server to fetch logs from
        auth_header: Optional authorization header for the remote server
        model_type: Optional type of model to use for analysis
        save_locally: Whether to save the logs locally before analysis
        use_rag: Whether to use RAG with Qdrant for analysis
        collection_name: Optional collection name to use for RAG
    """
    url: str = Field(..., description="The URL of the remote server to fetch logs from")
    auth_header: Optional[Dict[str, str]] = Field(None, description="Authorization header for the remote server")
    model_type: Optional[str] = Field(None, description="The model type to use for analysis")
    save_locally: bool = Field(True, description="Whether to save the logs locally before analysis")
    use_rag: bool = Field(False, description="Whether to use RAG with Qdrant for analysis")
    collection_name: Optional[str] = Field(None, description="Collection name to use for RAG")
    
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

class QdrantCollectionInfo(BaseModel):
    """
    Information about a Qdrant collection
    
    Attributes:
        name: The name of the collection
        is_current: Whether this collection is currently being used for RAG
    """
    name: str
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
    global CURRENT_EXECUTOR, CURRENT_EXECUTOR_TYPE
    
    # If no model specified, use the current one
    if model_type is None:
        model_type = CURRENT_EXECUTOR_TYPE
    
    # If requesting the current model and we have it cached, return it
    if model_type == CURRENT_EXECUTOR_TYPE and CURRENT_EXECUTOR is not None:
        return CURRENT_EXECUTOR
    
    # Otherwise, try to create the requested executor
    executor = llm_factory.create_executor(model_type)
    
    if executor is None:
        available = llm_factory.get_available_executors()
        available_str = ", ".join(available) if available else "None"
        raise HTTPException(
            status_code=400,
            detail=f"Requested model '{model_type}' is not available. Available models: {available_str}"
        )
    
    # Update the cache
    CURRENT_EXECUTOR = executor
    CURRENT_EXECUTOR_TYPE = model_type
    
    return executor

def _get_qdrant_config():
    """
    Fetch the Qdrant configuration from the MsgCenter API
    
    Returns:
        dict: The Qdrant configuration
        
    Raises:
        HTTPException: If the configuration cannot be fetched
    """
    try:
        response = requests.get(QDRANT_CONFIG_URL, timeout=5)
        if response.status_code == 200:
            return response.json().get('configs')
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch Qdrant configuration: {response.status_code}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching Qdrant configuration: {str(e)}"
        )

def _get_qdrant_collections():
    """
    Get a list of available Qdrant collections
    
    Returns:
        list: List of collection names
        
    Raises:
        HTTPException: If the collections cannot be fetched
    """
    try:
        config = _get_qdrant_config()
        qdrant_url = config.get('QDRANT', {}).get('url', 'http://localhost:6333')
        
        # Make a request to the Qdrant API to list collections
        response = requests.get(f"{qdrant_url}/collections", timeout=5)
        
        if response.status_code == 200:
            collections_data = response.json()
            return [collection.get('name') for collection in collections_data.get('result', {}).get('collections', [])]
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch Qdrant collections: {response.status_code}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching Qdrant collections: {str(e)}"
        )
        
def _fetch_remote_logs(url: str, auth_header: Optional[Dict[str, str]] = None) -> str:
    """
    Fetch logs from a remote server
    
    Args:
        url: The URL to fetch logs from
        auth_header: Optional authorization header
        
    Returns:
        str: The fetched logs
        
    Raises:
        HTTPException: If the logs cannot be fetched
    """
    try:
        headers = auth_header if auth_header else {}
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.text
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch logs from {url}: {response.status_code}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching logs from {url}: {str(e)}"
        )
        
def _save_logs_to_file(logs: str, filename: str = "fetched_logs.log") -> str:
    """
    Save logs to a local file
    
    Args:
        logs: The logs to save
        filename: The name of the file to save to
        
    Returns:
        str: The path to the saved file
        
    Raises:
        HTTPException: If the logs cannot be saved
    """
    try:
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Save logs to file
        file_path = logs_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(logs)
            
        return str(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error saving logs to file: {str(e)}"
        )
        
def _query_qdrant_for_context(query: str, collection_name: str) -> str:
    """
    Query Qdrant for context to use in the analysis
    
    Args:
        query: The query to search for
        collection_name: The name of the collection to search in
        
    Returns:
        str: The context from Qdrant
        
    Raises:
        HTTPException: If the context cannot be fetched
    """
    try:
        config = _get_qdrant_config()
        qdrant_url = config.get('QDRANT', {}).get('url', 'http://localhost:6333')
        
        # This is a simplified implementation - in a real system you would:
        # 1. Generate embeddings for the query using the same model as used in Qdrant
        # 2. Query Qdrant for similar vectors
        # 3. Process and return the context
        
        # For now, we'll just check if the collection exists
        response = requests.get(f"{qdrant_url}/collections/{collection_name}", timeout=5)
        
        if response.status_code != 200:
            return "No relevant context found in the knowledge base."
            
        # In a real implementation, you would query Qdrant with the embedded query
        # and return the retrieved context
        return f"Context from Qdrant collection '{collection_name}' would be retrieved here."
    except Exception as e:
        # Log the error but don't fail the analysis
        print(f"Error querying Qdrant for context: {str(e)}")
        return "Error retrieving context from the knowledge base."

@app.post("/switch-model", response_model=APIResponse)
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
    global CURRENT_EXECUTOR
    try:
        # Try to get the executor for the requested model
        CURRENT_EXECUTOR = _get_executor(model_type)
        
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

@app.post("/switch-collection", response_model=APIResponse)
async def switch_collection(collection_name: str = Body(..., embed=True)):
    """
    Switch the active Qdrant collection for RAG
    
    This endpoint allows the client to change which Qdrant collection is used for RAG.
    It validates that the requested collection exists before switching.
    
    Args:
        collection_name: The name of the collection to switch to
        
    Returns:
        APIResponse: A standardized response indicating success or failure
    """
    global CURRENT_COLLECTION
    try:
        # Check if the collection exists
        collections = _get_qdrant_collections()
        
        if collection_name not in collections:
            return APIResponse(
                success=False,
                message=f"Collection '{collection_name}' does not exist. Available collections: {', '.join(collections)}",
                data=None
            )
        
        # Update the current collection
        CURRENT_COLLECTION = collection_name
        
        return APIResponse(
            success=True,
            message=f"Successfully switched to collection: {collection_name}",
            data={"collection_name": collection_name}
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
            message=f"Error switching collection: {str(e)}",
            data=None
        )

@app.post("/analyze-logs", response_model=APIResponse)
async def analyze_logs(request: LogAnalysisRequest):
    """
    Analyze logs using the specified LLM model, optionally with RAG
    
    This is the main endpoint for log analysis. It takes log data from the client,
    formats it into a prompt for the LLM, and returns the analysis results. The client
    can optionally specify which model to use for the analysis and whether to use RAG.
    
    Args:
        request: The LogAnalysisRequest object containing logs and analysis preferences
        
    Returns:
        APIResponse: A standardized response with the analysis results or error details
    """
    try:
        # Get the executor for the requested model type (if specified)
        executor = _get_executor(request.model_type)
        
        # Determine the collection to use for RAG
        collection_name = request.collection_name or CURRENT_COLLECTION
        
        # Prepare the system message with appropriate instructions
        system_message = """
        You are an AI SIEM log analyzer. Your task is to analyze the provided logs and identify 
        any security issues, anomalies, or concerns. Provide a detailed explanation of your findings 
        and recommendations for action.
        
        Focus on:
        1. Unusual login patterns or failed authentication attempts
        2. Potential data exfiltration
        3. Signs of lateral movement
        4. Privilege escalation
        5. Unusual network traffic
        6. Malware indicators
        7. Configuration issues
        8. Any other security concerns
        
        Format your response with sections for:
        - Summary of findings
        - Detailed analysis
        - Recommendations
        - Severity level
        """
        
        # If RAG is requested, get context from Qdrant
        rag_context = ""
        if request.use_rag:
            try:
                # Use the first part of the logs as a query to find relevant context
                query = request.logs[:500]  # Use first 500 chars as the query
                rag_context = _query_qdrant_for_context(query, collection_name)
                
                # Add the RAG context to the system message
                system_message += f"""
                
                RELEVANT CONTEXT FROM KNOWLEDGE BASE:
                {rag_context}
                """
            except Exception as e:
                # Log the error but continue with the analysis without RAG
                print(f"Error using RAG: {str(e)}")
        
        # Prepare the full prompt
        prompt = f"""
        {system_message}
        
        LOGS:
        {request.logs}
        """
                    
        # Generate the analysis
        analysis = executor.generate_response(prompt)
        
        return APIResponse(
            success=True,
            message="Log analysis completed successfully",
            data={
                "analysis": analysis, 
                "model_used": CURRENT_EXECUTOR_TYPE,
                "rag_used": request.use_rag,
                "collection_used": collection_name if request.use_rag else None
            }
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
            message=f"Error analyzing logs: {str(e)}",
            data=None
        )

@app.post("/analyze-remote-logs", response_model=APIResponse)
async def analyze_remote_logs(request: RemoteLogRequest):
    """
    Fetch logs from a remote server and analyze them
    
    This endpoint fetches logs from a remote server, optionally saves them locally,
    and then analyzes them using the specified LLM model, optionally with RAG.
    
    Args:
        request: The RemoteLogRequest object containing the remote server details and analysis preferences
        
    Returns:
        APIResponse: A standardized response with the analysis results or error details
    """
    try:
        # Fetch logs from the remote server
        logs = _fetch_remote_logs(request.url, request.auth_header)
        
        # Save logs locally if requested
        saved_file_path = None
        if request.save_locally:
            # Generate a filename based on the URL
            filename = f"remote_logs_{Path(request.url).name}.log"
            saved_file_path = _save_logs_to_file(logs, filename)
        
        # Create a LogAnalysisRequest object to reuse the analyze_logs functionality
        analysis_request = LogAnalysisRequest(
            logs=logs,
            model_type=request.model_type,
            use_rag=request.use_rag,
            collection_name=request.collection_name
        )
        
        # Analyze the logs
        analysis_response = await analyze_logs(analysis_request)
        
        # Add the saved file path to the response if logs were saved locally
        if saved_file_path and analysis_response.success:
            analysis_response.data["saved_file_path"] = saved_file_path
        
        return analysis_response
    except HTTPException as e:
        return APIResponse(
            success=False,
            message=e.detail,
            data=None
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"Error analyzing remote logs: {str(e)}",
            data=None
        )

@app.post("/upload-log-file", response_model=APIResponse)
async def upload_and_analyze_log_file(
    file: UploadFile = File(...),
    model_type: Optional[str] = None,
    use_rag: bool = False,
    collection_name: Optional[str] = None
):
    """
    Upload a log file, save it locally, and analyze it
    
    This endpoint allows the client to upload a log file, which is saved locally
    and then analyzed using the specified LLM model, optionally with RAG.
    
    Args:
        file: The log file to upload and analyze
        model_type: Optional model type to use for analysis
        use_rag: Whether to use RAG for analysis
        collection_name: Optional collection name to use for RAG
        
    Returns:
        APIResponse: A standardized response with the analysis results or error details
    """
    try:
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Save the uploaded file
        file_path = logs_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Read the log file
        with open(file_path, "r", encoding="utf-8") as f:
            logs = f.read()
        
        # Create a LogAnalysisRequest object to reuse the analyze_logs functionality
        analysis_request = LogAnalysisRequest(
            logs=logs,
            model_type=model_type,
            use_rag=use_rag,
            collection_name=collection_name
        )
        
        # Analyze the logs
        analysis_response = await analyze_logs(analysis_request)
        
        # Add the saved file path to the response
        if analysis_response.success:
            analysis_response.data["saved_file_path"] = str(file_path)
        
        return analysis_response
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"Error uploading and analyzing log file: {str(e)}",
            data=None
        )

@app.get("/logs/{filename}", response_class=FileResponse)
async def get_log_file(filename: str):
    """
    Get a specific log file
    
    This endpoint returns a specific log file from the logs directory.
    
    Args:
        filename: The name of the log file to get
        
    Returns:
        FileResponse: The requested log file
        
    Raises:
        HTTPException: If the file does not exist
    """
    file_path = Path("logs") / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Log file {filename} not found")
    
    return FileResponse(str(file_path))

@app.get("/logs", response_model=APIResponse)
async def list_log_files():
    """
    List all log files in the logs directory
    
    This endpoint returns a list of all log files in the logs directory.
    
    Returns:
        APIResponse: A standardized response with the list of log files
    """
    try:
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        files = []
        for file_path in logs_dir.glob("*"):
            if file_path.is_file():
                files.append({
                    "name": file_path.name,
                    "size_bytes": file_path.stat().st_size,
                    "last_modified": file_path.stat().st_mtime
                })
        
        return APIResponse(
            success=True,
            message=f"Found {len(files)} log files",
            data={"files": files}
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message=f"Error listing log files: {str(e)}",
            data=None
        )

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and status verification
    
    This endpoint provides information about the API's health status, including
    which LLM models are currently available and which one is active. It also
    includes information about available Qdrant collections for RAG.
    
    Returns:
        dict: A dictionary with the health status and relevant information
    """
    try:
        available_models = llm_factory.get_available_executors()
        
        # Get Qdrant collections if possible
        qdrant_collections = []
        try:
            qdrant_collections = _get_qdrant_collections()
        except Exception as e:
            print(f"Error getting Qdrant collections: {str(e)}")
        
        return {
            "status": "healthy",
            "available_models": available_models,
            "current_model": CURRENT_EXECUTOR_TYPE,
            "qdrant_status": "available" if qdrant_collections else "unavailable",
            "available_collections": qdrant_collections,
            "current_collection": CURRENT_COLLECTION
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/models", response_model=APIResponse)
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
        available = llm_factory.get_available_executors()
        
        models_info = []
        for model in available:
            models_info.append(ModelInfo(
                name=model,
                description=f"LLM executor for {model.capitalize()}",
                is_current=(model == CURRENT_EXECUTOR_TYPE)
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

@app.get("/collections", response_model=APIResponse)
async def list_collections():
    """
    List all available Qdrant collections for RAG
    
    This endpoint returns information about all Qdrant collections that are currently
    available for use with RAG, including which one is active. This helps clients
    understand their options for collection switching.
    
    Returns:
        APIResponse: A standardized response with the list of available collections
    """
    try:
        collections = _get_qdrant_collections()
        
        collections_info = []
        for collection in collections:
            collections_info.append(QdrantCollectionInfo(
                name=collection,
                is_current=(collection == CURRENT_COLLECTION)
            ))
        
        return APIResponse(
            success=True,
            message="Available collections retrieved successfully",
            data=collections_info
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
            message=f"Error retrieving collections: {str(e)}",
            data=None
        )

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    uvicorn.run("agent:app", host="0.0.0.0", port=8000, reload=True)

# ============================================================================
# Curl Testing Script
# ============================================================================
# This section contains curl commands for testing the API endpoints
# You can copy these commands and run them in a terminal to test the API
#
# 1. Health Check - Verify API is running and check available models
# curl -X GET http://localhost:8000/health
#
# 2. List Models - Get all available LLM models
# curl -X GET http://localhost:8000/models
#
# 3. List Collections - Get all available Qdrant collections
# curl -X GET http://localhost:8000/collections
#
# 4. Switch Model - Change to a different LLM model (example: switch to gemini)
# curl -X POST http://localhost:8000/switch-model \
#     -H "Content-Type: application/json" \
#     -d '{"model_type": "gemini"}'
#
# 5. Switch Collection - Change to a different Qdrant collection
# curl -X POST http://localhost:8000/switch-collection \
#     -H "Content-Type: application/json" \
#     -d '{"collection_name": "security_logs"}'
#
# 6. Analyze Logs - Send logs for analysis with default model
# curl -X POST http://localhost:8000/analyze-logs \
#     -H "Content-Type: application/json" \
#     -d '{
#         "logs": "2024-07-31T10:15:22.123Z ERROR [auth-service] Failed login attempt for user admin from IP 192.168.1.100 - Invalid password (attempt 5 of 5)",
#         "use_rag": false
#     }'
#
# 7. Analyze Logs with RAG - Send logs for analysis with RAG
# curl -X POST http://localhost:8000/analyze-logs \
#     -H "Content-Type: application/json" \
#     -d '{
#         "logs": "2024-07-31T10:15:22.123Z ERROR [auth-service] Failed login attempt for user admin from IP 192.168.1.100 - Invalid password (attempt 5 of 5)",
#         "use_rag": true,
#         "collection_name": "security_logs"
#     }'
#
# 8. Analyze Remote Logs - Fetch and analyze logs from a remote server
# curl -X POST http://localhost:8000/analyze-remote-logs \
#     -H "Content-Type: application/json" \
#     -d '{
#         "url": "http://example.com/logs/security.log",
#         "save_locally": true,
#         "use_rag": false
#     }'
#
# 9. Upload and Analyze Log File - Upload a log file and analyze it
# curl -X POST http://localhost:8000/upload-log-file \
#     -F "file=@/path/to/local/logfile.log" \
#     -F "use_rag=false"
#
# 10. List Log Files - Get a list of all log files
# curl -X GET http://localhost:8000/logs
#
# 11. Get Log File - Get a specific log file
# curl -X GET http://localhost:8000/logs/logfile.log --output downloaded_logfile.log
