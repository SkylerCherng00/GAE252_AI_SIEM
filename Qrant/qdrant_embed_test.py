from qdrant_embed import QdrantDocManager

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
        
        # 4. Process a directory
        print("\n" + "="*80)
        print("PROCESSING A DIRECTORY")
        print("="*80)
        print(f"Testing directory processing with: src")

        dir_results = manager.process_directory(force_recreate=False)
        
        success_count = sum(1 for result in dir_results.values() if result)
        print(f"Directory processing results: {success_count}/{len(dir_results)} files processed successfully")
        
        # 5. List collections after processing
        print("\n" + "="*80)
        print("LISTING COLLECTIONS AFTER PROCESSING")
        print("="*80)
        updated_collections = manager.list_collections()
        
        new_collections = set(updated_collections) - set(existing_collections)
        print(f"New collections created: {new_collections}")
        
        # 6. Get collection points
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
                
            else:
                print("No points available for testing point details and search")
        else:
            print("No collections available for testing")
        
        # 7. Update embedding provider
        print("\n" + "="*80)
        print("TESTING EMBEDDING PROVIDER UPDATE")
        print("="*80)
        
        # Just test if the method runs without errors using the same provider
        current_provider = manager.embedding_provider
        print(f"Current embedding provider: {current_provider}")
        
        update_result = manager.update_embedding_provider(current_provider)
        print(f"Embedding provider update result: {'Success' if update_result else 'Failed'}")
        
        # 8. Test deleting a collection
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
        
        # 9. Test connection update
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