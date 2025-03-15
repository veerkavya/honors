import requests
import urllib3

# Disable SSL warnings (not recommended for production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

url = "https://api.roboflow.com/parking-system-molsb/workflows/custom-workflow?api_key=4zqgVnC7Tmo6bL3U7sFH"

response = requests.get(url, verify=False)

print(response.text)
