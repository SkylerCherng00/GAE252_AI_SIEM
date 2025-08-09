import requests
import argparse
from pathlib import Path
from typing import List

class LogAnalyzer:
    """
    A tool for analyzing log files by sending them to an analysis API endpoint.
    
    This class finds log files in a specified directory and sends them to
    the log analysis API for processing.
    """
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Initialize the LogAnalyzer with the API URL.
        
        Args:
            api_url: Base URL of the log analysis API
        """
        self.api_url = api_url
        self.upload_endpoint = f"{api_url}/agent/analyze-logs/upload"
    
    def get_log_files(self, log_dir: Path) -> List[Path]:
        """
        Get a list of log files from the specified directory.
        
        Args:
            log_dir: Directory containing log files
            
        Returns:
            List of Path objects pointing to log files
        """
        # Ensure the directory exists
        if not log_dir.exists() or not log_dir.is_dir():
            print(f"Error: Directory '{log_dir}' does not exist or is not a directory.")
            return []
        
        # Get all files with common log extensions
        log_files = []
        for ext in ['.log', '.txt', '.csv', '.json']:
            log_files.extend(log_dir.glob(f"*{ext}"))
        
        return log_files
    
    def analyze_log_file(self, file_path: Path, language_code: str = 'zh') -> dict:
        """
        Send a log file to the analysis API and return the response.
        
        Args:
            file_path: Path to the log file
            language_code: Language for the analysis output ('zh' or 'en')
            
        Returns:
            API response as a dictionary
        """
        if not file_path.exists():
            print(f"Error: File '{file_path}' does not exist.")
            return {"success": False, "message": f"File not found: {file_path}"}
        
        try:
            # Prepare the file for upload
            with open(file_path, 'rb') as file:
                files = {'file': (file_path.name, file, 'text/plain')}
                params = {'language_code': language_code}
                
                # Send the file to the API
                print(f"Sending file '{file_path.name}' to {self.upload_endpoint}")
                response = requests.post(self.upload_endpoint, files=files, params=params)
                
                # Check if the request was successful
                if response.status_code == 200:
                    return response.json()
                else:
                    error_msg = f"API returned error {response.status_code}: {response.text}"
                    print(f"Error: {error_msg}")
                    return {"success": False, "message": error_msg}
                
        except Exception as e:
            error_msg = f"Failed to analyze log file: {str(e)}"
            print(f"Error: {error_msg}")
            return {"success": False, "message": error_msg}
    
    def process_directory(self, log_dir: Path, language_code: str = 'zh') -> List[dict]:
        """
        Process all log files in the specified directory.
        
        Args:
            log_dir: Directory containing log files
            language_code: Language for the analysis output ('zh' or 'en')
            
        Returns:
            List of API responses for each file
        """
        log_files = self.get_log_files(log_dir)
        
        if not log_files:
            print(f"No log files found in '{log_dir}'.")
            return []
        
        print(f"Found {len(log_files)} log files in '{log_dir}'.")
        
        results = []
        for file_path in log_files:
            print(f"Processing file: {file_path.name}")
            result = self.analyze_log_file(file_path, language_code)
            results.append({
                "file": str(file_path),
                "result": result
            })
            
            # Print a summary of the result
            status = "Success" if result.get("success", False) else "Failed"
            print(f"  {status}: {result.get('message', 'No message')}")
            print()
            
        return results

def main():
    """
    Main function to run the log analyzer from command line.
    """
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='Analyze log files using the log analysis API.')
    parser.add_argument('--dir', type=str, default='validation/logs',
                       help='Directory containing log files (default: validation/logs)')
    parser.add_argument('--api', type=str, default='http://localhost:8000',
                       help='Base URL of the log analysis API (default: http://localhost:8000)')
    parser.add_argument('--lang', type=str, choices=['zh', 'en'], default='zh',
                       help='Language for analysis output (zh or en, default: zh)')
    
    args = parser.parse_args()
    
    # Initialize the log analyzer
    analyzer = LogAnalyzer(api_url=args.api)
    
    # Get the absolute path to the log directory
    # First, get the directory where this script is located
    script_dir = Path(__file__).parent.absolute()
    log_dir = script_dir / args.dir
    
    print(f"Analyzing log files in directory: {log_dir}")
    
    # Process all log files in the directory
    results = analyzer.process_directory(log_dir, args.lang)
    
    # Print summary
    print("\n=== Summary ===")
    print(f"Total files processed: {len(results)}")
    success_count = sum(1 for r in results if r['result'].get('success', False))
    print(f"Successful analyses: {success_count}")
    print(f"Failed analyses: {len(results) - success_count}")

if __name__ == "__main__":
    main()
