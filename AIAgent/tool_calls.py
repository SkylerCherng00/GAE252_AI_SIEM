from langchain.tools import BaseTool
from typing import Dict

class CurrentTimeTool(BaseTool):
    """
    Tool for retrieving the current time in UTC+8 (Taiwan/China/Singapore) timezone.
    
    This simple tool can be used when timestamp information is needed for logging,
    querying time-based services, or providing time context to the user.
    
    Returns:
        Dict containing the current time in 'YYYY-MM-DD HH:MM:SS' format
    """
    name: str = "current_time"
    description: str = "Get the current time in UTC+8 timezone."
    
    def _run(self, input=None) -> Dict[str, str]:
        """
        Get the current time in UTC+8 timezone.
        
        Returns:
            Dict[str, str]: Dictionary with key 'current_time' and value as the formatted timestamp
        """
        from datetime import datetime, timezone, timedelta
        current_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
        return {"current_time": current_time}

# Export collections of tools for different use cases
tools = [ CurrentTimeTool()]
