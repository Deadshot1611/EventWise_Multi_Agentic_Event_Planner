import os
import logging
import json
import traceback
import sys
import re
from dotenv import load_dotenv
from datetime import datetime

# Import from our modules
from utils import (
    get_event_details,
    parse_services_and_budget, format_services_for_display,
    service_selection_and_search, create_invitation, extract_text_from_crew_output
)
from agents import (
    create_requirements_crew, create_budget_crew, create_service_revision_crew
)
from tools import BudgetParserTool
from database import EventManager, store_event_details, store_services, store_invitation, get_event_venue, authenticate_user, show_user_events

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# ---------------------- Main Execution ----------------------
def main():
    try:
        print("Welcome to the Event Planner AI Assistant!")
        print("This tool will help you plan your event and find suitable venues and vendors.")
        
        # Authentication
        uid, user_name = authenticate_user()
        print(f"\nWelcome, {user_name}!")
        
        # Show user's events or create new one
        event_id = show_user_events(uid)
        
        if event_id:
            # Load existing event
            event_manager = EventManager()
            event = event_manager.get_event_by_id(event_id)
            
            if not event:
                print(f"Error: Could not find event with ID {event_id}")
                return
                
            print(f"\nLoaded event: {event['event_name']}")
            print(f"Date: {event['event_date']}")
            print(f"Location: {event['location']}")
            print(f"Current status: {event['current_status']}")
            
            # Convert event to details format for existing code
            details = {
                "event_name": event["event_name"],
                "event_category": event["event_category"],
                "event_date": event["event_date"],
                "num_guests": event["num_guests"],
                "budget": event["budget"],
                "location": event["location"]
            }
            
            # Check if services are already defined
            if event.get("services"):
                service_budget_list = []
                for service in event["services"]:
                    service_budget_list.append({
                        "service": service["service"],
                        "budget": service["budget"]
                    })
                
                # Display current services and status
                # Display current services and status
                print("\n=== Current Services ===")
                for service in event["services"]:
                    # Determine status based on both status field and presence of selected_provider
                    has_provider = service.get("selected_provider") is not None
                    is_completed = service.get("status") == "completed"
                    
                    # If there's an inconsistency (completed but no provider), fix it
                    if is_completed and not has_provider:
                        status = "⚠️ Marked completed but no provider selected"
                    elif is_completed or has_provider:
                        status = "✅ Completed"
                    else:
                        status = "⏳ Pending"
                    
                    print(f"{service['service']} (Budget: ₹{service['budget']:,}) - {status}")
                    
                    # Show provider if one is selected
                    if has_provider:
                        provider_name = service.get("selected_provider").get("name", "Unknown name")
                        print(f"   Provider: {provider_name}")
                    elif is_completed:
                        print(f"   Warning: No provider details available")
                
                # Ask if user wants to revise services
                revise_services = input("\nWould you like to revise the services or budget allocations? (yes/no): ").lower()
                
                if revise_services == "yes":
                    # Create JSON string from the current service_budget_list
                    current_services_json = json.dumps(service_budget_list)
                    
                    # Get feedback
                    feedback = input("\nWhat would you like to change? (e.g., 'Add a live band', 'Remove photography', 'Increase catering budget'): ")
                    
                    # Analyze feedback and revise services
                    revision_inputs = {
                        "user_feedback": feedback,
                        "current_services": current_services_json
                    }
                    
                    print("\nRevising services based on your feedback...")
                    revision_crew = create_service_revision_crew()
                    revision_output = revision_crew.kickoff(inputs=revision_inputs)
                    revision_results = extract_text_from_crew_output(revision_output)
                    
                    # Update the service_budget_list based on revisions
                    try:
                        revision_data = json.loads(revision_results)
                        
                        # Handle different possible formats of the response
                        if isinstance(revision_data, list) and all(isinstance(item, dict) for item in revision_data):
                            # If we have a list of service dictionaries
                            if all("service" in item and "budget" in item for item in revision_data):
                                service_budget_list = revision_data
                        elif isinstance(revision_data, dict):
                            # If we have an analysis with services_to_add, services_to_remove, etc.
                            if "services_to_add" in revision_data:
                                # Process additions
                                for service in revision_data.get("services_to_add", []):
                                    # Assign default budget
                                    default_budget = int(details["budget"] * 0.05)  # 5% of total budget
                                    service_budget_list.append({"service": service, "budget": default_budget})
                            
                            if "services_to_remove" in revision_data:
                                # Process removals
                                for service in revision_data.get("services_to_remove", []):
                                    service_budget_list = [item for item in service_budget_list if item["service"].lower() != service.lower()]
                            
                            if "services_to_modify" in revision_data:
                                # Process modifications
                                for mod in revision_data.get("services_to_modify", []):
                                    if "service" in mod:
                                        # Find the service to modify
                                        for item in service_budget_list:
                                            if item["service"].lower() == mod["service"].lower():
                                                # Extract budget change if available
                                                if "budget" in mod:
                                                    try:
                                                        item["budget"] = int(mod["budget"])
                                                    except ValueError:
                                                        pass
                                                elif "modification" in mod:
                                                    # Parse modification text for budget adjustments
                                                    if "increase" in mod["modification"].lower():
                                                        item["budget"] = int(item["budget"] * 1.3)  # Increase by 30%
                                                    elif "decrease" in mod["modification"].lower():
                                                        item["budget"] = int(item["budget"] * 0.7)  # Decrease by 30%
                        
                        # Store the updated services in MongoDB if event_id is provided
                        store_services(event_id, service_budget_list)
                        
                    except Exception as e:
                        print(f"Could not process revision results: {str(e)}")
                        print("Keeping current services.")
                
                # Continue with service selection
                service_selection_and_search(service_budget_list, details, event_id)
                
            else:
                # Need to generate services since none exist yet
                print("\nAnalyzing requirements for your event...")
                requirements_crew = create_requirements_crew()
                requirement_output = requirements_crew.kickoff(inputs=details)
                requirement_results = extract_text_from_crew_output(requirement_output)
                
                # Process requirement results
                try:
                    # Try to parse as JSON
                    services_list = json.loads(requirement_results)
                    if isinstance(services_list, list):
                        details["services"] = json.dumps(services_list)
                    else:
                        # If not a list, convert to a list
                        details["services"] = json.dumps([str(services_list)])
                except:
                    # If parsing fails, try to extract services
                    lines = requirement_results.split('\n')
                    service_names = []
                    for line in lines:
                        if (line.strip().startswith('-') or 
                            line.strip().startswith('*') or 
                            re.match(r'^\d+\.', line.strip())):
                            service = re.sub(r'^[-*\d\.]+\s*', '', line.strip())
                            # Extract just the service name if there are colons or other delimiters
                            service = re.sub(r':.*$', '', service).strip()
                            if service:
                                service_names.append(service)
                    
                    if service_names:
                        details["services"] = json.dumps(service_names)
                    else:
                        # Last resort: use event-specific defaults
                        event_type = details["event_category"].lower()
                        if "wedding" in event_type:
                            default_services = ["Venue", "Catering", "Decoration", "Photography", "Music", "Wedding Attire", "Invitations"]
                        elif "birthday" in event_type:
                            default_services = ["Venue", "Catering", "Decoration", "Photography", "Entertainment", "Cake"]
                        elif "corporate" in event_type:
                            default_services = ["Venue", "Catering", "AV Equipment", "Speakers", "Decoration", "Transportation"]
                        else:
                            default_services = ["Venue", "Catering", "Decoration", "Photography", "Entertainment"]
                        
                        details["services"] = json.dumps(default_services)
                
                # Step 2: Allocate budget
                print("\nAllocating budget for your services...")
                budget_crew = create_budget_crew()
                budget_output = budget_crew.kickoff(inputs=details)
                budget_results = extract_text_from_crew_output(budget_output)
                
                # Step 3: Parse the services and budget into a structured format
                service_budget_list = parse_services_and_budget(requirement_results, budget_results)
                
                # Step 4: User approval flow for services and budget
                while True:
                    # Display current services and budget
                    print(format_services_for_display(service_budget_list))
                    
                    # Ask for approval
                    approval = input("\nAre these services and budget allocations acceptable? (yes/no): ").lower()
                    
                    if approval == "yes":
                        # Store approved services in MongoDB
                        store_services(event_id, service_budget_list)
                        break
                    else:
                        # Get feedback for revision
                        feedback = input("\nWhat would you like to change? (e.g., 'Add a live band', 'Remove photography', 'Increase catering budget'): ")
                        
                        # Create JSON string from the current service_budget_list
                        current_services_json = json.dumps(service_budget_list)
                        
                        # Analyze feedback and revise services
                        revision_inputs = {
                            "user_feedback": feedback,
                            "current_services": current_services_json
                        }
                        
                        print("\nRevising services based on your feedback...")
                        revision_crew = create_service_revision_crew()
                        revision_output = revision_crew.kickoff(inputs=revision_inputs)
                        revision_results = extract_text_from_crew_output(revision_output)
                        
                        # Update the service_budget_list based on revisions
                        try:
                            revision_data = json.loads(revision_results)
                            
                            # Process different response formats
                            if isinstance(revision_data, list) and all(isinstance(item, dict) for item in revision_data):
                                if all("service" in item and "budget" in item for item in revision_data):
                                    service_budget_list = revision_data
                            elif isinstance(revision_data, dict):
                                # Process additions, removals, and modifications
                                if "services_to_add" in revision_data:
                                    for service in revision_data.get("services_to_add", []):
                                        default_budget = int(details["budget"] * 0.05)
                                        service_budget_list.append({"service": service, "budget": default_budget})
                                
                                if "services_to_remove" in revision_data:
                                    for service in revision_data.get("services_to_remove", []):
                                        service_budget_list = [item for item in service_budget_list if item["service"].lower() != service.lower()]
                                
                                if "services_to_modify" in revision_data:
                                    for mod in revision_data.get("services_to_modify", []):
                                        if "service" in mod:
                                            for item in service_budget_list:
                                                if item["service"].lower() == mod["service"].lower():
                                                    if "budget" in mod:
                                                        try:
                                                            item["budget"] = int(mod["budget"])
                                                        except ValueError:
                                                            pass
                                                    elif "modification" in mod:
                                                        if "increase" in mod["modification"].lower():
                                                            item["budget"] = int(item["budget"] * 1.3)
                                                        elif "decrease" in mod["modification"].lower():
                                                            item["budget"] = int(item["budget"] * 0.7)
                        except Exception as e:
                            print(f"Could not process revision results: {str(e)}")
                            print("Keeping current services.")
                
                # Once approved, continue with service selection
                service_selection_and_search(service_budget_list, details, event_id)
        else:
            # Create a new event
            details = get_event_details()
            
            # Store the event details
            event_id = store_event_details(uid, details)
            
            if not event_id:
                print("Failed to create event. Exiting...")
                return
                
            # Now follow the same flow as for a new event
            # Step 1: Generate initial services list
            print("\nAnalyzing requirements for your event...")
            requirements_crew = create_requirements_crew()
            requirement_output = requirements_crew.kickoff(inputs=details)
            requirement_results = extract_text_from_crew_output(requirement_output)
            
            # Process requirement results
            try:
                # Try to parse as JSON
                services_list = json.loads(requirement_results)
                if isinstance(services_list, list):
                    details["services"] = json.dumps(services_list)
                else:
                    # If not a list, convert to a list
                    details["services"] = json.dumps([str(services_list)])
            except:
                # If parsing fails, try to extract services
                lines = requirement_results.split('\n')
                service_names = []
                for line in lines:
                    if (line.strip().startswith('-') or 
                        line.strip().startswith('*') or 
                        re.match(r'^\d+\.', line.strip())):
                        service = re.sub(r'^[-*\d\.]+\s*', '', line.strip())
                        # Extract just the service name if there are colons or other delimiters
                        service = re.sub(r':.*$', '', service).strip()
                        if service:
                            service_names.append(service)
                
                if service_names:
                    details["services"] = json.dumps(service_names)
                else:
                    # Last resort: use event-specific defaults
                    event_type = details["event_category"].lower()
                    if "wedding" in event_type:
                        default_services = ["Venue", "Catering", "Decoration", "Photography", "Music", "Wedding Attire", "Invitations"]
                    elif "birthday" in event_type:
                        default_services = ["Venue", "Catering", "Decoration", "Photography", "Entertainment", "Cake"]
                    elif "corporate" in event_type:
                        default_services = ["Venue", "Catering", "AV Equipment", "Speakers", "Decoration", "Transportation"]
                    else:
                        default_services = ["Venue", "Catering", "Decoration", "Photography", "Entertainment"]
                    
                    details["services"] = json.dumps(default_services)
            
            # Step 2: Allocate budget
            print("\nAllocating budget for your services...")
            budget_crew = create_budget_crew()
            budget_output = budget_crew.kickoff(inputs=details)
            budget_results = extract_text_from_crew_output(budget_output)
            
            # Step 3: Parse the services and budget into a structured format
            service_budget_list = parse_services_and_budget(requirement_results, budget_results)
            
            # Step 4: User approval flow for services and budget
            while True:
                # Display current services and budget
                print(format_services_for_display(service_budget_list))
                
                # Ask for approval
                approval = input("\nAre these services and budget allocations acceptable? (yes/no): ").lower()
                
                if approval == "yes":
                    # Store approved services in MongoDB
                    store_services(event_id, service_budget_list)
                    break
                else:
                    # Get feedback for revision
                    feedback = input("\nWhat would you like to change? (e.g., 'Add a live band', 'Remove photography', 'Increase catering budget'): ")
                    
                    # Create JSON string from the current service_budget_list
                    current_services_json = json.dumps(service_budget_list)
                    
                    # Analyze feedback and revise services
                    revision_inputs = {
                        "user_feedback": feedback,
                        "current_services": current_services_json
                    }
                    
                    print("\nRevising services based on your feedback...")
                    revision_crew = create_service_revision_crew()
                    revision_output = revision_crew.kickoff(inputs=revision_inputs)
                    revision_results = extract_text_from_crew_output(revision_output)
                    
                    # Update the service_budget_list based on revisions
                    try:
                        revision_data = json.loads(revision_results)
                        
                        # Process different response formats
                        if isinstance(revision_data, list) and all(isinstance(item, dict) for item in revision_data):
                            if all("service" in item and "budget" in item for item in revision_data):
                                service_budget_list = revision_data
                        elif isinstance(revision_data, dict):
                            # Process additions, removals, and modifications
                            if "services_to_add" in revision_data:
                                for service in revision_data.get("services_to_add", []):
                                    default_budget = int(details["budget"] * 0.05)
                                    service_budget_list.append({"service": service, "budget": default_budget})
                            
                            if "services_to_remove" in revision_data:
                                for service in revision_data.get("services_to_remove", []):
                                    service_budget_list = [item for item in service_budget_list if item["service"].lower() != service.lower()]
                            
                            if "services_to_modify" in revision_data:
                                for mod in revision_data.get("services_to_modify", []):
                                    if "service" in mod:
                                        for item in service_budget_list:
                                            if item["service"].lower() == mod["service"].lower():
                                                if "budget" in mod:
                                                    try:
                                                        item["budget"] = int(mod["budget"])
                                                    except ValueError:
                                                        pass
                                                elif "modification" in mod:
                                                    if "increase" in mod["modification"].lower():
                                                        item["budget"] = int(item["budget"] * 1.3)
                                                    elif "decrease" in mod["modification"].lower():
                                                        item["budget"] = int(item["budget"] * 0.7)
                    except Exception as e:
                        print(f"Could not process revision results: {str(e)}")
                        print("Keeping current services.")
            
            # Once approved, continue with service selection
            service_selection_and_search(service_budget_list, details, event_id)
            
        # Invitation creation
        create_invite = input("\nWould you like to create an invitation for this event? (yes/no): ").lower()
        if create_invite == "yes":
            # Get venue details from MongoDB if available
            venue_name, venue_address = get_event_venue(event_id)
            
            # If no venue found in database, ask user
            if not venue_name:
                print("\nNo venue was selected earlier. Please provide venue details:")
                venue_name = input("Enter venue name: ")
                venue_address = input("Enter venue address: ")
            else:
                # Confirm venue with user
                print(f"\nUsing selected venue: {venue_name}")
                print(f"Address: {venue_address}")
                change_venue = input("Would you like to use a different venue? (yes/no): ").lower()
                if change_venue == "yes":
                    venue_name = input("Enter venue name: ")
                    venue_address = input("Enter venue address: ")
            
            # Create invitation with event details
            event_manager = EventManager()
            event = event_manager.get_event_by_id(event_id)
            
            invitation_result = create_invitation({
                "event_name": event["event_name"],
                "event_type": event["event_category"],
                "event_date": event["event_date"],
                "num_guests": event["num_guests"],
                "venue_name": venue_name,
                "venue_address": venue_address,
                "location": event["location"]
            })
            
            # Store invitation details
            if invitation_result:
                store_invitation(event_id, {
                    "invitation_id": invitation_result["invitation_id"],
                    "pdf_path": invitation_result["pdf_path"],
                    "download_url": invitation_result["download_url"],
                    "created_at": datetime.now()
                })
                
                print(f"\nInvitation created successfully!")
                print(f"PDF saved to: {invitation_result['pdf_path']}")
        
        print("\nThank you for using the Event Planner AI Assistant!")
            
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        print(traceback.format_exc())
        print("\nPlease try again or contact support.")

if __name__ == "__main__":
    main()