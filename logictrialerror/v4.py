import warnings
warnings.filterwarnings('ignore')
import os
import re
import json
import time
import logging
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Type, List, Dict, Any, Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import json
import logging
import re
import requests
from typing import List, Dict, Any, Optional, Type
from crewai_tools import ScrapeWebsiteTool, ScrapeElementFromWebsiteTool
from crewai_tools import SeleniumScrapingTool
from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Flowable
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate
#from mistralai.models.chat_completion import ChatMessage
from mistralai import Mistral
from mistralai.client import MistralClient
from urllib.parse import urlparse, parse_qs
import trafilatura
import time
from typing import Literal
from pydantic import Field
#from crewai_tools.tools.selenium_scraping_tool import SeleniumScrapingTool
from crewai_tools import SeleniumScrapingTool
from bs4 import BeautifulSoup
import random
import threading
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import uuid
from datetime import datetime
import bcrypt
import pymongo
from pymongo import MongoClient
from bson.binary import UuidRepresentation
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

# ---------------------- VenueLook Scraper Tool ----------------------

class VenueDetails(BaseModel):
    name: str
    address: str
    price: Optional[str] = None
    contact: Optional[str] = None
    rating: Optional[str] = None
    capacity: Optional[str] = None
    source: str
    url: Optional[str] = None

class JustDialVenueSearchInput(BaseModel):
    location: str = Field(..., description="City/area for venue search")
    event_type: str = Field(..., description="Type of event like birthday or wedding")
    venue_type: str = Field(..., description="Type of venue like banquet hall or restaurant")
    guest_count: int = Field(..., description="Number of guests")
    budget: int = Field(..., description="Budget for the venue in INR")
class UniversalVenueServiceTool(BaseTool):
    name: str = "universal_venue_service_tool"
    description: str = "Discovers venues for events using targeted search and extraction"
    args_schema: Type[BaseModel] = JustDialVenueSearchInput
    
    def _run(self, location: str, event_type: str, venue_type: str, guest_count: int, budget: int) -> List[Dict[str, Any]]:
        """
        Find venues matching the specified criteria through directed web search and content extraction
        """
        # Load API keys
        serper_api_key = os.environ.get("SERPER_API_KEY")
        mistral_api_key = os.environ.get("MISTRAL_API_KEY")
        
        if not serper_api_key or not mistral_api_key:
            logger.error("Missing required API keys")
            return [{"error": "Missing API keys"}]
        
        # Step 1: Build targeted search query focusing ONLY on venuelook.com
        search_query = f"Best {venue_type} in {location} under {budget} for {guest_count} guests site:venuelook.com"
        logger.info(f"Executing search with query: {search_query}")
        
        # Step 2: Execute search and get URLs
        search_results = self._execute_search(search_query, serper_api_key)
        if not search_results:
            logger.warning("No search results found for VenueLook")
            # Try a more generic search as fallback, still on venuelook.com
            backup_query = f"{venue_type} {location} venue site:venuelook.com"
            search_results = self._execute_search(backup_query, serper_api_key)
            if not search_results:
                return [{"error": "No venues found matching your criteria"}]
        
        # Step 3: Process results sequentially to avoid rate limits
        venue_data = []
        urls_processed = set()
        
        # Process up to 6 search results
        for i, result in enumerate(search_results[:6]):
            url = result.get("link")
            if not url or url in urls_processed or "venuelook.com" not in url:
                continue
                
            urls_processed.add(url)
            logger.info(f"Processing URL: {url}")
            
            # Extract content using Trafilatura with timeout
            content = self._extract_content(url)
            if not content or len(content) < 200:
                logger.warning(f"Insufficient content from {url}")
                continue
                
            # Extract structured venue data using Mistral with delay between calls
            venue_info = self._extract_venue_data(
                content, url, mistral_api_key, 
                event_type, venue_type, guest_count, budget, location
            )
            
            if venue_info:
                venue_data.append(venue_info)
            
            # Add a delay between processing URLs
            time.sleep(1.0)  # 1 second delay to avoid rate limits
        
        # If we don't have enough venues, try a more generic search
        if len(venue_data) < 3:
            logger.info("Not enough venues found, trying more generic search...")
            generic_query = f"venue {location} event site:venuelook.com"
            additional_results = self._execute_search(generic_query, serper_api_key)
            
            # Process additional results sequentially
            for i, result in enumerate(additional_results[:4]):
                url = result.get("link")
                if not url or url in urls_processed or "venuelook.com" not in url:
                    continue
                
                urls_processed.add(url)
                logger.info(f"Processing additional URL: {url}")
                
                content = self._extract_content(url)
                if not content or len(content) < 200:
                    continue
                    
                venue_info = self._extract_venue_data(
                    content, url, mistral_api_key, 
                    event_type, venue_type, guest_count, budget, location
                )
                
                if venue_info:
                    venue_data.append(venue_info)
                
                # Add a delay between processing URLs
                time.sleep(1.0)  # 1 second delay
        
        if not venue_data:
            return [{"error": "Could not extract venue information from search results"}]
        
        # Deduplicate venue data (max 6)
        deduplicated_venues = self._deduplicate_venues(venue_data)[:6]
        
        # Process venues sequentially (simplified approach)
        verified_venues = []
        
        for venue in deduplicated_venues:
            # Only proceed if we have a name
            if venue.get("name"):
                # Add map link
                venue = self._add_map_link(venue)
                # Extract contact
                venue = self._extract_contact_from_map(venue, serper_api_key, mistral_api_key)
                verified_venues.append(venue)
            else:
                # Keep original data if no name, but still add map link
                venue = self._add_map_link(venue)
                verified_venues.append(venue)
            
            # Add a delay between venues
            time.sleep(1.0)  # 1 second delay
            
        return verified_venues
    
    def _extract_venue_data(self, content: str, url: str, mistral_api_key: str,
                           event_type: str, venue_type: str, guest_count: int, 
                           budget: int, location: str) -> Optional[Dict[str, Any]]:
        """Extract structured venue data using Mistral LLM with retry logic"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Initialize Mistral client
                client = Mistral(api_key=mistral_api_key)
                
                # Create concise system prompt for venue extraction
                system_prompt = f"""
                Extract venue data for {event_type} in {location} for {guest_count} guests (budget: ₹{budget}).
                Extract: name, address, detailed all type of mentioned prices, capacity, rating based on reviews.
                Return ONLY valid JSON. Use null for missing fields.
                """
                
                # Limit content more aggressively
                user_prompt = f"""
                Extract venue details from:
                {content[:3000]}
                """
                
                # Create the messages
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                # Request JSON response format
                chat_response = client.chat.complete(
                    model="mistral-large-latest",
                    messages=messages,
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                
                # Handle different response formats
                if hasattr(chat_response, 'choices'):
                    if isinstance(chat_response.choices, list) and len(chat_response.choices) > 0:
                        result_text = chat_response.choices[0].message.content
                    elif isinstance(chat_response.choices, dict) and 'message' in chat_response.choices:
                        result_text = chat_response.choices['message'].content
                    else:
                        logger.error(f"Unexpected response format: {chat_response}")
                        raise ValueError("Unexpected API response format")
                else:
                    logger.error(f"Response missing choices attribute: {chat_response}")
                    raise ValueError("Missing choices in API response")
                    
                try:
                    result_data = json.loads(result_text)
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode JSON response: {result_text}")
                    raise ValueError("Failed to decode JSON response")
                
                # Add source URL and other fields
                result_data["source"] = url
                result_data["url"] = url
                result_data["source_site"] = urlparse(url).netloc
                    
                return result_data
                    
            except Exception as e:
                if "429" in str(e) or "rate limit" in str(e).lower():
                    # Rate limit hit - backoff exponentially
                    retry_delay = (1 * (2 ** attempt)) + (random.random() * 0.5)
                    logger.warning(f"Rate limit hit, retrying in {retry_delay:.1f}s")
                    time.sleep(retry_delay)
                    
                    # Last attempt, return None if it fails
                    if attempt == max_retries - 1:
                        logger.error(f"All retries failed for extracting venue data: {e}")
                        return None
                else:
                    # Other error, log and continue
                    logger.error(f"Error extracting venue data: {e}")
                    return None
    
    def _extract_contact_from_map(self, venue, serper_api_key, mistral_api_key):
        """Extract contact information with retries and simplified approach"""
        name = venue.get("name", "")
        address = venue.get("address", "")
        
        if not name:
            return venue
            
        # Create a search query for the venue's contact information
        search_query = f"{name} {address} phone number contact"
        logger.info(f"Searching for contact info: {search_query}")
        
        # Execute search
        search_results = self._execute_search(search_query, serper_api_key)
        if not search_results:
            return venue
            
        # Look for contact information in search results
        contact_content = ""
        
        # Collect snippets that might contain contact information
        for result in search_results[:2]:
            snippet = result.get("snippet", "")
            title = result.get("title", "")
            contact_content += f"\n{title}\n{snippet}"
            
        # Extract phone number using regular expressions
        phone_patterns = [
            r'(\+\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})',
            r'(\+\d{1,3}[-.\s]?)?\d{10}',
            r'(\+\d{1,3}[-.\s]?)?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
            r'(\+\d{1,3}[-.\s]?)?\d{5}[-.\s]?\d{5}',
            r'phone:?\s*[\(]?[+]?[\d\s\-\(\)]{8,20}[\)]?',
            r'contact:?\s*[\(]?[+]?[\d\s\-\(\)]{8,20}[\)]?',
            r'mobile:?\s*[\(]?[+]?[\d\s\-\(\)]{8,20}[\)]?'
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, contact_content, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    contact = ''.join(filter(None, matches[0]))
                else:
                    contact = matches[0]
                    
                # Clean the contact info
                contact = re.sub(r'[^\d+\-() ]', '', contact).strip()
                if contact and len(contact) >= 8:
                    venue["contact"] = contact
                    return venue  # Return early if regex found contact
                    
        # If regex fails, try using Mistral with retries
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # Initialize Mistral client
                client = Mistral(api_key=mistral_api_key)
                
                # Create simplified prompt
                system_prompt = "Extract the phone number for the venue from text. Return only the number."
                user_prompt = f"Venue: {name}\nText: {contact_content[:1500]}"
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                chat_response = client.chat.complete(
                    model="mistral-large-latest",
                    messages=messages,
                    temperature=0.1
                )
                
                if hasattr(chat_response, 'choices') and isinstance(chat_response.choices, list) and chat_response.choices:
                    extracted_contact = chat_response.choices[0].message.content.strip()
                    if "not available" not in extracted_contact.lower() and len(extracted_contact) >= 8:
                        venue["contact"] = extracted_contact
                        break
                
                # Add delay between attempts
                if attempt < max_retries - 1:
                    time.sleep(2.0)
                
            except Exception as e:
                logger.error(f"Error extracting contact with Mistral: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2.0)
                
        return venue
    
    def _add_map_link(self, venue):
        """Add a Google Maps link based on venue name and address"""
        name = venue.get("name", "")
        address = venue.get("address", "")
        
        if name and address:
            query = f"{name}, {address}".replace(" ", "+")
            venue["map_url"] = f"https://www.google.com/maps/search/?api=1&query={query}"
        elif name:
            query = name.replace(" ", "+")
            venue["map_url"] = f"https://www.google.com/maps/search/?api=1&query={query}"
        
        return venue
    
    def _execute_search(self, query: str, serper_api_key: str) -> List[Dict[str, Any]]:
        """Execute search with error handling and retries"""
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                headers = {
                    "X-API-KEY": serper_api_key,
                    "Content-Type": "application/json"
                }
                
                search_payload = {
                    "q": query,
                    "num": 10
                }
                
                response = requests.post(
                    "https://google.serper.dev/search", 
                    headers=headers, 
                    json=search_payload,
                    timeout=15
                )
                
                response.raise_for_status()
                
                results = response.json().get("organic", [])
                if "site:venuelook.com" in query:
                    results = [r for r in results if "venuelook.com" in r.get("link", "")]
                    
                return results
                
            except Exception as e:
                logger.warning(f"Search attempt {attempt+1} failed: {e}")
                time.sleep(1)
                
        logger.error("All search attempts failed")
        return []
    
    def _extract_content(self, url: str) -> Optional[str]:
        """Extract content from URL"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            }
            
            response = requests.get(url, headers=headers, timeout=8)
            
            if response.status_code == 200:
                # Try Trafilatura first
                extracted_text = trafilatura.extract(response.text)
                if extracted_text and len(extracted_text) >= 200:
                    return f"Source URL: {url}\n\n{extracted_text}"
                
                # BeautifulSoup fallback
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for main content
                for selector in ['.venue-details', '.venue-info', 'main', 'article', '.content']:
                    elements = soup.select(selector)
                    if elements:
                        text = '\n'.join([e.get_text(separator='\n', strip=True) for e in elements])
                        if text and len(text) >= 200:
                            return f"Source URL: {url}\n\n{text}"
                
                # Get paragraphs as last resort
                paragraphs = soup.find_all('p')
                if paragraphs:
                    text = '\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                    if text and len(text) >= 150:
                        return f"Source URL: {url}\n\n{text}"
                        
            return None
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return None
            
    def _deduplicate_venues(self, venues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate venues based on name"""
        if not venues:
            return []
            
        unique_venues = []
        seen_names = set()
        
        venues.sort(key=lambda x: sum(1 for k, v in x.items() if v is not None and v != ""), reverse=True)
        
        for venue in venues:
            name = venue.get("name", "").lower() if venue.get("name") else ""
            
            if name and name not in seen_names:
                seen_names.add(name)
                unique_venues.append(venue)
                
        return unique_venues
# ---------------------- Vendor Search Tool ----------------------
class VendorSearchInput(BaseModel):
    service_type: str = Field(..., description="Type of service like catering, decoration, photography")
    location: str = Field(..., description="City/area for vendor search")
    event_type: str = Field(..., description="Type of event like birthday or wedding")
    budget: int = Field(..., description="Budget for the service in INR")

class VendorDetails(BaseModel):
    name: str
    address: Optional[str] = None
    contact: Optional[str] = None
    rating: Optional[str] = None
    price: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    source: str

# Base Vendor Search Tool with common functionality
class BaseVendorSearchTool(BaseTool, ABC):
    name: str = "base_vendor_search_tool"
    description: str = "Base class for vendor search tools"
    args_schema: Type[BaseModel] = VendorSearchInput
    
    # Rate limiting parameters
    _request_count = 0
    _last_request_time = 0
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize lock in __init__ instead of at class level to avoid pickling issues
        self._request_lock = threading.Lock()
    
    def _run(self, service_type: str, location: str, event_type: str, budget: int) -> List[Dict[str, Any]]:
        """
        Run the vendor search with the implementation provided by the subclass
        """
        # Load API keys
        serper_api_key = self._get_api_key("SERPER_API_KEY")
        mistral_api_key = self._get_api_key("MISTRAL_API_KEY")
        
        if not serper_api_key or not mistral_api_key:
            logger.error("Missing required API keys")
            return [{"error": "Missing API keys"}]
        
        # Create a context object to pass to threads
        search_context = {
            "service_type": service_type,
            "location": location,
            "event_type": event_type,
            "budget": budget,
            "serper_api_key": serper_api_key,
            "mistral_api_key": mistral_api_key
        }
        
        # Get search sites and queries from the specialized implementation
        search_sites = self._get_search_sites(service_type)
        search_queries = self._generate_search_queries(service_type, event_type, location, budget, search_sites)
        
        # Execute searches and process results
        vendors_data = []
        seen_vendor_names = set()
        search_lock = threading.Lock()
        
        # Process search queries sequentially to maintain order of preferred sites
        for query in search_queries:
            logger.info(f"Executing search with query: {query}")
            
            # Apply rate limiting for SERP API
            search_results = self._execute_search_with_rate_limit(query, serper_api_key)
            
            if not search_results:
                logger.warning(f"No search results found for query: {query}")
                continue
            
            # Process results in parallel
            vendor_results = self._process_search_results_parallel(
                search_results, seen_vendor_names, search_lock, search_context
            )
            vendors_data.extend(vendor_results)
            
            # If we have enough vendors, no need to continue with more queries
            if len(vendors_data) >= 5:
                break
        
        # Deduplicate results
        unique_vendors = self._deduplicate_vendors(vendors_data)
        
        # Enhance vendor data with additional information in parallel
        enhanced_vendors = self._enhance_vendors_parallel(unique_vendors, search_context)
        
        if not enhanced_vendors:
            return [{"error": f"Could not find suitable {service_type} vendors in {location}"}]
            
        return enhanced_vendors

    def _get_api_key(self, key_name: str) -> Optional[str]:
        """Get API key from environment with error handling"""
        import os
        return os.environ.get(key_name)

    @abstractmethod
    def _get_search_sites(self, service_type: str) -> List[str]:
        """Return a list of websites to search based on service type"""
        pass
        
    @abstractmethod
    def _generate_search_queries(self, service_type: str, event_type: str, 
                                location: str, budget: int, sites: List[str]) -> List[str]:
        """Generate search queries for the specified service and parameters"""
        pass

    def _should_skip_url(self, url: str) -> bool:
        """Determine if a URL should be skipped"""
        skip_domains = [
            "facebook.com", "instagram.com", "linkedin.com", "youtube.com",
            "twitter.com", "pinterest.com", ".pdf"
        ]
        
        for domain in skip_domains:
            if domain in url:
                return True
                
        return False
    
    def _process_search_results_parallel(self, search_results, seen_vendor_names, search_lock, search_context):
        """Process search results in parallel using ThreadPoolExecutor"""
        vendors_data = []
        max_results = min(10, len(search_results))  # Process top 10 results max
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit tasks to the executor
            future_to_url = {
                executor.submit(self._process_search_result, result, seen_vendor_names, search_lock, search_context): 
                result.get("link") 
                for result in search_results[:max_results]
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_url):
                try:
                    vendor_info = future.result()
                    if vendor_info:
                        with search_lock:
                            vendors_data.append(vendor_info)
                        
                        # Check if we have enough vendors
                        with search_lock:
                            if len(vendors_data) >= 5:
                                # Cancel remaining futures
                                for f in future_to_url:
                                    if not f.done():
                                        f.cancel()
                                break
                except Exception as e:
                    logger.error(f"Error processing search result: {e}")
        
        return vendors_data
    
    def _process_search_result(self, result, seen_vendor_names, search_lock, context):
        """Process a single search result to extract vendor data"""
        url = result.get("link")
        if not url or self._should_skip_url(url):
            return None
        
        # Check if we've already processed this URL (thread-safe)
        with search_lock:
            if len(seen_vendor_names) >= 5:
                return None
        
        logger.info(f"Processing URL: {url}")
        
        # Extract content from URL with rate limiting
        content = self._extract_content_with_rate_limit(url)
        if not content or len(content) < 200:
            logger.warning(f"Insufficient content from {url}")
            return None
        
        # Extract vendor data using Mistral with rate limiting
        vendor_info = self._extract_vendor_data_with_rate_limit(
            content, url, context["mistral_api_key"], context["service_type"], 
            context["event_type"], context["location"], context["budget"]
        )
        
        if vendor_info and vendor_info.get("name"):
            vendor_name = vendor_info.get("name", "").lower()
            
            # Thread-safe check for duplicate vendor names
            with search_lock:
                if vendor_name in seen_vendor_names:
                    return None
                seen_vendor_names.add(vendor_name)
            
            return vendor_info
        
        return None
    
    def _execute_search_with_rate_limit(self, query: str, serper_api_key: str) -> List[Dict[str, Any]]:
        """Execute search with error handling, retries and rate limiting"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                self._apply_rate_limit("search")
                
                headers = {
                    "X-API-KEY": serper_api_key,
                    "Content-Type": "application/json"
                }
                
                search_payload = {
                    "q": query,
                    "num": 20
                }
                
                response = requests.post(
                    "https://google.serper.dev/search", 
                    headers=headers, 
                    json=search_payload,
                    timeout=20
                )
                
                response.raise_for_status()
                
                # Check for specific site-restricted queries
                results = response.json().get("organic", [])
                if "site:" in query:
                    site = query.split("site:")[1].strip()
                    results = [r for r in results if site in r.get("link", "")]
                    
                return results
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    # Rate limit hit - apply exponential backoff
                    retry_delay = (2 ** attempt) + (random.random() * 2)
                    logger.warning(f"Rate limit hit, retrying in {retry_delay:.1f}s")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"HTTP error: {str(e)}")
                    time.sleep(1)
            except Exception as e:
                logger.warning(f"Search attempt {attempt+1} failed: {e}")
                time.sleep(1)
                
        logger.error("All search attempts failed")
        return []
    
    def _extract_content_with_rate_limit(self, url: str) -> Optional[str]:
        """Extract content from URL using Trafilatura with rate limiting"""
        try:
            # Apply rate limiting for web requests
            self._apply_rate_limit("web")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.google.com/"
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # Try Trafilatura first
                extracted_text = trafilatura.extract(response.text)
                if extracted_text and len(extracted_text) >= 200:
                    return f"Source URL: {url}\n\n{extracted_text}"
                
                # BeautifulSoup fallback
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try service-specific content containers
                service_containers = [
                    '.vendor-details', '.vendor-info', '.service-details',
                    '.service-description', '.product-details', '.provider-info',
                    '.about-vendor', '.professional-details', '.service-provider'
                ]
                
                for selector in service_containers:
                    try:
                        elements = soup.select(selector)
                        if elements:
                            text = '\n'.join([e.get_text(separator='\n', strip=True) for e in elements])
                            if text and len(text) >= 200:
                                return f"Source URL: {url}\n\n{text}"
                    except:
                        continue
                
                # Try common content containers
                for selector in ['main', 'article', '.content', '#content', '.main-content']:
                    try:
                        elements = soup.select(selector)
                        if elements:
                            text = '\n'.join([e.get_text(separator='\n', strip=True) for e in elements])
                            if text and len(text) >= 200:
                                return f"Source URL: {url}\n\n{text}"
                    except:
                        continue
                
                # Extract paragraphs as last resort
                paragraphs = soup.find_all('p')
                if paragraphs:
                    text = '\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                    if text and len(text) >= 200:
                        return f"Source URL: {url}\n\n{text}"
                        
            return None
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return None
    
    def _extract_vendor_data_with_rate_limit(self, content: str, url: str, mistral_api_key: str,
                             service_type: str, event_type: str, location: str, 
                             budget: int) -> Optional[Dict[str, Any]]:
        """Extract structured vendor data using Mistral LLM with rate limiting"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Apply rate limiting for Mistral API
                self._apply_rate_limit("mistral")
                
                # Initialize Mistral client
                client = Mistral(api_key=mistral_api_key)
                
                # Create targeted system prompt for vendor extraction
                system_prompt = f"""
                You are a vendor data extraction specialist. Extract detailed information about a {service_type} vendor for a {event_type} in {location}.
                
                The vendor should be suitable for {event_type} events and within a budget of ₹{budget}.
                
                Extract EXACTLY these fields:
                - name: The vendor/service provider name
                - address: The physical address if available
                - contact: Phone number if available
                - rating: Customer rating of the vendor (if available)
                - price: Price information (package cost, hourly rate, etc.)
                - description: Brief description of their services
                - website: Their website URL if available
                - source: Use the source URL provided
                
                Return ONLY valid JSON format. If information is not found, use null.
                
                When extracting prices, be specific about pricing structure if available.
                """
                
                # Limit content to avoid token limits
                user_prompt = f"""
                Extract {service_type} vendor details from this text content:
                
                {content[:5000]}
                """
                
                # Create the messages
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                # Request JSON response format
                chat_response = client.chat.complete(
                    model="mistral-large-latest",
                    messages=messages,
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                
                result_text = chat_response.choices[0].message.content
                result_data = json.loads(result_text)
                
                # Add source URL if not present
                if "source" not in result_data or not result_data["source"]:
                    result_data["source"] = url
                    
                # Set service type
                result_data["service_type"] = service_type
                    
                return result_data
                    
            except requests.exceptions.HTTPError as e:
                if hasattr(e, 'response') and e.response.status_code == 429:
                    # Rate limit hit - exponential backoff with jitter
                    retry_delay = (2 ** attempt) + (random.random() * 2)
                    logger.warning(f"Mistral API rate limit hit, retrying in {retry_delay:.1f}s")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"HTTP error in Mistral API: {str(e)}")
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Error extracting vendor data (attempt {attempt+1}): {e}")
                time.sleep(1)
                
        logger.error("All attempts to extract vendor data failed")
        return None
    
    def _enhance_vendors_parallel(self, vendors, context):
        """Enhance multiple vendors in parallel with additional information"""
        if not vendors:
            return []
        
        enhanced_vendors = []
        results_lock = threading.Lock()
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit enhancement tasks to the executor
            future_to_vendor = {
                executor.submit(
                    self._enhance_vendor_details, 
                    vendor, 
                    context["serper_api_key"], 
                    context["mistral_api_key"], 
                    context["service_type"], 
                    context["location"]
                ): vendor for vendor in vendors
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_vendor):
                try:
                    enhanced_vendor = future.result()
                    if enhanced_vendor:
                        with results_lock:
                            enhanced_vendors.append(enhanced_vendor)
                except Exception as e:
                    logger.error(f"Error enhancing vendor: {e}")
        
        return enhanced_vendors
    
    def _enhance_vendor_details(self, vendor: Dict[str, Any], serper_api_key: str, 
                               mistral_api_key: str, service_type: str, location: str) -> Dict[str, Any]:
        """
        Enhance vendor details with additional searches for missing information
        """
        vendor_name = vendor.get("name", "")
        
        if not vendor_name:
            return vendor
            
        # Try to find missing contact information
        if not vendor.get("contact"):
            vendor = self._extract_contact_info(vendor, serper_api_key, mistral_api_key)
            
        # Try to find missing price information
        if not vendor.get("price"):
            vendor = self._extract_price_info(vendor, serper_api_key, mistral_api_key, service_type, location)
            
        return vendor
        
    def _extract_contact_info(self, vendor: Dict[str, Any], serper_api_key: str, mistral_api_key: str) -> Dict[str, Any]:
        """Extract contact information from search results"""
        vendor_name = vendor.get("name", "")
        location = vendor.get("address", "").split(",")[-1].strip() if vendor.get("address") else ""
        
        if not vendor_name:
            return vendor
            
        # Create search query
        search_query = f"{vendor_name} {location} contact phone number"
        logger.info(f"Searching for contact info: {search_query}")
        
        # Execute search with rate limiting
        search_results = self._execute_search_with_rate_limit(search_query, serper_api_key)
        if not search_results:
            return vendor
            
        # Look for contact information in search results
        contact_content = ""
        
        # Collect snippets that might contain contact information
        for result in search_results[:3]:
            snippet = result.get("snippet", "")
            title = result.get("title", "")
            contact_content += f"\n{title}\n{snippet}"
            
        # Extract phone number using regular expressions
        phone_patterns = [
            r'(\+\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})',
            r'(\+\d{1,3}[-.\s]?)?\d{10}',
            r'(\+\d{1,3}[-.\s]?)?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',
            r'(\+\d{1,3}[-.\s]?)?\d{5}[-.\s]?\d{5}',
            r'phone:?\s*[\(]?[+]?[\d\s\-\(\)]{8,20}[\)]?',
            r'contact:?\s*[\(]?[+]?[\d\s\-\(\)]{8,20}[\)]?',
            r'mobile:?\s*[\(]?[+]?[\d\s\-\(\)]{8,20}[\)]?',
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, contact_content, re.IGNORECASE)
            if matches:
                if isinstance(matches[0], tuple):
                    contact = ''.join(filter(None, matches[0]))
                else:
                    contact = matches[0]
                    
                # Clean the contact info
                contact = re.sub(r'[^\d+\-() ]', '', contact).strip()
                if contact and len(contact) >= 8:
                    vendor["contact"] = contact
                    return vendor
                    
        # If regex fails, try using Mistral with rate limiting
        if not vendor.get("contact") and contact_content:
            try:
                # Apply rate limiting
                self._apply_rate_limit("mistral")
                
                # Initialize Mistral client
                client = Mistral(api_key=mistral_api_key)
                
                # Create simpler system prompt for contact extraction
                system_prompt = f"""
                Extract the contact phone number for the vendor '{vendor_name}' from the following search results.
                Return only the phone number in standard format. If no clear phone number is found, say "Not available".
                """
                
                user_prompt = f"Content to analyze:\n{contact_content[:2000]}"
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                chat_response = client.chat.complete(
                    model="mistral-large-latest",
                    messages=messages,
                    temperature=0.1
                )
                
                extracted_contact = chat_response.choices[0].message.content.strip()
                
                # If Mistral returned a contact number (not "Not available")
                if "not available" not in extracted_contact.lower() and len(extracted_contact) >= 8:
                    vendor["contact"] = extracted_contact
                    
            except Exception as e:
                logger.error(f"Error extracting contact with Mistral: {e}")
                
        return vendor
        
    def _extract_price_info(self, vendor: Dict[str, Any], serper_api_key: str, 
                           mistral_api_key: str, service_type: str, location: str) -> Dict[str, Any]:
        """Extract or estimate price information"""
        vendor_name = vendor.get("name", "")
        
        if not vendor_name:
            return vendor
            
        # Create search query for pricing
        search_query = f"{vendor_name} {service_type} {location} price cost package"
        logger.info(f"Searching for price info: {search_query}")
        
        # Execute search with rate limiting
        search_results = self._execute_search_with_rate_limit(search_query, serper_api_key)
        if not search_results:
            # If no results, provide an estimate based on service type
            vendor["price"] = self._generate_price_estimate(service_type, location)
            return vendor
            
        # Extract content from top results - just use snippets for speed
        price_content = ""
        for result in search_results[:5]:
            snippet = result.get("snippet", "")
            title = result.get("title", "")
            price_content += f"\n{title}\n{snippet}"
                
        # Try to extract price using Mistral with rate limiting
        if price_content:
            try:
                # Apply rate limiting
                self._apply_rate_limit("mistral")
                
                # Initialize Mistral client
                client = Mistral(api_key=mistral_api_key)
                
                # Create system prompt for price extraction (simplified for speed)
                system_prompt = f"""
                Extract price information for '{vendor_name}' {service_type} services from the text.
                If no clear price is found, provide a reasonable estimate for {service_type} services in {location}.
                Return only the price information in a concise format.
                """
                
                user_prompt = f"Content to analyze:\n{price_content[:2000]}"
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                
                chat_response = client.chat.complete(
                    model="mistral-large-latest",
                    messages=messages,
                    temperature=0.1
                )
                
                extracted_price = chat_response.choices[0].message.content.strip()
                
                if extracted_price and "not available" not in extracted_price.lower():
                    vendor["price"] = extracted_price
                else:
                    vendor["price"] = self._generate_price_estimate(service_type, location)
                    
            except Exception as e:
                logger.error(f"Error extracting price with Mistral: {e}")
                vendor["price"] = self._generate_price_estimate(service_type, location)
        else:
            vendor["price"] = self._generate_price_estimate(service_type, location)
            
        return vendor
        
    def _generate_price_estimate(self, service_type: str, location: str) -> str:
        """Generate a reasonable price estimate based on service type and location"""
        service_type = service_type.lower()
        
        # Estimates for common service types
        if service_type in ["catering", "caterer", "food"]:
            return "Estimated ₹800-1500 per plate"
        elif service_type in ["decoration", "decorator", "decor"]:
            return "Estimated ₹15,000-50,000 depending on complexity"
        elif service_type in ["photography", "photographer"]:
            return "Estimated ₹15,000-30,000 per day"
        elif service_type in ["videography", "videographer"]:
            return "Estimated ₹20,000-40,000 per day"
        elif service_type in ["cake", "bakery"]:
            return "Estimated ₹800-1500 per kg"
        elif service_type in ["music", "dj"]:
            return "Estimated ₹10,000-25,000 per event"
        elif service_type in ["makeup", "makeup artist"]:
            return "Estimated ₹5,000-15,000 per session"
        elif service_type in ["mehendi", "mehndi artist"]:
            return "Estimated ₹3,000-10,000 per event"
        else:
            return f"Estimated ₹10,000-30,000 for {service_type} services"
    
    def _deduplicate_vendors(self, vendors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate vendors based on name and limit to top 5"""
        if not vendors:
            return []
            
        unique_vendors = []
        seen_names = set()
        
        # Sort by completeness of information (more complete first)
        vendors.sort(key=lambda x: sum(1 for k, v in x.items() 
                                    if v is not None and v != ""), 
                    reverse=True)
        
        for vendor in vendors:
            name = vendor.get("name", "").lower() if vendor.get("name") else ""
            
            if name and name not in seen_names:
                seen_names.add(name)
                unique_vendors.append(vendor)
                
                if len(unique_vendors) >= 5:  # Limit to top 5 vendors
                    break
                    
        return unique_vendors
    
    def _apply_rate_limit(self, api_type: str):
        """Apply rate limiting for different API types"""
        # Create a local lock if the instance one doesn't exist yet
        if not hasattr(self, '_request_lock'):
            self._request_lock = threading.Lock()
            
        with self._request_lock:
            current_time = time.time()
            
            # Define rate limits for different API types
            if api_type == "mistral":
                min_interval = 1.5  # 1.5 seconds between Mistral API calls
            elif api_type == "search":
                min_interval = 1.0  # 1 second between search API calls
            else:  # web requests
                min_interval = 0.5  # 0.5 seconds between web requests
            
            # Calculate time to wait
            elapsed = current_time - self._last_request_time
            if elapsed < min_interval:
                wait_time = min_interval - elapsed + (random.random() * 0.5)  # Add jitter
                time.sleep(wait_time)
            
            # Update last request time
            self._last_request_time = time.time()
            self._request_count += 1


# Specialized Vendor Search Tools

class CateringVendorTool(BaseVendorSearchTool):
    name: str = "catering_vendor_tool"
    description: str = "Discovers catering vendors for events using targeted search and extraction"
    
    def _get_search_sites(self, service_type: str) -> List[str]:
        """Return preferred sites for catering vendors"""
        return [ "venuelook.com", "weddingwire.in"]
    
    def _generate_search_queries(self, service_type: str, event_type: str, 
                               location: str, budget: int, sites: List[str]) -> List[str]:
        """Generate catering-specific search queries"""
        queries = []
        
        # # Sulekha-specific queries (primary focus)
        # queries.append(f"best caterer for {event_type} in {location} site:sulekha.com")
        # queries.append(f"top food catering services for {event_type} in {location} under {budget} site:sulekha.com")
        # queries.append(f"catering services in {location} for {event_type} site:sulekha.com")
        
        # VenueLook queries (secondary)
        queries.append(f"best caterer for {event_type} in {location} site:venuelook.com")
        queries.append(f"food catering services {event_type} {location} site:venuelook.com")
        
        # WeddingWire queries (tertiary)
        queries.append(f"top caterers {location} site:weddingwire.in")
        
        # Generic search as fallback
        queries.append(f"best caterers for {event_type} in {location}")
        queries.append(f"affordable catering services {location} {event_type}")
        
        return queries
        
class DecorationVendorTool(BaseVendorSearchTool):
    name: str = "decoration_vendor_tool"
    description: str = "Discovers decoration vendors for events using targeted search and extraction"
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize lock in __init__ instead of at class level to avoid pickling issues
        self._request_lock = threading.Lock()
    
    def _get_search_sites(self, service_type: str) -> List[str]:
        """Return preferred sites for decoration vendors"""
        # Changed order to make VenueLook primary, then Sulekha
        return ["venuelook.com", "sulekha.com", "weddingwire.in"]
    
    def _generate_search_queries(self, service_type: str, event_type: str, 
                               location: str, budget: int, sites: List[str]) -> List[str]:
        """Generate decoration-specific search queries"""
        queries = []
        
        # VenueLook as primary source
        queries.append(f"best decorator for {event_type} in {location} site:venuelook.com")
        queries.append(f"event decoration services in {location} site:venuelook.com")
        queries.append(f"decoration services {event_type} {location} site:venuelook.com")
        
        # Sulekha as secondary source
        queries.append(f"top decoration services for {event_type} in {location} site:sulekha.com")
        queries.append(f"event decorators {location} site:sulekha.com")
        
        # WeddingWire as tertiary source
        queries.append(f"decoration services {event_type} {location} site:weddingwire.in")
        
        return queries
    
    def _run(self, service_type: str, location: str, event_type: str, budget: int) -> List[Dict[str, Any]]:
        """
        Overridden to format results with offline and online sections
        """
        # Create header for offline vendors
        results = [{
            "name": "Offline Decoration Vendors",
            "service_type": "Header",
            "description": f"Physical decoration vendors in {location} for {event_type} events",
            "isHeader": True
        }]
        
        # Get offline vendors using standard search
        offline_vendors = super()._run(service_type, location, event_type, budget)
        
        # Add offline vendors (limit to 6 for better presentation)
        results.extend(offline_vendors[:6])
        
        # Get online decoration service links
        online_services = self._get_decoration_service_links(location, event_type)
        
        # Add online services if we have any
        if online_services:
            results.extend(online_services)
        
        return results
    
    def _get_decoration_service_links(self, location: str, event_type: str) -> List[Dict[str, Any]]:
        """Get direct decoration service links based on search results"""
        direct_services = []
        location_lower = location.lower()
        event_type_lower = event_type.lower()
        
        # Add a header item for online services
        online_header = {
            "name": "Online Decoration Vendors",
            "service_type": "Header",
            "description": f"Order {event_type} decorations online for delivery in {location}",
            "isHeader": True
        }
        direct_services.append(online_header)
        
        # Get API key for search
        serper_api_key = self._get_api_key("SERPER_API_KEY")
        if not serper_api_key:
            return direct_services  # Return just the header if no API key
        
        # Define primary online decoration sites we want to include
        primary_sites = [
            {"name": "Party One", "domain": "partyone.in"},
            {"name": "Haplun", "domain": "haplun.in"},
            {"name": "Balloon Dekor", "domain": "balloondekor.com"},
            {"name": "The Balloon Wala", "domain": "theballoonwala.com"},
            {"name": "FNP Celebrations", "domain": "fnp.com"},
            {"name": "Wanna Party", "domain": "wannaparty.in"},
            {"name": "Amazon Party Supplies", "domain": "amazon.in"}
        ]
        
        # Create search queries for online decoration services
        search_queries = [
            f"{event_type_lower} decorations online delivery {location_lower}",
            f"buy {event_type_lower} decoration supplies {location_lower}",
            f"order {event_type_lower} balloon decorations {location_lower}"
        ]
        
        # Track which primary sites we've found
        found_domains = set()
        all_results = []
        
        # Process each search query to find our primary sites
        for query in search_queries:
            try:
                # Apply rate limiting
                self._apply_rate_limit("search")
                
                headers = {
                    "X-API-KEY": serper_api_key,
                    "Content-Type": "application/json"
                }
                
                search_payload = {
                    "q": query,
                    "num": 10
                }
                
                response = requests.post(
                    "https://google.serper.dev/search", 
                    headers=headers, 
                    json=search_payload,
                    timeout=20
                )
                
                response.raise_for_status()
                results = response.json().get("organic", [])
                all_results.extend(results)
                
            except Exception as e:
                logger.error(f"Error searching for decoration services: {e}")
        
        # First, try to find all our primary sites in the search results
        for site in primary_sites:
            domain = site["domain"]
            site_name = site["name"]
            
            # Skip if we already found this domain
            if domain in found_domains:
                continue
                
            # Look for this domain in all results
            for result in all_results:
                link = result.get("link", "")
                result_domain = self._extract_domain(link)
                
                if domain in result_domain:
                    # Create simplified entry with just the link
                    service = {
                        "name": site_name,
                        "service_type": "Online Decoration Service",
                        "website": link,
                        "source": domain
                    }
                    direct_services.append(service)
                    found_domains.add(domain)
                    break
            
            # If we didn't find the site in results, use a default URL
            if domain not in found_domains:
                # Create default links for important primary sites
                default_url = ""
                if domain == "partyone.in":
                    default_url = f"https://www.partyone.in/{location_lower}"
                elif domain == "haplun.in":
                    default_url = f"https://haplun.in/{location_lower}/birthday-decoration"
                elif domain == "balloondekor.com":
                    default_url = f"https://balloondekor.com/birthday-decorations/{location_lower}"
                elif domain == "fnp.com":
                    default_url = "https://www.fnp.com/decoration-services"
                elif domain == "amazon.in":
                    default_url = "https://www.amazon.in/Party-Supplies/b?node=5925792031"
                
                # Add the site with default URL if we have one
                if default_url:
                    service = {
                        "name": site_name,
                        "service_type": "Online Decoration Service",
                        "website": default_url,
                        "source": domain
                    }
                    direct_services.append(service)
                    found_domains.add(domain)
        
        return direct_services

    def _extract_domain(self, url: str) -> str:
        """Extract the domain name from a URL"""
        try:
            domain = urlparse(url).netloc
            # Remove www. prefix if present
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except:
            # Fall back to simple extraction if urlparse fails
            match = re.search(r'https?://(?:www\.)?([^/]+)', url)
            if match:
                return match.group(1)
            return url

class PhotographyVendorTool(BaseVendorSearchTool):
    name: str = "photography_vendor_tool"
    description: str = "Discovers photography vendors for events using targeted search and extraction"
    
    def _get_search_sites(self, service_type: str) -> List[str]:
        """Return preferred sites for photography vendors"""
        return ["sulekha.com", "weddingwire.in", "wedmegood.com"]
    
    def _generate_search_queries(self, service_type: str, event_type: str, 
                               location: str, budget: int, sites: List[str]) -> List[str]:
        """Generate photography-specific search queries"""
        queries = []
        
        # Primary search queries
        queries.append(f"best photographer for {event_type} in {location} site:sulekha.com")
        queries.append(f"top photography services for {event_type} in {location} under {budget} site:sulekha.com")
        
        # Secondary sources
        queries.append(f"{event_type} photographers in {location} site:weddingwire.in")
        
        if "wedding" in event_type.lower():
            queries.append(f"wedding photographers in {location} site:wedmegood.com")
        
        # Video services often combined with photography
        queries.append(f"photo and video services for {event_type} in {location}")
        
        # Direct photography studio searches
        queries.append(f"professional {event_type} photography studios in {location}")
        
        return queries

class CakeVendorTool(BaseVendorSearchTool):
    name: str = "cake_vendor_tool"
    description: str = "Discovers cake vendors and bakeries for events using targeted search and extraction"
    
    def _get_search_sites(self, service_type: str) -> List[str]:
        """Return preferred sites for cake vendors"""
        return ["fnp.com", "bakingo.com", "igp.com", "mioamoreshop.com"]
    
    def _generate_search_queries(self, service_type: str, event_type: str, 
                               location: str, budget: int, sites: List[str]) -> List[str]:
        """Generate cake-specific search queries"""
        queries = []
        
        # Online cake delivery services
        queries.append(f"{event_type} cake delivery in {location} site:fnp.com")
        queries.append(f"{event_type} cake delivery in {location} site:mioamoreshop.com")
        queries.append(f"{event_type} cake delivery in {location} site:igp.com")
        
        if "wedding" in event_type.lower():
            queries.append(f"wedding cake in {location} site:mioamoreshop.com")
        elif "birthday" in event_type.lower():
            queries.append(f"birthday cake delivery {location}")
        
        # Local bakeries
        queries.append(f"best bakeries for {event_type} cakes in {location}")
        queries.append(f"custom {event_type} cake shops {location}")
        
        return queries

class EntertainmentVendorTool(BaseVendorSearchTool):
    name: str = "entertainment_vendor_tool"
    description: str = "Discovers entertainment vendors (DJs, musicians, performers) for events"
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize lock in __init__ instead of at class level to avoid pickling issues
        self._request_lock = threading.Lock()
    
    def _get_search_sites(self, service_type: str) -> List[str]:
        """Return preferred sites for entertainment vendors"""
        # Added showtimeevent.com as primary source
        return ["showtimeevent.com", "sulekha.com", "venuelook.com", "weddingwire.in"]
    
    def _generate_search_queries(self, service_type: str, event_type: str, 
                               location: str, budget: int, sites: List[str]) -> List[str]:
        """Generate entertainment-specific search queries"""
        queries = []
        
        # Determine specific entertainment type
        if "dj" in service_type.lower():
            specific_type = "DJ"
        elif "music" in service_type.lower():
            specific_type = "live music band"
        elif "dancer" in service_type.lower():
            specific_type = "dance performers"
        else:
            specific_type = "entertainment"
        
        # Primary search queries - showtimeevent.com
        queries.append(f"best {specific_type} for {event_type} in {location} site:showtimeevent.com")
        queries.append(f"{location} {event_type} {specific_type} site:showtimeevent.com")
        
        # Secondary search queries - sulekha
        queries.append(f"top {specific_type} services for {event_type} in {location} site:sulekha.com")
        queries.append(f"{specific_type} services {location} site:sulekha.com")
        
        # Tertiary search queries - venuelook and weddingwire
        queries.append(f"{specific_type} services for {event_type} {location} site:venuelook.com")
        queries.append(f"{specific_type} services for {event_type} {location} site:weddingwire.in")
        
        # More specific queries based on event type
        if "wedding" in event_type.lower():
            queries.append(f"wedding {specific_type} in {location}")
        elif "corporate" in event_type.lower():
            queries.append(f"corporate event {specific_type} in {location}")
        elif "birthday" in event_type.lower():
            queries.append(f"birthday party {specific_type} in {location}")
        
        # Generic fallback
        queries.append(f"{specific_type} services in {location}")
        
        return queries


class GenericVendorTool(BaseVendorSearchTool):
    name: str = "generic_vendor_tool"
    description: str = "Discovers vendors for any type of event service"
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize lock in __init__ instead of at class level to avoid pickling issues
        self._request_lock = threading.Lock()
    
    def _get_search_sites(self, service_type: str) -> List[str]:
        """Return general sites for any vendor type"""
        # Changed order to make VenueLook primary, then Sulekha
        return ["venuelook.com", "sulekha.com", "justdial.com"]
    
    def _generate_search_queries(self, service_type: str, event_type: str, 
                               location: str, budget: int, sites: List[str]) -> List[str]:
        """Generate generic search queries for any service type"""
        queries = []
        
        # Clean and normalize service type for search
        clean_service = service_type.lower().strip()
        
        # Primary search queries - VenueLook
        queries.append(f"best {clean_service} for {event_type} in {location} site:venuelook.com")
        queries.append(f"{clean_service} services in {location} for {event_type} site:venuelook.com")
        queries.append(f"{event_type} {clean_service} {location} site:venuelook.com")
        
        # Secondary search queries - Sulekha
        queries.append(f"top {clean_service} services {location} site:sulekha.com")
        queries.append(f"{clean_service} service providers {location} site:sulekha.com")
        
        # Tertiary search queries - JustDial
        queries.append(f"{clean_service} services {location} site:justdial.com")
        
        # Budget-specific queries
        queries.append(f"affordable {clean_service} for {event_type} in {location}")
        
        # Event-specific queries
        queries.append(f"{event_type} {clean_service} services in {location}")
        
        # Generic fallback
        queries.append(f"{clean_service} vendors in {location}")
        
        return queries

# Factory function to get the right tool based on service type
def get_vendor_tool_for_service(service_type: str) -> BaseVendorSearchTool:
    """Return the appropriate vendor tool based on the service type"""
    service_type_lower = service_type.lower()
    
    if any(term in service_type_lower for term in ["catering", "caterer", "food"]):
        return CateringVendorTool()
    elif any(term in service_type_lower for term in ["decoration", "decorator", "decor"]):
        return DecorationVendorTool()
    elif any(term in service_type_lower for term in ["photography", "photographer", "video", "videography"]):
        return PhotographyVendorTool()
    elif any(term in service_type_lower for term in ["cake", "bakery", "pastry"]):
        return CakeVendorTool()
    elif any(term in service_type_lower for term in ["dj", "music", "band", "entertainment", "performer"]):
        return EntertainmentVendorTool()
    else:
        return GenericVendorTool()

# Master tool that delegates to specialized tools
# Master tool that delegates to specialized tools
class VendorToolsManager(BaseTool):
    name: str = "vendor_tools_manager"
    description: str = "Manages vendor search across different service types"
    args_schema: Type[BaseModel] = VendorSearchInput
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize the lock in the manager
        self._request_lock = threading.Lock()
    
    def _run(self, service_type: str, location: str, event_type: str, budget: int) -> List[Dict[str, Any]]:
        """
        Delegates to the appropriate specialized tool based on service type
        """
        # Get the specialized tool for this service type
        vendor_tool = self._get_vendor_tool_for_service(service_type)
        
        # Log which specialized tool we're using
        logger.info(f"Using {vendor_tool.name} for service type: {service_type}")
        
        # Execute the search using the specialized tool
        results = vendor_tool._run(service_type, location, event_type, budget)
        
        return results
    
    def _get_vendor_tool_for_service(self, service_type: str) -> BaseVendorSearchTool:
        """Return the appropriate vendor tool based on the service type"""
        service_type_lower = service_type.lower()
        
        # Create a new instance each time to avoid any shared state issues
        if any(term in service_type_lower for term in ["catering", "caterer", "food"]):
            tool = CateringVendorTool()
            tool._request_lock = threading.Lock()  # Ensure lock is initialized
            return tool
        elif any(term in service_type_lower for term in ["decoration", "decorator", "decor"]):
            tool = DecorationVendorTool()
            tool._request_lock = threading.Lock()
            return tool
        elif any(term in service_type_lower for term in ["photography", "photographer", "video", "videography"]):
            tool = PhotographyVendorTool()
            tool._request_lock = threading.Lock()
            return tool
        elif any(term in service_type_lower for term in ["cake", "bakery", "pastry"]):
            tool = CakeVendorTool()
            tool._request_lock = threading.Lock()
            return tool
        elif any(term in service_type_lower for term in ["dj", "music", "band", "entertainment", "performer"]):
            tool = EntertainmentVendorTool()
            tool._request_lock = threading.Lock()
            return tool
        else:
            tool = GenericVendorTool()
            tool._request_lock = threading.Lock()
            return tool
# ---------------------- Enhanced Budget Parser ----------------------
class BudgetInput(BaseModel):
    raw_budget: str = Field(..., description="Budget in any format")

class BudgetParserTool(BaseTool):
    name: str = "Budget Parser"
    description: str = "Converts budget formats to standardized amount"
    args_schema: Type[BaseModel] = BudgetInput

    def _run(self, raw_budget: str) -> dict:
        # First try LLM parsing
        try:
            prompt = f"""
            Convert the budget to INR. Examples:
            - "20k INR" → 20000
            - "5L" → 500000
            - "1.2M" → 1200000
            - "₹75,000" → 75000
            
            Input: {raw_budget}
            Output JSON: {{"amount": number, "currency": "INR"}}
            """
            response = llm.invoke(prompt)
            data = json.loads(response)
            if "amount" in data and "currency" in data:
                return {"amount": data["amount"], "currency": data["currency"], "converted_INR": data["amount"]}
        except:
            pass
        
        # Fallback to regex parsing
        try:
            numbers = re.findall(r'\d+\.?\d*', raw_budget)
            if numbers:
                amount = float(numbers[0])
                if 'k' in raw_budget.lower():
                    amount *= 1000
                elif 'l' in raw_budget.lower() or 'lakh' in raw_budget.lower():
                    amount *= 100000
                elif 'm' in raw_budget.lower() or 'million' in raw_budget.lower():
                    amount *= 1000000
                return {
                    "amount": int(amount),
                    "currency": "INR",
                    "converted_INR": int(amount)
                }
        except:
            pass
        
        # Ultimate fallback
        return {"amount": 0, "currency": "INR", "converted_INR": 0}
# ---------------------- Service Request Analyzer Tool ----------------------
class ServiceRequestInput(BaseModel):
    user_request: str = Field(..., description="User's service modification request")
    current_services: str = Field(..., description="Current list of services with budgets")

class ServiceRequestAnalyzerTool(BaseTool):
    name: str = "Service Request Analyzer"
    description: str = "Analyzes user's request to modify services and budgets"
    args_schema: Type[BaseModel] = ServiceRequestInput

    def _run(self, user_request: str, current_services: str) -> str:
        # Get the Mistral API key from environment
        mistral_api_key = os.environ.get("MISTRAL_API_KEY")
        if not mistral_api_key:
            return {
                "services_to_add": [],
                "services_to_remove": [],
                "services_to_modify": [],
                "analysis": "API key not found for request: " + user_request
            }
            
        # Initialize Mistral client
        client = Mistral(api_key=mistral_api_key)
        
        system_prompt = """
        You are a service analysis assistant that helps understand user requests to modify services and budgets.
        Analyze the user's request and the current services, then provide a structured JSON response.
        """
        
        user_prompt = f"""
        Given the user's request to modify services and the current service list, analyze what changes need to be made.
        
        Current services and budget allocation:
        {current_services}
        
        User's request:
        "{user_request}"
        
        Provide your response as a JSON object with these fields:
        1. "services_to_add": [list of services to add]
        2. "services_to_remove": [list of services to remove] 
        3. "services_to_modify": [array of objects with service, modification, and optional budget]
        4. "analysis": "brief explanation of the changes"
        
        Example of correctly formatted JSON:
        {{
            "services_to_add": ["Live Band"],
            "services_to_remove": [],
            "services_to_modify": [
                {{
                    "service": "Catering", 
                    "modification": "Increase budget", 
                    "budget": 25000
                }}
            ],
            "analysis": "User wants to add a live band and increase catering budget"
        }}
        """
        
        # Create the messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            # Request JSON response format
            chat_response = client.chat.complete(
                model="mistral-large-latest",
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result_text = chat_response.choices[0].message.content
            return json.loads(result_text)
            
        except Exception as e:
            logger.error(f"Error analyzing service request: {e}")
            return {
                "services_to_add": [],
                "services_to_remove": [],
                "services_to_modify": [],
                "analysis": "Could not process request: " + user_request
            }
# Custom decorative flowable for invitation
class DecorationFlowable(Flowable):
    """A custom flowable to add decorative elements to the invitation"""
    def __init__(self, width, height, decoration_type, color):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.decoration_type = decoration_type
        self.color = color
        
    def draw(self):
        """Draw the decoration"""
        canvas = self.canv
        canvas.saveState()
        canvas.setStrokeColor(self.color)
        canvas.setFillColor(self.color)
        
        if self.decoration_type == "divider":
            # Draw a fancy divider
            canvas.setLineWidth(0.5)
            mid_y = self.height / 2
            canvas.line(0, mid_y, self.width * 0.4, mid_y)
            
            # Center ornament
            x = self.width * 0.5
            y = mid_y
            radius = min(self.height * 0.4, 5)
            canvas.circle(x, y, radius, fill=1)
            
            canvas.line(self.width * 0.6, mid_y, self.width, mid_y)
            
        elif self.decoration_type == "corner":
            # Draw corner decorations
            size = min(self.width, self.height) * 0.3
            line_width = 1.5
            canvas.setLineWidth(line_width)
            
            # Top left corner
            canvas.line(0, self.height, size, self.height)
            canvas.line(0, self.height, 0, self.height - size)
            
            # Top right corner
            canvas.line(self.width - size, self.height, self.width, self.height)
            canvas.line(self.width, self.height, self.width, self.height - size)
            
            # Bottom left corner
            canvas.line(0, 0, size, 0)
            canvas.line(0, 0, 0, size)
            
            # Bottom right corner
            canvas.line(self.width - size, 0, self.width, 0)
            canvas.line(self.width, 0, self.width, size)
            
        canvas.restoreState()

# ---------------------- Mistral API Setup ----------------------
class MistralAPI:
    def __init__(self):
        self.api_key = os.environ.get("MISTRAL_API_KEY")
        if not self.api_key:
            logger.warning("MISTRAL_API_KEY not found in environment variables")
        self.api_url = "https://api.mistral.ai/v1/chat/completions"
    
    def generate_invitation(self, event_details):
        """Generate an invitation using Mistral API"""
        if not self.api_key:
            # Fallback to a template if API key is not available
            return self._generate_template_invitation(event_details)
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # Format the prompt for Mistral - with improved instructions
            formatted_date = event_details.get("formatted_date", event_details.get("event_date", ""))
            
            # Format the prompt for Mistral - with improved, more exciting instructions
            prompt = f"""
            Create a beautiful, engaging invitation for a {event_details['event_type']} with these details:
            - Event name: {event_details['event_name']}
            - Host: {event_details['host_name']}
            - Date: {formatted_date}
            - Time: {event_details['event_time']}
            - Venue: {event_details['venue_name']}
            - Address: {event_details['venue_address']}
            - Style preference: {event_details.get('style_preference', 'elegant')}

            Special Instructions: {event_details.get('special_instructions', 'None')}
            RSVP: {event_details.get('rsvp_contact', 'None')}

            IMPORTANT FORMATTING INSTRUCTIONS:
            1. DO NOT start with "Dear Guest" or any greeting - this is a formal invitation card, not a letter
            2. DO NOT end with "Warm regards" or similar closings
            3. DO NOT use markdown formatting like asterisks (*) or underscores (_)
            4. Keep it concise but impactful (100-150 words maximum)
            5. Begin with an exciting, catchy headline that grabs attention
            6. Use vibrant, enthusiastic language that conveys celebration and joy
            7. Include some playful or emotional phrases that make the recipient feel special
            8. Make the invitation sound personal and meaningful, not generic
            9. Use elegant and evocative language appropriate for a {event_details['event_type']}

            Write ONLY the invitation text - no commentary, explanations, or formatting notes.
            """
            
            payload = {
                "model": "mistral-large-latest",
                "messages": [
                    {"role": "system", "content": "You are an expert invitation writer who creates beautiful, formal invitations for special events."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            invitation_text = result['choices'][0]['message']['content'].strip()
            
            # Clean up any markdown formatting that might still be present
            invitation_text = re.sub(r'\*{1,2}(.*?)\*{1,2}', r'\1', invitation_text)
            invitation_text = re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', invitation_text)
            
            return invitation_text
            
        except Exception as e:
            logger.error(f"Error generating invitation with Mistral API: {e}")
            # Fallback to template if API call fails
            return self._generate_template_invitation(event_details)
    
    def _generate_template_invitation(self, event_details):
        """Generate a template invitation when API is unavailable"""
        event_type = event_details['event_type'].lower()
        event_name = event_details['event_name']
        host_name = event_details['host_name']
        formatted_date = event_details.get("formatted_date", event_details.get("event_date", ""))
        
        if "birthday" in event_type:
            return f"""You're Invited to a Birthday Celebration!

Join us as we celebrate {event_name}'s birthday with joy and festivity.

The party will be held at {event_details['venue_name']} on {formatted_date} at {event_details['event_time']}.

We've planned a wonderful celebration with good food, music, and great company.

RSVP: {event_details.get('rsvp_contact', 'Please RSVP')}

Hosted by {host_name}
"""
        elif "wedding" in event_type:
            return f"""Together with their families

{event_name}

Request the honor of your presence at their wedding celebration

{formatted_date} at {event_details['event_time']}

{event_details['venue_name']}
{event_details['venue_address']}

RSVP: {event_details.get('rsvp_contact', 'Please RSVP')}
"""
        else:
            return f"""You Are Cordially Invited

Please join us for {event_name}

{formatted_date} at {event_details['event_time']}
{event_details['venue_name']}

{event_details.get('special_instructions', '')}

RSVP: {event_details.get('rsvp_contact', 'Please RSVP')}

Hosted by {host_name}
"""

# ---------------------- Invitation Input Model ----------------------
class InvitationInput(BaseModel):
    event_name: str = Field(..., description="Name of the event")
    event_type: str = Field(..., description="Type of event (birthday, wedding, etc.)")
    event_date: str = Field(..., description="Date of the event")
    event_time: Optional[str] = Field(None, description="Time of the event")
    venue_name: str = Field(..., description="Name of the venue")
    venue_address: str = Field(..., description="Address of the venue")
    host_name: str = Field(..., description="Name of the host")
    guest_count: Optional[int] = Field(None, description="Number of guests")
    special_instructions: Optional[str] = Field(None, description="Any special instructions")
    rsvp_contact: Optional[str] = Field(None, description="Contact for RSVP")
    style_preference: Optional[str] = Field(None, description="Style preference (formal, casual, playful, elegant)")
    background_color: Optional[str] = Field(None, description="Background color for the invitation")

class InvitationStyleInput(BaseModel):
    invitation_id: str = Field(..., description="ID of the invitation to style")
    color_scheme: str = Field(..., description="Selected color scheme")
    font_style: str = Field(..., description="Selected font style")
    border_style: Optional[str] = Field(None, description="Selected border style")
    background_color: Optional[str] = Field(None, description="Background color")

class EmailInvitationInput(BaseModel):
    invitation_id: str = Field(..., description="ID of the invitation to send")
    email_subject: str = Field(..., description="Subject of the email")
    email_addresses: List[str] = Field(..., description="List of email addresses to send to")
    sender_name: str = Field(..., description="Name of the sender")
    additional_message: Optional[str] = Field(None, description="Additional message in the email")
    cc_addresses: Optional[List[str]] = Field(None, description="CC email addresses")

# ---------------------- Invitation Tools ----------------------
class InvitationCreatorTool:
    name: str = "invitation_creator_tool"
    description: str = "Creates an invitation text based on event details"
    
    # Store generated invitations
    _invitations = {}
    
    def __init__(self):
        self.mistral_api = MistralAPI()
    
    def _run(self, event_name: str, event_type: str, event_date: str, event_time: Optional[str], 
             venue_name: str, venue_address: str, host_name: str, guest_count: Optional[int] = None,
             special_instructions: Optional[str] = None, rsvp_contact: Optional[str] = None,
             style_preference: Optional[str] = None, background_color: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates invitation text based on event details
        """
        logger.info(f"Creating invitation for {event_name}")
        
        # Use a default guest count if not provided
        if guest_count is None:
            guest_count = 30
        
        # Format event date
        try:
            # Try to parse different date formats
            date_formats = ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y"]
            parsed_date = None
            
            for date_format in date_formats:
                try:
                    parsed_date = datetime.strptime(event_date, date_format)
                    break
                except ValueError:
                    continue
            
            if parsed_date:
                formatted_date = parsed_date.strftime("%A, %B %d, %Y")
            else:
                formatted_date = event_date
        except Exception as e:
            logger.warning(f"Error formatting date: {e}")
            formatted_date = event_date
        
        try:
            # Prepare event details for Mistral API
            event_details = {
                "event_name": event_name,
                "event_type": event_type,
                "event_date": event_date,
                "formatted_date": formatted_date,
                "event_time": event_time if event_time else "To be announced",
                "venue_name": venue_name,
                "venue_address": venue_address,
                "host_name": host_name,
                "guest_count": guest_count,
                "special_instructions": special_instructions,
                "rsvp_contact": rsvp_contact,
                "style_preference": style_preference,
                "background_color": background_color
            }
            
            # Generate invitation text using Mistral API
            invitation_text = self.mistral_api.generate_invitation(event_details)
            
            # Generate a unique ID for this invitation
            invitation_id = str(uuid.uuid4())
            
            # Create invitation data object
            invitation_data = {
                "id": invitation_id,
                "event_name": event_name,
                "event_type": event_type,
                "event_date": formatted_date,
                "event_time": event_time,
                "venue_name": venue_name,
                "venue_address": venue_address,
                "host_name": host_name,
                "guest_count": guest_count,
                "special_instructions": special_instructions,
                "rsvp_contact": rsvp_contact,
                "style_preference": style_preference,
                "background_color": background_color,
                "text": invitation_text,
                "created_at": datetime.now().isoformat(),
                "color_scheme": None,
                "font_style": None,
                "border_style": None,
                "pdf_path": None
            }
            
            # Store the invitation data
            self._invitations[invitation_id] = invitation_data
            
            # Prepare response with invitation preview
            color_options = self._get_color_options()
            font_options = self._get_font_options()
            border_options = self._get_border_options()
            background_options = self._get_background_options()
            
            return {
                "invitation_id": invitation_id,
                "invitation_text": invitation_text,
                "color_options": color_options,
                "font_options": font_options,
                "border_options": border_options,
                "background_options": background_options
            }
            
        except Exception as e:
            logger.error(f"Error creating invitation: {e}")
            return {"error": f"Failed to create invitation: {str(e)}"}
    
    def _get_color_options(self):
        """Returns available color scheme options"""
        return [
            {"id": "elegant", "name": "Elegant Gold", "primary": "#4A4A4A", "secondary": "#E5E5E5", "accent": "#D4AF37"},
            {"id": "birthday", "name": "Birthday Pink", "primary": "#FF5252", "secondary": "#FFECB3", "accent": "#FF8A80"},
            {"id": "nature", "name": "Nature Green", "primary": "#2E7D32", "secondary": "#F1F8E9", "accent": "#AED581"},
            {"id": "ocean", "name": "Ocean Blue", "primary": "#1565C0", "secondary": "#E3F2FD", "accent": "#81D4FA"},
            {"id": "vintage", "name": "Vintage Brown", "primary": "#5D4037", "secondary": "#EFEBE9", "accent": "#A1887F"},
            {"id": "pastel", "name": "Pastel Purple", "primary": "#9575CD", "secondary": "#EDE7F6", "accent": "#B39DDB"},
            {"id": "wedding", "name": "Wedding Silver", "primary": "#455A64", "secondary": "#ECEFF1", "accent": "#B0BEC5"},
            {"id": "formal", "name": "Formal Black", "primary": "#212121", "secondary": "#F5F5F5", "accent": "#9E9E9E"}
        ]
    
    def _get_font_options(self):
        """Returns available font style options"""
        return [
            {"id": "times", "name": "Times (Classic)", "heading": "Times-Bold", "body": "Times-Roman"},
            {"id": "helvetica", "name": "Helvetica (Modern)", "heading": "Helvetica-Bold", "body": "Helvetica"},
            {"id": "courier", "name": "Courier (Typewriter)", "heading": "Courier-Bold", "body": "Courier"},
            {"id": "zapfdingbats", "name": "Zapf Dingbats (Decorative)", "heading": "ZapfDingbats", "body": "Helvetica"}
        ]
    
    def _get_border_options(self):
        """Returns available border style options"""
        return [
            {"id": "none", "name": "None (No Border)"},
            {"id": "simple", "name": "Simple Line"},
            {"id": "double", "name": "Double Line"},
            {"id": "dashed", "name": "Dashed"},
            {"id": "ornate", "name": "Ornate Corners"},
            {"id": "floral", "name": "Floral Border"}
        ]
        
    def _get_background_options(self):
        """Returns available background color options"""
        return [
            {"id": "white", "name": "White", "color": "#FFFFFF"},
            {"id": "cream", "name": "Cream", "color": "#FFF8E1"},
            {"id": "light_pink", "name": "Light Pink", "color": "#FFEEF8"},
            {"id": "light_blue", "name": "Light Blue", "color": "#E3F2FD"},
            {"id": "light_green", "name": "Light Green", "color": "#F1F8E9"},
            {"id": "lavender", "name": "Lavender", "color": "#F3E5F5"},
            {"id": "beige", "name": "Beige", "color": "#F5F5DC"},
            {"id": "light_gray", "name": "Light Gray", "color": "#F5F5F5"}
        ]
    
    @classmethod
    def get_invitation(cls, invitation_id):
        """Get invitation data by ID"""
        return cls._invitations.get(invitation_id)

class InvitationStylerTool:
    name: str = "invitation_styler_tool"
    description: str = "Applies style to an invitation and generates a PDF"
    
    def _run(self, invitation_id: str, color_scheme: str, font_style: str, 
             border_style: Optional[str] = None, background_color: Optional[str] = None) -> Dict[str, Any]:
        """
        Applies styling to the invitation and generates a PDF
        """
        logger.info(f"Styling invitation {invitation_id}")
        
        # Get the invitation data
        invitation_data = InvitationCreatorTool.get_invitation(invitation_id)
        if not invitation_data:
            return {"error": f"Invitation with ID {invitation_id} not found"}
        
        try:
            # Get color scheme, font style, and border style details
            color_options = InvitationCreatorTool()._get_color_options()
            font_options = InvitationCreatorTool()._get_font_options()
            border_options = InvitationCreatorTool()._get_border_options()
            background_options = InvitationCreatorTool()._get_background_options()
            
            selected_color = next((c for c in color_options if c["id"] == color_scheme), color_options[0])
            selected_font = next((f for f in font_options if f["id"] == font_style), font_options[0])
            selected_border = next((b for b in border_options if b["id"] == border_style), border_options[0]) if border_style else None
            
            # Get background color
            if background_color:
                selected_background = next((bg for bg in background_options if bg["id"] == background_color), background_options[0])
            else:
                # Default to cream background if none selected
                selected_background = next((bg for bg in background_options if bg["id"] == "cream"), background_options[0])
            
            # Update invitation data with selected styles
            invitation_data["color_scheme"] = selected_color
            invitation_data["font_style"] = selected_font
            invitation_data["border_style"] = selected_border
            invitation_data["background_color"] = selected_background
            
            # Generate the PDF
            pdf_path = self._generate_pdf(invitation_data)
            invitation_data["pdf_path"] = pdf_path
            
            # Return the result
            return {
                "invitation_id": invitation_id,
                "pdf_path": pdf_path,
                "download_url": f"/download/{os.path.basename(pdf_path)}",
                "preview_url": f"/preview/{os.path.basename(pdf_path)}",
                "message": "Invitation styled and PDF generated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error styling invitation: {e}")
            return {"error": f"Failed to style invitation: {str(e)}"}
    
    def _generate_pdf(self, invitation_data):
        """Generate PDF from invitation data using ReportLab with enhanced visual appeal"""
        # Get style information
        color_scheme = invitation_data["color_scheme"]
        font_style = invitation_data["font_style"]
        border_style = invitation_data["border_style"]
        background_color = invitation_data["background_color"]
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.getcwd(), "invitations")
        os.makedirs(output_dir, exist_ok=True)
        
        # Define the output file path
        event_name_slug = re.sub(r'[^\w\s-]', '', invitation_data["event_name"]).strip().lower()
        event_name_slug = re.sub(r'[-\s]+', '-', event_name_slug)
        filename = f"{event_name_slug}-{invitation_data['id'][:8]}.pdf"
        output_path = os.path.join(output_dir, filename)
        
        # Convert hex colors to ReportLab colors
        def hex_to_rgb(hex_color):
            h = hex_color.lstrip('#')
            return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4))
        
        primary_color = hex_to_rgb(color_scheme["primary"])
        secondary_color = hex_to_rgb(color_scheme["secondary"])
        accent_color = hex_to_rgb(color_scheme["accent"])
        background_rgb = hex_to_rgb(background_color["color"])
        
        class InvitationCanvas:
            """Handles drawing the background and decorative elements on each page"""
            def __init__(self, background_color, accent_color, border_style):
                self.background_color = background_color
                self.accent_color = accent_color
                self.border_style = border_style
                
            def on_page(self, canvas, doc):
                canvas.saveState()
                width, height = A5
                
                # Draw background color
                canvas.setFillColor(colors.Color(*self.background_color))
                canvas.rect(0, 0, width, height, fill=1, stroke=0)
                
                # Draw decorative border based on style
                canvas.setStrokeColor(colors.Color(*self.accent_color))
                
                if self.border_style["id"] == "simple":
                    # Simple border
                    canvas.setLineWidth(1.5)
                    margin = 20
                    canvas.rect(margin, margin, width-2*margin, height-2*margin)
                
                elif self.border_style["id"] == "double":
                    # Double border
                    canvas.setLineWidth(1)
                    outer_margin = 20
                    inner_margin = 30
                    # Outer border
                    canvas.rect(outer_margin, outer_margin, width-2*outer_margin, height-2*outer_margin)
                    # Inner border
                    canvas.rect(inner_margin, inner_margin, width-2*inner_margin, height-2*inner_margin)
                
                elif self.border_style["id"] == "dashed":
                    # Dashed border
                    canvas.setDash(6, 3)
                    canvas.setLineWidth(1)
                    margin = 20
                    canvas.rect(margin, margin, width-2*margin, height-2*margin)
                
                elif self.border_style["id"] == "ornate":
                    # Ornate corners
                    canvas.setLineWidth(1)
                    margin = 20
                    corner_size = 40
                    
                    # Top left
                    canvas.line(margin, height-margin, margin+corner_size, height-margin)
                    canvas.line(margin, height-margin, margin, height-margin-corner_size)
                    
                    # Top right
                    canvas.line(width-margin-corner_size, height-margin, width-margin, height-margin)
                    canvas.line(width-margin, height-margin, width-margin, height-margin-corner_size)
                    
                    # Bottom left
                    canvas.line(margin, margin, margin+corner_size, margin)
                    canvas.line(margin, margin, margin, margin+corner_size)
                    
                    # Bottom right
                    canvas.line(width-margin-corner_size, margin, width-margin, margin)
                    canvas.line(width-margin, margin, width-margin, margin+corner_size)
                    
                    # Corner decorations
                    for x, y in [(margin, height-margin), (width-margin, height-margin), 
                                (margin, margin), (width-margin, margin)]:
                        # Small decorative circle
                        canvas.setFillColor(colors.Color(*self.accent_color))
                        canvas.circle(x, y, 3, fill=1)
                
                elif self.border_style["id"] == "floral":
                    # Floral border - simplified representation
                    margin = 30
                    canvas.setLineWidth(1)
                    
                    # Draw a frame
                    canvas.rect(margin, margin, width-2*margin, height-2*margin)
                    
                    # Draw floral elements in corners
                    for x, y in [(margin, height-margin), (width-margin, height-margin), 
                               (margin, margin), (width-margin, margin)]:
                        
                        # Draw petal-like shapes
                        canvas.setFillColor(colors.Color(*self.accent_color, alpha=0.5))
                        radius = 15
                        for angle in range(0, 360, 45):
                            rad_angle = angle * 3.14159 / 180
                            x1 = x + radius * 0.8 * (1 if angle < 180 else -1)
                            y1 = y + radius * 0.8 * (1 if 45 <= angle <= 225 else -1)
                            canvas.circle(x1, y1, radius/2, fill=1)
                
                canvas.restoreState()
        
        # Create PDF document with custom page setup
        doc = SimpleDocTemplate(
            output_path, 
            pagesize=A5, 
            rightMargin=50, 
            leftMargin=50, 
            topMargin=50, 
            bottomMargin=50
        )
        
        # Create a canvas painter for background and decorations
        canvas_painter = InvitationCanvas(background_rgb, accent_color, border_style or {"id": "none"})
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Add custom styles with unique names to avoid conflicts
        styles.add(ParagraphStyle(
            name='InviteTitle',
            fontName=font_style["heading"],
            fontSize=22,
            alignment=TA_CENTER,
            textColor=colors.Color(*primary_color),
            spaceAfter=16
        ))
        
        styles.add(ParagraphStyle(
            name='InviteHeading',
            fontName=font_style["heading"],
            fontSize=16,
            alignment=TA_CENTER,
            textColor=colors.Color(*primary_color),
            spaceAfter=10
        ))
        
        styles.add(ParagraphStyle(
            name='InviteNormal',
            fontName=font_style["body"],
            fontSize=12,
            alignment=TA_CENTER,
            textColor=colors.Color(*primary_color),
            spaceAfter=6,
            leading=16
        ))
        
        styles.add(ParagraphStyle(
            name='InviteDetails',
            fontName=font_style["body"],
            fontSize=11,
            alignment=TA_CENTER,
            textColor=colors.Color(*primary_color),
            spaceAfter=4
        ))
        
        styles.add(ParagraphStyle(
            name='InviteVenue',
            fontName=font_style["heading"],
            fontSize=14,
            alignment=TA_CENTER,
            textColor=colors.Color(*accent_color),
            spaceAfter=6
        ))
        
        styles.add(ParagraphStyle(
            name='InviteFooter',
            fontName=font_style["body"],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.Color(*accent_color),
            spaceAfter=6,
            italic=True
        ))
        
        # Create story (content)
        story = []
        
        # Add title - first extract a good title from invitation text
        lines = invitation_data["text"].split('\n')
        title = invitation_data["event_name"]
        
        # Try to find a good title from the invitation text
        for line in lines[:3]:  # Check first few lines for a title
            if line.strip() and len(line.strip()) < 50:  # Find short enough line 
                title = line.strip()
                break
        
        # Start with decorative element
        accent_color_obj = colors.Color(*accent_color)
        story.append(DecorationFlowable(400, 20, "corner", accent_color_obj))
        story.append(Spacer(1, 0.2*inch))
        
        # Add title
        story.append(Paragraph(title, styles["InviteTitle"]))
        
        # Add decorative divider
        story.append(DecorationFlowable(400, 10, "divider", accent_color_obj))
        story.append(Spacer(1, 0.3*inch))
        
        # Process invitation text (split by paragraphs)
        paragraphs = invitation_data["text"].split('\n\n')
        
        # Skip the first paragraph if it's the title we already used
        start_idx = 1 if paragraphs and paragraphs[0].strip() == title else 0
        
        for paragraph in paragraphs[start_idx:]:
            if paragraph.strip():
                story.append(Paragraph(paragraph.strip(), styles["InviteNormal"]))
                story.append(Spacer(1, 0.15*inch))
        
        # Add venue information prominently
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph("VENUE", styles["InviteHeading"]))
        story.append(Paragraph(invitation_data["venue_name"], styles["InviteVenue"]))
        story.append(Paragraph(invitation_data["venue_address"], styles["InviteDetails"]))
        
        # Add decorative divider
        story.append(Spacer(1, 0.2*inch))
        story.append(DecorationFlowable(400, 10, "divider", accent_color_obj))
        story.append(Spacer(1, 0.2*inch))
        
        # Add event details
        details_text = f"Date: {invitation_data['event_date']}"
        if invitation_data["event_time"]:
            details_text += f" at {invitation_data['event_time']}"
        
        story.append(Paragraph(details_text, styles["InviteDetails"]))
        
        if invitation_data.get("special_instructions"):
            story.append(Spacer(1, 0.1*inch))
            story.append(Paragraph(f"Note: {invitation_data['special_instructions']}", styles["InviteDetails"]))
        
        # Add RSVP if available
        if invitation_data.get("rsvp_contact"):
            story.append(Spacer(1, 0.15*inch))
            story.append(Paragraph(f"RSVP: {invitation_data['rsvp_contact']}", styles["InviteFooter"]))
        
        # Add host
        story.append(Spacer(1, 0.15*inch))
        story.append(Paragraph(f"Hosted by {invitation_data['host_name']}", styles["InviteFooter"]))
        
        # Add final decorative element
        story.append(Spacer(1, 0.2*inch))
        story.append(DecorationFlowable(400, 20, "corner", accent_color_obj))
        
        # Create a custom frame
        frame = Frame(
            doc.leftMargin, 
            doc.bottomMargin, 
            A5[0] - 2*doc.leftMargin, 
            A5[1] - 2*doc.topMargin,
            id='normal'
        )
        
        # Create page template with our canvas painter
        template = PageTemplate(
            id='invitation_template', 
            frames=frame, 
            onPage=canvas_painter.on_page
        )

        # Add template and ensure all pages use the same style
        doc.addPageTemplates([template])

        # Use a custom document builder to apply background to all pages
        def _doNothing(canvas, doc):
            pass

        doc.build(story, onFirstPage=canvas_painter.on_page, onLaterPages=canvas_painter.on_page)
        
        return output_path

class EmailInvitationTool:
    name: str = "email_invitation_tool"
    description: str = "Sends invitation PDF via email"
    
    def _run(self, invitation_id: str, email_subject: str, email_addresses: List[str], 
             sender_name: str, additional_message: Optional[str] = None, 
             cc_addresses: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Sends invitation PDF to specified email addresses
        """
        logger.info(f"Sending invitation {invitation_id} via email")
        
        # Get the invitation data
        invitation_data = InvitationCreatorTool.get_invitation(invitation_id)
        if not invitation_data:
            return {"error": f"Invitation with ID {invitation_id} not found"}
        
        if not invitation_data.get("pdf_path"):
            return {"error": "Invitation PDF has not been generated yet"}
        
        try:
            # Get email credentials from environment variables
            email_user = os.environ.get("EMAIL_USER")
            email_password = os.environ.get("EMAIL_PASSWORD")
            email_server = os.environ.get("EMAIL_SERVER", "smtp.gmail.com")
            email_port = int(os.environ.get("EMAIL_PORT", 587))
            
            if not email_user or not email_password:
                return {"error": "Email credentials are not configured"}
            
            # Create multipart message
            msg = MIMEMultipart()
            msg['From'] = f"{sender_name} <{email_user}>"
            msg['To'] = ", ".join(email_addresses)
            msg['Subject'] = email_subject
            
            if cc_addresses and len(cc_addresses) > 0:
                msg['Cc'] = ", ".join(cc_addresses)
            
            # Create email body
            body = f"""
            Dear Guest,
            
            You are cordially invited to {invitation_data['event_name']}!
            
            Please find the attached invitation with all the details.
            
            {"" if not additional_message else additional_message + "\n\n"}
            Best regards,
            {sender_name}
            """
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach PDF invitation
            with open(invitation_data["pdf_path"], "rb") as f:
                attachment = MIMEApplication(f.read(), _subtype="pdf")
                attachment.add_header('Content-Disposition', 'attachment', 
                                      filename=os.path.basename(invitation_data["pdf_path"]))
                msg.attach(attachment)
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(email_server, email_port) as server:
                server.starttls()
                server.login(email_user, email_password)
                
                all_recipients = email_addresses + (cc_addresses if cc_addresses else [])
                server.sendmail(email_user, all_recipients, msg.as_string())
            
            # Return success result
            return {
                "success": True,
                "message": f"Invitation sent successfully to {len(email_addresses)} recipients",
                "recipients": email_addresses,
                "cc": cc_addresses
            }
            
        except Exception as e:
            logger.error(f"Error sending invitation email: {e}")
            return {"error": f"Failed to send invitation email: {str(e)}"}
class MongoDBManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.connect()
        
    def connect(self):
        """Connect to MongoDB and select database"""
        try:
            # Get connection string from environment variable or use local default
            mongo_uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
            self.client = MongoClient(mongo_uri)
            self.db = self.client["EventWise"]  # Database name as specified
            logger.info("Connected to MongoDB successfully")
            
            # Create indexes for better performance
            self.db.user_details.create_index("email", unique=True)
            self.db.event_details.create_index("uid")
            self.db.event_details.create_index("event_id", unique=True)
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            raise
    
    def close(self):
        """Close the MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    # ---------------------- User Management ----------------------
    def register_user(self, email, password, name=None):
        """Register a new user"""
        try:
            # Check if user already exists
            if self.db.user_details.find_one({"email": email}):
                return {"success": False, "message": "User with this email already exists"}
            
            # Hash the password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Generate a unique user ID
            uid = f"usr_{uuid.uuid4().hex[:16]}"
            
            # Create user document
            user_doc = {
                "uid": uid,
                "email": email,
                "password": hashed_password,
                "name": name if name else email.split('@')[0],  # Use part of email as name if not provided
                "created_at": datetime.now().isoformat()
            }
            
            # Insert into database
            result = self.db.user_details.insert_one(user_doc)
            
            return {
                "success": True, 
                "message": "User registered successfully",
                "uid": uid
            }
            
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return {"success": False, "message": f"Registration failed: {str(e)}"}
    
    def login_user(self, email, password):
        """Login a user"""
        try:
            # Find user by email
            user = self.db.user_details.find_one({"email": email})
            
            if not user:
                return {"success": False, "message": "User not found"}
            
            # Check password
            if bcrypt.checkpw(password.encode('utf-8'), user["password"]):
                return {
                    "success": True,
                    "message": "Login successful",
                    "uid": user["uid"],
                    "name": user.get("name", "")
                }
            else:
                return {"success": False, "message": "Incorrect password"}
                
        except Exception as e:
            logger.error(f"Error logging in: {e}")
            return {"success": False, "message": f"Login failed: {str(e)}"}
    
    def get_user_events(self, uid):
        """Get all events created by a user"""
        try:
            events = list(self.db.event_details.find({"uid": uid}))
            # Convert ObjectId to string for serialization
            for event in events:
                event["_id"] = str(event["_id"])
            
            return {"success": True, "events": events}
            
        except Exception as e:
            logger.error(f"Error getting user events: {e}")
            return {"success": False, "message": f"Could not retrieve events: {str(e)}"}
    
    # ---------------------- Event Management ----------------------
    def create_event(self, uid, event_details):
        """Create a new event"""
        try:
            # Generate a unique event ID
            event_id = f"evt_{uuid.uuid4().hex[:16]}"
            
            # Create event document
            event_doc = {
                "event_id": event_id,
                "uid": uid,
                "event_name": event_details["event_name"],
                "event_category": event_details["event_category"],
                "event_date": event_details["event_date"],
                "num_guests": event_details["num_guests"],
                "budget": event_details["budget"],
                "location": event_details["location"],
                "created_at": datetime.now().isoformat(),
                "current_status": "planning",
                "services": [],  # Will be populated later
                "invitation": None  # Will be populated if invitation is created
            }
            
            # Add event_time if available
            if "event_time" in event_details:
                event_doc["event_time"] = event_details["event_time"]
            
            # Insert into database
            result = self.db.event_details.insert_one(event_doc)
            
            return {
                "success": True,
                "message": "Event created successfully",
                "event_id": event_id
            }
            
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return {"success": False, "message": f"Could not create event: {str(e)}"}
    
    def update_event_services(self, event_id, services):
        """Update services for an event"""
        try:
            # Process each service and set initial status to 'pending'
            for service in services:
                service["status"] = "pending"
                service["selected_provider"] = None
            
            # Update services in the database
            result = self.db.event_details.update_one(
                {"event_id": event_id},
                {"$set": {"services": services}}
            )
            
            if result.modified_count > 0:
                return {"success": True, "message": "Services updated successfully"}
            else:
                return {"success": False, "message": "No changes made to services"}
                
        except Exception as e:
            logger.error(f"Error updating event services: {e}")
            return {"success": False, "message": f"Could not update services: {str(e)}"}
    
    def update_service_provider(self, event_id, service_name, provider_details):
        """Update provider details for a specific service"""
        try:
            # Find the event
            event = self.db.event_details.find_one({"event_id": event_id})
            
            if not event:
                return {"success": False, "message": "Event not found"}
            
            # Update the specific service
            updated = False
            services = event.get("services", [])
            
            for service in services:
                if service["service"].lower() == service_name.lower():
                    service["selected_provider"] = provider_details
                    service["status"] = "completed"
                    updated = True
                    break
            
            if not updated:
                return {"success": False, "message": f"Service '{service_name}' not found in event"}
            
            # Update current status based on completed services
            completed_services = [s["service"] for s in services if s["status"] == "completed"]
            current_status = f"done {', '.join(completed_services)}" if completed_services else "planning"
            
            # Update in database
            result = self.db.event_details.update_one(
                {"event_id": event_id},
                {"$set": {"services": services, "current_status": current_status}}
            )
            
            if result.modified_count > 0:
                return {"success": True, "message": f"Provider for {service_name} updated successfully"}
            else:
                return {"success": False, "message": "No changes made to provider"}
                
        except Exception as e:
            logger.error(f"Error updating service provider: {e}")
            return {"success": False, "message": f"Could not update provider: {str(e)}"}
    
    # No longer storing invitation details in the database
    
    def get_event(self, event_id):
        """Get details of a specific event"""
        try:
            event = self.db.event_details.find_one({"event_id": event_id})
            
            if not event:
                return {"success": False, "message": "Event not found"}
            
            # Convert ObjectId to string for serialization
            event["_id"] = str(event["_id"])
            
            return {"success": True, "event": event}
            
        except Exception as e:
            logger.error(f"Error getting event: {e}")
            return {"success": False, "message": f"Could not retrieve event: {str(e)}"}
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

# Create a new dedicated venue search agent
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

# Updated venue search task to retrieve more options
venue_search_task = Task(
    description=(
        "Conduct a comprehensive venue search in {location} for the {event_category} event using the UniversalVenueServiceTool. "
        "Search for venues with these parameters: {venue_type} for {num_guests} guests within a budget of {service_budget} INR. "
        "Aim to provide AT LEAST 10-15 venue options if available to support the 'Show More' feature. "
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
        "\nReturn the data in a clean, consistent JSON structure."
    ),
    agent=venue_search_coordinator,
    expected_output="List of suitable venues with structured details"
)

# Updated vendor search task to retrieve more options
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
        "\nReturn the data in a clean, consistent JSON structure."
    ),
    agent=vendor_service_coordinator,
    expected_output="List of suitable vendors with structured details"
)
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
    """Extract the text content from a CrewOutput object"""
    if hasattr(crew_output, 'raw_output'):
        return crew_output.raw_output
    elif hasattr(crew_output, 'result'):
        return crew_output.result
    elif hasattr(crew_output, 'outputs'):
        # If it's a dict of outputs, join them
        if isinstance(crew_output.outputs, dict):
            return "\n".join(str(v) for v in crew_output.outputs.values())
    
    # Fall back to string representation
    return str(crew_output)

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

def service_selection_and_search(approved_services, details):
    """Function to handle both venue and vendor searches using separate agents"""
    print("\n=== Service Vendor Search ===")
    print("Let's find vendors for your approved services:")

    # Track progress of selected services
    services_selected = []
    services_pending = [service["service"] for service in approved_services]

    # Display services for selection
    for i, service in enumerate(approved_services, 1):
        print(f"{i}. {service['service']} (Budget: ₹{service['budget']:,})")

    # Ask user which service to find vendors for
    while True:
        # Show progress tracker
        display_progress_tracker(services_selected, services_pending)
        
        search_vendors = input("\nWould you like to search for vendors for any of these services? (yes/no): ").lower()
        
        if search_vendors != "yes":
            break
            
        try:
            service_num = int(input("Enter the number of the service you'd like to find vendors for: "))
            if 1 <= service_num <= len(approved_services):
                selected_service = approved_services[service_num-1]
                
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
                    venue_crew = Crew(
                        agents=[venue_search_coordinator],
                        tasks=[venue_search_task],
                        process=Process.sequential,
                        verbose=True
                    )
                    service_output = venue_crew.kickoff(inputs=venue_inputs)
                    service_results = extract_text_from_crew_output(service_output)
                    
                    # Parse and display venue results
                    try:
                        venues = json.loads(service_results) if isinstance(service_results, str) else service_results
                        if isinstance(venues, dict) and "error" in venues:
                            print("No venues found matching your criteria.")
                            continue
                            
                        # Display venue results
                        print(format_venues_for_display(venues))
                        
                        # Ask if user wants to select a venue
                        if select_provider(venues, selected_service):
                            # Update progress tracker if a selection was made
                            services_selected.append(selected_service['service'])
                            if selected_service['service'] in services_pending:
                                services_pending.remove(selected_service['service'])
                    except:
                        print("Error processing venue search results.")
                else:
                    # Create inputs for vendor search
                    vendor_inputs = {
                        "service_type": selected_service['service'],
                        "location": details["location"],
                        "event_category": details["event_category"],
                        "service_budget": selected_service['budget']
                    }
                    
                    # Use vendor service coordinator for vendor searches
                    vendor_crew = Crew(
                        agents=[vendor_service_coordinator],
                        tasks=[vendor_search_task],
                        process=Process.sequential,
                        verbose=True
                    )
                    service_output = vendor_crew.kickoff(inputs=vendor_inputs)
                    service_results = extract_text_from_crew_output(service_output)
                    
                    # Parse and display vendor results
                    try:
                        vendors = json.loads(service_results) if isinstance(service_results, str) else service_results
                        if isinstance(vendors, dict) and "error" in vendors:
                            print("No vendors found matching your criteria.")
                            continue
                            
                        # Display vendor results
                        print(format_vendors_for_display(vendors))
                        
                        # Ask if user wants to select a vendor
                        if select_provider(vendors, selected_service):
                            # Update progress tracker if a selection was made
                            services_selected.append(selected_service['service'])
                            if selected_service['service'] in services_pending:
                                services_pending.remove(selected_service['service'])
                    except:
                        print("Error processing vendor search results.")
            else:
                print("Invalid service number. Please try again.")
        except ValueError:
            print("Please enter a valid number.")


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
# ---------------------- Invitation Flow Functions ----------------------
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
        
        # Detailed Gmail setup instructions
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

def validate_password(password):
    """
    Validate password strength
    Returns (is_valid, message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is valid"

def validate_email(email):
    """
    Validate email format
    Returns (is_valid, message)
    """
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_regex, email):
        return True, "Email is valid"
    else:
        return False, "Invalid email format"

def register_user_flow():
    """Interactive registration flow"""
    print("\n=== User Registration ===")
    
    # Get email
    while True:
        email = input("Enter your email: ")
        email_valid, email_msg = validate_email(email)
        if email_valid:
            break
        print(f"Error: {email_msg}")
    
    # Get password
    while True:
        password = input("Enter your password: ")
        pwd_valid, pwd_msg = validate_password(password)
        if not pwd_valid:
            print(f"Error: {pwd_msg}")
            continue
        
        confirm_password = input("Confirm your password: ")
        if password != confirm_password:
            print("Error: Passwords do not match")
            continue
        
        break
    
    # Get name (optional)
    name = input("Enter your name (optional): ")
    
    # Register in database
    db_manager = MongoDBManager()
    result = db_manager.register_user(email, password, name)
    db_manager.close()
    
    if result["success"]:
        print(f"Registration successful! Welcome, {name or email.split('@')[0]}!")
        return result["uid"]
    else:
        print(f"Registration failed: {result['message']}")
        return None

def login_user_flow():
    """Interactive login flow"""
    print("\n=== User Login ===")
    
    email = input("Enter your email: ")
    password = input("Enter your password: ")
    
    # Login in database
    db_manager = MongoDBManager()
    result = db_manager.login_user(email, password)
    db_manager.close()
    
    if result["success"]:
        print(f"Login successful! Welcome back, {result.get('name', email.split('@')[0])}!")
        return result["uid"]
    else:
        print(f"Login failed: {result['message']}")
        return None
def update_services_in_db(event_id, service_budget_list):
    """Update services in database"""
    db_manager = MongoDBManager()
    result = db_manager.update_event_services(event_id, service_budget_list)
    db_manager.close()
    
    if result["success"]:
        print("Services updated in database successfully!")
    else:
        print(f"Error updating services: {result['message']}")

def update_service_provider_in_db(event_id, service_name, provider_details):
    """Update service provider in database"""
    db_manager = MongoDBManager()
    result = db_manager.update_service_provider(event_id, service_name, provider_details)
    db_manager.close()
    
    if result["success"]:
        print(f"Provider for {service_name} updated in database successfully!")
    else:
        print(f"Error updating provider: {result['message']}")

def update_invitation_in_db(event_id, invitation_details):
    """Update invitation in database"""
    db_manager = MongoDBManager()
    result = db_manager.update_invitation(event_id, invitation_details)
    db_manager.close()
    
    if result["success"]:
        print("Invitation updated in database successfully!")
    else:
        print(f"Error updating invitation: {result['message']}")

def select_provider_with_db(event_id, providers, selected_service):
    """Helper function to select a provider from a list and update database"""
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
                
                # Update in database
                update_service_provider_in_db(event_id, selected_service['service'], selected_provider)
                
                return True
            else:
                print("Invalid option number. No selection made.")
                return False
        except ValueError:
            print("Please enter a valid number. No selection made.")
            return False
    return False

def service_selection_and_search_with_db(event_id, approved_services, details):
    """Function to handle both venue and vendor searches using separate agents with database updates"""
    print("\n=== Service Vendor Search ===")
    print("Let's find vendors for your approved services:")

    # Track progress of selected services
    services_selected = []
    services_pending = [service["service"] for service in approved_services]

    # Display services for selection
    for i, service in enumerate(approved_services, 1):
        print(f"{i}. {service['service']} (Budget: ₹{service['budget']:,})")

    # Ask user which service to find vendors for
    while True:
        # Show progress tracker
        display_progress_tracker(services_selected, services_pending)
        
        search_vendors = input("\nWould you like to search for vendors for any of these services? (yes/no): ").lower()
        
        if search_vendors != "yes":
            break
            
        try:
            service_num = int(input("Enter the number of the service you'd like to find vendors for: "))
            if 1 <= service_num <= len(approved_services):
                selected_service = approved_services[service_num-1]
                
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
                    venue_crew = Crew(
                        agents=[venue_search_coordinator],
                        tasks=[venue_search_task],
                        process=Process.sequential,
                        verbose=True
                    )
                    service_output = venue_crew.kickoff(inputs=venue_inputs)
                    service_results = extract_text_from_crew_output(service_output)
                    
                    # Parse and display venue results
                    try:
                        venues = json.loads(service_results) if isinstance(service_results, str) else service_results
                        if isinstance(venues, dict) and "error" in venues:
                            print("No venues found matching your criteria.")
                            continue
                            
                        # Display venue results
                        print(format_venues_for_display(venues))
                        
                        # Ask if user wants to select a venue, with database update
                        if select_provider_with_db(event_id, venues, selected_service):
                            # Update progress tracker if a selection was made
                            services_selected.append(selected_service['service'])
                            if selected_service['service'] in services_pending:
                                services_pending.remove(selected_service['service'])
                    except:
                        print("Error processing venue search results.")
                else:
                    # Create inputs for vendor search
                    vendor_inputs = {
                        "service_type": selected_service['service'],
                        "location": details["location"],
                        "event_category": details["event_category"],
                        "service_budget": selected_service['budget']
                    }
                    
                    # Use vendor service coordinator for vendor searches
                    vendor_crew = Crew(
                        agents=[vendor_service_coordinator],
                        tasks=[vendor_search_task],
                        process=Process.sequential,
                        verbose=True
                    )
                    service_output = vendor_crew.kickoff(inputs=vendor_inputs)
                    service_results = extract_text_from_crew_output(service_output)
                    
                    # Parse and display vendor results
                    try:
                        vendors = json.loads(service_results) if isinstance(service_results, str) else service_results
                        if isinstance(vendors, dict) and "error" in vendors:
                            print("No vendors found matching your criteria.")
                            continue
                            
                        # Display vendor results
                        print(format_vendors_for_display(vendors))
                        
                        # Ask if user wants to select a vendor, with database update
                        if select_provider_with_db(event_id, vendors, selected_service):
                            # Update progress tracker if a selection was made
                            services_selected.append(selected_service['service'])
                            if selected_service['service'] in services_pending:
                                services_pending.remove(selected_service['service'])
                    except:
                        print("Error processing vendor search results.")
            else:
                print("Invalid service number. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

def create_invitation_with_db(event_id, event_details):
    """
    Create an invitation using predefined event details
    Not storing in database per requirement
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
        return create_invitation_with_db(event_id, event_details)
    
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
# ---------------------- Input Collection ----------------------
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

# ---------------------- Main Execution ----------------------
def main():
    try:
        print("Welcome to the Event Planner AI Assistant!")
        print("This tool will help you plan your event and find suitable venues and vendors.")
        
        # Get event details from user
        details = get_event_details()
        
        # Step 1: Generate initial services list
        print("\nAnalyzing requirements for your event...")
        requirements_crew = Crew(
            agents=[requirement_analyzer],
            tasks=[requirement_task],
            process=Process.sequential,
            verbose=True
        )
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
        budget_crew = Crew(
            agents=[budget_allocator],
            tasks=[budget_task],
            process=Process.sequential,
            verbose=True
        )
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
                break
            else:
                # Get feedback
                feedback = input("\nWhat would you like to change? (e.g., 'Add a live band', 'Remove photography', 'Increase catering budget'): ")
                
                # Create JSON string from the current service_budget_list
                current_services_json = json.dumps(service_budget_list)
                
                # Analyze feedback and revise services
                revision_inputs = {
                    "user_feedback": feedback,
                    "current_services": current_services_json
                }
                
                print("\nRevising services based on your feedback...")
                revision_crew = Crew(
                    agents=[service_reviser],
                    tasks=[service_revision_task],
                    process=Process.sequential,
                    verbose=True
                )
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
                except Exception as e:
                    print(f"Could not process revision results: {str(e)}")
                    print("Keeping current services.")
        
        # Store the final approved services
        approved_services = service_budget_list
        
        # Step 5 & 6: Use the enhanced service selection and search flow with show more feature and progress tracker
        service_selection_and_search(approved_services, details)
        
        # Final summary
        print("\n=== Event Planning Complete ===")
        print(f"Event: {details['event_name']}")
        print(f"Type: {details['event_category']}")
        print(f"Date: {details['event_date']}")
        print(f"Location: {details['location']}")
        print(f"Guests: {details['num_guests']}")
        print(format_services_for_display(approved_services))
        
        # Display final progress - which services have providers selected
        selected_services = []
        pending_services = []
        
        for service in approved_services:
            if 'selected_provider' in service:
                selected_services.append(service['service'])
            else:
                pending_services.append(service['service'])
        
        # Display final progress tracker
        display_progress_tracker(selected_services, pending_services)
        # Ask if user wants to create an invitation
        create_invite = input("\nWould you like to create an invitation for this event? (yes/no): ").lower()
        if create_invite == "yes":
            # Get venue details from selected venue service, if available
            venue_name = ""
            venue_address = ""
            
            # Try to find venue from selected services
            for service in approved_services:
                if service['service'].lower() == "venue" and 'selected_provider' in service:
                    venue_name = service['selected_provider'].get('name', '')
                    venue_address = service['selected_provider'].get('address', '')
                    venue_map = service['selected_provider'].get('map_url', '')
                    break
            
            # If no venue was selected, ask user for venue details
            if not venue_name:
                print("\nNo venue was selected earlier. Please provide venue details:")
                venue_name = input("Enter venue name: ")
                venue_address = input("Enter venue address: ")
                venue_map = ""
            else:
                # Confirm venue with user
                print(f"\nUsing selected venue: {venue_name}")
                print(f"Address: {venue_address}")
                if venue_map:
                    print(f"Map: {venue_map}")
                change_venue = input("Would you like to use a different venue? (yes/no): ").lower()
                if change_venue == "yes":
                    venue_name = input("Enter venue name: ")
                    venue_address = input("Enter venue address: ")
            
            # Create invitation with event details
            invitation_result = create_invitation({
                "event_name": details["event_name"],
                "event_type": details["event_category"],
                "event_date": details["event_date"],
                "num_guests": details["num_guests"],
                "venue_name": venue_name,
                "venue_address": venue_address,
                "location": details["location"]
            })
            
            if invitation_result:
                print(f"\nInvitation created successfully!")
                print(f"PDF saved to: {invitation_result['pdf_path']}")
                print("\nThank you for using the Event Planner AI Assistant!")
                
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback
        print(traceback.format_exc())
        print("\nPlease try again or contact support.")

if __name__ == "__main__":
    main()