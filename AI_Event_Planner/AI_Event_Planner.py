import reflex as rx
from enum import Enum
import asyncio
import os
import bcrypt
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from pymongo import MongoClient
from bson.binary import UuidRepresentation
from datetime import datetime, timedelta
import uuid
from database import UserManager, EventManager 
from agents import create_requirements_crew, create_budget_crew
from utils import parse_services_and_budget, extract_text_from_crew_output
import json
from agents import create_service_revision_crew
from utils import extract_text_from_crew_output
import json
from database import EventManager, store_service_provider, get_event_venue
from agents import (
    create_venue_search_crew, 
    create_vendor_search_crew,
)
from utils import extract_text_from_crew_output
# For newer versions of Reflex
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define the color scheme
COLORS = {
    "background": "#FFFDE7",
    "primary": "#000000",
    "secondary": "#555555",
    "accent": "#2D2D2D",
    "button_bg": "#000000",
    "button_hover": "#333333",
    "card_bg": "#FFFDE7",
    "card_border": "#000000",
}

# Define styles
# Define styles
styles = {
    "container": {
        "width": "100%",
        "background": COLORS["background"],
        "color": COLORS["primary"],
        "font_family": "'Inter', sans-serif",
        "scroll_behavior": "smooth",
        "padding_top": "5rem",  # Add this line for navbar spacing
    },
    "nav": {
    "display": "flex",
    "background": "#fce28f",
    "align_items": "center",
    "justify_content": "space-between",
    "padding": "1.5rem 2rem",
    "border_bottom": f"1px solid {COLORS['card_border']}",
    "position": "fixed",  # Keep this
    "top": "0",
    "left": "0",
    "right": "0",
    "z_index": "1000",
    "width": "100%",
    "transition": "top 0.3s ease",  # Add smooth transition
    },
    "nav_brand": {
        "font_weight": "bold",
        "font_size": ["1rem","1.8rem","2.5rem"],
        "color": COLORS["primary"],
    },
    "btn_primary_large": {
        "padding": ["0.5rem 0.75rem", "1rem 1.2rem", "1.3rem 2rem"],
        "border_radius": "0.35rem",
        "border": "2px solid transparent",  # Start with transparent border
        "background": COLORS["button_bg"],
        "color": "white",
        "cursor": "pointer",
        "font_weight": "600",  # Made font slightly bolder
        "font_size": ["0.9rem","1rem","1.1rem"],
        "transition": "all 0.3s ease",  # Slightly longer transition for smoother effect
        "_hover": {
            "background": "#fda8e9",  # Light cream color on hover
            "color": "#000000",  # Text changes to black
            "border": "2px solid #000000",  # Border appears on hover
            "transform": "translateY(-2px)",
            "box_shadow": "0 5px 15px rgba(0, 0, 0, 0.1)",
        },
    },
    # Add this new style for the login button
    "btn_login": {
        "padding": ["0.5rem 0.75rem", "1rem 1.2rem", "1.3rem 2rem"],
        "border_radius": "0.0rem",
        "border": f"2px solid {COLORS['button_bg']}",  # Black border by default
        "background": "#fce28f",  # Same as navbar background
        "color": "#000000",  # Black text
        "cursor": "pointer",
        "font_weight": "600",
        "font_size": ["0.9rem","1rem","1.1rem"],
        "transition": "all 0.3s ease",
        "margin_right": "1rem",  # Add margin to separate the buttons
        "_hover": {
            "background": "#FFFDE7",  # Black background on hover
            "color": "black",  # White text on hover
            "transform": "translateY(-2px)",
            "box_shadow": "0 5px 15px rgba(0, 0, 0, 0.1)",
        },
    },
    "hero_section": {
        "display": "flex",
        "flex_direction": ["column", "column", "row"],
        "align_items": "center",
        "justify_content": "space-between",
        "padding": ["3rem 2rem", "4rem 2rem", "4rem 2rem"],
        "max_width": "1200px",
        "margin": "0 auto",
        "gap": ["2rem", "3rem", "4rem"],
    },
    "hero_content": {
        "flex": 1,
        "max_width": ["100%", "100%", "50%"],
    },
    "hero_image": {
        "flex": 1,
        "max_width": ["100%", "100%", "50%"],
        "display": "flex",
        "justify_content": "center",
        "transition": "all 0.3s ease",
        "_hover": {
            "transform": "scale(1.03)",
        },
    },
    "hero_title": {
        "font_size": ["3rem", "4rem", "5rem"],
        "font_weight": "800",
        "line_height": "1.1",
        "margin_bottom": "1.5rem",
        "color": COLORS["primary"],
    },
    "hero_subtitle": {
        "font_size": ["1rem", "1.15rem", "1.25rem"],
        "color": COLORS["secondary"],
        "line_height": "1.6",
        "margin_bottom": "2rem",
        "max_width": ["20rem", "22rem", "25rem"],
    },
    "features_section": {
        "padding": "5rem 2rem",
        "max_width": "1200px",
        "margin": "0 auto",
    },
    "features_title": {
        "font_size": "2.5rem",
        "font_weight": "700",
        "text_align": "center",
        "margin_bottom": "3rem",
        "color": COLORS["primary"],
    },
    "features_grid": {
        "display": "grid",
        "grid_template_columns": ["1fr", "repeat(2, 1fr)", "repeat(2, 1fr)"],  # Changed to 2 columns
        "gap": "2rem",
    },
    "feature_card": {
        "background": COLORS["card_bg"],
        "border": f"1px solid {COLORS['card_border']}",
        "border_radius": "0.75rem",
        "padding": "2rem",
        "transition": "all 0.3s ease",
        "_hover": {
            "transform": "translateY(-5px)",
            "box_shadow": "0 10px 25px rgba(0, 0, 0, 0.1)",
        },
    },
    "feature_icon": {
        "font_size": "2rem",
        "margin_bottom": "1rem",
        "display": "inline-block",
    },
    "feature_title": {
        "font_size": "1.25rem",
        "font_weight": "600",
        "margin_bottom": "0.75rem",
        "color": COLORS["primary"],
    },
    "feature_text": {
        "color": COLORS["secondary"],
        "line_height": "1.6",
    },
    "footer": {
        "background": "#fce28f",
        "padding": "2rem 2rem",
        "margin_top": "4rem",
    },
    "footer_content": {
        "max_width": "1200px",
        "margin": "0 auto",
        "display": "flex",
        "flex_direction": "column",
        "align_items": "center",  # Center align footer content
        "text_align": "center",  # Center align text
        "gap": "2rem",
    },
    "footer_link": {
        "display": "inline-block",  # Changed to inline-block for horizontal alignment
        "margin": "0 0.75rem",  # Changed from margin-bottom to horizontal margin
        "color": COLORS["secondary"],
        "transition": "color 0.3s ease",
        "_hover": {
            "color": COLORS["primary"],
        },
    },
    "footer_links_container": {
        "display": "flex",
        "flex_wrap": "wrap",
        "justify_content": "center",
        "gap": "0.5rem",
        "margin": "1.5rem 0",
    },
    "copyright": {
        "text_align": "center",
        "padding_top": "2rem",
        "color": COLORS["secondary"],
        "font_size": "0.9rem",
    },
    "modal_overlay": {
        "position": "fixed",
        "top": "0",
        "left": "0",
        "width": "100%",
        "height": "100%",
        "background": "rgba(0, 0, 0, 0.5)",
        "display": "flex",
        "align_items": "center",
        "justify_content": "center",
        "z_index": "2000",
    },
    "modal_content": {
        "background": "#FFFDE7",
        "padding": "2rem",
        "border_radius": "0.5rem",
        "max_width": "400px",
        "width": "90%",
        "position": "relative",
        "border": "2px solid #000000",
    },
    "modal_close": {
        "position": "absolute",
        "top": "1rem",
        "right": "1rem",
        "cursor": "pointer",
        "font_size": "1.5rem",
        "color": "#000000",
        "_hover": {
            "color": "#fda8e9",
        },
    },
    "form_input": {
        "width": "100%",
        "height": "45px",        # Fixed height for all inputs
        "padding": "0.75rem",
        "margin_bottom": "1rem",
        "border": "2px solid #000000",
        "border_radius": "0.25rem",
        "font_size": "1rem",
        "background": "#FFFFFF",
        "color": "#000000",
        "box_sizing": "border-box",
        },
    "form_label": {
        "display": "block",
        "margin_bottom": "0.5rem",
        "font_weight": "600",
        "color": "#000000",
    },
    "event_card": {
        "background": "#FFFDE7",
        "border": "2px solid #000000",
        "border_radius": "0.5rem",
        "padding": "1.5rem",
        "cursor": "pointer",
        "transition": "all 0.3s ease",
        "_hover": {
            "transform": "translateY(-5px)",
            "box_shadow": "0 5px 15px rgba(0, 0, 0, 0.1)",
            "background": "#fce28f",
        },
    },
    "add_event_button": {
        "width": "60px",
        "height": "60px",
        "border": "2px solid #000000",
        "border_radius": "50%",
        "background": "#fda8e9",
        "color": "black",
        "display": "flex",
        "align_items": "center",
        "justify_content": "center",
        "font_size": "2rem",
        "cursor": "pointer",
        "position": "fixed",
        "top": "100px",
        "right": "40px",   # Right side positioning
        "z_index": "1001",
        "transition": "all 0.3s ease",
        "_hover": {
            "transform": "scale(1.1)",
            "background": "#fda8e9",
            "box_shadow": "0 5px 15px rgba(0, 0, 0, 0.2)",
        },
    },
    "add_event_text": {
        "position": "fixed",
        "top": "170px",  # Above the + button
        "right": "20px",    # Right aligned
        "font_size": "0.9rem",
        "color": "#000555",
        "text_align": "center",
        "background": "#FFFDE7",
        "padding": "0.5rem 1rem",
        "border_radius": "0.5rem",
        "box_shadow": "0 2px 5px rgba(0, 0, 0, 0.1)",
        "z_index": "1001", # Higher than navbar
        "width": "100px",  # Fixed width for better alignment
    },
    "dashboard_container": {
        "width": "100%",
        "min_height": "100vh",
        "background": "#FFFDE7",
        "padding_top": "8rem",
    },
    "events_grid": {
        "display": "grid",
        "grid_template_columns": ["1fr", "repeat(2, 1fr)", "repeat(3, 1fr)"],
        "gap": "2rem",
        "max_width": "1200px",
        "margin": "2rem auto",
        "padding": "0 2rem",
    },
    "no_events_text": {
        "text_align": "center",
        "font_size": "1.5rem",
        "color": "#555555",
        "margin_top": "4rem",
    },
    "create_event_container": {
        "max_width": "1200px",
        "margin": "0 auto",
        "padding": "2rem",
        "background": "#FFFDE7",
        "padding_top": "8rem",
        "min_height": "100vh",  # Account for fixed navbar
    },
    "create_form_section": {
        "background": "rgba(252, 228, 143, 0.3)",
        "padding": "3rem",
        "border_radius": "1rem",
        "box_shadow": "0 4px 20px rgba(0, 0, 0, 0.08)",
        "margin_bottom": "2rem",
        "border": "2px solid #fce28f",
        "backdrop_filter": "blur(10px)",
    },
    "create_form_heading": {
        "color": "#000000",
        "font_size": "2.5rem",
        "font_weight": "700",
        "text_align": "center",
        "margin_bottom": "2rem",
        "font_family": "'Inter', sans-serif",
    },
    "create_form_label": {
        "display": "block",
        "margin_bottom": "0.5rem",
        "font_weight": "600",
        "color": "#fda8e9",
        "font_size": "1rem",
    },
    "create_form_input": {
    "width": "100%",
    "height": "45px",
    "padding": "0.75rem",
    "margin_bottom": "1rem",
    "border": "2px solid #000000",
    "border_radius": "0.25rem",
    "font_size": "1rem",
    "background": "#FFF5F9",
    "color": "#000000",  # Changed from #808080 to black for better readability
    "box_sizing": "border-box",
    "transition": "all 0.3s ease",
    "_focus": {
        "border_color": "#FF5252",
        "box_shadow": "0 0 0 3px rgba(255, 82, 82, 0.2)",
        },
    },
    "create_submit_button": {
        "width": "100%",
        "padding": "1rem",
        "background": "#000000",
        "color": "#FFF5F9",
        "border": "2px solid transparent",
        "border_radius": "0.35rem",
        "font_weight": "600",
        "font_size": "1.1rem",
        "cursor": "pointer",
        "transition": "all 0.3s ease",
        "_hover": {
            "background": "#fda8e9", #FF5252
            "color": "white",
            "border": "2px solid #000000",
            "transform": "translateY(-2px)",
            "box_shadow": "0 5px 15px rgba(0, 0, 0, 0.1)",
        },
    },
    "form_grid": {
        "display": "grid",
        "grid_template_columns": ["1fr", "repeat(2, 1fr)", "repeat(3, 1fr)"],
        "gap": "1.5rem",
        "margin_bottom": "2rem",
    },
    "service_card": {
        "background": "#FFFDE7",
        "padding": "1.5rem",
        "border_radius": "0.75rem",
        "border": "2px solid #000000",
        "text_align": "center",
        "transition": "all 0.3s ease",
        "cursor": "pointer",
        "_hover": {
            "transform": "translateY(-5px)",
            "box_shadow": "0 8px 25px rgba(0, 0, 0, 0.15)",
            "background": "#fce28f",
        },
    },
    "revision_section": {
        "background": "#FFFDE7",
        "padding": "2rem",
        "border_radius": "1rem",
        "margin_top": "2rem",
        "border": "2px solid #000000",
    },
    "example_chip": {
        "display": "inline-block",
        "padding": "0.5rem 1rem",
        "margin": "0.25rem",
        "background": "#000000",
        "color": "white",
        "border_radius": "2rem",
        "font_size": "0.9rem",
        "cursor": "pointer",
        "transition": "all 0.2s ease",
        "_hover": {
            "background": "#333333",
            "transform": "scale(1.05)",
        },
    },
    "success_popup": {
        "position": "fixed",
        "top": "50%",
        "left": "50%",
        "transform": "translate(-50%, -50%)",
        "background": "#FFFDE7",
        "padding": "3rem",
        "border_radius": "1rem",
        "box_shadow": "0 10px 30px rgba(0, 0, 0, 0.2)",
        "text_align": "center",
        "z_index": "2000",
        "border": "3px solid #000000",
        "max_width": "500px",
        "width": "90%",
    },
    "total_budget_box": {
        "background": "#000000",
        "color": "white",
        "padding": "1rem",
        "border_radius": "0.5rem",
        "text_align": "center",
        "margin": "1.5rem 0",
        "font_size": "1.2rem",
        "font_weight": "bold",
    },
    "loader_box": {
        "display": "flex",
        "flex_direction": "column",
        "align_items": "center",
        "justify_content": "center",
        "padding": "2rem",
        "gap": "1rem",
    },
    "event_header": {
        "padding": "2rem",
        "background": "rgba(252, 228, 143, 0.3)",
        "border_radius": "1rem",
        "box_shadow": "0 4px 20px rgba(0, 0, 0, 0.08)",
        "margin_bottom": "2rem",
        "border": "2px solid #fce28f",
    },
    "event_title": {
        "font_size": "2.5rem",
        "font_weight": "800",
        "color": "#fda8e9",
        "margin_bottom": "0.5rem",
    },
    "event_subtitle": {
        "font_size": "1.2rem",
        "color": "#000000",
        "margin_bottom": "1rem",
    },
    "event_stat": {
        "background": "#FFFFFF",
        "padding": "1rem",
        "border_radius": "0.5rem",
        "box_shadow": "0 2px 10px rgba(0, 0, 0, 0.05)",
        "text_align": "center",
        "border": "1px solid #E0E0E0",
    },
    "stat_label": {
        "font_size": "0.9rem",
        "color": "#555555",
        "margin_bottom": "0.25rem",
    },
    "stat_value": {
        "font_size": "1.5rem",
        "font_weight": "700",
        "color": "#000000",
    },
    "progress_bar_container": {
        "width": "100%",
        "height": "1rem",
        "background": "#E0E0E0",
        "border_radius": "0.5rem",
        "overflow": "hidden",
        "margin": "1rem 0",
    },
    "progress_bar_fill": {
        "height": "100%",
        "background": "#fda8e9",
        "border_radius": "0.5rem",
    },
    "service_pill": {
        "padding": "0.5rem 1rem",
        "border_radius": "2rem",
        "font_size": "0.9rem",
        "font_weight": "600",
        "cursor": "pointer",
        "transition": "all 0.2s ease",
        "border": "2px solid transparent",
        "text_align": "center",
        "_hover": {
            "transform": "translateY(-3px)",
            "box_shadow": "0 4px 12px rgba(0, 0, 0, 0.1)",
        },
    },
    "service_pill_completed": {
        "background": "#E6F6EE",
        "color": "#00A854",  # Darker green for better readability
        "border_color": "#00A854",
    },
    "service_pill_pending": {
        "background": "#FFF5F9",
        "color": "#333333",  # Much darker gray for better readability
        "border_color": "#DDDDDD",
    },
    "service_pill_selected": {
        "border_color": "#fda8e9",
        "box_shadow": "0 4px 12px rgba(253, 168, 233, 0.3)",
        "background": "#ffeaf8",  # Light pink background for selected pill
    },
    "service_detail_box": {
        "background": "rgba(255, 255, 255, 0.8)",
        "border_radius": "1rem",
        "padding": "2rem",
        "box_shadow": "0 4px 20px rgba(0, 0, 0, 0.08)",
        "border": "2px solid #fce28f",
        "margin_top": "2rem",
    },
    "provider_card": {
        "background": "#FFFFFF",
        "border_radius": "0.75rem",
        "padding": "1.5rem",
        "box_shadow": "0 4px 12px rgba(0, 0, 0, 0.08)",
        "border": "1px solid #E0E0E0",
        "transition": "all 0.3s ease",
        "cursor": "pointer",
        "_hover": {
            "transform": "translateY(-5px)",
            "box_shadow": "0 8px 24px rgba(0, 0, 0, 0.12)",
            "border_color": "#fda8e9",
        },
    },
    "provider_card_selected": {
        "border": "2px solid #fda8e9",
        "box_shadow": "0 8px 24px rgba(253, 168, 233, 0.2)",
    },
    "search_button": {
        "padding": "1rem 2rem",
        "background": "#000000",
        "color": "#FFFFFF",
        "border_radius": "0.5rem",
        "font_weight": "600",
        "cursor": "pointer",
        "transition": "all 0.3s ease",
        "_hover": {
            "background": "#fda8e9",
            "transform": "translateY(-3px)",
            "box_shadow": "0 4px 12px rgba(0, 0, 0, 0.1)",
        },
    },
    "edit_button": {
        "padding": "0.5rem 1rem",
        "background": "#EEEEEE",
        "color": "#555555",
        "border_radius": "0.5rem",
        "font_weight": "600",
        "font_size": "0.9rem",
        "cursor": "pointer",
        "transition": "all 0.2s ease",
        "_hover": {
            "background": "#DDDDDD",
        },
    },
    "invite_button": {
        "position": "fixed",
        "bottom": "2rem",
        "right": "2rem",
        "width": "60px",
        "height": "60px",
        "border_radius": "50%",
        "background": "#fda8e9",
        "color": "#FFFFFF",
        "display": "flex",
        "align_items": "center",
        "justify_content": "center",
        "font_size": "1.5rem",
        "box_shadow": "0 4px 12px rgba(253, 168, 233, 0.5)",
        "cursor": "pointer",
        "transition": "all 0.3s ease",
        "z_index": "100",
        "_hover": {
            "transform": "scale(1.1) rotate(15deg)",
            "box_shadow": "0 6px 18px rgba(253, 168, 233, 0.6)",
        },
    },
    "results_grid": {
        "display": "grid",
        "grid_template_columns": ["1fr", "repeat(2, 1fr)", "repeat(3, 1fr)"],
        "gap": "1.5rem",
        "margin_top": "1rem",
    },
    "no_results": {
        "padding": "2rem",
        "text_align": "center",
        "color": "#555555",
        "background": "#F8F8F8",
        "border_radius": "0.5rem",
        "margin_top": "1rem",
    },
    "vendor_name": {
        "font_size": "1.2rem",
        "font_weight": "700",
        "color": "#000000",
        "margin_bottom": "0.5rem",
    },
    "vendor_detail": {
        "font_size": "0.9rem",
        "color": "#555555",
        "margin_bottom": "0.25rem",
    },
    "vendor_price": {
        "font_size": "1.1rem",
        "font_weight": "700",
        "color": "#fda8e9",
        "margin_top": "0.5rem",
    },
    "select_vendor_button": {
        "width": "100%",
        "padding": "0.75rem",
        "background": "#000000",
        "color": "#FFFFFF",
        "border_radius": "0.35rem",
        "font_weight": "600",
        "text_align": "center",
        "cursor": "pointer",
        "margin_top": "1rem",
        "transition": "all 0.3s ease",
        "_hover": {
            "background": "#fda8e9",
        },
    },

}


# Create our state
# First, we need to add state variables to track scrolling
# Define data models for type safety
class ServiceProvider(rx.Base):
    name: str = "Unknown"  # Default value
    address: Optional[str] = None
    contact: Optional[str] = None
    price: Optional[str] = None
    source: Optional[str] = None  # Add field for source link
    map_link: Optional[str] = None  # Add field for map link

class EventService(rx.Base):
    service: str
    budget: int
    status: str = "pending"
    selected_provider: Optional[ServiceProvider] = None

class VendorResult(rx.Base):
    name: str
    address: Optional[str] = None
    contact: Optional[str] = None
    price: Optional[str] = None
    rating: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None  # Add field for source link
    map_link: Optional[str] = None  # Add field for map link

class State(rx.State):
    """The app state."""
    
    # Animation states (your existing code)
    active_button: str = ""
    active_card: int = -1
    scroll_position: int = 0
    previous_scroll_position: int = 0
    navbar_visible: bool = True  # Add this line
    
    # Auth data
    user_id: str = ""
    user_name: str = ""
    user_email: str = ""
    is_authenticated: bool = False
    
    # Auth form fields
    email: str = ""
    password: str = ""
    confirm_password: str = ""
    name: str = ""
    
    # Modal states
    show_login_modal: bool = False
    show_register_modal: bool = False
    
    # Loading and error states
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""
    
    # Events data
    user_events: list[dict] = []

    # Event creation form fields
    event_name: str = ""
    event_type: str = ""
    event_type_other: str = ""
    show_other_input: bool = False
    event_date: str = ""
    num_guests: str = ""
    budget: str = ""
    location: str = ""
    
    # Service management states
    generated_services: list[dict] = []
    revision_input: str = ""
    show_services: bool = False
    is_generating_services: bool = False
    show_success_popup: bool = False
    created_event_id: str = ""
    
    # Event type options
    event_types: list[str] = ["Birthday", "Wedding", "Corporate", "Anniversary", "Other"]
    
    # Animation states for services
    active_service_card: int = -1

    # Event detail specific state
    current_event_id: str = ""
    #current_event: dict = {}
    #selected_service: str = ""
    search_results: list = []
    #is_searching: bool = False
    service_details: dict = {}
    #is_loading_event: bool = True
    #error_message: str = ""
    success_message: str = ""
    
    provider_name: str = ""
    provider_contact: str = ""
    provider_address: str = ""
    provider_price: str = ""
    provider_rating: str = ""

    selected_event_id: str = ""
    current_event: dict = {}
    event_services: List[EventService] = []
    selected_service: str = ""
    is_loading_event: bool = True
    error_message: str = ""
    vendor_search_results: List[VendorResult] = []
    is_searching: bool = False

    # Provider selection tracking
    # Provider selection tracking
    is_venue_selected: bool = False
    is_service_provider_selected: bool = False
    selected_venue_name: str = ""
    selected_venue_address: str = ""
    selected_venue_contact: str = ""
    selected_venue_price: str = ""
    selected_provider_name: str = ""
    selected_provider_contact: str = ""
    selected_provider_price: str = ""

    venue_type: str = ""
    venue_type_other: str = ""
    show_venue_type_other: bool = False
    venue_types: list[str] = ["Banquet Hall", "Hotel", "Resort", "Restaurant", "Outdoor Garden", "Convention Center", "Farm House", "Beach Venue", "Other"]

    # Add these state variables to your State class
    # Invitation form fields
    invitation_venue_name: str = ""
    invitation_venue_address: str = ""
    invitation_time: str = ""
    host_name: str = ""
    rsvp_contact: str = ""
    style_preference: str = ""
    special_instructions: str = ""

    # Invitation generation state
    is_generating_invitation: bool = False
    is_regenerating_text: bool = False
    invitation_text: str = ""
    invitation_id: str = ""
    color_options: list[dict] = []  # Use typed lists for foreach
    font_options: list[dict] = []
    border_options: list[dict] = []
    background_options: list[dict] = []
    selected_color_scheme: str = "elegant"
    selected_font_style: str = "times"
    selected_border_style: str = "simple"
    selected_background: str = "cream"
    invitation_background: str = "#FFF8E1"  # Default background color (cream)

    # Highlight state for visual cues
    highlight_styling: bool = False
    highlight_email: bool = False

    # PDF generation state
    is_generating_pdf: bool = False
    pdf_path: str = ""
    download_url: str = ""

    # Email state
    email_subject: str = ""
    email_addresses: str = ""
    cc_addresses: str = ""
    sender_name: str = ""
    additional_message: str = ""
    is_sending_email: bool = False
    email_success: bool = False
    email_error: str = ""
    
    # Auth methods

    def toggle_login_modal(self):
        """Toggle login modal visibility"""
        self.show_login_modal = not self.show_login_modal
        self.error_message = ""
    
    def toggle_register_modal(self):
        """Toggle register modal visibility"""
        self.show_register_modal = not self.show_register_modal
        self.error_message = ""
    
    # In your State class, make sure these methods return redirects:

    async def handle_login(self, form_data: dict):
        """Handle user login"""
        self.is_loading = True
        self.error_message = ""
        
        try:
            user_manager = UserManager()
            result = user_manager.login_user(self.email, self.password)
            
            if result["success"]:
                self.user_id = result["uid"]
                self.user_name = result["name"]
                self.user_email = self.email
                self.is_authenticated = True
                self.show_login_modal = False
                
                # Clear form fields
                self.email = ""
                self.password = ""
                
                # Redirect to dashboard after successful login
                return rx.redirect("/dashboard")
            else:
                self.error_message = result["message"]
        except Exception as e:
            self.error_message = f"Login failed: {str(e)}"
        finally:
            self.is_loading = False

    async def handle_register(self, form_data: dict):
        """Handle user registration"""
        self.is_loading = True
        self.error_message = ""
        
        # Validate passwords match
        if self.password != self.confirm_password:
            self.error_message = "Passwords do not match"
            self.is_loading = False
            return
        
        # Validate password length
        if len(self.password) < 8:
            self.error_message = "Password must be at least 8 characters long"
            self.is_loading = False
            return
        
        # Validate password has at least one uppercase letter
        if not any(char.isupper() for char in self.password):
            self.error_message = "Password must contain at least one uppercase letter"
            self.is_loading = False
            return
        
        # Validate password has at least one lowercase letter
        if not any(char.islower() for char in self.password):
            self.error_message = "Password must contain at least one lowercase letter"
            self.is_loading = False
            return
        
        # Validate password has at least one number
        if not any(char.isdigit() for char in self.password):
            self.error_message = "Password must contain at least one number"
            self.is_loading = False
            return
        
        # Validate password has at least one special character
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?/"
        if not any(char in special_chars for char in self.password):
            self.error_message = "Password must contain at least one special character (!@#$%^&*...)"
            self.is_loading = False
            return
        
        try:
            user_manager = UserManager()
            result = user_manager.register_user(self.email, self.password, self.name)
            
            if result["success"]:
                self.user_id = result["uid"]
                self.user_name = self.name
                self.user_email = self.email
                self.is_authenticated = True
                self.show_register_modal = False
                
                # Clear form fields
                self.email = ""
                self.password = ""
                self.confirm_password = ""
                self.name = ""
                
                # Redirect to dashboard after successful registration
                return rx.redirect("/dashboard")
            else:
                self.error_message = result["message"]
        except Exception as e:
            self.error_message = f"Registration failed: {str(e)}"
        finally:
            self.is_loading = False
    
    # Event methods
    async def fetch_user_events(self):
        """Fetch all events for the logged-in user"""
        if not self.user_id:
            return
        
        self.is_loading = True
        try:
            event_manager = EventManager()
            events = event_manager.get_user_events(self.user_id)
            self.user_events = events
        except Exception as e:
            self.error_message = f"Failed to fetch events: {str(e)}"
        finally:
            self.is_loading = False
    
    def logout(self):
        """Logout user"""
        self.user_id = ""
        self.user_name = ""
        self.user_email = ""
        self.is_authenticated = False
        self.user_events = []
        return rx.redirect("/")
    
    def navigate_to_event_detail(self, event_id: str):
        """Navigate to event detail page with explicit event ID setting"""
        print(f"Navigating to event: {event_id}")
        self.selected_event_id = event_id  # Set the ID before navigation
        return rx.redirect(f"/event/{event_id}")
    
    def navigate_to_create_event(self):
        """Navigate to event creation page"""
        return rx.redirect("/event/create")
    
    # Animation methods from your original code
    def set_active_button(self, button_id: str):
        """Set the active button for hover effects."""
        self.active_button = button_id
    
    def clear_active_button(self):
        """Clear the active button state."""
        self.active_button = ""
    
    def set_active_card(self, card_id: int):
        """Set the active card for hover effects."""
        self.active_card = card_id
    
    def clear_active_card(self):
        """Clear the active card state."""
        self.active_card = -1

    def set_event_type(self, value: str):
        """Handle event type selection"""
        self.event_type = value
        self.show_other_input = (value == "Other")
        if value != "Other":
            self.event_type_other = ""
    
    async def create_event(self, form_data: dict):
        """Handle event creation form submission"""
        self.is_generating_services = True
        self.error_message = ""
        
        try:
            # Prepare event details
            event_category = self.event_type_other if self.event_type == "Other" else self.event_type
            event_details = {
                "event_name": self.event_name,
                "event_category": event_category.lower(),
                "event_date": self.event_date,
                "num_guests": int(self.num_guests),
                "budget": int(self.budget.replace(",", "").replace("₹", "")),
                "location": self.location
            }
            
            # Store event in database
            event_manager = EventManager()
            result = event_manager.create_event(self.user_id, event_details)
            
            if result["success"]:
                self.created_event_id = result["event_id"]
                
                # Generate services using backend agents
                await self.generate_services(event_details)
                
            else:
                self.error_message = result["message"]
                
        except Exception as e:
            self.error_message = f"Failed to create event: {str(e)}"
        finally:
            self.is_generating_services = False
    
    async def generate_services(self, event_details):
        """Generate services using backend agents"""
        try:
            # Import the necessary functions from your backend
            from agents import create_requirements_crew, create_budget_crew
            from utils import parse_services_and_budget, extract_text_from_crew_output
            import json
            
            # Step 1: Generate requirements using CrewAI
            requirements_crew = create_requirements_crew()
            requirement_output = requirements_crew.kickoff(inputs=event_details)
            requirement_results = extract_text_from_crew_output(requirement_output)
            
            # Process requirement results
            try:
                services_list = json.loads(requirement_results)
                if isinstance(services_list, list):
                    event_details["services"] = json.dumps(services_list)
                else:
                    event_details["services"] = json.dumps([str(services_list)])
            except:
                # Extract services from text if JSON parsing fails
                lines = requirement_results.split('\n')
                service_names = []
                for line in lines:
                    if line.strip().startswith('-') or line.strip().startswith('*'):
                        service = line.strip().lstrip('-*').strip()
                        if service:
                            service_names.append(service)
                
                if service_names:
                    event_details["services"] = json.dumps(service_names)
                else:
                    # Use defaults based on event type
                    event_type = event_details["event_category"].lower()
                    if "wedding" in event_type:
                        default_services = ["Venue", "Catering", "Decoration", "Photography", "Music", "Wedding Attire", "Invitations"]
                    elif "birthday" in event_type:
                        default_services = ["Venue", "Catering", "Decoration", "Photography", "Entertainment", "Cake"]
                    elif "corporate" in event_type:
                        default_services = ["Venue", "Catering", "AV Equipment", "Speakers", "Decoration", "Transportation"]
                    else:
                        default_services = ["Venue", "Catering", "Decoration", "Photography", "Entertainment"]
                    
                    event_details["services"] = json.dumps(default_services)
            
            # Step 2: Allocate budget using CrewAI
            budget_crew = create_budget_crew()
            budget_output = budget_crew.kickoff(inputs=event_details)
            budget_results = extract_text_from_crew_output(budget_output)
            
            # Parse the services and budget
            service_budget_list = parse_services_and_budget(requirement_results, budget_results)
            
            # Update state with generated services
            self.generated_services = service_budget_list
            self.show_services = True
            
            # Store services in database
            if self.created_event_id:
                from database import store_services
                store_services(self.created_event_id, service_budget_list)
            
        except Exception as e:
            self.error_message = f"Failed to generate services: {str(e)}"
            self.show_services = False

    def calculate_total_budget(self) -> str:
        """Calculate total budget from services"""
        total = sum(service.get("budget", 0) for service in self.generated_services)
        return f"₹{total:,}"
    
    async def revise_services(self):
        """Handle service revision request"""
        if not self.revision_input:
            return
            
        self.is_generating_services = True
        try:
            from agents import create_service_revision_crew
            from utils import extract_text_from_crew_output
            import json
            
            # Create JSON string from current services
            current_services_json = json.dumps(self.generated_services)
            
            # Create revision inputs
            revision_inputs = {
                "user_feedback": self.revision_input,
                "current_services": current_services_json
            }
            
            # Use service revision agent
            revision_crew = create_service_revision_crew()
            revision_output = revision_crew.kickoff(inputs=revision_inputs)
            revision_results = extract_text_from_crew_output(revision_output)
            
            # Update services based on revision
            if revision_results:
                try:
                    revision_data = json.loads(revision_results)
                
                # Handle different response formats
                    if isinstance(revision_data, list) and all(isinstance(item, dict) for item in revision_data):
                        if all("service" in item and "budget" in item for item in revision_data):
                            self.generated_services = revision_data
                    elif isinstance(revision_data, dict):
                        # Process additions, removals, and modifications
                        current_services = self.generated_services.copy()
                        
                        # Process removals
                        if "services_to_remove" in revision_data:
                            for service in revision_data.get("services_to_remove", []):
                                current_services = [item for item in current_services if item["service"].lower() != service.lower()]
                        
                        # Process additions
                        if "services_to_add" in revision_data:
                            total_budget = sum(item["budget"] for item in current_services)
                            remaining_budget = int(self.budget.replace(",", "").replace("₹", "")) - total_budget
                            for service in revision_data.get("services_to_add", []):
                                default_budget = min(remaining_budget * 0.2, remaining_budget)  # 20% of remaining or all remaining
                                current_services.append({"service": service, "budget": int(default_budget)})
                        
                        # Process modifications
                        if "services_to_modify" in revision_data:
                            for mod in revision_data.get("services_to_modify", []):
                                if "service" in mod:
                                    for item in current_services:
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
                        
                        self.generated_services = current_services
                    
                    # Clear revision input
                    self.revision_input = ""
                
                    # Update database
                    if self.created_event_id:
                        from database import store_services
                        store_services(self.created_event_id, self.generated_services)
                
                except json.JSONDecodeError:
                    # If JSON parsing fails, try to process as text
                    self.error_message = "Revision processed but couldn't parse response. Please try again."
                except Exception as e:
                    self.error_message = f"Error processing revision: {str(e)}"
            else:
                self.error_message = "No response from revision agent. Please try again."
                
        except Exception as e:
            self.error_message = f"Failed to revise services: {str(e)}"
        finally:
            self.is_generating_services = False
        
    def approve_services(self):
        """Approve services and show success popup"""
        # Services are already stored in database during generation/revision
        self.show_success_popup = True
    
    def continue_to_event_detail(self):
        """Navigate to event detail page"""
        self.show_success_popup = False
        # Clear form fields for next time
        self.event_name = ""
        self.event_type = ""
        self.event_type_other = ""
        self.event_date = ""
        self.num_guests = ""
        self.budget = ""
        self.location = ""
        self.generated_services = []
        self.show_services = False
        
        return rx.redirect(f"/event/{self.created_event_id}")
    
    # In the State class, add this:
    @rx.var
    def total_budget_display(self) -> str:
        """Computed var for total budget display"""
        if not self.generated_services:
            return "Total Budget Allocated: ₹0"
        total = sum(service.get("budget", 0) for service in self.generated_services)
        return f"Total Budget Allocated: ₹{total:,}"

    @rx.var
    def event_progress(self) -> float:
        """Calculate percentage of completed services"""
        if not self.current_event or "services" not in self.current_event:
            return 0
            
        services = self.current_event.get("services", [])
        if not services:
            return 0
            
        completed = sum(1 for service in services if service.get("status") == "completed")
        return (completed / len(services)) * 100
    
    @rx.var
    def days_until_event(self) -> int:
        """Calculate days until event"""
        if not self.current_event or "event_date" not in self.current_event:
            return 0
        try:
            event_date = datetime.strptime(self.current_event["event_date"], "%Y-%m-%d")
            today = datetime.now()
            return (event_date - today).days
        except:
            return 0
    @rx.var
    def overall_progress(self) -> str:
        """Calculate overall progress"""
        if not self.event_services:
            return "0/0 services completed"
        completed = sum(1 for s in self.event_services if s.status == "completed")
        total = len(self.event_services)
        return f"{completed}/{total} services completed"
    
    @rx.var
    def budget_used(self) -> float:
        """Calculate percentage of budget used"""
        if not self.current_event:
            return 0
            
        total_budget = self.current_event.get("budget", 0)
        if total_budget == 0:
            return 0
            
        # Calculate used budget based on services with selected providers
        used_budget = 0
        for service in self.current_event.get("services", []):
            if service.get("status") == "completed" and service.get("selected_provider"):
                used_budget += service.get("budget", 0)
                
        return (used_budget / total_budget) * 100
    
    @rx.var
    def completed_services(self) -> list:
        """Get list of completed services"""
        if not self.current_event:
            return []
            
        return [
            service for service in self.current_event.get("services", [])
            if service.get("status") == "completed"
        ]
    
    @rx.var
    def pending_services(self) -> list:
        """Get list of pending services"""
        if not self.current_event:
            return []
            
        return [
            service for service in self.current_event.get("services", [])
            if service.get("status") != "completed"
        ]
    # Add this method to the State class to calculate the progress percentage
    @rx.var
    def progress_percentage(self) -> str:
        """Calculate progress percentage for progress bar width"""
        if not self.event_services:
            return "0%"
        completed = sum(1 for s in self.event_services if s.status == "completed")
        total = len(self.event_services)
        if total == 0:
            return "0%"
        percentage = (completed / total) * 100
        return f"{percentage}%"
    
    @rx.var
    def has_selected_provider(self) -> bool:
        """Check if a provider is selected for the current service"""
        return (
            self.service_details is not None and 
            "status" in self.service_details and 
            self.service_details.get("status") == "completed"
        )
    @rx.var
    def event_category_display(self) -> str:
        """Get event category with proper capitalization"""
        if not self.current_event or "event_category" not in self.current_event:
            return ""
        
        category = self.current_event.get("event_category", "")
        # Manually capitalize first letter of each word
        if category:
            words = category.split()
            capitalized_words = [word[0].upper() + word[1:] if word else "" for word in words]
            return " ".join(capitalized_words)
        return ""
    # Update this method in your State class
    async def load_event_details(self):
        """Load event details from URL path or selected_event_id with improved synchronization"""
        self.is_loading_event = True
        self.error_message = ""
        
        try:
            # STEP 1: Extract event ID from URL path
            current_path = self.router.page.path
            print(f"Current page path: {current_path}")
            
            # Use regex to extract the event_id from the URL path
            import re
            path_match = re.search(r'/event/([^/]+)', current_path)
            url_event_id = None
            
            if path_match:
                url_event_id = path_match.group(1)
                if url_event_id == "[event_id]":  # This is a template, not a real ID
                    url_event_id = None
                else:
                    print(f"Event ID from URL: {url_event_id}")
            
            # STEP 2: Determine which event ID to use
            event_id = url_event_id or self.selected_event_id
            print(f"Using event_id for loading: {event_id}")
            
            if not event_id:
                self.error_message = "No valid event ID found"
                print("No valid event ID could be determined")
                return
                
            # STEP 3: Load the event data
            event_manager = EventManager()
            event = event_manager.get_event_by_id(event_id)
            
            if event:
                print(f"Successfully loaded event: {event['event_name']} (ID: {event['event_id']})")
                
                # STEP 4: Check if this is a different event than currently loaded
                if self.current_event and self.current_event.get('event_id') != event['event_id']:
                    print(f"Switching from event {self.current_event.get('event_id')} to {event['event_id']}")
                
                # STEP 5: Update state variables
                self.current_event = event
                self.selected_event_id = event['event_id']  # Ensure selected_event_id matches loaded event
                self.set_default_host_name()
                # STEP 6: Fetch services for this event
                await self.fetch_event_services()
                
            else:
                self.error_message = f"Event with ID {event_id} not found"
                print(f"Failed to find event with ID: {event_id}")
                
                # Debug: List all events in the database
                all_events = list(event_manager.event_collection.find({}, {"event_id": 1, "event_name": 1}))
                event_ids = [e["event_id"] for e in all_events]
                print(f"Available event IDs: {event_ids}")
        except Exception as e:
            import traceback
            print(f"Error loading event: {str(e)}")
            print(traceback.format_exc())
            self.error_message = f"Error: {str(e)}"
        finally:
            self.is_loading_event = False

    def set_default_host_name(self):
        """Explicitly set the host name from user name"""
        # Check if host_name is empty
        if not self.host_name:
            # Try to set it from user_name
            if self.user_name:
                self.host_name = self.user_name
                print(f"Setting host name to user name: {self.user_name}")
            # If still empty, try name
            elif hasattr(self, 'name') and self.name:
                self.host_name = self.name
                print(f"Setting host name to name: {self.name}")

    async def fetch_event_services(self):
        """Fetch services for the current event"""
        if not self.current_event:
            return
            
        services_data = self.current_event.get("services", [])
        # Convert to typed objects
        typed_services = []
        for service in services_data:
            provider = None
            if service.get("selected_provider"):
                provider = ServiceProvider(
                    name=service["selected_provider"].get("name", ""),
                    address=service["selected_provider"].get("address"),
                    contact=service["selected_provider"].get("contact"),
                    price=service["selected_provider"].get("price")
                )
            
            typed_services.append(EventService(
                service=service.get("service", ""),
                budget=service.get("budget", 0),
                status=service.get("status", "pending"),
                selected_provider=provider
            ))
        
        self.event_services = typed_services
        
        # If no service is selected and we have services, select the first one
        if not self.selected_service and self.event_services:
            self.selected_service = self.event_services[0].service


    def select_service(self, service_name):
        """Select a service to view details with improved MongoDB integration"""
        # If already selected, deselect it
        if self.selected_service == service_name:
            self.selected_service = ""
            self.service_details = {}
            return
            
        # Set the selected service
        self.selected_service = service_name
        
        # Create a new event manager instance to fetch fresh data
        event_manager = EventManager()
        
        # Get the event ID from current state
        event_id = self.current_event.get("event_id", self.selected_event_id)
        
        if not event_id:
            self.error_message = "Missing event ID"
            return
        
        # Fetch the latest event data directly from MongoDB
        event = event_manager.get_event_by_id(event_id)
        
        if not event:
            self.error_message = f"Event with ID {event_id} not found"
            return
        
        # Find service details in the freshly fetched event data
        for service in event.get("services", []):
            if service["service"] == service_name:
                # Update service_details with the latest data from MongoDB
                self.service_details = service
                
                # Clear any previous search results when changing services
                self.search_results = []
                self.is_searching = False
                self.success_message = ""
                
                # Debug logging
                logger.info(f"Selected service: {service_name}")
                logger.info(f"Service details: {self.service_details}")
                
                # Check if this service already has a provider selected
                if service.get("status") == "completed" and service.get("selected_provider"):
                    logger.info(f"Service {service_name} has a completed status and selected provider")
                else:
                    logger.info(f"Service {service_name} does not have a provider yet")
                    
                break
        else:
            # Service not found in the event data
            self.error_message = f"Service {service_name} not found in event data"
            self.service_details = {}
            
            # Clear previous search results when changing services
            self.search_results = []
            self.is_searching = False
            self.success_message = ""

    # async def search_vendors(self, service_type: str):
    #     """Trigger the appropriate agent to search for vendors/venues"""
    #     self.is_searching = True
    #     self.search_results = []
        
    #     try:
    #         # Get event details needed for search
    #         event_details = {
    #             "event_category": self.current_event["event_category"],
    #             "location": self.current_event["location"],
    #             "num_guests": self.current_event["num_guests"]
    #         }
            
    #         # Get service budget
    #         service_budget = 0
    #         for service in self.current_event.get("services", []):
    #             if service["service"] == service_type:
    #                 service_budget = service["budget"]
    #                 break
            
    #         # Create appropriate inputs based on service type
    #         if service_type.lower() == "venue":
    #             # For venue search
    #             venue_type = "banquet hall"  # Default, could be from user input
    #             venue_inputs = {
    #                 "location": event_details["location"],
    #                 "event_category": event_details["event_category"],
    #                 "service_budget": service_budget,
    #                 "num_guests": event_details["num_guests"],
    #                 "venue_type": venue_type
    #             }
                
    #             # Import venue search crew
    #             from agents import create_venue_search_crew
    #             venue_crew = create_venue_search_crew()
                
    #             # Execute venue search using asyncio to avoid blocking
    #             service_output = await asyncio.to_thread(
    #                 venue_crew.kickoff, inputs=venue_inputs
    #             )
                
    #             # Process results
    #             from utils import extract_text_from_crew_output
    #             service_results = extract_text_from_crew_output(service_output)
                
    #             # Parse results into a consistent format
    #             if isinstance(service_results, str):
    #                 try:
    #                     venues = json.loads(service_results)
    #                     self.search_results = venues
    #                 except:
    #                     self.error_message = "Failed to parse venue search results"
    #                     self.search_results = []
    #             else:
    #                 self.search_results = service_results or []
                
    #         else:
    #             # For other vendor searches
    #             vendor_inputs = {
    #                 "service_type": service_type,
    #                 "location": event_details["location"],
    #                 "event_category": event_details["event_category"],
    #                 "service_budget": service_budget
    #             }
                
    #             # Import vendor search crew
    #             from agents import create_vendor_search_crew
    #             vendor_crew = create_vendor_search_crew()
                
    #             # Execute vendor search
    #             service_output = await asyncio.to_thread(
    #                 vendor_crew.kickoff, inputs=vendor_inputs
    #             )
                
    #             # Process results
    #             from utils import extract_text_from_crew_output
    #             service_results = extract_text_from_crew_output(service_output)
                
    #             # Parse results
    #             if isinstance(service_results, str):
    #                 try:
    #                     vendors = json.loads(service_results)
    #                     self.search_results = vendors
    #                 except:
    #                     self.error_message = "Failed to parse vendor search results"
    #                     self.search_results = []
    #             else:
    #                 self.search_results = service_results or []
            
    #     except Exception as e:
    #         self.error_message = f"Error searching for vendors: {str(e)}"
    #         self.search_results = []
    #     finally:
    #         self.is_searching = False
    

    def select_service_for_vendor(self, service_name: str):
        """Select a service to view or modify"""
        self.selected_service = service_name
        # Clear any search results when changing service
        self.vendor_search_results = []
        self.is_searching = False
    
    async def start_vendor_search(self, service_type: str):
        """Start vendor search for the selected service"""
        if not service_type or not self.current_event:
            return
            
        self.is_searching = True
        self.vendor_search_results = []
        
        try:
            # Find the service to get its budget
            service_budget = 0
            for service in self.event_services:
                if service.service == service_type:
                    service_budget = service.budget
                    break
            
            # Create inputs for search agent
            search_inputs = {
                "service_type": service_type,
                "location": self.current_event["location"],
                "event_category": self.current_event["event_category"],
                "service_budget": service_budget
            }
            
            # Use appropriate crew based on service type
            if service_type.lower() == "venue":
                # For venue search
                venue_type = "banquet hall"  # Default value - could ask user
                venue_inputs = {
                    **search_inputs,
                    "venue_type": venue_type,
                    "num_guests": self.current_event["num_guests"]
                }
                
                from agents import create_venue_search_crew
                venue_crew = create_venue_search_crew()
                
                # Execute search using asyncio
                import asyncio
                from utils import extract_text_from_crew_output
                
                service_output = await asyncio.to_thread(
                    venue_crew.kickoff, inputs=venue_inputs
                )
                
                service_results = extract_text_from_crew_output(service_output)
            else:
                # For other vendor searches
                from agents import create_vendor_search_crew
                vendor_crew = create_vendor_search_crew()
                
                # Execute search using asyncio
                import asyncio
                from utils import extract_text_from_crew_output
                
                service_output = await asyncio.to_thread(
                    vendor_crew.kickoff, inputs=search_inputs
                )
                
                service_results = extract_text_from_crew_output(service_output)
            
            # Process results into typed objects
            if isinstance(service_results, str):
                import json
                try:
                    results_data = json.loads(service_results)
                except:
                    self.error_message = "Failed to parse search results"
                    return
            else:
                results_data = service_results
            
            # Convert to typed objects
            typed_results = []
            for vendor in results_data:
                if isinstance(vendor, dict):
                    typed_results.append(VendorResult(
                        name=vendor.get("name", vendor.get("Name", "Unknown")),
                        address=vendor.get("address", vendor.get("Address")),
                        contact=vendor.get("contact", vendor.get("Contact")),
                        price=vendor.get("price", vendor.get("Price")),
                        rating=vendor.get("rating", vendor.get("Rating")),
                        description=vendor.get("description", vendor.get("Description"))
                    ))
            
            self.vendor_search_results = typed_results
            
        except Exception as e:
            self.error_message = f"Error searching for vendors: {str(e)}"
        finally:
            self.is_searching = False

    async def select_vendor(self, vendor: dict):
        """Select a vendor for the current service with improved UI handling"""
        if not self.selected_service or not self.current_event:
            self.error_message = "Please select a service first"
            return
                
        try:
            # Get vendor name with fallback
            vendor_name = vendor.get('name', vendor.get('Name', 'Unknown Provider'))
            logger.info(f"Selecting {vendor_name} for service {self.selected_service}")
            logger.info(f"Current event ID: {self.current_event.get('event_id')}")
            
            # Convert vendor object to dict format for database
            vendor_dict = {
                "name": vendor_name,
                "address": vendor.get('address', vendor.get('Address', "")),
                "contact": vendor.get('contact', vendor.get('Contact', "")),
                "price": vendor.get('price', vendor.get('Price', "")),
                "rating": vendor.get('rating', vendor.get('Rating', "")),
                # Save links for display - ensure they're preserved
                "source": vendor.get('source', vendor.get('source_link', vendor.get('website', ""))),
                "map_link": vendor.get('map_link', vendor.get('map_url', "")),
            }
            
            # Get the event ID
            event_id = self.current_event.get("event_id", self.selected_event_id)
            if not event_id:
                self.error_message = "Missing event ID"
                return
            
            # Create a new event manager instance
            event_manager = EventManager()
            
            # Update the service with selected vendor
            result = event_manager.update_service_provider(
                event_id,
                self.selected_service,
                vendor_dict
            )
            
            if result["success"]:
                # Update local state
                for service in self.event_services:
                    if service.service == self.selected_service:
                        # Create a provider object
                        provider = ServiceProvider(
                            name=vendor_name,
                            address=vendor_dict["address"],
                            contact=vendor_dict["contact"],
                            price=vendor_dict["price"],
                            source=vendor_dict["source"],
                            map_link=vendor_dict["map_link"],
                            rating=vendor_dict["rating"],
                        )
                        service.selected_provider = provider
                        service.status = "completed"
                        break
                        
                # Update service_details directly to show the provider immediately
                self.service_details = {
                    **self.service_details,
                    "status": "completed",
                    "selected_provider": vendor_dict
                }
                
                # Clear search results and set success message
                self.search_results = []
                self.success_message = f"{vendor_name} has been selected as your {self.selected_service} provider!"
                
                # Update UI status indicators
                if self.selected_service == "Venue":
                    self.is_venue_selected = True
                    self.selected_venue_name = vendor_name
                    self.selected_venue_address = vendor_dict["address"]
                    self.selected_venue_contact = vendor_dict["contact"]
                    self.selected_venue_price = vendor_dict["price"]
                else:
                    self.is_service_provider_selected = True
                    self.selected_provider_name = vendor_name
                    self.selected_provider_contact = vendor_dict["contact"]
                    self.selected_provider_price = vendor_dict["price"]
            else:
                self.error_message = result["message"]
                    
        except Exception as e:
            import traceback
            logger.error(f"Error selecting vendor: {str(e)}")
            logger.error(traceback.format_exc())
            self.error_message = f"Error: {str(e)}"

    def clear_selected_vendor(self):
        """Clear the selected vendor for the current service and reset UI to search state"""
        if not self.selected_service or not self.current_event:
            return
                
        try:
            print(f"Clearing provider for service {self.selected_service}")
            
            # Get the event ID
            event_id = self.current_event.get("event_id", self.selected_event_id)
            if not event_id:
                self.error_message = "Missing event ID"
                return
            
            # Create a new event manager instance
            event_manager = EventManager()
            
            # Update the service with null provider
            result = event_manager.update_service_provider(
                event_id,
                self.selected_service,
                None  # Set to None to clear the provider
            )
            
            if result["success"]:
                print("Provider cleared successfully")
                # Update local state
                for service in self.event_services:
                    if service.service == self.selected_service:
                        service.selected_provider = None
                        service.status = "pending"
                        break
                        
                # Clear UI status indicators
                if self.selected_service == "Venue":
                    self.is_venue_selected = False
                    self.selected_venue_name = ""
                    self.selected_venue_address = ""
                    self.selected_venue_contact = ""
                    self.selected_venue_price = ""
                else:
                    self.is_service_provider_selected = False
                    self.selected_provider_name = ""
                    self.selected_provider_contact = ""
                    self.selected_provider_price = ""
                    
                # Reset service details to show search button
                # Update service_details directly to trigger UI refresh
                self.service_details = {
                    **self.service_details,
                    "status": "pending",  # Change status to pending
                    "selected_provider": None  # Clear provider
                }
                    
                # Clear search results to start fresh
                self.search_results = []
                self.is_searching = False
                    
                # Show success message
                self.success_message = f"Provider for {self.selected_service} has been removed"
            else:
                self.error_message = result["message"]
                    
        except Exception as e:
            import traceback
            print(f"Error clearing vendor: {str(e)}")
            print(traceback.format_exc())
            self.error_message = f"Error: {str(e)}"
    
    def navigate_to_invitation(self):
        """Navigate to invitation creation page with correct URL structure"""
        # Get event ID from current_event
        if self.current_event and "event_id" in self.current_event:
            event_id = self.current_event["event_id"]
            return rx.redirect(f"/event/{event_id}/invitation")
    
        # If we couldn't get a valid event ID, show an error message
        self.error_message = "Could not determine event ID for invitation"
        return None
    
    # Add this method to the State class to fix the title issue
    @rx.var
    def event_category_display(self) -> str:
        """Get event category with proper capitalization"""
        if not self.current_event or "event_category" not in self.current_event:
            return ""
        
        category = self.current_event.get("event_category", "")
        # Manually capitalize first letter of each word instead of using .title()
        if category:
            words = category.split()
            capitalized_words = [word[0].upper() + word[1:] if word else "" for word in words]
            return " ".join(capitalized_words)
        return ""
        
     
    @rx.var
    def services_list(self) -> list:
        """Get list of services for foreach"""
        if not self.current_event or "services" not in self.current_event:
            return []
        return self.current_event.get("services", [])
    def load_event_from_route(self):
        """Load event details from the route's event_id parameter"""
        self.is_loading_event = True
        self.error_message = ""
        
        try:
            print("Starting load_event_from_route...")
            # Get the current path
            path = self.router.page.path
            print(f"URL path: {path}")
            
            # Extract event_id from path like "/event/{event_id}"
            parts = path.split("/")
            print(f"Path parts: {parts}")
            
            if len(parts) >= 3 and parts[1] == "event":
                event_id = parts[2]
                print(f"Found event_id: {event_id}")
                self.current_event_id = event_id
                
                # Create a simple stub event for testing
                stub_event = {
                    "event_id": event_id,
                    "event_name": "Test Event",
                    "event_category": "birthday",
                    "event_date": "2025-06-01",
                    "location": "Test Location",
                    "num_guests": 50,
                    "budget": 50000,
                    "services": [
                        {
                            "service": "Venue",
                            "budget": 20000,
                            "status": "pending",
                            "selected_provider": None
                        },
                        {
                            "service": "Catering",
                            "budget": 15000,
                            "status": "pending",
                            "selected_provider": None
                        },
                        {
                            "service": "Decoration",
                            "budget": 10000,
                            "status": "pending",
                            "selected_provider": None
                        }
                    ]
                }
                
                # Update state with event details
                self.current_event = stub_event
                print("Set stub event data")
                
                # Initialize service data
                typed_services = []
                for service in stub_event.get("services", []):
                    provider = None
                    if service.get("selected_provider"):
                        provider = ServiceProvider(
                            name=service["selected_provider"].get("name", ""),
                            address=service["selected_provider"].get("address"),
                            contact=service["selected_provider"].get("contact"),
                            price=service["selected_provider"].get("price")
                        )
                    
                    typed_services.append(EventService(
                        service=service.get("service", ""),
                        budget=service.get("budget", 0),
                        status=service.get("status", "pending"),
                        selected_provider=provider
                    ))
                
                self.event_services = typed_services
                print(f"Created {len(typed_services)} typed service objects")
                
                # Select first service by default
                if self.event_services:
                    first_service = self.event_services[0].service
                    self.selected_service = first_service
                    print(f"Selected first service: {first_service}")
                    
                    # Set service details for selected service
                    for service in stub_event.get("services", []):
                        if service["service"] == first_service:
                            self.service_details = service
                            print(f"Set service details for {first_service}")
                            break
                            
            else:
                self.error_message = f"Invalid route format. Expected: /event/{{event_id}}, got: {path}"
                print(f"Invalid route format: {path}")
                
        except Exception as e:
            import traceback
            print(f"Error in load_event_from_route: {str(e)}")
            print(traceback.format_exc())
            self.error_message = f"Error loading event: {str(e)}"
        finally:
            self.is_loading_event = False
            print("Finished load_event_from_route")
    
    # Add these computed properties to the State class
    # Add these computed properties to the State class
    @rx.var
    def current_provider_name(self) -> str:
        """Get the name of the selected provider for the current service"""
        try:
            if not self.service_details:
                return "Unknown"
            if "selected_provider" not in self.service_details:
                return "Unknown"
            provider = self.service_details.get("selected_provider")
            if provider is None:
                return "Unknown"
            if isinstance(provider, dict) and "name" in provider:
                return provider["name"]
            if isinstance(provider, dict) and "Name" in provider:
                return provider["Name"]
            return "Unknown"
        except:
            return "Unknown"

    @rx.var
    def current_provider_contact(self) -> str:
        """Get the contact of the selected provider for the current service"""
        try:
            if not self.service_details:
                return "N/A"
            if "selected_provider" not in self.service_details:
                return "N/A"
            provider = self.service_details.get("selected_provider")
            if provider is None:
                return "N/A"
            if isinstance(provider, dict) and "contact" in provider:
                return provider["contact"]
            if isinstance(provider, dict) and "Contact" in provider:
                return provider["Contact"]
            return "N/A"
        except:
            return "N/A"

    @rx.var
    def current_provider_price(self) -> str:
        """Get the price of the selected provider for the current service"""
        try:
            if not self.service_details:
                return "N/A"
            if "selected_provider" not in self.service_details:
                return "N/A"
            provider = self.service_details.get("selected_provider")
            if provider is None:
                return "N/A"
            if isinstance(provider, dict) and "price" in provider:
                return provider["price"]
            if isinstance(provider, dict) and "Price" in provider:
                return provider["Price"]
            return "N/A"
        except:
            return "N/A"

    @rx.var
    def current_provider_address(self) -> str:
        """Get the address of the selected provider for the current service"""
        try:
            if not self.service_details:
                return "N/A"
            if "selected_provider" not in self.service_details:
                return "N/A"
            provider = self.service_details.get("selected_provider")
            if provider is None:
                return "N/A"
            if isinstance(provider, dict) and "address" in provider:
                return provider["address"]
            if isinstance(provider, dict) and "Address" in provider:
                return provider["Address"]
            return "N/A"
        except:
            return "N/A"
        
    @rx.var
    def current_provider_rating(self) -> str:
        """Get the rating of the selected provider for the current service"""
        try:
            if not self.service_details:
                return "N/A"
            if "selected_provider" not in self.service_details:
                return "N/A"
            provider = self.service_details.get("selected_provider")
            if provider is None:
                return "N/A"
            # Check for rating field
            if isinstance(provider, dict) and "rating" in provider and provider["rating"] not in [None, ""]:
                return str(provider["rating"])
            if isinstance(provider, dict) and "Rating" in provider and provider["Rating"] not in [None, ""]:
                return str(provider["Rating"])
            return "N/A"
        except:
            return "N/A"

    @rx.var
    def current_provider_source(self) -> str:
        """Get the source link of the selected provider"""
        try:
            if not self.service_details:
                return "N/A"
            if "selected_provider" not in self.service_details:
                return "N/A"
            provider = self.service_details.get("selected_provider")
            if provider is None:
                return "N/A"
            if isinstance(provider, dict) and "source" in provider and provider["source"] not in [None, ""]:
                return provider["source"]
            return "N/A"
        except:
            return "N/A"

    @rx.var
    def current_provider_map_link(self) -> str:
        """Get the map link of the selected provider"""
        try:
            if not self.service_details:
                return "N/A"
            if "selected_provider" not in self.service_details:
                return "N/A"
            provider = self.service_details.get("selected_provider")
            if provider is None:
                return "N/A"
            if isinstance(provider, dict) and "map_link" in provider and provider["map_link"] not in [None, ""]:
                return provider["map_link"]
            return "N/A"
        except:
            return "N/A"
        
    def set_venue_type(self, value: str):
        """Handle venue type selection"""
        self.venue_type = value
        self.show_venue_type_other = (value == "Other")
        if value != "Other":
            self.venue_type_other = ""
    
    # Add this new method to your State class
    async def search_vendors_with_venue_type(self, service_type: str):
        """Trigger the appropriate agent to search for vendors/venues with venue type support"""
        # Check if it's a venue search and validate venue type is selected
        if service_type == "Venue" and not self.venue_type:
            self.error_message = "Please select a venue type first"
            return
            
        # For venue searches, ensure we have a venue type
        venue_type = None
        if service_type == "Venue":
            if self.venue_type == "Other" and self.venue_type_other:
                venue_type = self.venue_type_other
            elif self.venue_type == "Other" and not self.venue_type_other:
                self.error_message = "Please specify the venue type"
                return
            else:
                venue_type = self.venue_type
        
        # Now set loading state and begin search
        self.is_searching = True
        self.search_results = []
        
        try:
            # Get event details needed for search
            event_details = {
                "event_category": self.current_event["event_category"],
                "location": self.current_event["location"],
                "num_guests": self.current_event["num_guests"]
            }
            
            # Get service budget
            service_budget = 0
            for service in self.current_event.get("services", []):
                if service["service"] == service_type:
                    service_budget = service["budget"]
                    break
            
            # Create appropriate inputs based on service type
            if service_type.lower() == "venue":
                # For venue search with venue_type
                venue_inputs = {
                    "location": event_details["location"],
                    "event_category": event_details["event_category"],
                    "service_budget": service_budget,
                    "num_guests": event_details["num_guests"],
                    "venue_type": venue_type  # Use the selected/specified venue type
                }
                
                # Import venue search crew
                from agents import create_venue_search_crew
                venue_crew = create_venue_search_crew()
                
                # Execute venue search using asyncio to avoid blocking
                service_output = await asyncio.to_thread(
                    venue_crew.kickoff, inputs=venue_inputs
                )
                
                # Process results
                from utils import extract_text_from_crew_output
                service_results = extract_text_from_crew_output(service_output)
                
                # Parse results into a consistent format
                if isinstance(service_results, str):
                    try:
                        venues = json.loads(service_results)
                        self.search_results = venues
                    except:
                        self.error_message = "Failed to parse venue search results"
                        self.search_results = []
                else:
                    self.search_results = service_results or []
                
            else:
                # For other vendor searches (no venue type needed)
                vendor_inputs = {
                    "service_type": service_type,
                    "location": event_details["location"],
                    "event_category": event_details["event_category"],
                    "service_budget": service_budget
                }
                
                # Import vendor search crew
                from agents import create_vendor_search_crew
                vendor_crew = create_vendor_search_crew()
                
                # Execute vendor search
                service_output = await asyncio.to_thread(
                    vendor_crew.kickoff, inputs=vendor_inputs
                )
                
                # Process results
                from utils import extract_text_from_crew_output
                service_results = extract_text_from_crew_output(service_output)
                
                # Parse results
                if isinstance(service_results, str):
                    try:
                        vendors = json.loads(service_results)
                        self.search_results = vendors
                    except:
                        self.error_message = "Failed to parse vendor search results"
                        self.search_results = []
                else:
                    self.search_results = service_results or []
            
        except Exception as e:
            self.error_message = f"Error searching for vendors: {str(e)}"
            self.search_results = []
        finally:
            self.is_searching = False

    # Add these methods to your State class

    def navigate_back_to_event(self):
        """Navigate back to the event detail page safely"""
        # Find event ID from current_event dictionary
        if self.current_event and isinstance(self.current_event, dict) and "event_id" in self.current_event:
            event_id = self.current_event["event_id"]
            return rx.redirect(f"/event/{event_id}")
        
        # If we can't determine the ID, go to dashboard as fallback
        return rx.redirect("/dashboard")

    # Method for safer redirect
    def get_event_url(self) -> str:
        """Safely get the event URL"""
        if self.current_event and isinstance(self.current_event, dict) and "event_id" in self.current_event:
            return f"/event/{self.current_event['event_id']}"
        return "/dashboard"

    # Form field setters
    def set_invitation_venue_name(self, value: str):
        """Set invitation venue name"""
        self.invitation_venue_name = value

    def set_invitation_venue_address(self, value: str):
        """Set invitation venue address"""
        self.invitation_venue_address = value

    def set_invitation_time(self, value: str):
        """Set invitation time"""
        self.invitation_time = value

    def set_host_name(self, value: str):
        """Set host name"""
        self.host_name = value

    def set_rsvp_contact(self, value: str):
        """Set RSVP contact"""
        self.rsvp_contact = value

    def set_style_preference(self, value: str):
        """Set style preference"""
        self.style_preference = value

    def set_special_instructions(self, value: str):
        """Set special instructions"""
        self.special_instructions = value

    # Visual highlight setters
    def set_highlight_styling(self):
        """Highlight the styling section"""
        self.highlight_styling = True
        return None

    # Invitation styling setters
    def set_selected_color_scheme(self, value: str):
        """Set selected color scheme"""
        self.selected_color_scheme = value

    def set_selected_font_style(self, value: str):
        """Set selected font style"""
        self.selected_font_style = value

    def set_selected_border_style(self, value: str):
        """Set selected border style"""
        self.selected_border_style = value

    def set_selected_background(self, value: str):
        """Set selected background color"""
        self.selected_background = value
        
        # Also update the invitation preview background color
        background_options = self._get_background_options()
        for bg in background_options:
            if bg["id"] == value:
                self.invitation_background = bg["color"]
                break

    # Style options getters - with proper return types
    def _get_color_options(self) -> list[dict]:
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

    def _get_font_options(self) -> list[dict]:
        """Returns available font style options"""
        return [
            {"id": "times", "name": "Times (Classic)", "heading": "Times-Bold", "body": "Times-Roman"},
            {"id": "helvetica", "name": "Helvetica (Modern)", "heading": "Helvetica-Bold", "body": "Helvetica"},
            {"id": "courier", "name": "Courier (Typewriter)", "heading": "Courier-Bold", "body": "Courier"},
            {"id": "zapfdingbats", "name": "Zapf Dingbats (Decorative)", "heading": "ZapfDingbats", "body": "Helvetica"}
        ]

    def _get_border_options(self) -> list[dict]:
        """Returns available border style options"""
        return [
            {"id": "none", "name": "None (No Border)"},
            {"id": "simple", "name": "Simple Line"},
            {"id": "double", "name": "Double Line"},
            {"id": "dashed", "name": "Dashed"},
            {"id": "ornate", "name": "Ornate Corners"},
            {"id": "floral", "name": "Floral Border"}
        ]
        
    def _get_background_options(self) -> list[dict]:
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

    # Initialize invitation form
    def initialize_invitation_form(self):
        """Initialize invitation form with data from event"""
        # Reset all invitation state fields
        self.invitation_text = ""
        self.invitation_id = ""
        self.pdf_path = ""
        self.download_url = ""
        self.email_success = False
        self.email_error = ""
        self.highlight_styling = False
        self.highlight_email = False
        
        # Find venue in services if available
        venue_name = ""
        venue_address = ""
        if self.event_services:
            for service in self.event_services:
                if service.service.lower() == "venue" and service.selected_provider:
                    venue_name = service.selected_provider.name
                    venue_address = service.selected_provider.address
                    break
        
        # Set venue info
        self.invitation_venue_name = venue_name or ""
        self.invitation_venue_address = venue_address or (self.current_event.get("location", "") if self.current_event else "")
        
        # Set host name to user name as default
        self.host_name = self.user_name or ""
        
        # Initialize style options
        self.color_options = self._get_color_options()
        self.font_options = self._get_font_options()
        self.border_options = self._get_border_options()
        self.background_options = self._get_background_options()

    # Email form field setters
    def set_email_subject(self, value: str):
        """Set email subject"""
        self.email_subject = value

    def set_email_addresses(self, value: str):
        """Set email addresses"""
        self.email_addresses = value

    def set_cc_addresses(self, value: str):
        """Set CC addresses"""
        self.cc_addresses = value

    def set_sender_name(self, value: str):
        """Set sender name"""
        self.sender_name = value

    def set_additional_message(self, value: str):
        """Set additional message"""
        self.additional_message = value

    # Core invitation functionality - NO JavaScript scrolling
    async def generate_invitation(self):
        """Generate invitation text using backend tools with error handling"""
        # Validate required fields
        if not self.invitation_venue_name:
            self.error_message = "Please enter a venue name"
            return
            
        if not self.invitation_time:
            self.error_message = "Please enter an event time"
            return
            
        if not self.host_name:
            self.error_message = "Please enter a host name"
            return
        
        self.is_generating_invitation = True
        self.error_message = ""
        
        try:
            # Prepare event details for invitation
            event_details = {
                "event_name": self.current_event.get("event_name", ""),
                "event_type": self.current_event.get("event_category", ""),
                "event_date": self.current_event.get("event_date", ""),
                "event_time": self.invitation_time,
                "venue_name": self.invitation_venue_name,
                "venue_address": self.invitation_venue_address,
                "host_name": self.host_name,
                "guest_count": self.current_event.get("num_guests", 30),
                "special_instructions": self.special_instructions,
                "rsvp_contact": self.rsvp_contact,
                "style_preference": self.style_preference
            }
            
            # Create invitation tool instance
            from tools import InvitationCreatorTool
            invitation_tool = InvitationCreatorTool()
            
            # Try to generate with API
            try:
                result = invitation_tool._run(**event_details)
            except Exception as api_error:
                # Fallback to template if API fails
                print(f"API error: {str(api_error)}. Using fallback template.")
                import time
                
                # Create a simple template invitation
                event_type = event_details["event_type"].lower()
                invitation_text = f"""You're Invited!

    Join us to celebrate {event_details["event_name"]}

    Date: {event_details["event_date"]}
    Time: {event_details["event_time"]}
    Location: {event_details["venue_name"]}
    {event_details["venue_address"]}

    {event_details.get("special_instructions", "")}

    RSVP: {event_details.get("rsvp_contact", "Please RSVP")}

    Hosted by {event_details["host_name"]}
    """
                # Create a minimal result to maintain expected structure
                result = {
                    "invitation_text": invitation_text,
                    "invitation_id": f"local_{int(time.time())}",  # Generate a local ID
                    "color_options": self._get_color_options(),
                    "font_options": self._get_font_options(),
                    "border_options": self._get_border_options(),
                    "background_options": self._get_background_options()
                }
            
            if "error" in result:
                self.error_message = result["error"]
                return
            
            # Update state with invitation data
            self.invitation_text = result["invitation_text"]
            self.invitation_id = result["invitation_id"]
            self.set_default_host_name()
            # Don't use JavaScript scrolling - return None
            return None
                
        except Exception as e:
            import traceback
            print(f"Error generating invitation: {str(e)}")
            print(traceback.format_exc())
            self.error_message = f"Error: {str(e)}"
        finally:
            self.is_generating_invitation = False

    async def regenerate_invitation_text(self):
        """Regenerate invitation text with slightly modified style preference"""
        self.is_regenerating_text = True
        
        # Store original style preference
        original_style = self.style_preference
        
        # Slightly modify style preference to get a new variation
        self.style_preference = f"{original_style} - please create a new variation"
        
        try:
            # Call generate_invitation but don't use its return value
            await self.generate_invitation()
        finally:
            # Restore original style preference
            self.style_preference = original_style
            self.is_regenerating_text = False

    async def generate_invitation_pdf(self):
        """Generate PDF invitation with selected styles"""
        if not self.invitation_id or not self.invitation_text:
            self.error_message = "Please generate invitation text first"
            return
        
        self.is_generating_pdf = True
        self.error_message = ""
        
        try:
            # Create styler tool instance
            from tools import InvitationStylerTool
            styler_tool = InvitationStylerTool()
            
            # Generate the styled PDF
            result = styler_tool._run(
                invitation_id=self.invitation_id,
                color_scheme=self.selected_color_scheme,
                font_style=self.selected_font_style,
                border_style=self.selected_border_style,
                background_color=self.selected_background
            )
            
            if "error" in result:
                self.error_message = result["error"]
                return
            
            # Update state with PDF data
            self.pdf_path = result["pdf_path"]
            self.download_url = result["download_url"]
            
            # Set default email subject if empty
            if not self.email_subject:
                self.email_subject = f"Invitation to {self.current_event.get('event_name', 'our event')}"
            
            # Set default sender name if empty
            if not self.sender_name:
                self.sender_name = self.host_name or self.user_name
            
            # Set highlight flag for email section
            self.highlight_email = True
            
            # Don't use JavaScript scrolling - return None
            return None
                
        except Exception as e:
            import traceback
            print(f"Error generating PDF: {str(e)}")
            print(traceback.format_exc())
            self.error_message = f"Error: {str(e)}"
        finally:
            self.is_generating_pdf = False

    async def send_invitation_emails(self):
        """Send invitation emails to specified addresses"""
        if not self.invitation_id or not self.pdf_path:
            self.email_error = "Please generate a PDF invitation first"
            return
            
        if not self.email_addresses:
            self.email_error = "Please enter at least one email address"
            return
        
        self.is_sending_email = True
        self.email_error = ""
        self.email_success = False
        
        try:
            # Parse email addresses
            email_list = [email.strip() for email in self.email_addresses.split(",") if email.strip()]
            
            if not email_list:
                self.email_error = "Please enter valid email addresses"
                return
            
            # Parse CC addresses if provided
            cc_list = None
            if self.cc_addresses:
                cc_list = [email.strip() for email in self.cc_addresses.split(",") if email.strip()]
            
            # Create email tool instance
            from tools import EmailInvitationTool
            email_tool = EmailInvitationTool()
            
            # Send the emails
            result = email_tool._run(
                invitation_id=self.invitation_id,
                email_subject=self.email_subject,
                email_addresses=email_list,
                sender_name=self.sender_name,
                additional_message=self.additional_message,
                cc_addresses=cc_list
            )
            
            if "error" in result:
                self.email_error = result["error"]
                return
            
            # Set success flag
            self.email_success = True
            
            # Store invitation in MongoDB
            from datetime import datetime
            event_id = self.current_event.get("event_id", "")
            if event_id:
                from database import store_invitation
                invitation_data = {
                    "invitation_id": self.invitation_id,
                    "pdf_path": self.pdf_path,
                    "download_url": self.download_url,
                    "created_at": datetime.now().isoformat(),
                    "sent_to": email_list
                }
                store_invitation(event_id, invitation_data)
                
        except Exception as e:
            import traceback
            print(f"Error sending emails: {str(e)}")
            print(traceback.format_exc())
            self.email_error = f"Error: {str(e)}"
        finally:
            self.is_sending_email = False
# UI Components - Fixed modals
def login_modal():
    """Login modal component"""
    return rx.cond(
        State.show_login_modal,
        rx.center(
            rx.box(
                rx.box(
                    rx.text("×", 
                        style=styles["modal_close"],
                        on_click=State.toggle_login_modal,
                    ),
                    rx.heading("Login", size="3", margin_bottom="1.5rem"),
                    
                    rx.form(
                        rx.vstack(
                            rx.box(
                                rx.text("Email", style=styles["form_label"]),
                                rx.input(
                                    placeholder="Enter your email",
                                    type="email",
                                    value=State.email,
                                    on_change=State.set_email,
                                    style=styles["form_input"],
                                    required=True,
                                ),
                                width="100%",  # Ensure box takes full width
                            ),
                            rx.box(
                                rx.text("Password", style=styles["form_label"]),
                                rx.input(
                                    placeholder="Enter your password",
                                    type="password",
                                    value=State.password,
                                    on_change=State.set_password,
                                    style=styles["form_input"],
                                    required=True,
                                ),
                                width="100%",  # Ensure box takes full width
                            ),
                            rx.cond(
                                State.error_message != "",
                                rx.text(
                                    State.error_message,
                                    color="red",
                                    margin_bottom="1rem",
                                ),
                            ),
                            rx.button(
                                rx.cond(
                                    State.is_loading,
                                    "Logging in...",
                                    "Login"
                                ),
                                type="submit",
                                style={
                                    **styles["btn_primary_large"],
                                    "width": "100%",   # Make button full width
                                    "margin": "0",     # Remove any margin
                                },
                                disabled=State.is_loading,
                            ),
                            spacing="4",
                            width="100%",  # Make vstack full width
                        ),
                        on_submit=State.handle_login,
                        reset_on_submit=False,
                        width="100%",  # Make form full width
                    ),
                ),
                style=styles["modal_content"],
                on_click=rx.stop_propagation,
            ),
            style=styles["modal_overlay"],
            on_click=State.toggle_login_modal,
        ),
    )

def register_modal():
    """Register modal component"""
    return rx.cond(
        State.show_register_modal,
        rx.center(
            rx.box(
                rx.box(
                    rx.text("×", 
                        style=styles["modal_close"],
                        on_click=State.toggle_register_modal,
                    ),
                    rx.heading("Create Account", size="3", margin_bottom="1.5rem"),
                    
                    rx.form(
                        rx.vstack(
                            rx.box(
                                rx.text("Full Name", style=styles["form_label"]),
                                rx.input(
                                    placeholder="Enter your name",
                                    value=State.name,
                                    on_change=State.set_name,
                                    style=styles["form_input"],
                                    required=True,
                                ),
                                width="100%",
                            ),
                            rx.box(
                                rx.text("Email", style=styles["form_label"]),
                                rx.input(
                                    placeholder="Enter your email",
                                    type="email",
                                    value=State.email,
                                    on_change=State.set_email,
                                    style=styles["form_input"],
                                    required=True,
                                ),
                                width="100%",
                            ),
                            rx.box(
                                rx.text("Password", style=styles["form_label"]),
                                rx.input(
                                    placeholder="Enter your password",
                                    type="password",
                                    value=State.password,
                                    on_change=State.set_password,
                                    style=styles["form_input"],
                                    required=True,
                                ),
                                width="100%",
                            ),
                            rx.text(
                                "Password must contain: 8+ characters, uppercase, lowercase, number, special character",
                                font_size="0.8rem",
                                color="#666666",
                                margin_top="-0.75rem",
                                margin_bottom="1rem",
                                width="100%",
                            ),
                            rx.box(
                                rx.text("Confirm Password", style=styles["form_label"]),
                                rx.input(
                                    placeholder="Confirm your password",
                                    type="password",
                                    value=State.confirm_password,
                                    on_change=State.set_confirm_password,
                                    style=styles["form_input"],
                                    required=True,
                                ),
                                width="100%",
                            ),
                            rx.cond(
                                State.error_message != "",
                                rx.text(
                                    State.error_message,
                                    color="red",
                                    margin_bottom="1rem",
                                ),
                            ),
                            rx.button(
                                rx.cond(
                                    State.is_loading,
                                    "Creating account...",
                                    "Register"
                                ),
                                type="submit",
                                style={
                                    **styles["btn_primary_large"],
                                    "width": "100%",   # Make button full width
                                    "margin": "0",     # Remove any margin
                                },
                                disabled=State.is_loading,
                            ),
                            spacing="4",
                            width="100%",  # Make vstack full width
                        ),
                        on_submit=State.handle_register,
                        reset_on_submit=False,
                        width="100%",  # Make form full width
                    ),
                ),
                style=styles["modal_content"],
                on_click=rx.stop_propagation,
            ),
            style=styles["modal_overlay"],
            on_click=State.toggle_register_modal,
        ),
    )
# Updated navbar function (with State instead of AuthState)
# Fix the navbar with proper scrolling behavior
def navbar():
    """Navigation bar with brand and buttons from original code"""
    return rx.box(
        rx.flex(
            # Left side - Brand
            rx.box(
                rx.heading("EventWise", style=styles["nav_brand"]),
            ),
            # Right side - Buttons
            rx.hstack(
                rx.button(
                    "Login",
                    style=styles["btn_login"],
                    on_click=State.toggle_login_modal,
                ),
                rx.button(
                    "Get started for free",
                    style=styles["btn_primary_large"],
                    on_click=State.toggle_register_modal,
                ),
                spacing="4",
            ),
            justify_content="space-between",
            width="100%",
        ),
        style=styles["nav"],
        id="navbar",
    )

def hero_section():
    """Hero section with heading and image."""
    return rx.box(
        rx.flex(
            # Left content - Text and button
            rx.box(
                rx.heading(
                    rx.text("Plan Smarter.", as_="div", margin_bottom=["2rem", "3rem", "4rem"]),
                    rx.text("Enjoy Better.", as_="div"),
                    style=styles["hero_title"],
                ),
                rx.text(
                    "EventWise lets intelligent agents handle the chaos behind great events.",
                    style=styles["hero_subtitle"],
                    margin_top=["1.8rem", "2.3rem", "3.5rem"],
                ),
                rx.button(
                    "Get started for free", 
                    style=styles["btn_primary_large"],
                    on_click=State.toggle_register_modal,  # Changed this line
                    on_mouse_enter=lambda: State.set_active_button("hero_get_started"),
                    on_mouse_leave=State.clear_active_button,
                    transform=rx.cond(
                        State.active_button == "hero_get_started",
                        "translateY(-2px)",
                        "translateY(0)"
                    ),
                    box_shadow=rx.cond(
                        State.active_button == "hero_get_started",
                        "0 5px 15px rgba(0, 0, 0, 0.1)",
                        "none"
                    ),
                    background=rx.cond(
                        State.active_button == "hero_get_started",
                        COLORS["button_hover"],
                        COLORS["button_bg"]
                    ),
                ),
                style=styles["hero_content"],
            ),
            # Right content - Static container with no hover effects
            rx.box(
                rx.html(
                    """
                    <div style="width: 100%; height: 100%; overflow: hidden;">
                        <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
                        <lottie-player 
                            src="/animations/lottieani.json" 
                            background="transparent" 
                            speed="1" 
                            style="width: 100%; height: auto;" 
                            loop 
                            autoplay>
                        </lottie-player>
                    </div>
                    """
                ),
                # Modified style with NO hover effects or transitions
                flex=1,
                max_width=["100%", "100%", "50%"],
                display="flex",
                justify_content="center",
                # Explicitly REMOVE all hover or transition properties
                transition="none",
                _hover={},  # Empty hover state
            ),
            style=styles["hero_section"],
        ),
    )
def testimonial_section():
    """Testimonial section with large quotes."""
    return rx.box(
        rx.vstack(
            rx.box(
                rx.text(
                    "\u201C",  # Opening quote mark (Unicode)
                    font_size=["4rem", "5rem", "7rem"],
                    font_weight="700",
                    line_height="1",
                    color="#fce28f",
                    margin_bottom="-2rem",
                    font_family="'Playfair Display', serif",  # More elegant font
                ),
                rx.text(
                    "Let us do the running around. You just show up and shine.",
                    font_size=["1.5rem", "1.8rem", "2.2rem"],
                    font_weight="600",
                    color=COLORS["primary"],
                    margin_bottom="1rem",
                    text_align="center",
                    font_style="italic",
                    font_family="'Playfair Display', serif",  # Elegant, cursive-like font
                ),
                rx.text(
                    "Skip the stress. Keep the memories.",
                    font_size=["1.3rem", "1.5rem", "1.8rem"],
                    font_weight="500",
                    color=COLORS["secondary"],
                    margin_bottom="1rem",
                    text_align="center",
                    font_style="italic",
                    font_family="'Playfair Display', serif",
                ),
                rx.text(
                    "From venue to vibe — we've got it covered.",
                    font_size=["1.3rem", "1.5rem", "1.8rem"],
                    font_weight="500",
                    color=COLORS["secondary"],
                    text_align="center",
                    font_style="italic",
                    font_family="'Playfair Display', serif",
                ),
                rx.box(
                    rx.text(
                        "\u201D",  # Closing quote mark (Unicode)
                        font_size=["4rem", "5rem", "7rem"],
                        font_weight="700",
                        line_height="1",
                        color="#fce28f",
                        font_family="'Playfair Display', serif",
                    ),
                    display="flex",
                    justify_content="flex-end",  # Right align the closing quote
                    width="100%",
                    margin_top="-2rem",
                ),
                max_width="800px",
                margin="0 auto",
                padding="2rem",
            ),
            width="100%",
            padding=["3rem 1rem", "4rem 2rem", "5rem 2rem"],
            background="#FFFDE7",
            border_top=f"1px solid {COLORS['card_border']}",
            border_bottom=f"1px solid {COLORS['card_border']}",
        ),
    )
def gif_showcase_section():
    """GIF showcase section with a catchy heading."""
    return rx.box(
        rx.vstack(
            rx.heading(
                "See the Magic Unfold",
                font_size=["2rem", "2.5rem", "3rem"],
                font_weight="700",
                text_align="center",
                margin_bottom=["1rem", "1.2rem", "1.5rem"],
                color=COLORS["primary"],
            ),
            # rx.text(
            #     "From chaos to celebration in one seamless experience",
            #     font_size=["1rem", "1.1rem", "1.25rem"],
            #     color=COLORS["secondary"],
            #     text_align="center",
            #     margin_bottom=["2rem", "2.5rem", "3rem"],
            # ),
            # GIF container - simpler than video as GIFs auto-play and loop by default
            rx.box(
                rx.image(
                    src="/gifs/home.gif",
                    width="100%",
                    max_width="744px",
                    height="auto",
                    border_radius="8px",
                    box_shadow="0 10px 25px rgba(0, 0, 0, 0.1)",
                    transition="all 0.3s ease",
                    _hover={
                        "transform": "scale(1.02)",
                        "box_shadow": "0 15px 30px rgba(0, 0, 0, 0.15)",
                    },
                ),
                width="100%",
                display="flex",
                justify_content="center",
                align_items="center",
            ),
            spacing="6",
            width="100%",
            max_width="1200px",
            margin="0 auto",
            padding=["3rem 1rem", "4rem 2rem", "5rem 2rem"],
        ),
    )
def feature_card(icon_emoji: str, title: str, description: str, card_id: int):
    """Feature card component with hover animations."""
    return rx.box(
        rx.vstack(
            rx.text(
                icon_emoji,
                style=styles["feature_icon"],
            ),
            rx.text(
                title,
                style=styles["feature_title"],
            ),
            rx.text(
                description,
                style=styles["feature_text"],
            ),
            align_items="flex-start",
            spacing="4",
        ),
        on_mouse_enter=lambda: State.set_active_card(card_id),
        on_mouse_leave=State.clear_active_card,
        transform=rx.cond(
            State.active_card == card_id,
            "translateY(-5px)",
            "translateY(0)"
        ),
        box_shadow=rx.cond(
            State.active_card == card_id,
            "0 10px 25px rgba(0, 0, 0, 0.1)",
            "none"
        ),
        border=f"1px solid {COLORS['card_border']}",
        border_radius="0.75rem",
        padding="2rem",
        background=COLORS["card_bg"],
        transition="all 0.3s ease",
    )


def features_section():
    """Features section with 2x3 grid of cards."""
    return rx.box(
        rx.vstack(
            rx.heading(
                "Powerful features for seamless event planning",
                style=styles["features_title"],
            ),
            # Using flex containers for rows with two features each
            # Row 1
            rx.flex(
                rx.box(
                    rx.vstack(
                        rx.text(
                            "📍",
                            style=styles["feature_icon"],
                        ),
                        rx.text(
                            "Smart Venue & Service Finder",
                            style=styles["feature_title"],
                        ),
                        rx.text(
                            "AI-powered scraping finds the best venues and vendors that match your budget and event type.",
                            style=styles["feature_text"],
                        ),
                        align_items="flex-start",
                        spacing="4",
                    ),
                    on_mouse_enter=lambda: State.set_active_card(0),
                    on_mouse_leave=State.clear_active_card,
                    transform=rx.cond(
                        State.active_card == 0,
                        "translateY(-5px)",
                        "translateY(0)"
                    ),
                    box_shadow=rx.cond(
                        State.active_card == 0,
                        "0 10px 25px rgba(0, 0, 0, 0.1)",
                        "none"
                    ),
                    border=f"1px solid {COLORS['card_border']}",
                    border_radius="0.75rem",
                    padding="2rem",
                    background=COLORS["card_bg"],
                    transition="all 0.3s ease",
                    width="48%",
                ),
                rx.box(
                    rx.vstack(
                        rx.text(
                            "💲",
                            style=styles["feature_icon"],
                        ),
                        rx.text(
                            "Intelligent Budget Splitting",
                            style=styles["feature_title"],
                        ),
                        rx.text(
                            "Automatically distributes your budget across services like catering, décor, and more — optimized by guest count and preferences.",
                            style=styles["feature_text"],
                        ),
                        align_items="flex-start",
                        spacing="4",
                    ),
                    on_mouse_enter=lambda: State.set_active_card(1),
                    on_mouse_leave=State.clear_active_card,
                    transform=rx.cond(
                        State.active_card == 1,
                        "translateY(-5px)",
                        "translateY(0)"
                    ),
                    box_shadow=rx.cond(
                        State.active_card == 1,
                        "0 10px 25px rgba(0, 0, 0, 0.1)",
                        "none"
                    ),
                    border=f"1px solid {COLORS['card_border']}",
                    border_radius="0.75rem",
                    padding="2rem",
                    background=COLORS["card_bg"],
                    transition="all 0.3s ease",
                    width="48%",
                ),
                width="100%",
                justify_content="space-between",
                margin_bottom="2rem",
            ),
            # Row 2
            rx.flex(
                rx.box(
                    rx.vstack(
                        rx.text(
                            "✓",
                            style=styles["feature_icon"],
                        ),
                        rx.text(
                            "Verified Discovery Engine",
                            style=styles["feature_title"],
                        ),
                        rx.text(
                            "Instantly shows verified venues and vendors with contact info, pricing, and real reviews — no fluff.",
                            style=styles["feature_text"],
                        ),
                        align_items="flex-start",
                        spacing="4",
                    ),
                    on_mouse_enter=lambda: State.set_active_card(2),
                    on_mouse_leave=State.clear_active_card,
                    transform=rx.cond(
                        State.active_card == 2,
                        "translateY(-5px)",
                        "translateY(0)"
                    ),
                    box_shadow=rx.cond(
                        State.active_card == 2,
                        "0 10px 25px rgba(0, 0, 0, 0.1)",
                        "none"
                    ),
                    border=f"1px solid {COLORS['card_border']}",
                    border_radius="0.75rem",
                    padding="2rem",
                    background=COLORS["card_bg"],
                    transition="all 0.3s ease",
                    width="48%",
                ),
                rx.box(
                    rx.vstack(
                        rx.text(
                            "💰",
                            style=styles["feature_icon"],
                        ),
                        rx.text(
                            "Smart Budgeting System",
                            style=styles["feature_title"],
                        ),
                        rx.text(
                            "Adapts in real-time to changes in your needs, adjusting service recommendations and costs instantly.",
                            style=styles["feature_text"],
                        ),
                        align_items="flex-start",
                        spacing="4",
                    ),
                    on_mouse_enter=lambda: State.set_active_card(3),
                    on_mouse_leave=State.clear_active_card,
                    transform=rx.cond(
                        State.active_card == 3,
                        "translateY(-5px)",
                        "translateY(0)"
                    ),
                    box_shadow=rx.cond(
                        State.active_card == 3,
                        "0 10px 25px rgba(0, 0, 0, 0.1)",
                        "none"
                    ),
                    border=f"1px solid {COLORS['card_border']}",
                    border_radius="0.75rem",
                    padding="2rem",
                    background=COLORS["card_bg"],
                    transition="all 0.3s ease",
                    width="48%",
                ),
                width="100%",
                justify_content="space-between",
                margin_bottom="2rem",
            ),
            # Row 3
            rx.flex(
                rx.box(
                    rx.vstack(
                        rx.text(
                            "🤖",
                            style=styles["feature_icon"],
                        ),
                        rx.text(
                            "Agentic Booking Automation",
                            style=styles["feature_title"],
                        ),
                        rx.text(
                            "From search to confirmation — our agents handle it all. Book venues and services without lifting a finger.",
                            style=styles["feature_text"],
                        ),
                        align_items="flex-start",
                        spacing="4",
                    ),
                    on_mouse_enter=lambda: State.set_active_card(4),
                    on_mouse_leave=State.clear_active_card,
                    transform=rx.cond(
                        State.active_card == 4,
                        "translateY(-5px)",
                        "translateY(0)"
                    ),
                    box_shadow=rx.cond(
                        State.active_card == 4,
                        "0 10px 25px rgba(0, 0, 0, 0.1)",
                        "none"
                    ),
                    border=f"1px solid {COLORS['card_border']}",
                    border_radius="0.75rem",
                    padding="2rem",
                    background=COLORS["card_bg"],
                    transition="all 0.3s ease",
                    width="48%",
                ),
                rx.box(
                    rx.vstack(
                        rx.text(
                            "📚",
                            style=styles["feature_icon"],
                        ),
                        rx.text(
                            "Event History Database",
                            style=styles["feature_title"],
                        ),
                        rx.text(
                            "Every event you create is securely stored — revisit, duplicate, or share past plans with ease.",
                            style=styles["feature_text"],
                        ),
                        align_items="flex-start",
                        spacing="4",
                    ),
                    on_mouse_enter=lambda: State.set_active_card(5),
                    on_mouse_leave=State.clear_active_card,
                    transform=rx.cond(
                        State.active_card == 5,
                        "translateY(-5px)",
                        "translateY(0)"
                    ),
                    box_shadow=rx.cond(
                        State.active_card == 5,
                        "0 10px 25px rgba(0, 0, 0, 0.1)",
                        "none"
                    ),
                    border=f"1px solid {COLORS['card_border']}",
                    border_radius="0.75rem",
                    padding="2rem",
                    background=COLORS["card_bg"],
                    transition="all 0.3s ease",
                    width="48%",
                ),
                width="100%",
                justify_content="space-between",
            ),
            spacing="6",
        ),
        style=styles["features_section"],
    )


def footer_section():
    """Smaller, more compact footer section."""
    return rx.box(
        rx.hstack(
            rx.text(
                "EventWise",
                font_size="1.2rem",
                font_weight="600",
                color=COLORS["primary"],
            ),
            rx.text(
                "© 2025 EventWise, Inc. All rights reserved.",
                color=COLORS["secondary"],
                font_size="0.9rem",
            ),
            justify_content="space-between",
            width="100%",
            max_width="1200px",
            margin="0 auto",
            padding=["1rem", "1.25rem", "1.5rem"],
        ),
        background="#fce28f",
        padding="0.75rem 2rem",
        margin_top="3rem",  # Reduced from 4rem
    )


# Updated landing page
def landing_page():
    """The main landing page with modals and proper scroll handling"""
    return rx.box(
        navbar(),  # No special transform styling needed
        hero_section(),
        gif_showcase_section(),
        testimonial_section(),
        features_section(),
        footer_section(),
        # Add modals
        login_modal(),
        register_modal(),
        # Add JavaScript for scroll behavior
        rx.html("""
            <script>
                let prevScrollpos = window.pageYOffset;
                let navbar = null;
                
                window.addEventListener('DOMContentLoaded', (event) => {
                    navbar = document.querySelector('nav') || document.querySelector('[id="navbar"]') || document.querySelector('header > div:first-child');
                });
                
                window.onscroll = function() {
                    if (!navbar) {
                        navbar = document.querySelector('nav') || document.querySelector('[id="navbar"]') || document.querySelector('header > div:first-child');
                    }
                    
                    if (navbar) {
                        let currentScrollPos = window.pageYOffset;
                        
                        if (prevScrollpos > currentScrollPos || currentScrollPos <= 0) {
                            // Scrolling UP or at the top
                            navbar.style.transform = "translateY(0)";
                            navbar.style.transition = "transform 0.3s ease";
                        } else {
                            // Scrolling DOWN
                            navbar.style.transform = "translateY(-100%)";
                            navbar.style.transition = "transform 0.3s ease";
                        }
                        
                        prevScrollpos = currentScrollPos;
                    }
                };
            </script>
        """),
        style=styles["container"],
    )
def dashboard():
    """Dashboard page"""
    return dashboard_content()

def navbar_dashboard():
    """Navigation bar for dashboard"""
    return rx.box(
        rx.hstack(
            # Left side
            rx.heading("EventWise", style=styles["nav_brand"]),
            
            # Spacer to push logout to right
            rx.spacer(),
            
            # Right side  
            rx.button(
                "Logout",
                style=styles["btn_login"],
                on_click=State.logout,
            ),
            width="100%",
        ),
        style=styles["nav"],
    )
def dashboard_content():
    """Actual dashboard content"""
    return rx.box(
        navbar_dashboard(),
        rx.box(
            # Add Event Button with text - simpler structure
            rx.box(
                "+",
                style=styles["add_event_button"],
                on_click=State.navigate_to_create_event,
            ),
            rx.text(
                "Create Event",
                style=styles["add_event_text"],
            ),
            
            # Main content
            rx.cond(
                State.is_loading,
                rx.center(
                    rx.text("Loading events...", font_size="1.5rem", color="#555555"),
                    padding="4rem",
                ),
                rx.cond(
                    State.user_events.length() > 0,
                    rx.box(
                        rx.heading(
                            f"Welcome back, {State.user_name}!",
                            size="6",
                            margin_bottom="2rem",
                            text_align="center",
                            color="#000000",
                            font_weight="700",
                        ),
                        rx.box(
                            rx.foreach(
                                State.user_events,
                                event_card,
                            ),
                            style=styles["events_grid"],
                        ),
                    ),
                    rx.center(
                        rx.text(
                            "No events created yet",
                            style=styles["no_events_text"],
                        ),
                    ),
                ),
            ),
            style=styles["dashboard_container"],
        ),
        on_mount=State.fetch_user_events,
    )

def event_card(event: dict):
    """Single event card component"""
    return rx.box(
        rx.vstack(
            rx.heading(
                event["event_name"],
                size="2",
                margin_bottom="0.5rem",
                font_weight="700",  # ADD THIS for bolder text
                font_family="'Inter', sans-serif",
                color="#fda8e9",  # ADD THIS to change font
            ),
            rx.text(
                f"Date: {event['event_date']}",
                color="#555555",
                margin_bottom="0.25rem",
            ),
            rx.text(
                f"Location: {event['location']}",
                color="#555555",
                margin_bottom="0.25rem",
            ),
            rx.text(
                f"Status: {event['current_status']}",
                color="#888888",
                font_size="0.9rem",
            ),
            align_items="flex-start",
            width="100%",
        ),
        style=styles["event_card"],
        on_click=lambda: State.navigate_to_event_detail(event["event_id"]),
    )

def create_event_navbar():
    """Navigation bar for create event page with scroll behavior"""
    return rx.box(
        rx.flex(
            rx.box(
                rx.heading("EventWise", style=styles["nav_brand"]),
            ),
            rx.button(
                "Back to Dashboard",
                style=styles["btn_login"],
                on_click=lambda: rx.redirect("/dashboard"),
            ),
            justify="between",
            align="center",
            width="100%",
        ),
        style=styles["nav"],
        id="navbar",
    )


def service_card(service: dict, index: int):
    """Enhanced service card with better colors"""
    return rx.box(
        rx.vstack(
            rx.text(service["service"], font_size="1.2rem", font_weight="bold", color="#000000"),
            rx.text(f"₹{service['budget']:,}", font_size="1.5rem", margin_top="0.5rem", color="#FF5252"),
            spacing="3",
        ),
        style={
            "background": "#FFFFFF",
            "padding": "1.5rem",
            "border_radius": "0.75rem",
            "border": "2px solid #fda8e9",
            "text_align": "center",
            "transition": "all 0.3s ease",
            "cursor": "pointer",
            "_hover": {
                "transform": "translateY(-5px)",
                "box_shadow": "0 8px 25px rgba(255, 82, 82, 0.2)",
                "background": "#FFF0F0",
            },
        },
        on_mouse_enter=lambda: State.set_active_service_card(index),
        on_mouse_leave=lambda: State.set_active_service_card(-1),
        transform=rx.cond(
            State.active_service_card == index,
            "translateY(-5px)",
            "translateY(0)"
        ),
    )

def success_popup_content():
    """Enhanced success popup with animations"""
    return rx.box(
        rx.html("""
            <style>
            @keyframes confetti {
                0% { transform: translateY(0) rotate(0); opacity: 1; }
                100% { transform: translateY(-100px) rotate(720deg); opacity: 0; }
            }
            .confetti {
                position: absolute;
                width: 10px;
                height: 10px;
                background: #ffd700;
                animation: confetti 3s ease-out;
            }
            </style>
            <div style="position: relative;">
                <div class="confetti" style="left: 10%; animation-delay: 0s;"></div>
                <div class="confetti" style="left: 30%; animation-delay: 0.2s; background: #ff6b6b;"></div>
                <div class="confetti" style="left: 50%; animation-delay: 0.4s; background: #4ecdc4;"></div>
                <div class="confetti" style="left: 70%; animation-delay: 0.6s; background: #45b7d1;"></div>
                <div class="confetti" style="left: 90%; animation-delay: 0.8s; background: #ff9999;"></div>
            </div>
        """),
        rx.vstack(
            rx.text("🎉", font_size="5rem"),
            rx.heading("Event Created Successfully!", size="3", margin="1rem 0"),
            rx.text(
                f"Your event '{State.event_name}' has been created and is ready for planning!",
                text_align="center",
                margin_bottom="2rem",
                font_size="1.1rem",
            ),
            rx.button(
                "Continue Planning →",
                on_click=State.continue_to_event_detail,
                style={
                    **styles["btn_primary_large"],
                    "width": "100%",
                    "font_size": "1.2rem",
                    "padding": "1rem 2rem",
                },
            ),
            spacing="4",
        ),
        style=styles["success_popup"],
    )

def create_event_page():
    """Enhanced event creation page with better UI"""
    return rx.box(  # New outer wrapper to control side colors
        rx.box(  # Original outer box
            create_event_navbar(),
            rx.box(
                # Error message display
                rx.cond(
                    State.error_message != "",
                    rx.box(
                        rx.text(State.error_message, color="#FF5252"),
                        padding="1rem",
                        background="rgba(255, 82, 82, 0.1)",
                        border="2px solid #fda8e9",
                        border_radius="0.5rem",
                        margin_bottom="1rem",
                    ),
                ),
                
                # Form Section
                rx.box(
                    rx.heading(
                        "Create Your Perfect Event ✨", 
                        style=styles["create_form_heading"]
                    ),
                    
                    rx.form(
                        rx.box(
                            # Event Name
                            rx.box(
                                rx.text("Event Name", style=styles["create_form_label"]),
                                rx.input(
                                    # placeholder="Give your event a magical name",
                                    value=State.event_name,
                                    on_change=State.set_event_name,
                                    style=styles["create_form_input"],
                                    required=True,
                                ),
                            ),
                            
                            # Event Type
                            rx.box(
                                rx.text("Event Type", style=styles["create_form_label"]),
                                rx.select(
                                    State.event_types,
                                    placeholder="What are we celebrating?",
                                    on_change=State.set_event_type,
                                    value=State.event_type,
                                    style={**styles["create_form_input"], "cursor": "pointer"},
                                    required=True,
                                ),
                                rx.cond(
                                    State.show_other_input,
                                    rx.input(
                                        placeholder="Tell us more about your event",
                                        value=State.event_type_other,
                                        on_change=State.set_event_type_other,
                                        style={**styles["create_form_input"], "margin_top": "0.5rem"},
                                        required=True,
                                    ),
                                ),
                            ),
                            
                            # Event Date
                            rx.box(
                                rx.text("Event Date", style=styles["create_form_label"]),
                                rx.input(
                                    type="date",
                                    value=State.event_date,
                                    on_change=State.set_event_date,
                                    style=styles["create_form_input"],
                                    required=True,
                                ),
                            ),
                            
                            # Number of Guests
                            rx.box(
                                rx.text("Number of Guests", style=styles["create_form_label"]),
                                rx.input(
                                    type="number",
                                    # placeholder="How many amazing people?",
                                    value=State.num_guests,
                                    on_change=State.set_num_guests,
                                    style=styles["create_form_input"],
                                    placeholder_color="#B8B370",
                                    required=True,
                                ),
                            ),
                            
                            # Budget
                            rx.box(
                                rx.text("Budget (₹)", style=styles["create_form_label"]),
                                rx.input(
                                    # placeholder="Your investment in memories",
                                    value=State.budget,
                                    on_change=State.set_budget,
                                    style=styles["create_form_input"],
                                    required=True,
                                ),
                            ),
                            
                            # Location
                            rx.box(
                                rx.text("Location (City)", style=styles["create_form_label"]),
                                rx.input(
                                    # placeholder="Where the magic happens",
                                    value=State.location,
                                    on_change=State.set_location,
                                    style=styles["create_form_input"],
                                    required=True,
                                ),
                            ),
                            
                            style=styles["form_grid"],
                        ),
                        
                    # Replace the submit button section (around line 1287-1301)
                    rx.button(
                        rx.cond(
                            State.is_generating_services,
                            "AI Agents Working Their Magic... ✨",
                            "Let's Plan This Event! 🚀"
                        ),
                        type="submit",
                        style=styles["create_submit_button"],
                        disabled=State.is_generating_services,
                    ),

                    on_submit=State.create_event,
                    ),
                    style=styles["create_form_section"],
                    ),

                    # Loading animation should appear after form submission
                    rx.cond(
                        State.is_generating_services,
                        rx.box(
                            loading_animation(),
                            margin_top="2rem",
                            width="100%",
                            display="flex",
                            justify_content="center",
                        ),
                    ),
                
                # Services Section
                rx.cond(
                    State.show_services,
                    rx.box(
                        rx.heading(
                            "Your Event Services", 
                            size="4", 
                            margin_bottom="1.5rem", 
                            text_align="center",
                            color="#000000"
                        ),
                        
                        # Total Budget Display
                        # Replace the total budget box with this:
                        rx.text(
                            State.total_budget_display,
                            font_size="1.4rem",
                            font_weight="800",
                            text_align="center", 
                            margin="1.5rem 0",
                            color="#000000",
                        ),
                        
                        # Service Cards Grid
                        rx.box(
                            rx.foreach(
                                State.generated_services,
                                lambda service, index: service_card(service, index)
                            ),
                            display="grid",
                            grid_template_columns=["1fr", "repeat(2, 1fr)", "repeat(4, 1fr)"],
                            gap="1rem",
                        ),
                        
                        # Revision Section
                        rx.box(
                            rx.text(
                                "Want to customize your services?", 
                                font_weight="bold", 
                                font_size="1.2rem", 
                                margin_bottom="1rem",
                                color="#000000"
                            ),
                            rx.text(
                                "Click on suggestions or type your own:", 
                                font_size="0.9rem", 
                                color="#666", 
                                margin_bottom="1rem"
                            ),
                            rx.box(
                                rx.text("Remove band", style=styles["example_chip"], on_click=lambda: State.set_revision_input("Remove band")),
                                rx.text("Increase catering budget", style=styles["example_chip"], on_click=lambda: State.set_revision_input("Increase catering budget")),
                                rx.text("Add DJ service", style=styles["example_chip"], on_click=lambda: State.set_revision_input("Add DJ service")),
                                rx.text("Reduce decoration cost", style=styles["example_chip"], on_click=lambda: State.set_revision_input("Reduce decoration cost")),
                                margin="1rem 0",
                                display="flex",
                                flex_wrap="wrap",
                                gap="0.5rem",
                            ),
                            rx.hstack(
                                rx.input(
                                    placeholder="Type your magical changes here...",
                                    value=State.revision_input,
                                    on_change=State.set_revision_input,
                                    style={**styles["create_form_input"], "margin_bottom": "0"},
                                ),
                                rx.button(
                                    rx.cond(
                                        State.is_generating_services,
                                        "Updating...",
                                        "Apply Changes"
                                    ),
                                    on_click=State.revise_services,
                                    style={
                                        **styles["btn_primary_large"],
                                        "background": "#fda8e9",
                                        "color": "white",
                                        "_hover": {
                                            "background": "#FF8A80",
                                        },
                                    },
                                    disabled=State.is_generating_services,
                                ),
                                spacing="4",
                                width="100%",
                            ),
                            rx.cond(
                                State.is_generating_services,
                                rx.box(
                                    loading_animation(),
                                    margin_top="1rem",
                                    width="100%",
                                    display="flex",
                                    justify_content="center",
                                ),
                            ),
                            style={
                                **styles["revision_section"],
                                "background": "rgba(252, 228, 143, 0.3)",
                                "border": "2px solid #fce28f",
                            },
                        ),
                        
                        # Approve Button
                        rx.button(
                            "I'm Happy with These Services ✅",
                            on_click=State.approve_services,
                            style={
                                **styles["btn_primary_large"],
                                "width": "100%",
                                "margin_top": "2rem",
                                "background": "#28a745",
                                "font_size": "1.1rem",
                                "padding": "1rem",
                            },
                        ),
                    ),
                ),
                
                # Success Popup
                rx.cond(
                    State.show_success_popup,
                    rx.box(
                        success_popup_content(),
                        position="fixed",
                        top="0",
                        left="0",
                        width="100%",
                        height="100%",
                        background="rgba(0, 0, 0, 0.5)",
                        z_index="1999",
                    ),
                ),
                
                style=styles["create_event_container"],
            ),
            # Add scroll behavior script
            rx.html("""
                <script>
                    let prevScrollpos = window.pageYOffset;
                    let navbar = null;
                    
                    window.addEventListener('DOMContentLoaded', (event) => {
                        navbar = document.querySelector('[id="navbar"]');
                    });
                    
                    window.onscroll = function() {
                        if (!navbar) {
                            navbar = document.querySelector('[id="navbar"]');
                        }
                        
                        if (navbar) {
                            let currentScrollPos = window.pageYOffset;
                            
                            if (prevScrollpos > currentScrollPos || currentScrollPos <= 0) {
                                navbar.style.transform = "translateY(0)";
                                navbar.style.transition = "transform 0.3s ease";
                            } else {
                                navbar.style.transform = "translateY(-100%)";
                                navbar.style.transition = "transform 0.3s ease";
                            }
                            
                            prevScrollpos = currentScrollPos;
                        }
                    };
                </script>
            """),
        ),
        style={
            "background": "#FFFDE7",  # Change this to whatever color you want on the sides
            "min_height": "100vh",
            "width": "100%",
        }
    )

# Add this code to enhance the scrolling properties for the navbar in the event detail page

def event_header():
    """Event header with details and stats - Updated with expanded width and more clickable pills"""
    return rx.box(
        rx.hstack(
            # Left side - Event info
            rx.vstack(
                # Event title and type
                rx.heading(State.current_event.get("event_name", ""), size="3", color="#000000"),
                rx.text(
                    f"Type: {State.event_category_display}",
                    font_size="1.2rem",
                    margin_bottom="1rem",
                    color="#000000",
                ),
                
                # Event details row
                rx.hstack(
                    rx.text(f"📆 {State.current_event.get('event_date', '')}", color="#000000"),
                    rx.text(f"📍 {State.current_event.get('location', '')}", color="#000000"),
                    rx.text(f"👥 {State.current_event.get('num_guests', '')} Guests", color="#000000"),
                    spacing="5",
                    wrap="wrap",
                    margin_bottom="1rem",
                ),
                
                # Progress bar
                rx.box(
                    rx.box(
                        width=State.progress_percentage,
                        height="100%",
                        background="#fda8e9",
                        border_radius="0.5rem",
                    ),
                    width="100%",
                    height="1rem",
                    background="#E0E0E0",
                    border_radius="0.5rem",
                    overflow="hidden",
                    margin="1rem 0",
                ),
                
                # Stats - Only showing days remaining and services completed
                rx.hstack(
                    # Days until event
                    rx.box(
                        rx.text("DAYS REMAINING", font_size="0.9rem", color="#444444", margin_bottom="0.25rem"),
                        rx.text(State.days_until_event, font_size="1.5rem", font_weight="700", color="#000000"),
                        background="#FFFFFF",
                        padding="1rem",
                        border_radius="0.5rem",
                        box_shadow="0 2px 10px rgba(0, 0, 0, 0.05)",
                        text_align="center",
                        border="1px solid #E0E0E0",
                    ),
                    
                    # Services completed
                    rx.box(
                        rx.text("SERVICES COMPLETED", font_size="0.9rem", color="#444444", margin_bottom="0.25rem"),
                        rx.text(
                            State.overall_progress,
                            font_size="1.5rem",
                            font_weight="700",
                            color="#000000",
                        ),
                        background="#FFFFFF",
                        padding="1rem",
                        border_radius="0.5rem",
                        box_shadow="0 2px 10px rgba(0, 0, 0, 0.05)",
                        text_align="center",
                        border="1px solid #E0E0E0",
                    ),
                    
                    spacing="4",
                    width="100%",
                ),
                
                align_items="stretch",
                width="70%",
            ),
            
            # Right side - Service pills with improved clickable appearance
            rx.box(
                rx.text(
                    "Select a service:",
                    font_weight="700",
                    margin_bottom="1rem",
                    color="#000000",
                    font_size="1.1rem",
                ),
                # Use a vertical flex container for the pills
                rx.vstack(
                    rx.foreach(
                        State.event_services.to(list[EventService]),
                        lambda service, index: rx.box(
                            rx.hstack(
                                # Service name
                                rx.text(service.service, color="#000000", font_weight="600"),
                                
                                # Status indicator
                                rx.cond(
                                    (service.status == "completed"),
                                    rx.text("✅", font_size="1rem"),
                                    rx.text("⏳", font_size="1rem"),
                                ),
                                spacing="2",
                                width="100%",
                            ),
                            # More obvious button-like styling
                            background=rx.cond(
                                (service.status == "completed"),
                                "#E6F6EE",
                                rx.cond(
                                    (State.selected_service == service.service),
                                    "#ffeaf8",
                                    "#FFF5F9"
                                )
                            ),
                            color="#000000",
                            padding="0.75rem 1rem",
                            border_radius="0.5rem",
                            border=rx.cond(
                                (service.status == "completed"),
                                "2px solid #00A854",
                                rx.cond(
                                    (State.selected_service == service.service),
                                    "2px solid #fda8e9",
                                    "2px solid #DDDDDD"
                                )
                            ),
                            margin_bottom="0.75rem",
                            box_shadow="0 2px 4px rgba(0, 0, 0, 0.05)",
                            cursor="pointer",
                            transition="all 0.2s ease",
                            _hover={
                                "transform": "translateY(-2px)",
                                "box_shadow": "0 4px 8px rgba(0, 0, 0, 0.1)",
                                "border_color": "#fda8e9",
                            },
                            width="100%",
                            on_click=lambda s=service: State.select_service(s.service),
                        )
                    ),
                    width="100%",
                    spacing="0",
                    align_items="stretch",
                ),
                width="30%",
                padding="1.5rem",  # Increased padding
                background="rgba(255, 255, 255, 0.7)",
                border_radius="0.75rem",
                border="1px solid #E0E0E0",
                height="fit-content",
                box_shadow="0 4px 12px rgba(0, 0, 0, 0.05)",  # Added shadow for depth
            ),
            
            spacing="4",
            align_items="flex-start",
            width="100%",
        ),
        style={
            **styles["event_header"],
            "padding": "2.5rem",  # Increased padding for more length
            "background": "rgba(252, 228, 143, 0.3)",
            "border_radius": "1rem",
            "box_shadow": "0 4px 20px rgba(0, 0, 0, 0.08)",
            "margin_bottom": "2rem",
            "border": "2px solid #fce28f",
            "width": "100%",  # Ensure full width
        },
    )
def service_tab(service: EventService, index: int):
    """Small clickable service tab"""
    return rx.box(
        rx.hstack(
            rx.text(service.service, font_size="0.9rem"),
            rx.cond(
                service.status == "completed",
                rx.text("✅", font_size="0.9rem"),
                rx.text("⏳", font_size="0.9rem"),
            ),
            spacing="2",
        ),
        padding="0.5rem 1rem",
        border_radius="1rem",
        cursor="pointer",
        background=rx.cond(
            State.selected_service == service.service,
            "#fda8e9",
            "#f0f0f0"
        ),
        color=rx.cond(
            State.selected_service == service.service,
            "white",
            "#333333"
        ),
        border=rx.cond(
            service.status == "completed",
            "1px solid #28a745",
            "1px solid transparent"
        ),
        on_click=lambda service=service: State.select_service_for_vendor(service.service),
        _hover={
            "transform": "translateY(-2px)",
            "box_shadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
        },
        transition="all 0.2s ease",
    )

def vendor_result_card(vendor: VendorResult):
    """Card to display vendor search result"""
    return rx.box(
        rx.vstack(
            rx.heading(vendor.name, size="4"),
            rx.cond(
                vendor.contact != None,
                rx.text(f"📞 {vendor.contact}"),
                rx.text("")
            ),
            rx.cond(
                vendor.address != None,
                rx.text(f"📍 {vendor.address}"),
                rx.text("")
            ),
            rx.cond(
                vendor.price != None,
                rx.text(f"💰 {vendor.price}", color="#FF5252", font_weight="600"),
                rx.text("")
            ),
            rx.cond(
                vendor.rating != None,
                rx.text(f"⭐ Rating: {vendor.rating}"),
                rx.text("")
            ),
            rx.cond(
                vendor.description != None,
                rx.text(vendor.description, color="#666666", font_size="0.9rem"),
                rx.text("")
            ),
            rx.button(
                "Select This Provider",
                on_click=lambda v=vendor: State.select_vendor(v),
                style={
                    **styles["btn_primary_large"],
                    "width": "100%",
                    "margin_top": "1rem",
                },
            ),
            align_items="flex-start",
            spacing="2",
            width="100%",
        ),
        background="white",
        padding="1.5rem",
        border_radius="0.75rem",
        border="1px solid #e0e0e0", 
        transition="all 0.3s ease",
        _hover={
            "border_color": "#fda8e9",
            "transform": "translateY(-5px)",
            "box_shadow": "0 10px 25px rgba(0, 0, 0, 0.1)",
        },
    )

def loading_animation():
    """Loading animation while agents are working"""
    return rx.box(
        rx.vstack(
            rx.html("""
                <style>
                @keyframes pulse {
                    0% { opacity: 0.6; transform: scale(1); }
                    50% { opacity: 1; transform: scale(1.1); }
                    100% { opacity: 0.6; transform: scale(1); }
                }
                .pulse-animation {
                    animation: pulse 1.5s ease-in-out infinite;
                }
                </style>
                <div class="pulse-animation" style="font-size: 3rem;">🤖</div>
            """),
            rx.text("AI Agents are working...", font_size="1.4rem", font_weight="bold", color="#000000"),
            rx.text("This might take a moment", font_size="1rem", color="#666"),
            spacing="4",
            align_items="center",
        ),
        padding="2rem",
        background="rgba(255, 255, 255, 0.9)",
        border_radius="1rem",
        box_shadow="0 4px 20px rgba(0, 0, 0, 0.1)",
    )

def active_service_section():
    """Section for currently selected service"""
    return rx.box(
        rx.vstack(
            # Service info header
            rx.hstack(
                rx.cond(
                    State.selected_service != "",
                    rx.heading(
                        State.selected_service,
                        size="4",
                        color="#000000",
                    ),
                    rx.text("")
                ),
                rx.spacer(),
                rx.cond(
                    State.event_services.length() > 0,
                    rx.text(
                        lambda: f"Budget: ₹{next((s.budget for s in State.event_services if s.service == State.selected_service), 0):,}",
                        font_weight="600",
                        color="#FF5252",
                    ),
                    rx.text("")
                ),
                width="100%",
            ),
            
            rx.divider(),
            
            # Service content - selected provider or search
            rx.cond(
                # Check if service has provider
                State.event_services.length() > 0 & rx.cond(
                    lambda: any(s.status == "completed" for s in State.event_services if s.service == State.selected_service),
                    True,
                    False
                ),
                # Selected provider view
                rx.box(
                    rx.vstack(
                        rx.text("Selected Provider:", font_weight="600", margin_bottom="1rem"),
                        rx.box(
                            rx.vstack(
                                rx.heading(
                                    lambda: next((s.selected_provider.name for s in State.event_services if s.service == State.selected_service and s.selected_provider), "Unknown"),
                                    size="4",
                                ),
                                rx.text(
                                    lambda: next((s.selected_provider.contact for s in State.event_services if s.service == State.selected_service and s.selected_provider), ""),
                                    color="#666666",
                                ),
                                rx.text(
                                    lambda: next((s.selected_provider.address for s in State.event_services if s.service == State.selected_service and s.selected_provider), ""),
                                    color="#666666",
                                ),
                                rx.text(
                                    lambda: next((s.selected_provider.price for s in State.event_services if s.service == State.selected_service and s.selected_provider), ""),
                                    color="#FF5252",
                                    font_weight="600",
                                ),
                                rx.button(
                                    "Change Provider",
                                    on_click=lambda: State.start_vendor_search(State.selected_service),
                                    style=styles["btn_login"],
                                    margin_top="1rem",
                                ),
                                align_items="flex-start",
                                spacing="2",
                                width="100%",
                            ),
                            background="white",
                            padding="1.5rem",
                            border_radius="0.75rem",
                            border="2px solid #28a745",
                            width="100%",
                        ),
                        align_items="flex-start",
                        width="100%",
                    ),
                    width="100%",
                ),
                # Search interface view
                rx.vstack(
                    rx.cond(
                        State.is_searching,
                        loading_animation(),
                        rx.cond(
                            State.vendor_search_results.length() > 0,
                            rx.vstack(
                                rx.text(
                                    f"Select a {State.selected_service} provider:",
                                    font_weight="600",
                                    margin_bottom="1rem",
                                ),
                                rx.grid(
                                    rx.foreach(
                                        State.vendor_search_results.to(list[VendorResult]),
                                        vendor_result_card,
                                    ),
                                    template_columns="repeat(auto-fill, minmax(300px, 1fr))",
                                    gap="1.5rem",
                                ),
                                align_items="flex-start",
                                width="100%",
                            ),
                            rx.vstack(
                                rx.text(
                                    "Find the perfect match for your event!",
                                    font_size="1.2rem",
                                    margin_bottom="1rem",
                                ),
                                rx.button(
                                    f"Search for {State.selected_service} Providers",
                                    on_click=lambda: State.start_vendor_search(State.selected_service),
                                    style=styles["btn_primary_large"],
                                ),
                                align_items="center",
                                padding="2rem",
                            ),
                        ),
                    ),
                    width="100%",
                ),
            ),
            
            align_items="flex-start",
            width="100%",
            spacing="4",
        ),
        padding="2rem",
        background="#FFFFFF",
        border_radius="1rem",
        border="1px solid #E0E0E0",
        box_shadow="0 4px 20px rgba(0, 0, 0, 0.05)",
    )

def floating_invitation_button():
    """Floating button to create invitation with text label"""
    return rx.box(
        # Button container with background
        rx.hstack(
            # Icon
            rx.html("""
                <div style="display: flex; align-items: center; justify-content: center;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="3" y="5" width="18" height="14" rx="2"></rect>
                        <polyline points="3 7 12 13 21 7"></polyline>
                    </svg>
                </div>
            """),
            # Text label
            rx.text(
                "Create Invitation",
                font_weight="500",
                font_size="1rem",
                margin_left="0.5rem",
            ),
            # Container styling
            spacing="2",
            background="#fda8e9",
            color="white",
            padding="0.8rem 1.2rem",
            border_radius="1.5rem",
            box_shadow="0 4px 12px rgba(253, 168, 233, 0.5)",
            cursor="pointer",
            transition="all 0.3s ease",
            _hover={
                "transform": "translateY(-3px)",
                "box_shadow": "0 6px 18px rgba(253, 168, 233, 0.6)",
            },
        ),
        # Positioning
        position="fixed",
        bottom="2rem",
        right="2rem",
        z_index="100",
        on_click=State.navigate_to_invitation,
    )

def error_notification():
    """Error notification component"""
    return rx.cond(
        State.error_message != "",
        rx.box(
            rx.hstack(
                rx.icon("triangle_alert", color="red"),
                rx.text(State.error_message),
                rx.spacer(),
                rx.icon(
                    "x",
                    cursor="pointer",
                    on_click=lambda: State.set_error_message(""),
                ),
                width="100%",
            ),
            padding="1rem",
            background="rgba(255, 82, 82, 0.1)",
            border="1px solid #FF5252",
            border_radius="0.5rem",
            margin_bottom="1.5rem",
        ),
        rx.box()
    )

def service_detail():
    """Service detail component with centered alignment and deeper colors"""
    return rx.cond(
        State.selected_service != "",
        rx.box(
            rx.vstack(
                # Service header
                rx.hstack(
                    rx.heading(
                        State.selected_service,
                        size="3",
                        color="#000000",  # Deeper black
                    ),
                    rx.spacer(),
                    rx.text(
                        f"Budget: ₹{State.service_details.get('budget', 0):,}",
                        font_weight="600",
                        color="#E91E63",  # Deeper pink/red
                    ),
                    width="100%",
                ),
                
                # Divider
                rx.divider(),
                
                # Service status and actions - Centered
                rx.center(
                    rx.cond(
                        State.service_details.get("status") == "completed",
                        # SELECTED PROVIDER VIEW
                        rx.vstack(
                            rx.text(
                                "Selected Provider",
                                font_weight="600",
                                margin_bottom="1rem",
                                color="#000000",  # Deeper black
                            ),
                            
                            # Provider card with details
                            rx.box(
                                rx.vstack(
                                    # Success icon
                                    rx.html("""
                                        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#007E33" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                                            <polyline points="22 4 12 14.01 9 11.01"></polyline>
                                        </svg>
                                    """),
                                    rx.text(
                                        "Provider Selected Successfully!",
                                        font_weight="700", 
                                        color="#007E33",  # Deeper green
                                        font_size="1.2rem",
                                        margin_bottom="1rem",
                                    ),
                                    
                                    # Provider name
                                    rx.heading(
                                        State.current_provider_name,
                                        size="4",
                                        margin_bottom="0.75rem",
                                        color="#1A237E",  # Deep blue for name
                                    ),
                                    
                                    # Provider contact if available
                                    rx.cond(
                                        State.current_provider_contact != "N/A",
                                        rx.text(
                                            f"📞 {State.current_provider_contact}",
                                            margin_bottom="0.75rem",
                                            color="#424242",  # Deeper text color
                                            font_weight="500",
                                        ),
                                    ),
                                    
                                    # Provider address if available
                                    rx.cond(
                                        State.current_provider_address != "N/A",
                                        rx.text(
                                            f"📍 {State.current_provider_address}",
                                            margin_bottom="0.75rem",
                                            color="#424242",  # Deeper text color
                                            font_weight="500",
                                        ),
                                    ),
                                    
                                    # Provider price if available
                                    rx.cond(
                                        State.current_provider_price != "N/A",
                                        rx.text(
                                            f"💰 {State.current_provider_price}",
                                            color="#C2185B",  # Deeper pink for price
                                            font_weight="600",
                                            margin_bottom="0.75rem",
                                        ),
                                    ),
                                    
                                    # Provider rating if available
                                    rx.cond(
                                        State.current_provider_rating != "N/A",
                                        rx.text(
                                            f"⭐ Rating: {State.current_provider_rating}",
                                            color="#FF8F00",  # Deep amber for rating
                                            font_weight="600",
                                            margin_bottom="0.75rem",
                                        ),
                                    ),
                                    
                                    # Source if available
                                    rx.cond(
                                        State.current_provider_source != "N/A",
                                        rx.link(
                                            f"🔗 Visit Website",
                                            href=State.current_provider_source,
                                            is_external=True,
                                            color="#0277BD",  # Deep blue for links
                                            margin_bottom="0.75rem",
                                            font_weight="500",
                                            text_decoration="underline",
                                            _hover={
                                                "color": "#01579B",
                                                "text_decoration": "underline",
                                            },
                                        ),
                                    ),
                                    
                                    # Map link if available
                                    rx.cond(
                                        State.current_provider_map_link != "N/A",
                                        rx.link(
                                            "📍 View on Map",
                                            href=State.current_provider_map_link,
                                            is_external=True,
                                            color="#0277BD",  # Deep blue for links
                                            margin_bottom="0.75rem",
                                            font_weight="500",
                                            text_decoration="underline",
                                            _hover={
                                                "color": "#01579B",
                                                "text_decoration": "underline",
                                            },
                                        ),
                                    ),
                                    
                                    # Change Provider button with fixed icon
                                    rx.button(
                                        rx.hstack(
                                            rx.icon("refresh_cw"),  # Fixed icon
                                            rx.text("Change Provider"),
                                            spacing="2",
                                        ),
                                        on_click=State.clear_selected_vendor,
                                        style={
                                            "padding": "0.75rem 1.5rem",
                                            "background": "#263238",  # Deeper background
                                            "border": "1px solid #000000",
                                            "border_radius": "0.5rem",
                                            "color": "white",  # White text for better contrast
                                            "font_weight": "600",
                                            "cursor": "pointer",
                                            "_hover": {
                                                "background": "#455A64",  # Lighter on hover
                                                "transform": "translateY(-2px)",
                                                "box_shadow": "0 4px 12px rgba(0, 0, 0, 0.15)",
                                            },
                                            "transition": "all 0.2s ease",
                                        },
                                    ),
                                    align_items="center",  # Center items
                                    spacing="4",
                                    width="100%",
                                ),
                                padding="2rem",
                                background="#FFFFFF",
                                border="2px solid #007E33",  # Deeper green border
                                border_radius="1rem",
                                box_shadow="0 6px 16px rgba(0, 0, 0, 0.1)",  # Deeper shadow
                                width="100%",
                                max_width="600px",  # Add max width for better centering
                                margin="0 auto",  # Center horizontally
                            ),
                            
                            width="100%",
                            align_items="center",  # Center align content
                        ),
                        
                        # SEARCH STATE - Show search button or loading
                        rx.cond(
                            State.is_searching,
                            # LOADING STATE
                            rx.box(
                                rx.vstack(
                                    # Custom loader
                                    rx.html("""
                                        <style>
                                            .loader {
                                                border: 5px solid #f3f3f3;
                                                border-radius: 50%;
                                                border-top: 5px solid #fda8e9;
                                                width: 50px;
                                                height: 50px;
                                                -webkit-animation: spin 1s linear infinite;
                                                animation: spin 1s linear infinite;
                                            }
                                            @keyframes spin {
                                                0% { transform: rotate(0deg); }
                                                100% { transform: rotate(360deg); }
                                            }
                                        </style>
                                        <div class="loader"></div>
                                    """),
                                    rx.heading(
                                        "AI Agents are Searching...",
                                        size="3",
                                        color="#000000",
                                        margin_top="1.5rem",
                                    ),
                                    rx.text(
                                        f"Finding the best {State.selected_service} providers for your event",
                                        color="#555555",
                                        font_size="1.1rem",
                                    ),
                                    rx.text(
                                        "This might take a moment as our AI searches for quality options that match your budget and requirements.",
                                        color="#777777",
                                        margin_top="1rem",
                                    ),
                                    align_items="center",
                                    padding="3rem",
                                    text_align="center",
                                ),
                                width="100%",
                                max_width="600px",  # Add max width
                                background="#FFF5F9",
                                border_radius="1rem",
                                border="2px dashed #fda8e9",
                                box_shadow="0 4px 12px rgba(0, 0, 0, 0.05)",
                                margin="0 auto",  # Center horizontally
                            ),
                            # NOT SEARCHING - Show search button with venue type selector if needed
                            rx.vstack(
                                # Title text
                                rx.text(
                                    "No provider selected yet. Find the perfect match for your event!",
                                    margin_bottom="1.5rem",
                                    color="#000000",
                                    font_size="1.1rem",
                                ),
                                
                                # Add venue type selector only for Venue service
                                rx.cond(
                                    State.selected_service == "Venue",
                                    rx.vstack(
                                        rx.text(
                                            "What type of venue are you looking for?",
                                            color="#424242",
                                            font_weight="500",
                                            margin_bottom="0.5rem",
                                        ),
                                        # Venue type dropdown
                                        rx.select(
                                            State.venue_types,
                                            placeholder="Select venue type",
                                            on_change=State.set_venue_type,
                                            value=State.venue_type,
                                            color="#000000",
                                            border="1px solid #000000",
                                            background="#FFFFFF",
                                            width="100%",
                                            margin_bottom="1rem",
                                        ),
                                        # Show text input for "Other" option
                                        rx.cond(
                                            State.show_venue_type_other,
                                            rx.input(
                                                placeholder="Please specify venue type",
                                                value=State.venue_type_other,
                                                on_change=State.set_venue_type_other,
                                                border="1px solid #000000",
                                                color="#000000",
                                                width="100%",
                                                margin_bottom="1rem",
                                            ),
                                        ),
                                        width="100%",
                                        align_items="flex-start",
                                    ),
                                ),
                                
                                # Search button - updated to pass venue type when relevant
                                rx.button(
                                    rx.hstack(
                                        rx.icon("search"),
                                        rx.text(f"Find {State.selected_service} Providers"),
                                        spacing="2",
                                    ),
                                    on_click=lambda: State.search_vendors_with_venue_type(State.selected_service),
                                    style={
                                        "background": "#000000",
                                        "color": "#FFFFFF",
                                        "padding": "1.2rem 2rem",
                                        "font_weight": "600",
                                        "font_size": "1.1rem",
                                        "border_radius": "0.5rem",
                                        "box_shadow": "0 4px 12px rgba(0, 0, 0, 0.1)",
                                        "_hover": {
                                            "background": "#fda8e9",
                                            "transform": "translateY(-3px)",
                                            "box_shadow": "0 6px 16px rgba(0, 0, 0, 0.15)",
                                        },
                                        "transition": "all 0.3s ease",
                                    },
                                    disabled=State.is_searching,
                                ),
                                align_items="center",
                                spacing="4",
                                padding="3rem",
                                text_align="center",
                                width="100%",
                                max_width="600px",  # Add max width
                                margin="0 auto",  # Center horizontally
                            ),
                        ),
                    ),
                    width="100%",  # Full width for the center component
                ),
                
                # Search results section - Center aligned
                rx.cond(
                    (~State.is_searching) & 
                    (State.search_results.length() > 0) & 
                    (State.service_details.get("status") != "completed"),
                    rx.center(
                        rx.vstack(
                            rx.heading(
                                f"{State.selected_service} Options",
                                size="4",
                                margin_bottom="1rem",
                                color="#000000",
                            ),
                            rx.text(
                                "Select a provider that best matches your requirements:",
                                margin_bottom="1.5rem",
                                color="#000000",
                            ),
                            # Results grid
                            rx.box(
                                rx.foreach(
                                    State.search_results.to(list[dict]),
                                    vendor_card,
                                ),
                                style={
                                    "display": "grid",
                                    "grid_template_columns": ["1fr", "repeat(2, 1fr)", "repeat(3, 1fr)"],
                                    "gap": "1.5rem",
                                    "margin_top": "1rem",
                                },
                                width="100%",
                            ),
                            # Add a success notification that appears when a vendor is selected
                            rx.cond(
                                State.success_message != "",
                                rx.box(
                                    rx.hstack(
                                        rx.icon("check", color="green"),
                                        rx.text(
                                            State.success_message,
                                            color="#00A854",
                                            font_weight="600",
                                        ),
                                        spacing="2",
                                    ),
                                    padding="1rem",
                                    background="rgba(0, 168, 84, 0.1)",
                                    border_radius="0.5rem",
                                    border="1px solid #00A854",
                                    margin_top="1.5rem",
                                    width="100%",
                                ),
                            ),
                            width="100%",
                            align_items="center",  # Center align items
                            spacing="4",
                        ),
                        width="100%",
                    ),
                    rx.box(),  # Empty box if no results or still searching
                ),
                
                align_items="center",  # Center align all items
                width="100%",
                spacing="4",
            ),
            style={
                "padding": "2.5rem",
                "background": "#FFFFFF",
                "border_radius": "1rem",
                "box_shadow": "0 6px 20px rgba(0, 0, 0, 0.12)",  # Deeper shadow
                "border": "2px solid #FFC107",  # Deeper yellow border
                "margin_top": "2rem",
                "width": "100%",
            },
        ),
        rx.box(
            rx.center(
                rx.vstack(
                    rx.icon("arrow_up", font_size="3xl", color="#424242"),  # Deeper gray
                    rx.text(
                        "Please select a service from above to proceed",
                        font_size="1.2rem",
                        color="#212121",  # Deeper text color
                        font_weight="600",
                    ),
                    align_items="center",
                    spacing="4",
                ),
                height="200px",
                width="100%",
                background="#f0f0f0",  # Slightly darker background
                border_radius="1rem",
                border="2px dashed #9E9E9E",  # Darker border
            ),
        ),  # Guide when no service selected
    )

# Update the floating invitation button function to include text

def create_invitation_button():
    """Floating button to create invitation with text label"""
    return rx.box(
        # Button container with background
        rx.hstack(
            # Icon
            rx.html("""
                <div style="display: flex; align-items: center; justify-content: center;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="3" y="5" width="18" height="14" rx="2"></rect>
                        <polyline points="3 7 12 13 21 7"></polyline>
                    </svg>
                </div>
            """),
            # Text label
            rx.text(
                "Create Invitation",
                font_weight="500",
                font_size="1rem",
                margin_left="0.5rem",
            ),
            # Container styling
            spacing="2",
            background="#fda8e9",
            color="white",
            padding="0.8rem 1.2rem",
            border_radius="1.5rem",
            box_shadow="0 4px 12px rgba(253, 168, 233, 0.5)",
            cursor="pointer",
            transition="all 0.3s ease",
            _hover={
                "transform": "translateY(-3px)",
                "box_shadow": "0 6px 18px rgba(253, 168, 233, 0.6)",
            },
        ),
        # Positioning
        position="fixed",
        bottom="2rem",
        right="2rem",
        z_index="100",
        # Use navigation method instead of direct URL construction
        on_click=State.navigate_to_invitation,
    )

def notifications():
    """Notification messages for success/error"""
    return rx.vstack(
        # Error message
        rx.cond(
            State.error_message != "",
            rx.box(
                rx.hstack(
                    rx.icon("triangle_alert", color="red"),  # Changed from "alert" to "triangle_alert"
                    rx.text(State.error_message),
                    rx.spacer(),
                    rx.icon(
                        "x",
                        cursor="pointer",
                        on_click=lambda: State.set_error_message(""),
                    ),
                    width="100%",
                ),
                padding="1rem",
                background="rgba(255, 82, 82, 0.1)",
                border="1px solid #FF5252",
                border_radius="0.5rem",
                margin_bottom="1rem",
            ),
        ),
        
        # Success message
        rx.cond(
            State.success_message != "",
            rx.box(
                rx.hstack(
                    rx.icon("check_check", color="green"),  # Changed from "check" to "check_check"
                    rx.text(State.success_message),
                    rx.spacer(),
                    rx.icon(
                        "x",
                        cursor="pointer",
                        on_click=lambda: State.set_success_message(""),
                    ),
                    width="100%",
                ),
                padding="1rem",
                background="rgba(0, 168, 84, 0.1)",
                border="1px solid #00A854",
                border_radius="0.5rem",
                margin_bottom="1rem",
            ),
        ),
        width="100%",
    )


def vendor_card(vendor):
    """Vendor search result card with simplified implementation"""
    # Safely extract vendor properties with fallbacks
    name = vendor.get("name", vendor.get("Name", "Unknown Provider"))
    contact = vendor.get("contact", vendor.get("Contact", ""))
    address = vendor.get("address", vendor.get("Address", ""))
    price = vendor.get("price", vendor.get("Price", ""))
    rating = vendor.get("rating", vendor.get("Rating", ""))
    description = vendor.get("description", vendor.get("Description", ""))
    source = vendor.get("source", vendor.get("source_link", vendor.get("website", "")))
    map_link = vendor.get("map_link", vendor.get("map_url", ""))
    
    return rx.box(
        rx.vstack(
            # Vendor name
            rx.heading(name, size="4", color="#000000"),
            
            # Contact info if available
            rx.cond(
                contact != "",
                rx.text(f"📞 {contact}", color="#333333"),
            ),
            
            # Address if available
            rx.cond(
                address != "",
                rx.text(f"📍 {address}", color="#333333"),
            ),
            
            # Map link if available
            rx.cond(
                map_link != "",
                rx.link(
                    "View on Map",
                    href=map_link,
                    is_external=True,
                    color="#1E88E5",
                    text_decoration="underline",
                    font_size="0.9rem",
                    margin_top="0.5rem",
                ),
            ),
            
            # Rating if available
            rx.cond(
                rating != "",
                rx.text(f"⭐ {rating}", color="#333333", font_weight="600"),
            ),
            
            # Price - handle as string to avoid issues
            rx.cond(
                price != "",
                rx.text(
                    f"💰 {price}" if isinstance(price, str) else "See pricing options",
                    color="#FF5252",
                    font_weight="700",
                    margin_top="0.5rem",
                ),
            ),
            
            # Description if available
            rx.cond(
                description != "",
                rx.text(
                    description,
                    color="#666666",
                    font_size="0.9rem",
                    margin_top="0.5rem",
                ),
            ),
            
            # Source link if available
            rx.cond(
                source != "",
                rx.link(
                    "Visit Website",
                    href=source,
                    is_external=True,
                    color="#1E88E5",
                    text_decoration="underline",
                    margin_top="0.5rem",
                ),
            ),
            
            # Select button
            rx.button(
                "Select This Provider",
                # Pass the vendor dict directly
                on_click=lambda: State.select_vendor(vendor),
                background="#000000",
                color="#FFFFFF",
                padding="0.75rem",
                border_radius="0.5rem",
                width="100%",
                font_weight="600",
                margin_top="1rem",
                cursor="pointer",
                transition="all 0.3s ease",
                _hover={
                    "background": "#fda8e9",
                    "transform": "translateY(-2px)",
                    "box_shadow": "0 4px 12px rgba(0, 0, 0, 0.1)",
                },
            ),
            
            align_items="flex_start",
            spacing="2",
            width="100%",
        ),
        background="white",
        padding="1.8rem",
        border_radius="0.75rem",
        border="1px solid #e0e0e0", 
        transition="all 0.3s ease",
        box_shadow="0 2px 8px rgba(0, 0, 0, 0.05)",
        _hover={
            "border_color": "#fda8e9",
            "transform": "translateY(-5px)",
            "box_shadow": "0 10px 25px rgba(0, 0, 0, 0.1)",
        },
    )

def navbar_event_page():
    """Navigation bar for event detail page"""
    return rx.box(
        rx.hstack(
            # Left side
            rx.heading("EventWise", style=styles["nav_brand"]),
            
            # Spacer to push logout to right
            rx.spacer(),
            
            # Right side
            rx.button(
                "Back to Dashboard",
                style=styles["btn_login"],
                on_click=lambda: rx.redirect("/dashboard"),
            ),
            width="100%",
            # The justify prop uses "between" not "space-between"
            justify="between",
        ),
        style=styles["nav"],
        id="navbar",
    )

def event_detail_page():
    """Event detail page with service selection and vendor search"""
    return rx.box(
        # Navbar
        navbar_event_page(),
        
        # Main content
        rx.box(
            rx.cond(
                State.is_loading_event,
                # Loading view
                rx.center(
                    loading_animation(),
                    height="100vh",
                ),
                # Loaded view
                rx.vstack(
                    # Notifications
                    notifications(),
                    
                    # Event header section with integrated service pills
                    event_header(),
                    
                    # Service detail and vendor search
                    service_detail(),
                    
                    # Floating invitation button
                    create_invitation_button(),
                    
                    width="100%",
                    spacing="4",
                    align_items="flex-start",
                ),
            ),
            # Main content container styling
            max_width="1200px",
            margin="0 auto",
            padding="8rem 2rem 2rem 2rem",  # Top padding for navbar
            min_height="100vh",
        ),
        
        # JavaScript for scroll behavior
        rx.html("""
            <script>
                let prevScrollpos = window.pageYOffset;
                let navbar = null;
                
                window.addEventListener('DOMContentLoaded', (event) => {
                    navbar = document.querySelector('nav') || document.querySelector('[id="navbar"]') || document.querySelector('header > div:first-child');
                });
                
                window.onscroll = function() {
                    if (!navbar) {
                        navbar = document.querySelector('nav') || document.querySelector('[id="navbar"]') || document.querySelector('header > div:first-child');
                    }
                    
                    if (navbar) {
                        let currentScrollPos = window.pageYOffset;
                        
                        if (prevScrollpos > currentScrollPos || currentScrollPos <= 0) {
                            // Scrolling UP or at the top
                            navbar.style.transform = "translateY(0)";
                            navbar.style.transition = "transform 0.3s ease";
                        } else {
                            // Scrolling DOWN
                            navbar.style.transform = "translateY(-100%)";
                            navbar.style.transition = "transform 0.3s ease";
                        }
                        
                        prevScrollpos = currentScrollPos;
                    }
                };
            </script>
        """),
        
        
        # Set event ID on page load
        on_mount=State.load_event_details,
        
        # Page background
        background="#FFFDE7",
        min_height="100vh",
        width="100%",
    )

def invitation_navbar():
    """Navigation bar for invitation page"""
    return rx.box(
        rx.hstack(
            # Left side
            rx.heading("EventWise", style=styles["nav_brand"]),
            
            # Spacer to push buttons to right
            rx.spacer(),
            
            # Right side - Use the navigate_back_to_event method to avoid or issues
            rx.button(
                "Back to Event",
                style=styles["btn_login"],
                on_click=State.navigate_back_to_event,
            ),
            width="100%",
            justify="between",
        ),
        style=styles["nav"],
        id="navbar",
    )

def invitation_page():
    """Invitation creation and customization page"""
    return rx.box(
        # Navbar
        invitation_navbar(),
        
        # Main content
        rx.box(
            rx.cond(
                State.is_loading_event,
                # Loading view
                rx.center(
                    loading_animation(),
                    height="100vh",
                ),
                # Loaded view
                rx.vstack(
                    # Notifications area for errors
                    rx.cond(
                        State.error_message != "",
                        rx.box(
                            rx.hstack(
                                rx.icon(
                                    "triangle_alert",  # Corrected icon name
                                    color="#FF5252",
                                    font_size="1.5rem",
                                ),
                                rx.text(State.error_message),
                                spacing="3",
                            ),
                            padding="1rem",
                            background="rgba(255, 82, 82, 0.1)",
                            border_radius="0.5rem",
                            border="1px solid #FF5252",
                            margin_bottom="1.5rem",
                            width="100%",
                        ),
                    ),
                    
                    # Event info section
                    rx.box(
                        rx.vstack(
                            rx.heading(
                                f"Create Invitation for {State.current_event.get('event_name', '')}",
                                size="3",
                                color="#000000",
                            ),
                            rx.text(
                                f"Type: {State.event_category_display} | Date: {State.current_event.get('event_date', '')} | Location: {State.current_event.get('location', '')}",
                                color="#666666",
                            ),
                            align_items="center",
                            spacing="1",
                            width="100%",
                        ),
                        padding="1.5rem",
                        border_radius="0.75rem",
                        background="rgba(252, 228, 143, 0.3)",
                        border="2px solid #fce28f",
                        margin_bottom="2rem",
                        width="100%",
                    ),
                    
                    # Step 1: Basic invitation info form
                    rx.cond(
                        State.invitation_text == "",  # Show only when invitation not yet generated
                        rx.box(
                            rx.vstack(
                                rx.heading(
                                    "Step 1: Invitation Details",
                                    size="4",
                                    margin_bottom="1rem",
                                    color="#000000",
                                ),
                                
                                # Venue selection
                                rx.box(
                                    rx.text("Venue Information", style=styles["create_form_label"]),
                                    rx.input(
                                        placeholder="Venue name",
                                        value=State.invitation_venue_name,
                                        on_change=State.set_invitation_venue_name,
                                        style=styles["create_form_input"],
                                    ),
                                    rx.input(
                                        placeholder="Venue address",
                                        value=State.invitation_venue_address,
                                        on_change=State.set_invitation_venue_address,
                                        style=styles["create_form_input"],
                                    ),
                                    width="100%",
                                ),
                                
                                # Two columns grid for shorter inputs
                                rx.grid(
                                    # Event time
                                    rx.box(
                                        rx.text("Event Time", style=styles["create_form_label"]),
                                        rx.input(
                                            placeholder="e.g., 7:00 PM",
                                            value=State.invitation_time,
                                            on_change=State.set_invitation_time,
                                            style=styles["create_form_input"],
                                        ),
                                    ),
                                    
                                    # Host name
                                    rx.box(
                                        rx.text("Host Name", style=styles["create_form_label"]),
                                        rx.input(
                                            placeholder="e.g., John & Sarah Smith",
                                            value=State.host_name,
                                            on_change=State.set_host_name,
                                            style=styles["create_form_input"],
                                        ),
                                    ),
                                    
                                    # RSVP contact
                                    rx.box(
                                        rx.text("RSVP Contact", style=styles["create_form_label"]),
                                        rx.input(
                                            placeholder="e.g., 555-123-4567 or john@example.com",
                                            value=State.rsvp_contact,
                                            on_change=State.set_rsvp_contact,
                                            style=styles["create_form_input"],
                                        ),
                                    ),
                                    
                                    # Style preference
                                    rx.box(
                                        rx.text("Style Preference", style=styles["create_form_label"]),
                                        rx.select(
                                            ["Elegant", "Casual", "Formal", "Playful", "Modern", "Vintage"],
                                            placeholder="Select a style",
                                            value=State.style_preference,
                                            on_change=State.set_style_preference,
                                            style=styles["create_form_input"],
                                        ),
                                    ),
                                    
                                    # Special instructions
                                    rx.box(
                                        rx.text("Special Instructions (Optional)", style=styles["create_form_label"]),
                                        rx.text_area(
                                            placeholder="Any special instructions for guests...",
                                            value=State.special_instructions,
                                            on_change=State.set_special_instructions,
                                            height="100px",
                                            style=styles["create_form_input"],
                                        ),
                                        grid_column="span 2",
                                    ),
                                    
                                    template_columns="repeat(2, 1fr)",
                                    gap="1.5rem",
                                    width="100%",
                                ),
                                
                                # Generate invitation button
                                rx.button(
                                    rx.cond(
                                        State.is_generating_invitation,
                                        "Generating Your Invitation...",
                                        "Generate Invitation Text"
                                    ),
                                    on_click=State.generate_invitation,
                                    style=styles["create_submit_button"],
                                    disabled=State.is_generating_invitation,
                                ),
                                
                                # Loading animation
                                rx.cond(
                                    State.is_generating_invitation,
                                    rx.center(
                                        loading_animation(),
                                        margin_top="1.5rem",
                                    ),
                                ),
                                
                                align_items="stretch",
                                width="100%",
                                spacing="4",
                            ),
                            padding="2rem",
                            background="#FFFFFF",
                            border_radius="1rem",
                            border="2px solid #E0E0E0",
                            box_shadow="0 4px 20px rgba(0, 0, 0, 0.05)",
                            margin_bottom="2rem",
                            width="100%",
                            id="step1_section",
                        ),
                    ),
                    
                    # Step 2: Invitation Preview and Style Selection
                    rx.cond(
                        State.invitation_text != "",  # Only show when invitation text is generated
                        rx.box(
                            rx.vstack(
                                rx.heading(
                                    "Step 2: Invitation Preview & Styling",
                                    size="4", 
                                    margin_bottom="1rem",
                                    color="#000000",
                                ),
                                
                                # Invitation text preview
                                rx.box(
                                    rx.vstack(
                                        rx.heading(
                                            "Preview",
                                            size="5",
                                            margin_bottom="1rem",
                                            color="#000000",
                                        ),
                                        rx.box(
                                            rx.text(
                                                State.invitation_text,
                                                style={
                                                    "white_space": "pre-wrap",
                                                    "text_align": "center",
                                                    "line_height": "1.8",
                                                    "font_family": "'Times New Roman', serif",
                                                    "color": "#333333",
                                                    "font_size": "1.1rem",
                                                    "padding": "1.5rem",
                                                },
                                            ),
                                            background=State.invitation_background,
                                            border_radius="0.5rem",
                                            border="1px solid #E0E0E0",
                                            box_shadow="0 2px 10px rgba(0, 0, 0, 0.05)",
                                            width="100%",
                                            min_height="250px",
                                            display="flex",
                                            align_items="center",
                                            justify_content="center",
                                        ),
                                        align_items="stretch",
                                        width="100%",
                                    ),
                                    width="100%",
                                    margin_bottom="2rem",
                                ),
                                
                                # Approval question
                                rx.box(
                                    rx.text(
                                        "Are you happy with this invitation text?",
                                        font_weight="600",
                                        margin_bottom="1rem",
                                        text_align="center",
                                        color="#000000",
                                    ),
                                    rx.hstack(
                                        rx.button(
                                            "Generate New Text",
                                            on_click=State.regenerate_invitation_text,
                                            style={
                                                "background": "#FFFFFF",
                                                "color": "#000000",
                                                "border": "2px solid #000000",
                                                "padding": "0.75rem 1.5rem",
                                                "border_radius": "0.5rem",
                                                "font_weight": "600",
                                                "cursor": "pointer",
                                                "_hover": {
                                                    "background": "#F5F5F5",
                                                },
                                            },
                                        ),
                                        rx.button(
                                            "Proceed with Styling",
                                            on_click=State.set_highlight_styling,
                                            style={
                                                "background": "#000000",
                                                "color": "white",
                                                "border": "2px solid #000000",
                                                "padding": "0.75rem 1.5rem",
                                                "border_radius": "0.5rem",
                                                "font_weight": "600",
                                                "cursor": "pointer",
                                                "_hover": {
                                                    "background": "#333333",
                                                },
                                            },
                                        ),
                                        justify="center",
                                        spacing="4",
                                    ),
                                    width="100%",
                                    margin_bottom="2rem",
                                ),
                                
                                # Styling options header
                                rx.heading(
                                    "Customize Your Invitation",
                                    size="4",
                                    margin="1rem 0",
                                    color="#000000",
                                    id="styling_section",
                                ),
                                
                                # Color scheme selection
                                rx.box(
                                    rx.text(
                                        "Choose a Color Scheme:",
                                        font_weight="600",
                                        margin_bottom="0.5rem",
                                        color="#000000",
                                    ),
                                    rx.flex(  # Using flex instead of wrap
                                        rx.foreach(
                                            State.color_options.to(list[dict]),  # Type conversion
                                            lambda color, i: rx.box(
                                                rx.vstack(
                                                    rx.box(
                                                        height="2rem",
                                                        width="100%",
                                                        background=color["primary"],
                                                        border_radius="0.25rem 0.25rem 0 0",
                                                    ),
                                                    rx.box(
                                                        height="0.5rem",
                                                        width="100%",
                                                        background=color["accent"],
                                                    ),
                                                    rx.box(
                                                        height="1.5rem",
                                                        width="100%",
                                                        background=color["secondary"],
                                                        border_radius="0 0 0.25rem 0.25rem",
                                                    ),
                                                    rx.text(
                                                        color["name"],
                                                        font_size="0.8rem",
                                                        color="#666666",
                                                        margin_top="0.25rem",
                                                    ),
                                                    width="80px",
                                                    spacing="0",
                                                ),
                                                cursor="pointer",
                                                padding="0.5rem",
                                                border_radius="0.5rem",
                                                border=rx.cond(
                                                    State.selected_color_scheme == color["id"],
                                                    "2px solid #fda8e9",
                                                    "2px solid transparent",
                                                ),
                                                background=rx.cond(
                                                    State.selected_color_scheme == color["id"],
                                                    "rgba(253, 168, 233, 0.1)",
                                                    "transparent",
                                                ),
                                                transition="all 0.2s ease",
                                                _hover={
                                                    "transform": "translateY(-3px)",
                                                    "box_shadow": "0 4px 12px rgba(0, 0, 0, 0.1)",
                                                },
                                                on_click=lambda c=color: State.set_selected_color_scheme(c["id"]),
                                            )
                                        ),
                                        spacing="3",
                                        justify="center",
                                        width="100%",
                                        margin_bottom="1.5rem",
                                        wrap="wrap",  # Add this for wrap behavior
                                    ),
                                ),
                                
                                # Font style selection
                                rx.box(
                                    rx.text(
                                        "Choose a Font Style:",
                                        font_weight="600",
                                        margin_bottom="0.5rem",
                                        color="#000000",
                                    ),
                                    rx.flex(  # Using flex instead of wrap
                                        rx.foreach(
                                            State.font_options.to(list[dict]),  # Type conversion
                                            lambda font, i: rx.box(
                                                rx.text(
                                                    font["name"],
                                                    style={
                                                        "font_family": font["heading"],
                                                        "font_size": "1rem",
                                                    }
                                                ),
                                                cursor="pointer",
                                                padding="0.75rem 1.5rem",
                                                border_radius="0.5rem",
                                                border=rx.cond(
                                                    State.selected_font_style == font["id"],
                                                    "2px solid #fda8e9",
                                                    "1px solid #E0E0E0",
                                                ),
                                                background=rx.cond(
                                                    State.selected_font_style == font["id"],
                                                    "rgba(253, 168, 233, 0.1)",
                                                    "#FFFFFF",
                                                ),
                                                transition="all 0.2s ease",
                                                _hover={
                                                    "transform": "translateY(-2px)",
                                                    "box_shadow": "0 4px 12px rgba(0, 0, 0, 0.1)",
                                                },
                                                on_click=lambda f=font: State.set_selected_font_style(f["id"]),
                                            )
                                        ),
                                        spacing="3",
                                        justify="center",
                                        width="100%",
                                        margin_bottom="1.5rem",
                                        wrap="wrap",  # Add this for wrap behavior
                                    ),
                                ),
                                
                                # Border style selection
                                rx.box(
                                    rx.text(
                                        "Choose a Border Style:",
                                        font_weight="600",
                                        margin_bottom="0.5rem",
                                        color="#000000",
                                    ),
                                    rx.flex(  # Using flex instead of wrap
                                        rx.foreach(
                                            State.border_options.to(list[dict]),  # Type conversion
                                            lambda border, i: rx.box(
                                                rx.text(
                                                    border["name"],
                                                    style={
                                                        "font_size": "0.9rem",
                                                    }
                                                ),
                                                cursor="pointer",
                                                padding="0.75rem 1.5rem",
                                                border_radius="0.5rem",
                                                border=rx.cond(
                                                    State.selected_border_style == border["id"],
                                                    "2px solid #fda8e9",
                                                    "1px solid #E0E0E0",
                                                ),
                                                background=rx.cond(
                                                    State.selected_border_style == border["id"],
                                                    "rgba(253, 168, 233, 0.1)",
                                                    "#FFFFFF",
                                                ),
                                                transition="all 0.2s ease",
                                                _hover={
                                                    "transform": "translateY(-2px)",
                                                    "box_shadow": "0 4px 12px rgba(0, 0, 0, 0.1)",
                                                },
                                                on_click=lambda b=border: State.set_selected_border_style(b["id"]),
                                            )
                                        ),
                                        spacing="3",
                                        justify="center",
                                        width="100%",
                                        margin_bottom="1.5rem",
                                        wrap="wrap",  # Add this for wrap behavior
                                    ),
                                ),
                                
                                # Background color selection
                                rx.box(
                                    rx.text(
                                        "Choose a Background Color:",
                                        font_weight="600",
                                        margin_bottom="0.5rem",
                                        color="#000000",
                                    ),
                                    rx.flex(  # Using flex instead of wrap
                                        rx.foreach(
                                            State.background_options.to(list[dict]),  # Type conversion
                                            lambda bg, i: rx.box(
                                                rx.vstack(
                                                    rx.box(
                                                        width="70px",
                                                        height="70px",
                                                        background=bg["color"],
                                                        border_radius="0.25rem",
                                                        border="1px solid #E0E0E0",
                                                    ),
                                                    rx.text(
                                                        bg["name"],
                                                        font_size="0.8rem",
                                                        color="#666666",
                                                        margin_top="0.25rem",
                                                    ),
                                                    align_items="center",
                                                ),
                                                cursor="pointer",
                                                padding="0.5rem",
                                                border_radius="0.5rem",
                                                border=rx.cond(
                                                    State.selected_background == bg["id"],
                                                    "2px solid #fda8e9",
                                                    "2px solid transparent",
                                                ),
                                                background=rx.cond(
                                                    State.selected_background == bg["id"],
                                                    "rgba(253, 168, 233, 0.1)",
                                                    "transparent",
                                                ),
                                                transition="all 0.2s ease",
                                                _hover={
                                                    "transform": "translateY(-3px)",
                                                    "box_shadow": "0 4px 12px rgba(0, 0, 0, 0.1)",
                                                },
                                                on_click=lambda b=bg: State.set_selected_background(b["id"]),
                                            )
                                        ),
                                        spacing="3",
                                        justify="center",
                                        width="100%",
                                        margin_bottom="1.5rem",
                                        wrap="wrap",  # Add this for wrap behavior
                                    ),
                                ),
                                
                                # Generate PDF button
                                rx.button(
                                    rx.cond(
                                        State.is_generating_pdf,
                                        "Generating PDF...",
                                        "Generate PDF Invitation"
                                    ),
                                    on_click=State.generate_invitation_pdf,
                                    style=styles["create_submit_button"],
                                    disabled=State.is_generating_pdf,
                                ),
                                
                                # Loading animation for PDF generation
                                rx.cond(
                                    State.is_generating_pdf,
                                    rx.center(
                                        loading_animation(),
                                        margin_top="1.5rem",
                                    ),
                                ),
                                
                                align_items="stretch",
                                width="100%",
                                spacing="4",
                            ),
                            padding="2rem",
                            background=rx.cond(
                                State.highlight_styling,
                                "#FFFCE6",  # Highlighted background
                                "#FFFFFF",  # Regular background
                            ),
                            border_radius="1rem",
                            border=rx.cond(
                                State.highlight_styling,
                                "2px solid #fda8e9",  # Highlighted border
                                "2px solid #E0E0E0",  # Regular border
                            ),
                            box_shadow="0 4px 20px rgba(0, 0, 0, 0.05)",
                            margin_bottom="2rem",
                            width="100%",
                            id="step2_section",
                        ),
                    ),
                    
                    # Step 3: PDF Generated and Email Options
                    rx.cond(
                        State.pdf_path != "",  # Only show when PDF is generated
                        rx.box(
                            rx.vstack(
                                rx.heading(
                                    "Step 3: Send Your Invitation",
                                    size="4",
                                    margin_bottom="1rem",
                                    color="#000000",
                                ),
                                
                                # PDF success message
                                rx.box(
                                    rx.vstack(
                                        rx.icon(
                                            "check_check",  # Corrected icon name
                                            color="#00A854",
                                            font_size="2rem",
                                        ),
                                        rx.heading(
                                            "PDF Generated Successfully!",
                                            size="5",
                                            color="#00A854",
                                        ),
                                        rx.text(
                                            "Your invitation is ready to be shared with your guests",
                                            color="#333333",
                                        ),
                                        # Use a link instead of window_open
                                        rx.link(
                                            "Download PDF",
                                            href=State.download_url,
                                            is_external=True,
                                            style={
                                                "background": "#00A854",
                                                "color": "white",
                                                "padding": "0.75rem 1.5rem",
                                                "border_radius": "0.5rem",
                                                "font_weight": "600",
                                                "cursor": "pointer",
                                                "display": "inline-block",
                                                "text_decoration": "none",
                                                "_hover": {
                                                    "background": "#008C48",
                                                },
                                            },
                                            margin_top="1rem",
                                        ),
                                        align_items="center",
                                        spacing="2",
                                    ),
                                    padding="2rem",
                                    background="#E6F6EE",
                                    border_radius="0.75rem",
                                    border="1px solid #00A854",
                                    margin_bottom="2rem",
                                    width="100%",
                                    text_align="center",
                                ),
                                
                                # Email form
                                rx.heading(
                                    "Send Invitation via Email",
                                    size="5",
                                    margin_bottom="1rem",
                                    color="#000000",
                                ),
                                
                                # Email fields
                                rx.vstack(
                                    # Email subject
                                    rx.box(
                                        rx.text("Email Subject", style=styles["create_form_label"]),
                                        rx.input(
                                            placeholder=f"Invitation to {State.current_event.get('event_name', 'our event')}",
                                            value=State.email_subject,
                                            on_change=State.set_email_subject,
                                            style=styles["create_form_input"],
                                        ),
                                        width="100%",
                                    ),
                                    
                                    # Email addresses
                                    rx.box(
                                        rx.text("Recipient Email Addresses (comma-separated)", style=styles["create_form_label"]),
                                        rx.input(
                                            placeholder="guest1@example.com, guest2@example.com",
                                            value=State.email_addresses,
                                            on_change=State.set_email_addresses,
                                            style=styles["create_form_input"],
                                        ),
                                        width="100%",
                                    ),
                                    
                                    # Two column layout for CC and sender
                                    rx.grid(
                                        # CC addresses
                                        rx.box(
                                            rx.text("CC Addresses (optional)", style=styles["create_form_label"]),
                                            rx.input(
                                                placeholder="cc1@example.com, cc2@example.com",
                                                value=State.cc_addresses,
                                                on_change=State.set_cc_addresses,
                                                style=styles["create_form_input"],
                                            ),
                                        ),
                                        
                                        # Sender name
                                        rx.box(
                                            rx.text("Sender Name", style=styles["create_form_label"]),
                                            rx.input(
                                                placeholder="Your Name",
                                                value=State.sender_name,
                                                on_change=State.set_sender_name,
                                                style=styles["create_form_input"],
                                            ),
                                        ),
                                        
                                        template_columns="repeat(2, 1fr)",
                                        gap="1.5rem",
                                        width="100%",
                                    ),
                                    
                                    # Additional message
                                    rx.box(
                                        rx.text("Additional Message (optional)", style=styles["create_form_label"]),
                                        rx.text_area(
                                            placeholder="Any additional message to include in the email...",
                                            value=State.additional_message,
                                            on_change=State.set_additional_message,
                                            height="100px",
                                            style=styles["create_form_input"],
                                        ),
                                        width="100%",
                                    ),
                                    
                                    # Send email button
                                    rx.button(
                                        rx.cond(
                                            State.is_sending_email,
                                            "Sending Emails...",
                                            "Send Invitation Emails"
                                        ),
                                        on_click=State.send_invitation_emails,
                                        style=styles["create_submit_button"],
                                        disabled=State.is_sending_email,
                                    ),
                                    
                                    # Loading animation for email sending
                                    rx.cond(
                                        State.is_sending_email,
                                        rx.center(
                                            loading_animation(),
                                            margin_top="1.5rem",
                                        ),
                                    ),
                                    
                                    # Email success message
                                    rx.cond(
                                        State.email_success,
                                        rx.box(
                                            rx.hstack(
                                                rx.icon(
                                                    "check_check",  # Corrected icon name
                                                    color="#00A854",
                                                    font_size="1.5rem",
                                                ),
                                                rx.text(
                                                    "Invitation emails sent successfully!",
                                                    color="#00A854",
                                                    font_weight="600",
                                                ),
                                                spacing="2",
                                            ),
                                            padding="1rem",
                                            background="#E6F6EE",
                                            border_radius="0.5rem",
                                            border="1px solid #00A854",
                                            margin_top="1rem",
                                            width="100%",
                                        ),
                                    ),
                                    
                                    # Email error message
                                    rx.cond(
                                        State.email_error != "",
                                        rx.box(
                                            rx.hstack(
                                                rx.icon(
                                                    "triangle_alert",  # Corrected icon name
                                                    color="#FF5252",
                                                    font_size="1.5rem",
                                                ),
                                                rx.text(
                                                    State.email_error,
                                                    color="#FF5252",
                                                    font_weight="600",
                                                ),
                                                spacing="2",
                                            ),
                                            padding="1rem",
                                            background="rgba(255, 82, 82, 0.1)",
                                            border_radius="0.5rem",
                                            border="1px solid #FF5252",
                                            margin_top="1rem",
                                            width="100%",
                                        ),
                                    ),
                                    
                                    align_items="stretch",
                                    width="100%",
                                    spacing="4",
                                ),
                                
                                # Return to event button - use a dedicated method
                                rx.button(
                                    "Return to Event Details",
                                    on_click=State.navigate_back_to_event,
                                    style={
                                        "background": "#FFFFFF",
                                        "color": "#000000",
                                        "border": "2px solid #000000",
                                        "padding": "0.75rem 1.5rem",
                                        "border_radius": "0.5rem",
                                        "font_weight": "600",
                                        "margin_top": "2rem",
                                        "cursor": "pointer",
                                        "_hover": {
                                            "background": "#F5F5F5",
                                        },
                                    },
                                ),
                                
                                align_items="stretch",
                                width="100%",
                                spacing="4",
                            ),
                            padding="2rem",
                            background=rx.cond(
                                State.highlight_email,
                                "#FFFCE6",  # Highlighted background
                                "#FFFFFF",  # Regular background
                            ),
                            border_radius="1rem",
                            border=rx.cond(
                                State.highlight_email,
                                "2px solid #fda8e9",  # Highlighted border
                                "2px solid #E0E0E0",  # Regular border
                            ),
                            box_shadow="0 4px 20px rgba(0, 0, 0, 0.05)",
                            width="100%",
                            id="step3_section",
                        ),
                    ),
                    
                    width="100%",
                    spacing="6",
                    align_items="stretch",
                ),
            ),
            
            # Main content container styling
            max_width="1200px",
            margin="0 auto",
            padding="8rem 2rem 4rem 2rem",  # Top padding for navbar
            min_height="100vh",
        ),
        
        # JavaScript for navbar scrolling only - no custom scrolling functions
        rx.html("""
            <script>
                // Navbar scroll behavior
                let prevScrollpos = window.pageYOffset;
                let navbar = null;
                
                window.addEventListener('DOMContentLoaded', (event) => {
                    navbar = document.querySelector('nav') || document.querySelector('[id="navbar"]') || document.querySelector('header > div:first-child');
                });
                
                window.onscroll = function() {
                    if (!navbar) {
                        navbar = document.querySelector('nav') || document.querySelector('[id="navbar"]') || document.querySelector('header > div:first-child');
                    }
                    
                    if (navbar) {
                        let currentScrollPos = window.pageYOffset;
                        
                        if (prevScrollpos > currentScrollPos || currentScrollPos <= 0) {
                            // Scrolling UP or at the top
                            navbar.style.transform = "translateY(0)";
                            navbar.style.transition = "transform 0.3s ease";
                        } else {
                            // Scrolling DOWN
                            navbar.style.transform = "translateY(-100%)";
                            navbar.style.transition = "transform 0.3s ease";
                        }
                        
                        prevScrollpos = currentScrollPos;
                    }
                };
            </script>
        """),
        
        # Only run initialization methods - no scrolling functions
       on_mount=[State.load_event_details, State.initialize_invitation_form],
        
        # Page background
        background="#FFFDE7",
        min_height="100vh",
        width="100%",
    )


# Add this page to your app

# App configuration
# App configuration
app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap",
        "https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500;1,600;1,700&display=swap",
    ]
)
app.add_page(landing_page, route="/")
app.add_page(dashboard, route="/dashboard")
app.add_page(create_event_page, route="/event/create")
app.add_page(event_detail_page, route="/event/[event_id]")
app.add_page(invitation_page, route="/event/[event_id]/invitation")  # Add this line