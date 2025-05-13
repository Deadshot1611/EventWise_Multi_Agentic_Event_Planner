# AI_Event_Planner/components/navbar.py
import reflex as rx
from AI_Event_Planner.state import AuthState

# Color scheme (matching your landing page style)
COLORS = {
    "background": "#FFFDE7",
    "primary": "#000000",
    "secondary": "#555555",
    "accent": "#2D2D2D",
    "nav_bg": "#fce28f",  # Navbar background color from your landing page
    "button_bg": "#000000",
    "button_hover": "#333333",
}

# Define styles
navbar_styles = {
    "nav": {
        "display": "flex",
        "background": COLORS["nav_bg"],
        "align_items": "center",
        "justify_content": "space_between",
        "padding": "1.5rem 2rem",
        "border_bottom": f"1px solid {COLORS['primary']}",
        "position": "fixed",
        "top": "0",
        "left": "0",
        "right": "0",
        "z_index": "1000",
        "width": "100%",
    },
    "nav_brand": {
        "font_weight": "bold",
        "font_size": ["1rem", "1.8rem", "2.5rem"],
        "color": COLORS["primary"],
        "cursor": "pointer",
    },
    "nav_links": {
        "display": "flex",
        "gap": "1.5rem",
        "align_items": "center",
    },
    "btn_primary": {
        "padding": ["0.5rem 0.75rem", "0.75rem 1rem", "0.75rem 1.5rem"],
        "border_radius": "0.35rem",
        "border": "2px solid transparent",
        "background": COLORS["button_bg"],
        "color": "white",
        "cursor": "pointer",
        "font_weight": "600",
        "font_size": ["0.9rem", "1rem", "1.1rem"],
        "transition": "all 0.3s ease",
        "_hover": {
            "background": "#fda8e9",
            "color": "#000000",
            "border": "2px solid #000000",
            "transform": "translateY(-2px)",
            "box_shadow": "0 5px 15px rgba(0, 0, 0, 0.1)",
        },
    },
    "btn_secondary": {
        "padding": ["0.5rem 0.75rem", "0.75rem 1rem", "0.75rem 1.5rem"],
        "border_radius": "0.0rem",
        "border": f"2px solid {COLORS['button_bg']}",
        "background": "transparent",
        "color": COLORS["primary"],
        "cursor": "pointer",
        "font_weight": "600",
        "font_size": ["0.9rem", "1rem", "1.1rem"],
        "transition": "all 0.3s ease",
        "_hover": {
            "background": COLORS["primary"],
            "color": "white",
            "transform": "translateY(-2px)",
            "box_shadow": "0 5px 15px rgba(0, 0, 0, 0.1)",
        },
    },
    "user_name": {
        "font_weight": "500",
        "color": COLORS["primary"],
        "margin_right": "1rem",
    }
}

def navbar():
    """Navigation bar component."""
    return rx.box(
        rx.flex(
            # Left side - Brand
            rx.heading(
                "EventWise", 
                style=navbar_styles["nav_brand"],
                on_click=lambda: rx.redirect("/"),
            ),
            
            # Right side - Conditional based on auth state
            rx.cond(
                AuthState.is_authenticated,
                # If authenticated - show user name and logout
                rx.hstack(
                    rx.text(
                        rx.cond(
                            AuthState.user_name != "",
                            rx.fragment(f"Hello, ", AuthState.user_name),
                            "Hello, User",
                        ),
                        style=navbar_styles["user_name"],
                    ),
                    rx.button(
                        "Logout",
                        style=navbar_styles["btn_secondary"],
                        on_click=AuthState.logout,
                    ),
                    margin_left="auto",  # Push to the right
                    spacing="4",
                ),
                # If not authenticated - show login/register buttons
                rx.hstack(
                    rx.button(
                        "Login",
                        style=navbar_styles["btn_secondary"],
                        on_click=lambda: rx.redirect("/auth"),
                    ),
                    rx.button(
                        "Get started",
                        style=navbar_styles["btn_primary"],
                        on_click=lambda: rx.redirect("/auth?register=true"),
                    ),
                    margin_left="auto",  # Push to the right
                    spacing="4",
                ),
            ),
            width="100%",
        ),
        style=navbar_styles["nav"],
    )