# 🎯 Event Wise – AI-Driven Automated Event Planning System

**Event Wise** is a multi-agent AI-powered platform that streamlines event planning by automating the entire process—from understanding user needs to finding the perfect venue and coordinating vendor services. Built using CrewAI, Mistral LLMs, and smart scraping/search tools, Event Wise delivers intelligent, real-time event planning with minimal human intervention.

---

## 🚀 Key Features

### 🤖 Multi-Agent Workflow (CrewAI)
Event Wise is built on a modular CrewAI architecture, where each agent has a specific responsibility:

- **Event Intake Agent** – Captures event details (type, date, location, preferences).
- **Requirements Analyzer Agent** – Parses user input to extract structured event requirements.
- **Budget Allocation Agent** – Distributes the total budget across key services like venue, catering, decor, etc.
- **Venue Search Agent** – Uses web search, scraping, and validation tools to find matching venues.
- **Service Search Agents** – Locates caterers, decorators, photographers, and more, tailored to event needs.
- **Negotiation Agent** – Initiates negotiation via email, WhatsApp, or calls for better pricing and availability.
- **Booking & Confirmation Agent** – Confirms bookings with venues/vendors and generates receipts or summaries.
- **Chat & Memory Agent** – Maintains conversation history, tracks user preferences, and supports follow-up actions.

---

## 🛠️ Tech Stack

- **LLMs**: Mistral Large (via API) for function calling and structured output generation
- **Agent Framework**: [CrewAI](https://github.com/joaomdmoura/crewAI)
- **Search & Scraping**:
  - Google + Serper.dev for intelligent search
  - Trafilatura for HTML-to-text content extraction
  - Selenium for interactive scraping (e.g., JustDial, VenueLook)
- **Backend**: Python with Pydantic v2 for schema validation
- **Frontend (Optional)**: Streamlit or custom UI for interaction and venue selection
- **Orchestration**: Centralized LLM orchestrator chatbot for managing user input and delegating tasks

---

## 🧠 Core Capabilities

- **Dynamic Budget Allocation** – No hardcoded logic; the system intelligently assigns budgets based on event type, guest count, and user intent.
- **Smart Venue Discovery** – Combines search, scraping, and multi-stage validation to find high-quality venue options with real phone numbers, addresses, prices, and source URLs.
- **Universal Vendor Search** – Can search across any event service (e.g., catering, photography) using structured queries and real-time web data.
- **Relevance Ranking** – Venue and vendor suggestions are ranked by availability, rating, match with user needs, and price fit.
- **User-Centric Interaction** – The LLM chatbot handles follow-ups, comparisons, re-querying, and personalized decision support.
- **Memory Management** – Avoids repeating venues and services already shown; tracks selections and preferences throughout the conversation.

---

## 📦 Example Use Case

> **User Flow:** The user fills out a form specifying event details.

**Form Input:**
- **Event Type**: Birthday Party  
- **Location**: Kolkata  
- **Guest Count**: 50  
- **Budget**: ₹80,000  

---

**Event Wise** responds by:

1. **Parsing the Form Input** – Automatically extracts structured data from the submitted form (event type, location, guest count, budget).
2. **Smart Budget Allocation** – Intelligently divides the total budget (e.g., ₹40,000 for venue, ₹30,000 for catering, ₹10,000 for decor), tailored to the event type.
3. **Venue Discovery** – Uses Google and JustDial to search for suitable banquet halls in Kolkata, matching the budget and guest count.
4. **Data Extraction & Validation** – Collects structured details for each venue, including:
   - Name, address, verified phone number  
   - Price estimate, rating, images (if available)  
   - Booking source URL  
5. **Interactive Response** – Displays top 3–5 venue options to the user in a clear, actionable format.
6. **Follow-up Prompt** – The chatbot asks:  
   > "Would you like to book one of these venues, see more options, or compare details?"
7. **Service Provider Matching** – Repeats the same process for vendors like caterers, decorators, and photographers.
8. **Negotiation & Booking** – Initiates vendor negotiations if requested and confirms bookings on the user’s behalf.

---



## 🧩 Roadmap

- [x] Venue discovery with validation and fallback
- [x] Budget-aware multi-service search
- [x] Centralized chatbot orchestrator
- [ ] WhatsApp/email-based Negotiation Agent
- [ ] Invite generator and guest RSVP management
- [ ] User dashboard to track selected venues/services

---
## 👤 Author
Event Wise was created by Amritanshu Lairi as an intelligent automation project to revolutionize how people plan events.

