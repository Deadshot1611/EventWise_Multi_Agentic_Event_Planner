import os
import re
import json
import time
import logging
from crewai import Agent, Task, Crew, Process, LLM
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# Import tools from tools.py
from tools import (
    UniversalVenueServiceTool,
    VendorToolsManager,
    BudgetParserTool,
    ServiceRequestAnalyzerTool
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# ---------------------- LLM Setup ----------------------
llm = LLM(
    model="mistral/mistral-large-latest",
    temperature=0.3
)

# ---------------------- Professional Agents ----------------------
requirement_analyzer = Agent(
    role="Event Requirements Analyst",
    goal="Accurately identify all essential services required for executing a successful event based on the event type and guest count.",
    backstory=(
        "You are a seasoned event planning consultant with years of experience in organizing various events like weddings, birthday parties, corporate functions, and cultural gatherings. "
        "You specialize in breaking down high-level event ideas into practical service needs. "
        "You understand how different event categories and guest sizes impact logistics and can identify only the necessary, standard services required—without suggesting extravagant or niche offerings."
    ),
    llm=llm,
    verbose=True
)

budget_allocator = Agent(
    role="Financial Strategist",
    goal="Optimize budget allocations across services to ensure a successful event while maintaining financial constraints",
    backstory=(
        "You are a financial wizard in the event planning industry with expertise in cost analysis and budget optimization. "
        "You've helped numerous clients distribute their budget effectively across different services, ensuring they get the best value for their money. "
        "You know typical price ranges for various services across different event types and can recommend realistic allocations based on priorities."
    ),
    llm=llm,
    verbose=True
)

service_reviser = Agent(
    role="Service Customization Specialist",
    goal="Adjust services based on client feedback to perfectly match their vision and preferences",
    backstory=(
        "You are an expert in tailoring event services to client needs with years of experience in refining event plans. "
        "You have a knack for understanding what clients want even when their requests are vague, and you can translate their feedback into actionable changes. "
        "You're skilled at finding the right balance between client wishes and practical constraints, ensuring the event plan remains coherent and executable."
    ),
    tools=[ServiceRequestAnalyzerTool()],
    llm=llm,
    verbose=True
)

vendor_service_coordinator = Agent(
    role="Vendor Service Coordinator", 
    goal="Find perfect service vendors that match the event requirements, location, and budget constraints",
    backstory=(
        "You are a vendor coordination expert with extensive knowledge of service providers across different cities. "
        "You have deep connections in the event planning industry and know exactly which vendors to recommend for specific event types. "
        "You are skilled at finding reliable vendors for any service category, from catering and decoration to photography and entertainment. "
        "Your recommendations always consider the client's budget, location, and specific event needs, ensuring a perfect match for their event."
    ),
    tools=[
        VendorToolsManager()  # Only use VendorToolsManager for vendor searches
    ],
    llm=llm,
    verbose=True
)

venue_search_coordinator = Agent(
    role="Venue Search Specialist", 
    goal="Find perfect venues that match the event requirements, location, and budget constraints",
    backstory=(
        "You are a venue search expert with extensive knowledge of event venues across different cities. "
        "You have deep connections with venue owners and managers, allowing you to find the perfect match for any event. "
        "You understand the specific requirements of different event types and can recommend venues that suit the client's needs. "
        "Your venue recommendations always consider capacity, budget, location, and the specific ambiance needed for the event type."
    ),
    tools=[
        UniversalVenueServiceTool()  # Only use UniversalVenueServiceTool for venue searches
    ],
    llm=llm,
    verbose=True
)

# ---------------------- Tasks ----------------------
requirement_task = Task(
    description=(
        "Analyze the requirements for an event categorized as '{event_category}' with approximately {num_guests} guests. "
        "Identify the core services typically needed to organize such an event. Focus on essential and standard services only—"
        "such as venue, catering, decoration, photography, entertainment, and guest management. Avoid suggesting overly luxurious or non-standard services. "
        "Consider the specific needs of a {event_category} event - for example, a wedding might need different services than a corporate event. "
        "Format your response as a JSON array of service names. For example: "
        "['Venue', 'Catering', 'Decoration', 'Photography', 'Entertainment']"
    ),
    agent=requirement_analyzer,
    expected_output="A JSON array of required services"
)

budget_task = Task(
    description=(
        "Allocate {budget} INR for {event_category} event with {num_guests} guests and these services: {services}. "
        "Provide a detailed budget breakdown for each service, ensuring the total matches the overall budget. "
        "Consider the typical costs for a {event_category} event in {location}. Allocate more budget to critical services "
        "and less to optional ones."
        "Format your response as a JSON object where keys are service names and values are budget amounts in INR. For example: "
        "{{\"Venue\": 50000, \"Catering\": 60000, \"Decoration\": 20000, \"Photography\": 15000, \"Entertainment\": 25000, \"Guest Management\": 10000, \"Contingency\": 30000}}"
    ),
    agent=budget_allocator,
    expected_output="JSON budget breakdown by service"
)

service_revision_task = Task(
    description=(
        "Revise services based on the following client feedback: '{user_feedback}' for the current services: {current_services}. "
        "Analyze what the client wants to change, add, or remove from their current service list. "
        "Make appropriate adjustments to services and their budget allocations to fulfill the client's wishes while ensuring the overall plan remains coherent. "
        "If the client wants to add new services, allocate a reasonable budget for them. "
        "If the client wants to remove services, reallocate the freed budget to other services proportionally or as specified. "
        "If the client wants to modify budgets, adjust as requested while maintaining a balanced overall plan."
    ),
    agent=service_reviser,
    expected_output="Updated list of services with budget"
)

venue_search_task = Task(
    description=(
        "Conduct a comprehensive venue search in {location} for the {event_category} event using the UniversalVenueServiceTool. "
        "Search for venues with these parameters: {venue_type} for {num_guests} guests within a budget of {service_budget} INR. "
        "Aim to provide AT LEAST 5-8 venue options"
        "Provide comprehensive information in this structured format:"
        "\n- Name: Full name of the venue"
        "\n- Address: Complete physical address with landmarks if available"
        "\n- Contact: Phone number of the venue"
        "\n- Price: Detailed pricing information (per plate or package cost)"
        "\n- Capacity: Maximum number of guests the venue can accommodate"
        "\n- Rating: Customer rating of the venue (if available)"
        "\n- Map URL: Google Maps link to the venue location"
        "\n- Website: URL to the venue's website or listing page"
        "\n- Source: Source website where the venue information was found"
        "\nEnsure all venues are suitable for the specified event type, budget, and guest count."
        "\nThis task is ONLY for searching venues - don't search for any other type of vendors."
        "\nReturn the data in a clean, consistent JSON structure with no backticks."
    ),
    agent=venue_search_coordinator,
    expected_output="List of suitable venues with structured details"
)

vendor_search_task = Task(
    description=(
        "Based on the selected service type '{service_type}', conduct a comprehensive vendor search in {location} for the {event_category} event. "
        "Use the VendorToolsManager to search for {service_type} vendors with a budget of {service_budget} INR. "
        "Aim to provide AT LEAST 10-15 vendor options if available to support the 'Show More' feature. "
        "For vendors, provide information in this format:"
        "\n- Name: Full name of the vendor/service provider"
        "\n- Contact: Phone number of the vendor"
        "\n- Address: Physical address if available"
        "\n- Price: Detailed pricing information (package cost, hourly rate, etc.)"
        "\n- Rating: Customer rating of the vendor (if available)"
        "\n- Description: Brief description of their services"
        "\n- Website: URL to the vendor's website or listing page"
        "\n- Source: Source website where the vendor information was found"
        "\nEnsure all results are suitable for the specified event type, budget, and guest count."
        "\nNEVER search for venues - this task is ONLY for non-venue services like catering, decoration, photography, entertainment, etc."
        "\nReturn the data in a clean, consistent JSON structure with no backticks."
    ),
    agent=vendor_service_coordinator,
    expected_output="List of suitable vendors with structured details"
)

# ---------------------- Crew Creation Functions ----------------------
def create_requirements_crew():
    """Create and return the requirements analysis crew"""
    return Crew(
        agents=[requirement_analyzer],
        tasks=[requirement_task],
        process=Process.sequential,
        verbose=True
    )

def create_budget_crew():
    """Create and return the budget allocation crew"""
    return Crew(
        agents=[budget_allocator],
        tasks=[budget_task],
        process=Process.sequential,
        verbose=True
    )

def create_service_revision_crew():
    """Create and return the service revision crew"""
    return Crew(
        agents=[service_reviser],
        tasks=[service_revision_task],
        process=Process.sequential,
        verbose=True
    )

def create_venue_search_crew():
    """Create and return the venue search crew"""
    return Crew(
        agents=[venue_search_coordinator],
        tasks=[venue_search_task],
        process=Process.sequential,
        verbose=True
    )

def create_vendor_search_crew():
    """Create and return the vendor search crew"""
    return Crew(
        agents=[vendor_service_coordinator],
        tasks=[vendor_search_task],
        process=Process.sequential,
        verbose=True
    )