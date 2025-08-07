from fastapi import FastAPI, HTTPException, UploadFile, File, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import  Dict, Any, Optional
import os
from pathlib import Path
import uvicorn
from datetime import datetime
import shutil

# Change the working directory to the project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Import QdrantDocManager from embed_documents module
from qdrant_embed import QdrantDocManager


# Create FastAPI app
app = FastAPI(
    title="Qdrant Document Manager API",
    description="API for managing document embeddings in Qdrant vector database",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Pydantic models for request and response schemas
class ConnectionInfo(BaseModel):
    qdrant_url: str = Field(default="http://localhost:6333", description="URL of the Qdrant server")
    qdrant_api_key: Optional[str] = Field(default=None, description="API key for Qdrant authentication")

class EmbeddingProviderConfig(BaseModel):
    provider: str = Field(description="Embedding provider ('ollama', 'azure', or 'gemini')")
    config_override: Optional[Dict[str, Any]] = Field(default=None, description="Configuration overrides for the provider")

class ProcessDocumentRequest(BaseModel):
    collection_name: Optional[str] = Field(default=None, description="Optional custom collection name")
    force_recreate: bool = Field(default=False, description="Whether to recreate the collection if it exists")

# Global QdrantDocManager instance
document_manager = None

def get_document_manager():
    """
    Lazy initialization of the QdrantDocManager
    """
    global document_manager
    if document_manager is None:
        document_manager = QdrantDocManager()
    return document_manager


@app.get("/qdrant", tags=["Status"])
async def root():
    """
    Root endpoint that returns API status.
    
    Returns:
        dict: Status information
        
    Example Return:
        ```json
        {
            "status": "ok",
            "message": "Qdrant Document Manager API is running",
            "version": "1.0.0"
        }
        ```
    """
    return {
        "status": "ok",
        "message": "Qdrant Document Manager API is running",
        "version": "1.0.0"
    }

@app.get("/qdrant/connection/test", tags=["Connection Management"])
async def test_connection():
    """
    Test the connection to the Qdrant server.
    
    Args:
        conn_info (ConnectionInfo, optional): Connection information. If not provided, uses current connection.
    
    Returns:
        dict: Connection test results
        
    Example Return:
        ```json
        {
            "success": true,
            "message": "Connection successful! Server has 5 collections",
            "collections_count": 5
        }
        ```
        
    Raises:
        HTTPException: If the connection test fails
        
    Example CURL:
        ```bash
        curl -X GET "http://localhost:8000/qdrant/connection/test"
        ```
    """
    dm = get_document_manager()
    
    try:
        conn = dm.test_connection()
        
        if conn:
            # Get collections count
            collections = dm.list_collections()
            return {
                "success": True,
                "message": f"Connection successful! Server has {len(collections)} collections",
                "collections_count": len(collections)
            }
        else:
            raise HTTPException(status_code=500, detail="Connection test failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection error: {str(e)}")

@app.post("/qdrant/embedding/provider", tags=["Embedding Management"])
async def update_embedding_provider(
    config: EmbeddingProviderConfig = Body(...)
):
    """
    Update the embedding provider and related settings.
    
    Args:
        config (EmbeddingProviderConfig): New embedding provider configuration
    
    Returns:
        dict: Update status
        
    Example Return:
        ```json
        {
            "success": true,
            "message": "Successfully updated embedding provider to: azure",
            "provider": "azure"
        }
        ```
        
    Raises:
        HTTPException: If the update fails
        
    Example CURL:
        ```bash
        # Update to Azure provider
        curl -X POST "http://localhost:8000/qdrant/embedding/provider" \\
            -H "Content-Type: application/json" \\
            -d '{
                "provider": "azure",
                "config_override": {
                    "azure_api_key": "your-api-key",
                    "azure_api_base": "https://your-endpoint.openai.azure.com",
                    "azure_embedding_deployment": "text-embedding-ada-002"
                }
            }'
            
        # Update to Ollama provider
        curl -X POST "http://localhost:8000/qdrant/embedding/provider" \\
            -H "Content-Type: application/json" \\
            -d '{
                "provider": "ollama"
            }'
        ```
    """
    dm = get_document_manager()
    
    try:
        success = dm.update_embedding_provider(
            provider=config.provider,
            config_override=config.config_override
        )
        
        if success:
            return {
                "success": True,
                "message": f"Successfully updated embedding provider to: {config.provider}",
                "provider": config.provider
            }
        else:
            raise HTTPException(status_code=400, detail=f"Failed to update embedding provider")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating embedding provider: {str(e)}")

@app.get("/qdrant/collections", tags=["Collections"])
async def list_collections():
    """
    List all collections in the Qdrant database.
    
    Returns:
        dict: List of collections and their count
        
    Example Return:
        ```json
        {
            "collections": ["document1", "user_guide", "technical_specs"],
            "count": 3
        }
        ```
        
    Example CURL:
        ```bash
        curl -X GET "http://localhost:8000/collections"
        ```
    """
    dm = get_document_manager()
    
    try:
        collections = dm.list_collections()
        return {
            "collections": collections,
            "count": len(collections)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing collections: {str(e)}")

@app.delete("/qdrant/collections/delete/{collection_name}", tags=["Collections"])
async def delete_collection(collection_name: str):
    """
    Delete a specific collection.
    
    Args:
        collection_name (str): Name of the collection to delete
    
    Returns:
        dict: Deletion status
        
    Example Return:
        ```json
        {
            "success": true,
            "message": "Successfully deleted collection: document1"
        }
        ```
        
    Raises:
        HTTPException: If the collection doesn't exist or deletion fails
        
    Example CURL:
        ```bash
        curl -X DELETE "http://localhost:8000/qdrant/deletecollection/COLLECTION_NAME"
        ```
    """
    dm = get_document_manager()
    
    try:
        success = dm.delete_collection(collection_name)
        
        if success:
            return {
                "success": True,
                "message": f"Successfully deleted collection: {collection_name}"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' does not exist or could not be deleted")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting collection: {str(e)}")

@app.get("/qdrant/collections/{collection_name}/points", tags=["Points"])
async def get_collection_points(
    collection_name: str,
    limit: int = Query(default=100, ge=1, le=1000),
    with_payload: bool = Query(default=True),
    with_vectors: bool = Query(default=False)
):
    """
    Get points from a specific collection.
    
    Args:
        collection_name (str): Name of the collection
        limit (int, optional): Maximum number of points to retrieve. Defaults to 100.
        with_payload (bool, optional): Whether to include payload data. Defaults to True.
        with_vectors (bool, optional): Whether to include vector data. Defaults to False.
    
    Returns:
        dict: Collection points and metadata
        
    Example Return:
        ```json
        {
            "points": [
                {
                    "id": "point_123",
                    "payload": {
                        "page_content": "This is the document content...",
                        "filename": "document.pdf",
                        "source": "/path/to/document.pdf"
                    },
                    "vector": [0.1, 0.2, 0.3, ...],
                    "vector_dimension": 384,
                    "payload_summary": {
                        "keys": ["page_content", "filename", "source"],
                        "content_preview": {
                            "page_content": "This is the document content...",
                            "filename": "document.pdf"
                        }
                    }
                },
                {...}
            ],
            "count": 2
        }
        ```
        
    Raises:
        HTTPException: If the collection doesn't exist
        
    Example CURL:
        ```bash
        curl -X GET "http://localhost:8000/qdrant/collections/COLLECTION_NAME/points?limit=10&with_vectors=true"
        ```
    """
    dm = get_document_manager()
    
    try:
        points = dm.get_collection_points(
            collection_name=collection_name,
            limit=limit,
            with_payload=with_payload,
            with_vectors=with_vectors
        )
        
        if points is None:
            points = []
            
        return {
            "points": points,
            "count": len(points)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting collection points: {str(e)}")

@app.get("/qdrant/collections/{collection_name}/points/{point_id}", tags=["Points"])
async def get_point_details(collection_name: str, point_id: str):
    """
    Get detailed information about a specific point.
    
    Args:
        collection_name (str): Name of the collection containing the point
        point_id (str): ID of the specific point to retrieve
    
    Returns:
        dict: Detailed point information
        
    Example Return:
        ```json
        {
            "id": "point_123",
            "payload": {
                "page_content": "This is the full document content that was embedded...",
                "filename": "user_manual.pdf",
                "source": "/documents/user_manual.pdf"
            },
            "vector": [0.123, -0.456, 0.789, ...],
            "vector_dimension": 384,
            "payload_analysis": {
                "total_keys": 3,
                "key_types": {
                    "page_content": "str",
                    "filename": "str", 
                    "source": "str"
                },
                "content_lengths": {
                    "page_content": 1247,
                    "filename": 16,
                    "source": 28
                }
            }
        }
        ```
        
    Raises:
        HTTPException: If the point or collection doesn't exist
        
    Example CURL:
        ```bash
        curl -X GET "http://localhost:8000/qdrant/collections/COLLECTION_NAME/points/POINT_ID"
        ```
    """
    dm = get_document_manager()
    
    try:
        point = dm.get_point_details(collection_name, point_id)
        
        if not point:
            raise HTTPException(status_code=404, detail=f"Point '{point_id}' not found in collection '{collection_name}'")
            
        return point
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting point details: {str(e)}")

@app.post("/qdrant/document/upload", tags=["Document Processing"])
async def process_document(
    file: UploadFile = File(...),
    force_recreate: bool = True,
):
    """
    Upload and process a document, storing its embeddings in Qdrant.
    
    Args:
        file (UploadFile): The document file to process
        force_recreate (bool): Whether to recreate the collection if it exists
    
    Returns:
        dict: Processing status and collection information
        
    Example Return:
        ```json
        {
            "success": true,
            "file_path": "docs/user_manual.pdf"
        }
        ```
        
    Raises:
        HTTPException: If the file upload or processing fails
        
    Example CURL:
        ```bash
        curl -X POST "http://localhost:8000/qdrant/document/upload" \
            -F "file=@/path/to/document.pdf" \
            -F "force_recreate=false" \
        ```
    """
    dm = get_document_manager()
    
    # Check file extension
    allowed_extensions = ['.pdf', '.md', '.txt', '.csv', '.json', '.xml']
    file_extension = Path(file.filename).suffix.lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file extension: {file_extension}. Allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Create docs directory if it doesn't exist
        docs_dir = Path("docs")
        docs_dir.mkdir(exist_ok=True)
        
        # Save file to docs directory
        file_path = docs_dir / file.filename
        print(f"Saving file to: {file_path}")
        
        # The crucial step: write the contents of the UploadFile to the new file
        # Using a sync operation with a thread pool to avoid blocking the event loop
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Now that the file is saved, you can process it.
        dm.process_document(file_path=file_path, force_recreate=force_recreate)      

        return {
            "success": True,
            "file_path": str(file_path)
        }
    except Exception as e:
        # Catch and handle exceptions, making sure to include the original error message
        # for better debugging.
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

def _list_directory_files(dir_path):
    """
    Helper function to list files in a directory
    
    Args:
        dir_path (Path): Path to the directory to list files from
        
    Returns:
        list: List of file details
    """
    dir_path.mkdir(exist_ok=True)
    
    files = []
    for file_path in dir_path.glob("*"):
        if file_path.is_file():
            stats = file_path.stat()
            files.append({
                "name": file_path.name,
                "path": str(file_path),
                "size_bytes": stats.st_size,
                "last_modified": datetime.fromtimestamp(stats.st_mtime).isoformat()
            })
    
    return files

@app.get("/qdrant/list/files", tags=["File Management"])
async def list_files(directory: str = Query(default="docs", enum=["src", "docs"])):
    """
    List all files in the specified directory (either 'src' or 'docs').
    
    Args:
        directory (str): The directory to list files from. Must be either 'src' or 'docs'.
    
    Returns:
        dict: List of files in the specified directory
        
    Example Return:
        ```json
        {
            "directory": "docs",
            "files": [
                {
                    "name": "document1.pdf",
                    "path": "docs/document1.pdf",
                    "size_bytes": 12345,
                    "last_modified": "2023-07-01T10:30:45"
                },
                {
                    "name": "document2.txt",
                    "path": "docs/document2.txt",
                    "size_bytes": 5678,
                    "last_modified": "2023-07-02T14:20:30"
                }
            ],
            "count": 2
        }
        ```
        
    Example CURL:
        ```bash
        curl -X GET "http://localhost:8000/qdrant/list/files?directory=docs"
        curl -X GET "http://localhost:8000/qdrant/list/files?directory=src"
        ```
    """
    try:
        # Validate directory parameter
        if directory not in ["src", "docs"]:
            raise HTTPException(status_code=400, detail="Directory parameter must be either 'src' or 'docs'")
        
        dir_path = Path(directory)
        files = _list_directory_files(dir_path)
        
        return {
            "directory": directory,
            "files": files,
            "count": len(files)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
