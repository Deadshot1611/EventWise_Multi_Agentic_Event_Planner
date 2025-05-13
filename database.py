import os
import uuid
import json
import logging
import re
from datetime import datetime
import bcrypt
import pymongo
from pymongo import MongoClient
from bson.binary import UuidRepresentation
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_mongo_client():
    """Create and return a MongoDB client with proper UUID representation"""
    mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
    client = MongoClient(mongo_uri, uuidRepresentation="standard")
    return client

class UserManager:
    """Class to handle user registration, login and management"""
    
    def __init__(self):
        """Initialize the user manager with database connection"""
        self.client = get_mongo_client()
        self.db = self.client.EventWise
        self.user_collection = self.db.user_details
    
    def register_user(self, email, password, name):
        """Register a new user"""
        # Check if email already exists
        if self.user_collection.find_one({"email": email}):
            return {"success": False, "message": "Email already registered"}
        
        # Hash the password
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt)
        
        # Generate a unique user ID
        uid = f"usr_{uuid.uuid4().hex[:12]}"
        
        # Create user document
        user_doc = {
            "uid": uid,
            "email": email,
            "password": hashed_password,
            "name": name,
            "created_at": datetime.now()
        }
        
        # Insert into database
        try:
            self.user_collection.insert_one(user_doc)
            return {"success": True, "uid": uid, "message": "Registration successful"}
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return {"success": False, "message": f"Registration failed: {str(e)}"}
    
    def login_user(self, email, password):
        """Login a user"""
        # Find user by email
        user = self.user_collection.find_one({"email": email})
        if not user:
            return {"success": False, "message": "Email not found"}
        
        # Verify password
        password_bytes = password.encode('utf-8')
        stored_password = user["password"]
        
        if bcrypt.checkpw(password_bytes, stored_password):
            return {
                "success": True, 
                "uid": user["uid"], 
                "name": user["name"],
                "message": "Login successful"
            }
        else:
            return {"success": False, "message": "Incorrect password"}
    
    def get_user_by_uid(self, uid):
        """Get user details by UID"""
        user = self.user_collection.find_one({"uid": uid})
        if user:
            # Remove sensitive info
            if "password" in user:
                del user["password"]
            return user
        return None

class EventManager:
    """Class to handle event management operations"""
    
    def __init__(self):
        """Initialize the event manager with database connection"""
        self.client = get_mongo_client()
        self.db = self.client.EventWise
        self.event_collection = self.db.eventdetails
    
    def create_event(self, uid, event_details):
        """Create a new event for the user"""
        # Generate a unique event ID
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        
        # Build the event document
        event_doc = {
            "event_id": event_id,
            "uid": uid,
            "event_name": event_details["event_name"],
            "event_category": event_details["event_category"],
            "event_date": event_details["event_date"],
            "num_guests": event_details["num_guests"],
            "budget": event_details["budget"],
            "location": event_details["location"],
            "created_at": datetime.now(),
            "current_status": "initial_planning",
            "services": [],
            "invitation": None
        }
        
        # Insert into database
        try:
            self.event_collection.insert_one(event_doc)
            return {"success": True, "event_id": event_id, "message": "Event created successfully"}
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return {"success": False, "message": f"Event creation failed: {str(e)}"}
    
    def get_user_events(self, uid):
        """Get all events created by a user"""
        try:
            events = list(self.event_collection.find({"uid": uid}))
            # Format for display - just need basic info
            formatted_events = []
            for event in events:
                formatted_events.append({
                    "event_id": event["event_id"],
                    "event_name": event["event_name"],
                    "event_date": event["event_date"],
                    "location": event["location"],
                    "current_status": event["current_status"],
                    "created_at": event["created_at"]
                })
            return formatted_events
        except Exception as e:
            logger.error(f"Error retrieving user events: {e}")
            return []
    
    def get_event_by_id(self, event_id):
        """Get event details by event ID"""
        return self.event_collection.find_one({"event_id": event_id})
    
    def update_services(self, event_id, services):
        """Update the services for an event"""
        try:
            # First get the current status to preserve it
            event = self.get_event_by_id(event_id)
            if not event:
                return {"success": False, "message": "Event not found"}
            
            # Update the services
            self.event_collection.update_one(
                {"event_id": event_id},
                {"$set": {"services": services}}
            )
            return {"success": True, "message": "Services updated successfully"}
        except Exception as e:
            logger.error(f"Error updating services: {e}")
            return {"success": False, "message": f"Service update failed: {str(e)}"}
    
    def update_service_provider(self, event_id, service_name, provider_details):
        """Update a specific service provider"""
        try:
            # Find the event
            event = self.get_event_by_id(event_id)
            if not event:
                return {"success": False, "message": "Event not found"}
            
            # Find the service
            services = event.get("services", [])
            service_found = False
            
            for service in services:
                if service["service"].lower() == service_name.lower():
                    # Make sure we have actual provider details before marking as completed
                    if provider_details:
                        service["selected_provider"] = provider_details
                        service["status"] = "completed"
                        service_found = True
                    else:
                        # Don't mark as completed if provider_details is None or empty
                        service["selected_provider"] = None
                        service["status"] = "pending"
                        service_found = True
                    break
            
            if not service_found:
                return {"success": False, "message": f"Service '{service_name}' not found"}
            
            # Update current status
            completed_services = [s["service"] for s in services if s.get("status") == "completed"]
            current_status = f"done {', '.join(completed_services)}" if completed_services else "services_planned"
            
            # Update the event in database
            self.event_collection.update_one(
                {"event_id": event_id},
                {
                    "$set": {
                        "services": services,
                        "current_status": current_status
                    }
                }
            )
            
            return {"success": True, "message": f"Provider for {service_name} updated successfully"}
        except Exception as e:
            logger.error(f"Error updating service provider: {e}")
            return {"success": False, "message": f"Provider update failed: {str(e)}"}
    
    def update_invitation(self, event_id, invitation_data):
        """Update the invitation for an event"""
        try:
            self.event_collection.update_one(
                {"event_id": event_id},
                {"$set": {"invitation": invitation_data}}
            )
            return {"success": True, "message": "Invitation updated successfully"}
        except Exception as e:
            logger.error(f"Error updating invitation: {e}")
            return {"success": False, "message": f"Invitation update failed: {str(e)}"}

# The following functions are helpers for integration with the main code
def authenticate_user():
    """Authenticate a user with login or registration"""
    print("\n=== Event Planner Authentication ===")
    choice = input("Would you like to login or register? (login/register): ").lower()
    
    user_manager = UserManager()
    
    if choice == "register":
        print("\n=== User Registration ===")
        email = input("Email: ")
        
        # Basic email validation
        while not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            print("Invalid email format. Please try again.")
            email = input("Email: ")
        
        name = input("Full Name: ")
        
        # Password with validation
        while True:
            password = input("Password: ")
            confirm_password = input("Confirm Password: ")
            
            if password != confirm_password:
                print("Passwords do not match. Please try again.")
                continue
            
            # Password strength check
            if len(password) < 8:
                print("Password must be at least 8 characters long.")
                continue
                
            if not any(c.isupper() for c in password):
                print("Password must contain at least one uppercase letter.")
                continue
                
            if not any(c.isdigit() for c in password):
                print("Password must contain at least one number.")
                continue
                
            if not any(c in "!@#$%^&*()_-+=<>?/" for c in password):
                print("Password must contain at least one special character.")
                continue
                
            break
        
        result = user_manager.register_user(email, password, name)
        
        if result["success"]:
            print(f"\n{result['message']}")
            return result["uid"], name
        else:
            print(f"\nRegistration failed: {result['message']}")
            return authenticate_user()  # Try again
    
    elif choice == "login":
        print("\n=== User Login ===")
        email = input("Email: ")
        password = input("Password: ")
        
        result = user_manager.login_user(email, password)
        
        if result["success"]:
            print(f"\n{result['message']}")
            return result["uid"], result["name"]
        else:
            print(f"\nLogin failed: {result['message']}")
            retry = input("Would you like to try again? (yes/no): ").lower()
            if retry == "yes":
                return authenticate_user()  # Try again
            else:
                print("Exiting...")
                exit()
    
    else:
        print("Invalid choice. Please enter 'login' or 'register'.")
        return authenticate_user()  # Try again

def show_user_events(uid):
    """Show events created by the user and allow selection"""
    event_manager = EventManager()
    events = event_manager.get_user_events(uid)
    
    if not events:
        print("\nYou don't have any events yet.")
        return None
    
    print("\n=== Your Events ===")
    for i, event in enumerate(events, 1):
        print(f"{i}. {event['event_name']} - {event['event_date']} ({event['location']})")
        print(f"   Status: {event['current_status']}")
        
    print(f"{len(events) + 1}. Create a new event")
    
    while True:
        try:
            choice = int(input("\nSelect an event or create a new one: "))
            if 1 <= choice <= len(events):
                return events[choice - 1]["event_id"]
            elif choice == len(events) + 1:
                return None  # Create new event
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a number.")

def store_event_details(uid, details):
    """Store initial event details in MongoDB"""
    event_manager = EventManager()
    result = event_manager.create_event(uid, details)
    
    if result["success"]:
        print(f"\n{result['message']}")
        return result["event_id"]
    else:
        print(f"\nFailed to store event: {result['message']}")
        return None

def store_services(event_id, service_budget_list):
    """Store the services and budget allocations for an event"""
    event_manager = EventManager()
    
    # Convert to the format we want to store
    services = []
    for item in service_budget_list:
        services.append({
            "service": item["service"],
            "budget": item["budget"],
            "status": "pending",
            "selected_provider": None
        })
    
    result = event_manager.update_services(event_id, services)
    
    if result["success"]:
        print(f"\n{result['message']}")
        return True
    else:
        print(f"\nFailed to store services: {result['message']}")
        return False

def store_service_provider(event_id, service_name, provider_details):
    """Store the selected service provider for a service"""
    event_manager = EventManager()
    result = event_manager.update_service_provider(event_id, service_name, provider_details)
    
    if result["success"]:
        print(f"\n{result['message']}")
        return True
    else:
        print(f"\nFailed to store provider: {result['message']}")
        return False

def store_invitation(event_id, invitation_data):
    """Store the invitation details for an event"""
    event_manager = EventManager()
    result = event_manager.update_invitation(event_id, invitation_data)
    
    if result["success"]:
        print(f"\n{result['message']}")
        return True
    else:
        print(f"\nFailed to store invitation: {result['message']}")
        return False

def get_event_venue(event_id):
    """Get the venue details for an event if available"""
    event_manager = EventManager()
    event = event_manager.get_event_by_id(event_id)
    
    if not event:
        return None, None
    
    # Look for venue in services
    services = event.get("services", [])
    for service in services:
        if service["service"].lower() == "venue" and service.get("selected_provider"):
            venue_name = service["selected_provider"].get("name", "")
            venue_address = service["selected_provider"].get("address", "")
            return venue_name, venue_address
    
    return None, None