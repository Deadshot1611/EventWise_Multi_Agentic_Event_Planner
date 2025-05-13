import re
import json
import logging
import traceback
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from crewai import Crew, Process

# Import from other files
from agents import (
    requirement_analyzer, budget_allocator, service_reviser,
    vendor_service_coordinator, venue_search_coordinator,
    requirement_task, budget_task, service_revision_task,
    venue_search_task, vendor_search_task,
    create_requirements_crew, create_budget_crew, create_service_revision_crew,
    create_venue_search_crew, create_vendor_search_crew
)
from tools import (
    InvitationCreatorTool, InvitationStylerTool, EmailInvitationTool,
    BudgetParserTool
)
from database import (
    EventManager, UserManager, 
    store_event_details, store_services, store_service_provider,
    store_invitation, get_event_venue
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ---------------------- Helper Functions ----------------------
def parse_services_and_budget(requirement_result, budget_result):
    """Parse the agent outputs to extract services and their budget allocations"""
    services = []
    budget_allocations = {}
    
    # First try to parse requirements output as JSON array
    try:
        services = json.loads(requirement_result)
        if not isinstance(services, list):
            services = []
    except:
        # If JSON parsing fails, try to extract services using regex
        service_matches = re.findall(r'["\']([^"\']+)["\']', requirement_result)
        if service_matches:
            services = [match.strip() for match in service_matches]
        else:
            # Last resort: extract services from numbered/bulleted lists
            lines = requirement_result.split('\n')
            for line in lines:
                if (line.strip().startswith('-') or 
                    line.strip().startswith('*') or 
                    re.match(r'^\d+\.', line.strip())):
                    service = re.sub(r'^[-*\d\.]+\s*', '', line.strip())
                    # Extract just the service name if there are colons or other delimiters
                    service = re.sub(r':.*$', '', service).strip()
                    if service:
                        services.append(service)
    
    # Try to parse budget output as JSON
    try:
        budget_data = json.loads(budget_result)
        if isinstance(budget_data, dict):
            budget_allocations = {k: int(v) for k, v in budget_data.items()}
    except:
        # If JSON parsing fails, try to extract budget items using regex
        for service in services:
            # Look for service name followed by amount
            match = re.search(rf'{re.escape(service)}.*?(\d[\d,.]+)', budget_result, re.IGNORECASE)
            if match:
                amount_str = re.sub(r'[^\d]', '', match.group(1))
                budget_allocations[service] = int(amount_str) if amount_str else 0
    
    # Combine into a single structure
    service_budget_list = []
    for service in services:
        service_budget_list.append({
            "service": service,
            "budget": budget_allocations.get(service, 0)
        })
    
    return service_budget_list

def extract_text_from_crew_output(crew_output):
    """Extract the text content from a CrewOutput object with better error handling"""
    try:
        if crew_output is None:
            logger.warning("Received None output from agent")
            return ""
            
        if hasattr(crew_output, 'raw_output'):
            return crew_output.raw_output or ""
        elif hasattr(crew_output, 'result'):
            return crew_output.result or ""
        elif hasattr(crew_output, 'outputs'):
            # If it's a dict of outputs, join them
            if isinstance(crew_output.outputs, dict):
                # Filter out None values
                valid_outputs = {k: v for k, v in crew_output.outputs.items() if v is not None}
                if not valid_outputs:
                    return ""
                return "\n".join(str(v) for v in valid_outputs.values())
        
        # Fall back to string representation
        return str(crew_output) if crew_output else ""
    except Exception as e:
        logger.error(f"Error extracting text from crew output: {e}")
        return ""  # Return empty string on error
    
def format_services_for_display(services_list):
    """Format the services list for user-friendly display"""
    total = sum(item["budget"] for item in services_list)
    result = "\n=== Services and Budget Allocation ===\n"
    for item in services_list:
        result += f"- {item['service']}: ₹{item['budget']:,}\n"
    result += f"\nTotal Budget: ₹{total:,}"
    return result

def format_venues_for_display(venues_json):
    """Format the venues JSON for user-friendly display"""
    try:
        venues = json.loads(venues_json) if isinstance(venues_json, str) else venues_json
        if not venues or venues == "No venues found matching your criteria." or isinstance(venues, dict) and "error" in venues:
            return "No venues found matching your criteria."
        
        result = "\n=== Venue Recommendations ===\n"
        for i, venue in enumerate(venues, 1):
            # Check for both capitalized and lowercase field names
            name = venue.get('Name', venue.get('name', 'Unnamed Venue'))
            price = venue.get('Price', venue.get('price', venue.get('price_per_plate', 'Not specified')))
            address = venue.get('Address', venue.get('address', 'Not specified'))
            contact = venue.get('Contact', venue.get('contact', 'Not specified'))
            capacity = venue.get('Capacity', venue.get('capacity', 'Not specified'))
            rating = venue.get('Rating', venue.get('rating', 'Not specified'))
            url = venue.get('URL', venue.get('url', venue.get('Website', venue.get('website', None))))
            map_url = venue.get('Map URL', venue.get('map_url', None))
            source = venue.get('Source', venue.get('source', venue.get('source_site', 'Online')))
            
            result += f"{i}. {name}\n"
            result += f"   Price: {price}\n"
            result += f"   Address: {address}\n"
            result += f"   Contact: {contact}\n"
            
            if capacity and capacity != "Not specified":
                result += f"   Capacity: {capacity}\n"
            if rating and rating != "Not specified":
                result += f"   Rating: {rating}\n"
            if url:
                result += f"   Website: {url}\n"
            if map_url:
                result += f"   Map: {map_url}\n"
            result += f"   Source: {source}\n\n"
        return result
    except Exception as e:
        logger.error(f"Error formatting venues: {str(e)}")
        return str(venues_json) if isinstance(venues_json, (str, dict, list)) else "No venues available"

def format_vendors_for_display(vendors_json):
    """Format the vendors JSON for user-friendly display"""
    try:
        vendors = json.loads(vendors_json) if isinstance(vendors_json, str) else vendors_json
        if not vendors or vendors == "No vendors found matching your criteria." or isinstance(vendors, dict) and "error" in vendors:
            return "No vendors found matching your criteria."
        
        result = "\n=== Vendor Recommendations ===\n"
        for i, vendor in enumerate(vendors, 1):
            # Check for both capitalized and lowercase field names
            name = vendor.get('Name', vendor.get('name', 'Unnamed Vendor'))
            service_type = vendor.get('Service_type', vendor.get('service_type', 'Service'))
            price = vendor.get('Price', vendor.get('price', 'Price not specified'))
            address = vendor.get('Address', vendor.get('address', 'Address not specified'))
            contact = vendor.get('Contact', vendor.get('contact', 'Contact not specified'))
            rating = vendor.get('Rating', vendor.get('rating', 'Rating not specified'))
            description = vendor.get('Description', vendor.get('description', ''))
            website = vendor.get('Website', vendor.get('website', 'Website not specified'))
            source = vendor.get('Source', vendor.get('source', 'Online'))
            
            result += f"{i}. {name}\n"
            result += f"   Service: {service_type}\n"
            result += f"   Price: {price}\n"
            result += f"   Contact: {contact}\n"
            
            if address and address != "Address not specified":
                result += f"   Address: {address}\n"
            if rating and rating != "Rating not specified":
                result += f"   Rating: {rating}\n"
            if description:
                result += f"   Description: {description[:100]}...\n"
            if website and website != "Website not specified":
                result += f"   Website: {website}\n"
            result += f"   Source: {source}\n\n"
        return result
    except Exception as e:
        logger.error(f"Error formatting vendors: {str(e)}")
        return str(vendors_json) if isinstance(vendors_json, (str, dict, list)) else "No vendors available"

def display_progress_tracker(selected, pending):
    """Display a progress tracker showing selected and pending services"""
    print("\n=== Planning Progress ===")
    if selected:
        print("✅ Selected services:")
        for service in selected:
            print(f"  • {service}")
    
    if pending:
        print("⏳ Pending services:")
        for service in pending:
            print(f"  • {service}")
    print("=====================")

def select_provider(providers, selected_service):
    """Helper function to select a provider from a list"""
    select_provider = input("\nWould you like to select one of these options? (yes/no): ").lower()
    
    if select_provider == "yes":
        try:
            provider_num = int(input("Enter the number of the option you'd like to select: "))
            if 1 <= provider_num <= len(providers):
                selected_provider = providers[provider_num-1]
                print(f"\nYou've selected: {selected_provider.get('name', selected_provider.get('Name', 'Unknown'))}")
                print(f"Contact: {selected_provider.get('contact', selected_provider.get('Contact', 'Not available'))}")
                
                address = selected_provider.get('address', selected_provider.get('Address'))
                if address:
                    print(f"Address: {address}")
                    
                price_field = selected_provider.get('price', selected_provider.get('Price'))
                if price_field:
                    print(f"Price: {price_field}")
                
                # Store selected provider in the service
                selected_service['selected_provider'] = selected_provider
                return True
            else:
                print("Invalid option number. No selection made.")
                return False
        except ValueError:
            print("Please enter a valid number. No selection made.")
            return False
    return False

def service_selection_and_search(approved_services, details, event_id=None):
    """Function to handle both venue and vendor searches using separate agents"""
    print("\n=== Service Vendor Search ===")
    print("Let's find vendors for your approved services:")

    # Track progress of selected services
    services_selected = []
    services_pending = []
    
    # Properly categorize services based on their status
    for service in approved_services:
        # Check for status or selected_provider in the service data
        if service.get("status") == "completed" or service.get("selected_provider"):
            services_selected.append(service["service"])
        else:
            services_pending.append(service["service"])
    
    # If we don't have status info in approved_services, we need to check differently
    if not any("status" in service for service in approved_services) and event_id:
        # Fetch the event to get accurate status information
        event_manager = EventManager()
        event = event_manager.get_event_by_id(event_id)
        if event and event.get("services"):
            # Reset our tracking lists
            services_selected = []
            services_pending = []
            # Use the event's services data which should have complete status info
            for service in event.get("services", []):
                if service.get("status") == "completed" or service.get("selected_provider"):
                    services_selected.append(service["service"])
                else:
                    services_pending.append(service["service"])
    
    # Display services for selection
    for i, service in enumerate(approved_services, 1):
        status = "✅ Completed" if service["service"] in services_selected else "⏳ Pending"
        print(f"{i}. {service['service']} (Budget: ₹{service['budget']:,}) [{status}]")

    # Ask user which service to find vendors for
    while True:
        # Show progress tracker
        display_progress_tracker(services_selected, services_pending)
        
        if not services_pending:
            print("\nCongratulations! You've selected providers for all services.")
            break
            
        search_vendors = input("\nWould you like to search for vendors for any of these services? (yes/no): ").lower()
        
        if search_vendors != "yes":
            break
            
        try:
            service_num = int(input("Enter the number of the service you'd like to find vendors for: "))
            if 1 <= service_num <= len(approved_services):
                selected_service = approved_services[service_num-1]
                
                # Skip if service is already completed
                if selected_service["service"] in services_selected:
                    print(f"\nYou've already selected a provider for {selected_service['service']}.")
                    continue_search = input("Would you like to search for a different provider? (yes/no): ").lower()
                    if continue_search != "yes":
                        continue
                
                print(f"\nSearching for {selected_service['service']} vendors matching your requirements...")
                print("This might take a few minutes as we search multiple sources...")
                
                # Choose the appropriate agent and task based on the selected service
                if selected_service['service'].lower() == "venue":
                    # Get venue type for venue searches
                    venue_type = input("What type of venue are you looking for? (e.g., banquet hall, restaurant, resort): ")
                    
                    # Create inputs for venue search
                    venue_inputs = {
                        "location": details["location"],
                        "event_category": details["event_category"],
                        "service_budget": selected_service['budget'],
                        "num_guests": details["num_guests"],
                        "venue_type": venue_type
                    }
                    
                    # Use venue search coordinator for venue searches
                    venue_crew = create_venue_search_crew()
                    service_output = venue_crew.kickoff(inputs=venue_inputs)
                    logger.debug(f"Raw venue output: {service_output}")
                    service_results = extract_text_from_crew_output(service_output)
                    logger.debug(f"Extracted venue results: {service_results[:500]}...")
                    
                    # Parse and display venue results
                    try:
                        # First check if we have valid output
                        if not service_results or (isinstance(service_results, str) and service_results.strip() == ""):
                            print("No results returned from the venue search. The agent may have encountered an issue.")
                            continue
                            
                        # Try to parse JSON, but handle various formats gracefully
                        if isinstance(service_results, str):
                            try:
                                venues = json.loads(service_results)
                            except json.JSONDecodeError:
                                # If it's not valid JSON, log the actual content for debugging
                                logger.error(f"Invalid JSON received: {service_results[:200]}...")
                                print("Received invalid data format from venue search. Unable to process results.")
                                continue
                        else:
                            venues = service_results
                        
                        # Check if we got an error message
                        if isinstance(venues, dict) and "error" in venues:
                            print(f"No venues found matching your criteria: {venues['error']}")
                            continue
                            
                        # Validate that venues is a list
                        if not isinstance(venues, list):
                            print("Unexpected data format received. Expected a list of venues.")
                            logger.error(f"Unexpected venue data type: {type(venues)}")
                            continue
                            
                        # Ensure we have at least one venue
                        if not venues:
                            print("No venues found matching your criteria.")
                            continue
                        
                        # Display venue results
                        print(format_venues_for_display(venues))
                        
                        # Ask if user wants to select a venue
                        if select_provider(venues, selected_service):
                            # Store the selected provider in MongoDB if event_id is provided
                            if event_id:
                                store_service_provider(event_id, selected_service['service'], selected_service['selected_provider'])
                            
                            # Update progress tracker if a selection was made
                            if selected_service['service'] not in services_selected:
                                services_selected.append(selected_service['service'])
                            if selected_service['service'] in services_pending:
                                services_pending.remove(selected_service['service'])
                    except Exception as e:
                        # Log full error details for debugging
                        logger.error(f"Error processing venue search results: {str(e)}")
                        logger.error(f"Service results type: {type(service_results)}")
                        if isinstance(service_results, str):
                            logger.error(f"Service results preview: {service_results[:200]}...")
                        print(f"Error processing venue search results: {str(e)}")
                        print("Please try a different service or try again later.")
                else:
                    # Create inputs for vendor search
                    vendor_inputs = {
                        "service_type": selected_service['service'],
                        "location": details["location"],
                        "event_category": details["event_category"],
                        "service_budget": selected_service['budget']
                    }
                    
                    # Use vendor service coordinator for vendor searches
                    vendor_crew = create_vendor_search_crew()
                    service_output = vendor_crew.kickoff(inputs=vendor_inputs)
                    logger.debug(f"Raw vendor output: {service_output}")
                    service_results = extract_text_from_crew_output(service_output)
                    logger.debug(f"Extracted vendor results: {service_results[:500]}...")
                    
                    # Parse and display vendor results
                    try:
                        # First check if we have valid output
                        if not service_results or (isinstance(service_results, str) and service_results.strip() == ""):
                            print("No results returned from the vendor search. The agent may have encountered an issue.")
                            continue
                            
                        # Try to parse JSON, but handle various formats gracefully
                        if isinstance(service_results, str):
                            try:
                                vendors = json.loads(service_results)
                            except json.JSONDecodeError:
                                # If it's not valid JSON, log the actual content for debugging
                                logger.error(f"Invalid JSON received: {service_results[:200]}...")
                                print("Received invalid data format from vendor search. Unable to process results.")
                                continue
                        else:
                            vendors = service_results
                        
                        # Check if we got an error message
                        if isinstance(vendors, dict) and "error" in vendors:
                            print(f"No vendors found matching your criteria: {vendors['error']}")
                            continue
                            
                        # Validate that vendors is a list
                        if not isinstance(vendors, list):
                            print("Unexpected data format received. Expected a list of vendors.")
                            logger.error(f"Unexpected vendor data type: {type(vendors)}")
                            continue
                            
                        # Ensure we have at least one vendor
                        if not vendors:
                            print("No vendors found matching your criteria.")
                            continue
                        
                        # Display vendor results
                        print(format_vendors_for_display(vendors))
                        
                        # Ask if user wants to select a vendor
                        if select_provider(vendors, selected_service):
                            # Store the selected provider in MongoDB if event_id is provided
                            if event_id:
                                store_service_provider(event_id, selected_service['service'], selected_service['selected_provider'])
                            
                            # Update progress tracker if a selection was made
                            if selected_service['service'] not in services_selected:
                                services_selected.append(selected_service['service'])
                            if selected_service['service'] in services_pending:
                                services_pending.remove(selected_service['service'])
                    except Exception as e:
                        # Log full error details for debugging
                        logger.error(f"Error processing vendor search results: {str(e)}")
                        logger.error(f"Service results type: {type(service_results)}")
                        if isinstance(service_results, str):
                            logger.error(f"Service results preview: {service_results[:200]}...")
                        print(f"Error processing vendor search results: {str(e)}")
                        print("Please try a different service or try again later.")
            else:
                print("Invalid service number. Please try again.")
        except ValueError:
            print("Please enter a valid number.")
            
def create_invitation(event_details):
    """
    Create an invitation using predefined event details
    """
    print("\n=== Invitation Creation ===")
    
    # Confirm venue details first
    print(f"\nCurrent venue: {event_details['venue_name']}")
    change_venue = input("Would you like to change the venue name? (yes/no): ").lower()
    
    if change_venue == "yes":
        event_details['venue_name'] = input("Enter the venue name: ")
        event_details['venue_address'] = input("Enter the venue address: ")
    
    # Additional details needed for invitation
    if 'event_time' not in event_details:
        event_details['event_time'] = input("Enter the event time (e.g., 6:00 PM): ")
    
    if 'host_name' not in event_details:
        event_details['host_name'] = input("Enter the host name: ")
    
    if 'rsvp_contact' not in event_details:
        event_details['rsvp_contact'] = input("Enter RSVP contact details (phone/email): ")
    
    if 'special_instructions' not in event_details:
        event_details['special_instructions'] = input("Enter any special instructions (optional): ")
    
    if 'style_preference' not in event_details:
        event_details['style_preference'] = input("Enter style preference (formal/casual/playful/elegant): ")
    
    # Map num_guests to guest_count if needed
    if 'guest_count' not in event_details and 'num_guests' in event_details:
        event_details['guest_count'] = event_details['num_guests']
    
    # Create invitation tool instance
    invitation_tool = InvitationCreatorTool()
    
    # Generate invitation text using Mistral
    print("\nGenerating invitation text using Mistral AI...")
    print("This may take a moment...")
    
    result = invitation_tool._run(
        event_name=event_details['event_name'],
        event_type=event_details['event_type'],
        event_date=event_details['event_date'],
        event_time=event_details['event_time'],
        venue_name=event_details['venue_name'],
        venue_address=event_details['venue_address'],
        host_name=event_details['host_name'],
        guest_count=event_details.get('guest_count') or event_details.get('num_guests', 30),
        special_instructions=event_details.get('special_instructions'),
        rsvp_contact=event_details.get('rsvp_contact'),
        style_preference=event_details.get('style_preference')
    )
    
    if "error" in result:
        print(f"Error creating invitation: {result['error']}")
        return None
    
    # Display the invitation text
    print("\n=== Invitation Preview ===")
    print(result['invitation_text'])
    print("========================")
    
    # Ask for approval
    approval = input("\nIs this invitation text acceptable? (yes/no): ").lower()
    
    if approval != "yes":
        print("Let's try again with some adjustments.")
        feedback = input("What changes would you like to make? ")
        
        # Update style preference based on feedback
        event_details['style_preference'] = event_details.get('style_preference', '') + f". Feedback: {feedback}"
        
        # Regenerate with updated preferences
        return create_invitation(event_details)
    
    # Show style options and get user's choices
    print("\n=== Style Options ===")
    
    # Display color options
    print("\nColor Schemes:")
    for i, color in enumerate(result['color_options'], 1):
        print(f"{i}. {color['name']}: Primary={color['primary']}, Secondary={color['secondary']}, Accent={color['accent']}")
    
    color_choice = int(input("\nSelect a color scheme (number): "))
    selected_color = result['color_options'][color_choice-1]['id']
    
    # Display font options
    print("\nFont Styles:")
    for i, font in enumerate(result['font_options'], 1):
        print(f"{i}. {font['name']}")
    
    font_choice = int(input("\nSelect a font style (number): "))
    selected_font = result['font_options'][font_choice-1]['id']
    
    # Display border options
    print("\nBorder Styles:")
    for i, border in enumerate(result['border_options'], 1):
        print(f"{i}. {border['name']}")
    
    border_choice = int(input("\nSelect a border style (number): "))
    selected_border = result['border_options'][border_choice-1]['id']
    
    # Display background options
    print("\nBackground Colors:")
    for i, bg in enumerate(result['background_options'], 1):
        print(f"{i}. {bg['name']}: {bg['color']}")
    
    bg_choice = int(input("\nSelect a background color (number): "))
    selected_bg = result['background_options'][bg_choice-1]['id']
    
    # Create the styled PDF
    print("\nGenerating styled PDF invitation...")
    styler_tool = InvitationStylerTool()
    style_result = styler_tool._run(
        invitation_id=result['invitation_id'],
        color_scheme=selected_color,
        font_style=selected_font,
        border_style=selected_border,
        background_color=selected_bg
    )
    
    if "error" in style_result:
        print(f"Error styling invitation: {style_result['error']}")
        return None
    
    # Show PDF generation success
    print(f"\nPDF generated successfully: {style_result['pdf_path']}")
    print(f"Download URL: {style_result['download_url']}")
    
    # Ask if user wants to email the invitation
    send_email = input("\nWould you like to email this invitation? (yes/no): ").lower()
    
    if send_email == "yes":
        # Collect email details
        email_subject = input("Enter email subject: ")
        if not email_subject:
            email_subject = f"Invitation to {event_details['event_name']}"
        
        email_addresses_input = input("Enter email addresses (comma-separated): ")
        email_addresses = [email.strip() for email in email_addresses_input.split(",")]
        
        sender_name = input("Enter sender name: ")
        if not sender_name:
            sender_name = event_details['host_name']
        
        additional_message = input("Enter an additional message (optional): ")
        
        cc_addresses_input = input("Enter CC email addresses (comma-separated, optional): ")
        cc_addresses = [email.strip() for email in cc_addresses_input.split(",")] if cc_addresses_input else None
        
        # Send the email
        print("\nSending invitation emails...")
        email_tool = EmailInvitationTool()
        email_result = email_tool._run(
            invitation_id=result['invitation_id'],
            email_subject=email_subject,
            email_addresses=email_addresses,
            sender_name=sender_name,
            additional_message=additional_message,
            cc_addresses=cc_addresses
        )

        if "error" in email_result:
            print(f"Error sending emails: {email_result['error']}")
        else:
            print(f"Success! Invitation sent to {len(email_addresses)} recipients.")
    return {
        "invitation_id": result['invitation_id'],
        "pdf_path": style_result['pdf_path'],
        "download_url": style_result['download_url']
    }

def get_event_details():
    print("\n=== Event Planning ===")
    details = {
        "event_name": input("Event Name: "),
        "event_category": input("Event Type (e.g., wedding, birthday party, corporate event): ").lower(),
        "event_date": input("Date (YYYY-MM-DD): "),
        "num_guests": int(input("Guest Count: ")),
        "raw_budget": input("Budget (e.g., '20k INR', '2L', '₹100,000'): "),
        "location": input("Location (city): ")
    }
    
    # Parse budget
    budget_data = BudgetParserTool()._run(details["raw_budget"])
    details.update({
        "budget": budget_data["converted_INR"],
        "venue_budget": int(budget_data["converted_INR"] * 0.35)  # Allocate 35% for venue
    })
    return details