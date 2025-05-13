import os
import re
import json
import time
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import uuid
from datetime import datetime
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
from dotenv import load_dotenv
import requests
import random
import io
# Additional imports for invitation functionality

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

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

# ---------------------- Main Execution ----------------------
def main():
    """
    Main function to run the invitation flow with predefined values
    """
    try:
        print("Welcome to the Event Invitation Creator!")
        
        # Predefined event details
        event_details = {
            "event_name": "Disha",
            "event_type": "birthday party",
            "event_date": "01/09/2025",
            "num_guests": 30,
            "budget": 30000,
            "location": "Kolkata",
            "venue_name": "Rainbow Garden",  # Sample venue name
            "venue_address": "25 Park Street, Kolkata"  # Sample venue address
        }
        
        # Create invitation
        invitation_result = create_invitation(event_details)
        
        if invitation_result:
            print("\n=== Invitation Process Complete ===")
            print(f"Invitation PDF saved to: {invitation_result['pdf_path']}")
            print(f"Download URL: {invitation_result['download_url']}")
            print("\nThank you for using the Event Invitation Creator!")
        
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        import traceback
        print(traceback.format_exc())
        print("\nPlease try again or contact support.")

if __name__ == "__main__":
    main()