from datetime import datetime

endpoint_url = "http://msgcenter:10000/config/"
endpoint_rpa_url = "http://rpa:10002/alert"

# Function to get timestamp for print statements
def get_timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')