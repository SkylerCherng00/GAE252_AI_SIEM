import re
from datetime import datetime
from typing import Dict, Any, Optional
from .endpoint import get_timestamp
from .util_mongodb import MongoDBHandler

class ReportIDFactory:
    """
    A singleton class responsible for generating unique report IDs.
    Before generating a new ID, it checks the latest report ID in the 
    LogAnalysisResults collection in MongoDB.
    """
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """
        Create a singleton instance of the factory
        """
        if cls._instance is None:
            cls._instance = super(ReportIDFactory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, mongo_handler: Optional[MongoDBHandler] = None):
        """
        Initialize the ReportIDFactory
        """
        # Only initialize once
        if self._initialized:
            return
        
        try:
            self.mongo_handler = mongo_handler if mongo_handler else MongoDBHandler()
            self._initialized = True
            print(f"{get_timestamp()} - INFO - factory_reportid.py ReportIDFactory.__init__() - ReportIDFactory initialized successfully")
        except Exception as e:
            print(f"{get_timestamp()} - ERROR - factory_reportid.py ReportIDFactory.__init__() - Failed to initialize ReportIDFactory: {e}")
            raise
    
    def _get_latest_report_id(self) -> Optional[str]:
        """
        Query MongoDB to get the latest report ID from LogAnalysisResults collection
        
        Returns:
            Optional[str]: The latest report ID or None if no reports exist
        """
        try:
            # Query the collection and sort by report_id in descending order to get the latest
            # We only need the report_id field, so use projection
            results = self.mongo_handler.query_data(
                collection_name="LogAnalysisResults",
                query={},
                projection={"report_id": 1, "_id": 0},
                limit=1,
                sort=[("report_id", -1)]  # Sort in descending order
            )
            
            if results and len(results) > 0 and "report_id" in results[0]:
                latest_id = results[0]["report_id"]
                print(f"{get_timestamp()} - INFO - factory_reportid.py ReportIDFactory._get_latest_report_id() - Latest report ID found: {latest_id}")
                return latest_id
            else:
                print(f"{get_timestamp()} - INFO - factory_reportid.py ReportIDFactory._get_latest_report_id() - No existing report IDs found")
                return None
                
        except Exception as e:
            print(f"{get_timestamp()} - ERROR - factory_reportid.py ReportIDFactory._get_latest_report_id() - Failed to get latest report ID: {e}")
            return None
    
    def _extract_sequence_number(self, report_id: str) -> int:
        """
        Extract the sequence number from a report ID
        
        Args:
            report_id: The report ID to extract from
            
        Returns:
            int: The sequence number or 0 if parsing fails
        """
        try:
            # Assuming report ID format is: REP-YYYYMMDD-XXXX where XXXX is the sequence
            match = re.search(r'REP-\d{8}-(\d+)', report_id)
            if match:
                return int(match.group(1))
            return 0
        except Exception:
            return 0
    
    def generate_report_id(self) -> str:
        """
        Generate a unique report ID based on the current date and the latest ID in the database
        
        Returns:
            str: A new unique report ID
        """
        try:
            # Get today's date in YYYYMMDD format
            today = datetime.now().strftime('%Y%m%d')
            
            # Get the latest report ID from MongoDB
            latest_id = self._get_latest_report_id()
            
            # Default starting sequence number
            sequence_number = 1
            
            if latest_id:
                # Check if the latest report is from today
                if today in latest_id:
                    # Extract the sequence number and increment it
                    sequence_number = self._extract_sequence_number(latest_id) + 1
            
            # Format: REP-YYYYMMDD-XXXX (XXXX is zero-padded sequence number)
            new_report_id = f"REP-{today}-{sequence_number:04d}"
            
            print(f"{get_timestamp()} - INFO - factory_reportid.py ReportIDFactory.generate_report_id() - Generated new report ID: {new_report_id}")
            return new_report_id
            
        except Exception as e:
            print(f"{get_timestamp()} - ERROR - factory_reportid.py ReportIDFactory.generate_report_id() - Failed to generate report ID: {e}")
            # Fallback report ID in case of error
            fallback_id = f"REP-{datetime.now().strftime('%Y%m%d')}-ERROR"
            return fallback_id
    
    def register_report_id(self, report_data: Dict[str, Any]) -> bool:
        """
        Register a new report ID by inserting it into the MongoDB collection
        
        Args:
            report_data: Dictionary containing report data including report_id
            
        Returns:
            bool: True if registration was successful, False otherwise
        """
        try:
            # Ensure the report data has a report_id
            if "report_id" not in report_data:
                report_data["report_id"] = self.generate_report_id()
            
            # Ensure the report data has a timestamp
            if "timestamp" not in report_data:
                report_data["timestamp"] = datetime.now().isoformat()
            
            # Insert the report data into the collection
            success = self.mongo_handler.insert_data(
                collection_name="LogAnalysisResults",
                data=report_data
            )
            
            if success:
                print(f"{get_timestamp()} - INFO - factory_reportid.py ReportIDFactory.register_report_id() - Report ID registered successfully: {report_data['report_id']}")
            else:
                print(f"{get_timestamp()} - ERROR - factory_reportid.py ReportIDFactory.register_report_id() - Failed to register report ID: {report_data['report_id']}")
            
            return success
        except Exception as e:
            print(f"{get_timestamp()} - ERROR - factory_reportid.py ReportIDFactory.register_report_id() - Error registering report ID: {e}")
            return False


def main():
    """
    Main function demonstrating ReportIDFactory usage
    """
    # Create a ReportIDFactory instance
    report_factory = ReportIDFactory()
    
    # Generate a new report ID
    new_report_id = report_factory.generate_report_id()
    print(f"{get_timestamp()} - INFO - factory_reportid.py main() - Generated report ID: {new_report_id}")
    
    # Example: Register a new report with this ID
    sample_report = {
        "report_id": new_report_id,
        "analysis_type": "security_scan",
        "summary": "Sample security analysis report",
        "details": {
            "threats_detected": 0,
            "scan_duration_seconds": 120
        }
    }
    
    report_factory.register_report_id(sample_report)
    
    # Generate another report ID (should be incremented)
    another_report_id = report_factory.generate_report_id()
    print(f"{get_timestamp()} - INFO - factory_reportid.py main() - Another report ID: {another_report_id}")


if __name__ == "__main__":
    main()