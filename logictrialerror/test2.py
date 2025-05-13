import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("ELEVENLABS_API_KEY")
AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
PHONE_NUMBER = "+918583949261"  # Use international format

# Custom data to be passed to the agent
custom_data = {
    "venue_name": "Hotel Thames International",
    "event_type": "birthday party",
    "date": "2025-09-01",
    "guest_count": "30",
    "budget": "12000"
}

# Start the call
url = "https://api.elevenlabs.io/v1/telephony/call/agent"
headers = {
    "xi-api-key": API_KEY,
    "Content-Type": "application/json"
}
data = {
    "agent_id": AGENT_ID,
    "phone_number": PHONE_NUMBER,
    "custom_data": custom_data
}

response = requests.post(url, headers=headers, json=data)

# Print the result
if response.status_code == 200:
    print("✅ Call initiated successfully!")
    print(response.json())
else:
    print(f"❌ Failed to initiate call: {response.status_code}")
    print(response.text)
