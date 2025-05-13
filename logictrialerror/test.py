import os
import asyncio
import signal
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface

# Load environment variables
load_dotenv()

# Get environment variables
AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Create ElevenLabs client
client = ElevenLabs(api_key=API_KEY)

# Set up signal handler for clean exit
def handle_sigint(sig, frame):
    print("\nExiting...")
    exit(0)

signal.signal(signal.SIGINT, signal.SIG_IGN)

# Create test function
async def test_booking_agent():
    # Define booking parameters
    venue_name = "Hotel Thames International"
    date = "2025-09-01"
    guest_count = "30"
    budget = "12000"
    event_type = "birthday party"
    
    print("\n=== AI Booking Agent ===")
    print(f"Calling {venue_name} to book a venue for {event_type}...")
    print(f"Date: {date}, Guests: {guest_count}, Budget: ₹{budget}")
    print("\nStarting the call. Please speak when prompted...")
    print("(Press Ctrl+C to exit)")
    
    try:
        # Create conversation with the agent
        # Note: The correct parameters for Conversation class according to docs
        conversation = Conversation(
            # Pass agent ID directly
            agent_id=AGENT_ID,
            # Use the default audio interface
            audio_interface=DefaultAudioInterface(),
            # Print the conversation to the console with callbacks
            callback_agent_response=lambda response: print(f"Agent: {response}"),
            callback_user_transcript=lambda transcript: print(f"User: {transcript}"),
            # Enable system prompt overrides
            system_prompt_variables={
                "venue_name": venue_name,
                "event_type": event_type,
                "date": date,
                "guest_count": guest_count,
                "budget": budget,
                "phone_number": "8583949261"  # Default test number
            }
        )
        
        # Restore signal handler now that we've set up the conversation
        signal.signal(signal.SIGINT, handle_sigint)
        
        # Start the conversation
        conversation_id = conversation.start()
        print(f"Conversation started with ID: {conversation_id}")
        
        # Wait for the conversation to end
        conversation.wait_for_session_end()
        
        print("\n=== Call Completed ===")
        print(f"Conversation ID: {conversation_id}")
        
        return conversation_id
    
    except Exception as e:
        print(f"\nError during booking call: {str(e)}")
        return None

# Run the test
if __name__ == "__main__":
    asyncio.run(test_booking_agent())