import pymongo
import requests
from typing import Dict, List, Any, Union
from .endpoint import endpoint_url, get_timestamp

# HTTP Endpoint
CONFIG_FACTORY_URL = endpoint_url + "config_mongodb"

class MongoDBHandler:
    """
    A class to handle MongoDB operations including connecting to the database,
    creating collections, inserting data, and querying data.
    """
    _instance = None
    
    def __new__(cls):
        """
        Create a singleton instance of the factory
        
        """
        if cls._instance is None:
            cls._instance = super(MongoDBHandler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_name: str = "gae252_siem"):
        """
        Initialize the MongoDB handler with connection string and database name.
        
        Args:
            connection_string: MongoDB connection string
            db_name: Name of the database to connect to
        """
        # Only initialize once
        if self._initialized:
            return
        try:
            # Fetch configuration from HTTP endpoint
            response = requests.get(CONFIG_FACTORY_URL, timeout=5)
            if response.status_code == 200:
                self.config = response.json().get('configs')
                print(f"{get_timestamp()} - INFO - util_mongodb.py MongoDBHandler.__init__() - Configuration loaded from API: {CONFIG_FACTORY_URL}")
                
            else:
                print(f"{get_timestamp()} - ERROR - util_mongodb.py MongoDBHandler.__init__() - Failed to fetch configuration from API: {response.status_code}")
            connection_string = self.config.get('Mongodb', '').get('connection_string', '')
            self.client = pymongo.MongoClient(connection_string)
            self.db = self.client[db_name]
            self.client.server_info()
            print(f"{get_timestamp()} - INFO - util_mongodb.py MongoDBHandler.__init__() - Successfully connected to MongoDB: {db_name}")
            
        except pymongo.errors.ServerSelectionTimeoutError as e:
            print(f"{get_timestamp()} - ERROR - util_mongodb.py MongoDBHandler.__init__() - Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            print(f"{get_timestamp()} - ERROR - util_mongodb.py MongoDBHandler.__init__() - An error occurred while connecting to MongoDB: {e}")
            raise
        except Exception as e:
            print(f"{get_timestamp()} - ERROR - util_mongodb.py MongoDBHandler.__init__() - Error occurred while initialization: {e}")
            raise
        finally:
            self._initialized = True
    
    def create_collection(self, collection_name: str) -> bool:
        """
        Create a new collection in the database if it doesn't exist.
        
        Args:
            collection_name: Name of the collection to create
            
        Returns:
            bool: True if collection was created or already exists, False otherwise
        """
        try:
            # Check if collection already exists
            if collection_name in self.db.list_collection_names():
                print(f"{get_timestamp()} - INFO - util_mongodb.py MongoDBHandler.create_collection() - Collection '{collection_name}' already exists")
                return True
            
            # Create collection
            self.db.create_collection(collection_name)
            print(f"{get_timestamp()} - INFO - util_mongodb.py MongoDBHandler.create_collection() - Collection '{collection_name}' created successfully")
            return True
        except Exception as e:
            print(f"{get_timestamp()} - ERROR - util_mongodb.py MongoDBHandler.create_collection() - Failed to create collection '{collection_name}': {e}")
            return False
    
    def insert_data(self, collection_name: str, data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> bool:
        """
        Insert one or multiple documents into a specified collection.
        
        Args:
            collection_name: Name of the collection to insert data into
            data: A dictionary or list of dictionaries representing the document(s) to insert
            
        Returns:
            bool: True if insertion was successful, False otherwise
        """
        try:
            collection = self.db[collection_name]
            
            # Handle single document or multiple documents
            if isinstance(data, dict):
                result = collection.insert_one(data)
                print(f"{get_timestamp()} - INFO - util_mongodb.py MongoDBHandler.insert_data() - Document inserted with ID: {result.inserted_id}")
            elif isinstance(data, list):
                result = collection.insert_many(data)
                print(f"{get_timestamp()} - INFO - util_mongodb.py MongoDBHandler.insert_data() - Inserted {len(result.inserted_ids)} documents")
            else:
                print(f"{get_timestamp()} - ERROR - util_mongodb.py MongoDBHandler.insert_data() - Data must be a dictionary or a list of dictionaries")
                return False
                
            return True
        except Exception as e:
            print(f"{get_timestamp()} - ERROR - util_mongodb.py MongoDBHandler.insert_data() - Failed to insert data into '{collection_name}': {e}")
            return False
    
    def query_data(self, collection_name: str, query: Dict[str, Any] = None, 
                   projection: Dict[str, Any] = None, limit: int = 0,
                   sort: List[tuple] = None) -> List[Dict[str, Any]]:
        """
        Query documents from a specified collection.
        
        Args:
            collection_name: Name of the collection to query
            query: Dictionary specifying the query criteria
            projection: Dictionary specifying the fields to include/exclude
            limit: Maximum number of documents to return (0 for no limit)
            sort: List of (key, direction) pairs for sort order
            
        Returns:
            List of documents matching the query criteria
        """
        try:
            collection = self.db[collection_name]
            
            # Default to empty query if None provided
            if query is None:
                query = {}
                
            # Execute query with optional parameters
            cursor = collection.find(query, projection)
            
            # Apply sort if provided
            if sort:
                cursor = cursor.sort(sort)
                
            # Apply limit if provided
            if limit > 0:
                cursor = cursor.limit(limit)
                
            # Convert cursor to list
            result = list(cursor)
            print(f"{get_timestamp()} - INFO - util_mongodb.py MongoDBHandler.query_data() - Query returned {len(result)} documents from '{collection_name}'")
            return result
        except Exception as e:
            print(f"{get_timestamp()} - ERROR - util_mongodb.py MongoDBHandler.query_data() - Failed to query data from '{collection_name}': {e}")
            return []
    
    def update_data(self, collection_name: str, query: Dict[str, Any], 
                    update_data: Dict[str, Any], upsert: bool = False) -> bool:
        """
        Update documents in a specified collection.
        
        Args:
            collection_name: Name of the collection to update
            query: Dictionary specifying which documents to update
            update_data: Dictionary specifying the update operations
            upsert: If True, create a new document when no document matches the query
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            collection = self.db[collection_name]
            
            # Ensure update_data has proper operator
            if not any(key.startswith('$') for key in update_data.keys()):
                update_data = {'$set': update_data}
            
            result = collection.update_many(query, update_data, upsert=upsert)
            print(f"{get_timestamp()} - INFO - util_mongodb.py MongoDBHandler.update_data() - Updated {result.modified_count} documents in '{collection_name}'")
            return True
        except Exception as e:
            print(f"{get_timestamp()} - ERROR - util_mongodb.py MongoDBHandler.update_data() - Failed to update data in '{collection_name}': {e}")
            return False
    
    def delete_data(self, collection_name: str, query: Dict[str, Any]) -> bool:
        """
        Delete documents from a specified collection.
        
        Args:
            collection_name: Name of the collection to delete from
            query: Dictionary specifying which documents to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            collection = self.db[collection_name]
            result = collection.delete_many(query)
            print(f"{get_timestamp()} - INFO - util_mongodb.py MongoDBHandler.delete_data() - Deleted {result.deleted_count} documents from '{collection_name}'")
            return True
        except Exception as e:
            print(f"{get_timestamp()} - ERROR - util_mongodb.py MongoDBHandler.delete_data() - Failed to delete data from '{collection_name}': {e}")
            return False
    
    def close_connection(self) -> None:
        """
        Close the MongoDB connection.
        """
        try:
            self.client.close()
            print(f"{get_timestamp()} - INFO - util_mongodb.py MongoDBHandler.close_connection() - MongoDB connection closed")
        except Exception as e:
            print(f"{get_timestamp()} - ERROR - util_mongodb.py MongoDBHandler.close_connection() - Error closing MongoDB connection: {e}")

def main():
    """
    Main function demonstrating MongoDB operations.
    """
    # Create a MongoDB handler instance
    mongo_handler = MongoDBHandler()
    
    # Example 1: Create a collection
    collection_name = "security_events"
    mongo_handler.create_collection(collection_name)
    
    # Example 2: Insert a single document
    event_data = {
        "timestamp": "2025-08-05T12:34:56Z",
        "source_ip": "192.168.1.100",
        "destination_ip": "10.0.0.5",
        "event_type": "login_attempt",
        "status": "failed",
        "user": "admin",
        "details": {
            "attempt_count": 3,
            "location": "Unknown"
        }
    }
    mongo_handler.insert_data(collection_name, event_data)
    
    # Example 3: Insert multiple documents
    events_data = [
        {
            "timestamp": "2025-08-05T12:40:00Z",
            "source_ip": "192.168.1.101",
            "destination_ip": "10.0.0.5",
            "event_type": "login_attempt",
            "status": "success",
            "user": "user1",
            "details": {
                "location": "New York"
            }
        },
        {
            "timestamp": "2025-08-05T12:45:30Z",
            "source_ip": "192.168.1.102",
            "destination_ip": "10.0.0.6",
            "event_type": "file_access",
            "status": "success",
            "user": "user2",
            "details": {
                "file_path": "/sensitive/data.txt",
                "operation": "read"
            }
        }
    ]
    mongo_handler.insert_data(collection_name, events_data)
    
    # Example 4: Query all documents in a collection
    all_events = mongo_handler.query_data(collection_name)
    print(f"main() - All events: {len(all_events)}")
    
    # Example 5: Query with specific criteria
    failed_logins = mongo_handler.query_data(
        collection_name, 
        query={"event_type": "login_attempt", "status": "failed"}
    )
    print(f"main() - Failed login attempts: {len(failed_logins)}")
    
    # Example 6: Query with projection (include only specific fields)
    login_sources = mongo_handler.query_data(
        collection_name,
        query={"event_type": "login_attempt"},
        projection={"source_ip": 1, "status": 1, "_id": 0}
    )
    print("main() - Login sources:")
    for login in login_sources:
        print(f"  main() - Source IP: {login['source_ip']}, Status: {login['status']}")
    
    # Example 7: Update data
    mongo_handler.update_data(
        collection_name,
        query={"user": "admin"},
        update_data={"$set": {"status": "investigated"}}
    )
    
    # Example 8: Delete data
    # mongo_handler.delete_data(
    #     collection_name,
    #     query={"event_type": "file_access"}
    # )
    
    # Close connection when done
    mongo_handler.close_connection()

if __name__ == "__main__":
    # You need to install pymongo first:
    # pip install pymongo
    main()