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
import json
import datetime
import os
import math
# Change the working directory to the project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from utils.factory_llm import LLMExecutorFactory, LLMExecutor
from utils.factory_embedding import EmbeddingModelFactory, EmbeddingModel
from utils.util_mongodb import MongoDBHandler
from utils.factory_reportid import ReportIDFactory

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
        report_id_factory: Singleton instance of ReportIDFactory for generating report IDs
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
        self.report_id_factory: ReportIDFactory = ReportIDFactory()
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
        print(f"- INFO - agent.py lifespan() - System prompt messages loaded.")
    except Exception as e:
        print(f"- ERROR - agent.py lifespan() - Failed to load system prompt messages: {e}")
        raise RuntimeError("Failed to load system prompt messages, application cannot start.") from e
        
    # Initialize LLM for analysis tasks
    # Get the executor and then get the actual LangChain model from it
    APP_STATE.llm = _get_executor(APP_STATE.current_executor_type).get_model()
    print(f"- INFO - agent.py lifespan() - Agent executors initialized.")

    # Initialize MongoDB handler
    APP_STATE.mongo_handler = MongoDBHandler()  # Initialize MongoDB handler
    print(f"- INFO - agent.py lifespan() - MongoDB handler initialized.")

    # Initialize ReportIDFactory
    APP_STATE.report_id_factory = ReportIDFactory(APP_STATE.mongo_handler)
    print(f"- INFO - agent.py lifespan() - ReportIDFactory initialized.")

    yield

# Initialize FastAPI application with metadata
app = FastAPI(title="AI SIEM Log Analysis API", 
              description="API for analyzing logs using different LLM models", 
              version="1.0.3",
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
            print(f"- ERROR - agent.py _write_to_mongodb() - Failed to create or verify collection: {collection_name}")
            return False
        
        # Insert the data
        result = APP_STATE.mongo_handler.insert_data(collection_name, data)
        
        if result:
            print(f"- INFO - agent.py _write_to_mongodb() - Successfully wrote data to MongoDB collection: {collection_name}")
        else:
            print(f"- ERROR - agent.py _write_to_mongodb() - Failed to write data to MongoDB collection: {collection_name}")
            
        return result
    except Exception as e:
        print(f"- ERROR - agent.py _write_to_mongodb() - Error writing to MongoDB: {str(e)}")
        return False

PREVIEW_RESULT = list()

def _preview_logs_analyze(logs: str) -> str:
    try:
        global PREVIEW_RESULT
        print(logs)
        # If the log is small enough, preview it directly
        preview_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(APP_STATE.sysmsg_logpreviewer),
            ("human", "Preview the following logs:\n\n{input}")
        ])
        preview_chain = preview_prompt | APP_STATE.llm
        preview_result = preview_chain.invoke({"input": logs})
        PREVIEW_RESULT.append(preview_result.content)
    except Exception as e:
        print(f"- ERROR - agent.py _preview_logs_analyze() - Error during log preview: {str(e)}")

def _preview_logs(logs: str) -> str:
    """
    Preview and chunk logs to fit within a specified token limit, then summarize each chunk.

    This function takes a string of logs, estimates the number of tokens,
    and if it exceeds a certain limit, it chunks the logs into smaller
    parts. Each chunk is prefixed with a header indicating its position
    (e.g., "Chunk 1 of 3"). Each chunk is then sent to an LLM for previewing.
    The previews are then combined.

    Args:
        logs (str): The raw log data.

    Returns:
        str: The summarized preview of the logs.
    """
    try:
        # Constants for token estimation and limits
        CHARS_PER_TOKEN = 4
        MAX_TOKENS_LLM = 128000  # Adjust this based on your LLM's capabilities
        # MAX_TOKENS_PER_MINUTE = 1000000  # Adjust this based on your LLM's capabilities
        MAX_TOKENS_PER_CHUNK = MAX_TOKENS_LLM * 0.6

        estimated_total_tokens = len(logs) / CHARS_PER_TOKEN
        print(f"- INFO - agent.py _preview_logs() - Estimated total tokens: {estimated_total_tokens}")

        if estimated_total_tokens <= MAX_TOKENS_PER_CHUNK:
            # If the log is small enough, preview it directly
            preview_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(APP_STATE.sysmsg_logpreviewer),
                ("human", "Preview the following logs:\n\n{input}")
            ])
            preview_chain = preview_prompt | APP_STATE.llm
            preview_result = preview_chain.invoke({"input": logs})
            print(f"- INFO - agent.py _preview_logs() - Log preview completed without chunking.")
            return preview_result.content

        # If the logs exceed the limit, chunk them by lines
        print(f"- INFO - agent.py _preview_logs() - Log exceeds token limit, chunking logs...")
        lines = logs.split('\n')
        
        chunks = []
        current_chunk_lines = []
        current_chunk_tokens = 0

        print(f"- INFO - agent.py _preview_logs() - Splitting logs into chunks...")
        for line in lines:
            line_tokens = len(line) / CHARS_PER_TOKEN
            if current_chunk_tokens + line_tokens > MAX_TOKENS_PER_CHUNK and current_chunk_lines:
                chunks.append("\n".join(current_chunk_lines))
                current_chunk_lines = [line]
                current_chunk_tokens = line_tokens
            else:
                current_chunk_lines.append(line)
                current_chunk_tokens += line_tokens
        print(f"- INFO - agent.py _preview_logs() - Finished splitting logs into {len(chunks)} chunks.")

        if current_chunk_lines:
            chunks.append("\n".join(current_chunk_lines))

        # Add headers to each chunk and preview each one
        total_chunks = len(chunks)
        summarized_chunks = []
        for i, chunk in enumerate(chunks):
            print(f"- INFO - agent.py _preview_logs() - Processing chunk {i+1} of {total_chunks}...")
            chunk_header = f"--- Chunk {i+1} of {total_chunks} ---\n"
            headed_chunk = chunk_header + chunk

            # preview_prompt = ChatPromptTemplate.from_messages([
            #     SystemMessage(APP_STATE.sysmsg_logpreviewer),
            #     ("human", "Preview the following log chunk:\n\n{input}")
            # ])
            # preview_chain = preview_prompt | APP_STATE.llm
            # preview_result = preview_chain.invoke({"input": headed_chunk})
            # summarized_chunks.append(preview_result.content)
            import threading
            t = threading.Thread(target=_preview_logs_analyze, args=(headed_chunk))
            t.start()  # Start the thread to preview the chunk asynchronously
        # Join the summarized chunks into a single string
        t.join()
        print(f"- INFO - agent.py _preview_logs() - All chunks processed, summarizing results...")
        return None
        # return "\n\n".join(summarized_chunks)
    except Exception as e:
        print(f"- ERROR - agent.py _preview_logs() - Error during log preview: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to preview logs: {str(e)}"
        )

def _analyze_logs(
        logs: str,
        collection_name: Optional[str] = "SecurityCriteria",
        top_k: Optional[int] = 5,
        language_code: Optional[str] = 'zh',
        log_src :str = 'From_Pure_Logs'
        ) -> str:
    """
    Analyze logs using the LLM executor and return the results.
    Args:
        logs (str): The raw log data to analyze.
        collection_name (str): The name of the Qdrant collection to search in for similar logs.
        top_k (int): The number of similar documents to retrieve from Qdrant.
        language_code (str): The language in which the report should be generated (default is 'zh' for Traditional Chinese and 'en' for English).
        log_src (str): The source of the logs, used for reporting purposes.
                       Default is 'From_Pure_Logs'.
    Returns:
        str: The analysis results from the LLM.
    """
    try:
        print(f"- INFO - agent.py _analyze_logs() - Analyzing logs with language code: {language_code}")
        # Preview the logs before analysis
        preview_result_content = _preview_logs(logs)
        if not preview_result_content:
            preview_result_content = "\n\n".join(PREVIEW_RESULT)
        print(f"- INFO - agent.py _analyze_logs() - Log preview completed.")

        # Integrate with Qdrant for similarity search if a collection is specified
        # Create a chat prompt template for the agent
        print(f"- INFO - agent.py _analyze_logs() - Starting log analysis...")
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
        agent_reply = rag_chain.invoke({"input": preview_result_content, "lang": language_code})
        result = agent_reply.get('answer', 'No answer found').strip('`json')
        print(f"- INFO - agent.py _analyze_logs() - Complete Log analysis")
        # print(f"Log analysis result: {result}\n")

        # The result will be a dict with an "answer" key containing the processed response
        # print(f"Log preview result: {preview_result.content}\n")
        # print(f"Agent reply type: {type(agent_reply)} keys:{agent_reply.keys()}\n")
        # print(f"Agent reply input: {agent_reply.get('input', 'Non input found')}\n")
        # print(f"Agent reply context: {agent_reply.get('context', 'No context found')}\n")
        # print(f"Agent reply answer type: {type(agent_reply.get('answer', 'No answer found'))}\n") # str
        # print(f"Agent reply answer: {agent_reply.get('answer', 'No answer found')}\n")

        # Write the analysis result to MongoDB
        result_json = json.loads(result)
        # print(f"json parsing result: {result_json}")

        for dict_ele in result_json:
            if dict_ele:
                _thread_safe_process(input=dict_ele, language_code=language_code, log_src=log_src)
        
        # Return just the answer string, not the whole dict
        return result
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

def _thread_safe_process(input:dict=None, language_code:str='' , log_src:str = '') -> bool:
    """
    Thread-safe function to process input data and launch QRT execution.
    Args:
        input (dict): The input data to process, expected to contain log analysis results.
        language_code (str): The language in which the report should be generated.
        log_src (str): The source of the logs, used for reporting purposes.
    Returns:
        True if processing was successful, False otherwise.
    """
    try:
        if input:
            import threading
            with threading.Lock():
                timestamp_float = datetime.datetime.now().timestamp()
                input['timestamp'] = timestamp_float
                report_id = APP_STATE.report_id_factory.generate_report_id()
                input['report_id'] = report_id
                input['log_src'] = log_src

                # Start the QRT thread to handle quick response team execution
                print(f"- INFO - agent.py _thread_safe_process() - Starting to launch QRT...")
                qrt = threading.Thread(target=_launch_qrt, args=(str(input), language_code, timestamp_float, report_id, log_src, input.get("analysis_report", '')))
                qrt.start()  # Start the QRT thread to handle quick response team execution

                print(f"- INFO - agent.py _thread_safe_process() - Starting to write log analysis result to MongoDB...")
                mongo = threading.Thread(target=_write_to_mongodb, args=('LogAnalysisResults', input))
                mongo.start()

        return True
    except Exception as e:
        print(f"- ERROR - agent.py _thread_safe_process() - Error processing input: {str(e)}")
        return False

def _launch_qrt(
        condition : str,
        language_code: Optional[str] = 'zh',
        timestamp : float = .0,
        report_id: Optional[str] = '',
        log_src: str = '',
        md_content: str = ''
        ) -> None:
    """
    Launch the Quick Response Team (QRT) execution based on the provided condition.
    Args:
        condition (str): The condition to analyze and execute the QRT response.
        language_code (str): The language in which the report should be generated (default is 'zh' for Traditional Chinese and 'en' for English).
        timestamp (float): The timestamp of the analysis, used for logging and reporting.
        report_id (str): The unique identifier for the report, used for tracking and reference.
        log_src (str): The source of the logs, used for reporting purposes.
        md_content (str): The full report made by analysis function.
    Returns:
        None
    """
    try:
        print(f"- INFO - agent.py _launch_qrt() - Starting QRT execution...")
        
        # Integrate with Qdrant for similarity search if a collection is specified
        # Create a chat prompt template for the agent
        qrt_prompt = ChatPromptTemplate.from_messages([
            SystemMessage(APP_STATE.sysmsg_qrt),
            ("human", '''Analyze the following condition based on the provided context.\n
                Context:\n{context}\n
                Report:\n{input}\n
                Please provide a response in {lang} language.'''),
        ])
        
        # Create a document chain that can process the retrieved documents
        document_chain = create_stuff_documents_chain(llm = APP_STATE.llm, prompt = qrt_prompt)
        
        # Get the retriever for security criteria
        retriever_sop = _get_retriever_instance(collection_name='SOP', top_k=5)
        # retriever_comtable = _get_retriever_instance(collection_name='ComTable', top_k=5)

        # Create a custom retriever that combines results from both SOP and ComTable
        # from langchain_core.runnables import chain
        # @chain
        # def custom_retriever(inputs):
        #     q = inputs["input"]
        #     docsA = retriever_sop.invoke(q)
        #     docsB = retriever_comtable.invoke(q)
        #     return docsA + docsB

        # Create a proper retrieval chain that will combine documents with the query
        # rag_chain = create_retrieval_chain(custom_retriever, document_chain)
        rag_chain = create_retrieval_chain(retriever_sop, document_chain)
        
        # The invoke method expects a dict with the 'input' key
        agent_reply = rag_chain.invoke({"input": condition, "lang": language_code})
        result = agent_reply.get('answer', 'No answer found').strip('`json') # string
        # print(f"Complete QRT execution")
        # print(f"QRT response: {result}\n")

        # The result will be a dict with an "answer" key containing the processed response
        # print(f"Agent reply input: {agent_reply.get('input', 'Non input found')}\n")
        # print(f"Agent reply context: {agent_reply.get('context', 'No context found')}\n")
        # print(f"Agent reply answer type: {type(agent_reply.get('answer', 'No answer found'))}\n")
        # print(f"Agent reply answer: {agent_reply.get('answer', 'No answer found')}\n")

        # Write the QRT response to MongoDB
        result_json = json.loads(result)
        result_json['short_report'] += f"\n*Report ID:* {report_id}\n" if language_code == 'en' else f"\n*報告 ID:* {report_id}\n"
        result_json['short_report'] += f"\n*Log Source:* {log_src}\n" if language_code == 'en' else f"\n*日誌來源:* {log_src}\n"
        result_json['md_content'] = md_content

        # Send the QRT response to the RPA endpoint
        print(f"- INFO - agent.py _launch_qrt() - Sending QRT response to RPA endpoint...")
        if result_json.get('priority_level') == 'P1' or result_json.get('priority_level') == 'P2':
            import requests
            from utils.endpoint import endpoint_rpa_url
            requests.post(endpoint_rpa_url, json=result_json)
            
        # Add timestamp to the result JSON and write to MongoDB
        result_json['timestamp'] = timestamp
        # print(f"QRT response JSON: {result_json}\n")
        print(f"- INFO - agent.py _launch_qrt() - Starting to write QRT response to MongoDB...")
        _write_to_mongodb(collection_name='QRTResults', data=result_json)
        
        return None
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to decode JSON from QRT response: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to launch QRT: {str(e)}"
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
    allowed_extensions = ['.txt', '.csv', '.json', '.log', 'md']
    file_extension = Path(file.filename).suffix.lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file extension: {file_extension}. Allowed: {', '.join(allowed_extensions)}"
        )
    
    if file.filename.lower().count('test'):
        print(f"- INFO - agent.py analyze_logs_upload() - Test file detected, skipping analysis.")
        return {
            "success": True,
            "message": "Test file detected, skipping analysis",
            "data": None
        }
    
    try:
        # Create docs directory if it doesn't exist
        docs_dir = Path("logs")
        docs_dir.mkdir(exist_ok=True)
        
        # Save file to docs directory
        file_path = docs_dir / file.filename
        print(f"- INFO - agent.py analyze_logs_upload() - Saving file to: {file_path}")
        
        # Read directly from UploadFile (before saving)
        # As file.read() happens, the internal file cursor advances to the very end of the file
        content = await file.read()
        content = content.decode('utf-8')
        # Rewind the file cursor to the beginning
        await file.seek(0)

        # The crucial step: write the contents of the UploadFile to the new file
        # Using a sync operation with a thread pool to avoid blocking the event loop
        # Save file by tempfile
        import shutil
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "success": True,
            "message": "Log analysis started",
            "data": _analyze_logs(content, language_code=language_code, log_src=file.filename)
        }
    except Exception as e:
        # Catch and handle exceptions, making sure to include the original error message
        # for better debugging.
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")
    finally:
        del content

if __name__ == "__main__":
    uvicorn.run("agent:app", host="0.0.0.0", port=10001)