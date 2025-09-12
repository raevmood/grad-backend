# EventHub AI Operations

This document describes all **AI-driven components** of the EventHub platform, their architecture, and operational flow. The system integrates **semantic search, generative AI assistants, a multi-vector database setup, MCP-based cross-VM communication, and no-code AI agents** for automation.

---

## System Structure
![alt text](<EventHub AI System Flow.png>)

## 🏗️ System Overview

EventHub AI operates across **two VMs** and **n8n Cloud**:

- **VM1: Event Search & Creation**
  - Semantic search with RAG pipeline
  - Vector database for event data (ChromaDB)
  - Event content generation (titles, tags, descriptions)

- **VM2: Assistance & Automation**
  - AI chatbot with dual vector access (Help/Guidelines DB + Event DB via MCP)
  - No-code AI agents for email RSVP/reminders
  - AI moderation assistance for event risk assessment

- **n8n Cloud**
  - Hosts automation flows triggered by events (RSVP notifications, reminders, moderation pipelines)
  - Provides header-authenticated webhook endpoints for communication

---

## 📖 Components

### 1. Semantic Search (VM1)

- **Purpose**: Provide users with natural-language event discovery.
- **Pipeline**:
  1. User query → pre-processed for filters (location, free/paid, category, dates).
  2. Query embedding generated with `SentenceTransformer(all-MiniLM-L6-v2)`.
  3. Embedding compared against event vectors stored in **ChromaDB**.
  4. Top-N results filtered by similarity threshold and returned.
- **Database**: ChromaDB with persistent storage.
- **Population**:
  - Events fetched from API or fallback sample dataset.
  - Stored as global vectors with metadata (`title`, `location`, `startDateTime`, `isFree`, `tags`, etc.).
- **Endpoints**:
  - `POST /search` → Perform semantic search.
  - `POST /refresh-embeddings` → Refresh stored vectors.
  - Background thread auto-refreshes embeddings every 30 minutes.

---

### 2. Event Content Generation (VM1)

- **Purpose**: Assist event creators with high-quality metadata.
- **Pipeline**:
  1. User submits a draft event description/title.
  2. **EventContentCrew** (CrewAI agent) generates:
     - Optimized event **title**
     - Relevant **tags**
     - Expanded **description**
  3. Returned to user as structured proposals.
- **Endpoint**:
  - `POST /generate-event` → Returns AI-proposed event content.

---

### 3. AI Chatbot (VM2)

- **Purpose**: Provide interactive support and knowledge access.
- **Features**:
  - Answers FAQs from **Help/Guidelines vector DB** (local).
  - Provides contextual event recommendations via **MCP connection** to the event vector DB (VM1).
- **Architecture**:
  - Built on `langchain` + LLM (Gemini/Groq).
  - Integrated into frontend via simple chatbot UI.
  - Uses **DualRAGRetriever** to query:
    - **Help DB** (local ChromaDB)
    - **Event DB** (remote via MCP client)
- **Flow**:
  1. User asks question.
  2. Query routed to appropriate retriever(s).
  3. Results formatted into LLM context.
  4. AI response streamed to user.

---

### 4. MCP Cross-VM Bridge (VM1 ↔ VM2)

- **Purpose**: Allow VM2 chatbot to access event embeddings on VM1.
- **Implementation**:
  - **MCP Server (VM1)**: Wraps event search functions (`perform_search`, `get_all_events`).
  - **MCP Client (VM2)**: Subprocess JSON-RPC communication with server.
  - Requests like `tools/call` are routed, responses returned as JSON.
- **Error Handling**:
  - Startup initializes embeddings automatically.
  - JSON-RPC responses wrapped with error handling to avoid crashes.
- **Benefit**: Decouples responsibilities while maintaining real-time access.

---

### 5. No-Code AI Agents (VM2 + n8n Cloud)

#### 📩 Email RSVP Notifications & Reminders
- Managed in **n8n Cloud** via webhook-triggered flows.
- AI agents handle:
  - Personalized RSVP confirmation emails.
  - Scheduled reminder emails prior to event start.
- Integrated with event metadata and user RSVP data.

#### 🛡️ Moderation & Risk Assessment
- Automated risk assessment pipeline:
  - AI agent analyzes created events for spam, scam, and unsafe content.
  - Flags suspicious events for review.
  - Runs in **n8n Cloud**, triggered on new event creation.

---

## ⚙️ Deployment & Operations

### VM1 (Search + Event Creation)
- Runs `FastAPI` app (`app.py`).
- Hosts:
  - `/search`, `/generate-event`, `/refresh-embeddings`
  - MCP server (`mcp_event_server.py`)
- Vector DB stored in `./chroma_db`.

### VM2 (Chatbot + Agents)
- Runs chatbot service with:
  - LangChain retrievers
  - MCP client (`mcp_client.py`)
  - Chat UI integration
- Connects to n8n Cloud agents for automation.

### n8n Cloud
- Hosts:
  - RSVP automation flows
  - Reminder flows
  - Moderation pipeline
- Secured with header authentication.

---

### Multi-LLM integration

The system uses multiple large language models to balance accuracy, creativity, and efficiency. LangChain acts as the orchestration layer between the models, routing requests depending on task type.

1. Google Generative AI is used for natural language understanding, semantic search queries, and event title, description, and tag generation. Its strengths in contextual coherence and structured output make it ideal for search indexing and event metadata creation.

2. Groq is used for high-speed, low-latency inference tasks. It powers real-time chatbot responses and moderation analysis, where speed and throughput are more important than long-form creativity.

3. Hugging Face integration provides model hosting and vector database access. Embeddings stored in ChromaDB are generated and retrieved through the Hugging Face pipeline, ensuring events and help documents are consistently represented across both VMs.

This design ensures that no single LLM is overloaded and each is applied where its strengths are most relevant. The assistant VM dynamically selects the correct model path via LangChain, while the event VM consistently defaults to Google Generative AI for content creation and retrieval.


## 🔒 Security

- **Cross-VM communication**: MCP only exposes limited event retrieval/search functions.
- **n8n Cloud webhooks**: Protected via header-based authentication.
- **CORS**: Enabled for frontend integration.

---

## 📌 Summary of AI Responsibilities

| Component                | AI Role                                        | Location |
|---------------------------|-----------------------------------------------|----------|
| Semantic Event Search     | Embedding + vector retrieval (RAG)            | VM1      |
| Event Content Generation  | LLM-assisted title, tags, description          | VM1      |
| AI Chatbot                | Dual-RAG assistant (Help DB + Event DB via MCP)| VM2      |
| MCP Bridge                | Secure cross-VM event data access              | VM1↔VM2  |
| RSVP Emails & Reminders   | No-code agent automation (n8n Cloud)           | VM2+n8n  |
| Event Moderation          | AI risk assessment (scam/spam/safety)          | VM2+n8n  |

---

## How to Run the App

The system is deployed across two VMs and integrates with Hugging Face Spaces, n8n Cloud, and LangChain-based AI services. Before running, ensure you have Python 3.10+, Docker, and Git installed.

# Step 1: Clone the repository
git clone https://huggingface.co/spaces/Sench729/EventHub
cd EventHub

# Step 2: Install dependencies
pip install -r requirements.txt

# Step 3: Start the Event VM (Semantic Search + Event AI Creation)
This VM handles semantic search, the vector database of event data, and AI generation of event titles, tags, and descriptions.
python app.py

# Step 4: Start the Assistant VM (Chatbot + MCP Integration + Agents)
This VM hosts the AI chatbot, MCP client to the event vector DB, and the no code automation agents.
python chatbot.py
python mcp_server.py

# Step 5: Connect MCP Client to Remote Event VM
The chatbot VM connects via MCP to the event semantic search VM. Ensure the event VM is running before launching the chatbot.

# Step 6: Running with Docker
Each VM can also be containerized:
docker build -t eventhub-event-vm -f Dockerfile.event .
docker build -t eventhub-assistant-vm -f Dockerfile.assistant .
docker run -p 8000:8000 eventhub-event-vm
docker run -p 8080:8080 eventhub-assistant-vm

# Step 7: Configure API Keys
Set environment variables for Google Generative AI, Groq, and Hugging Face authentication before starting the services:
export GOOGLE_API_KEY=your_key
export GROQ_API_KEY=your_key
export HF_TOKEN=your_key

# Step 8: Integrate n8n Agents
The RSVP email notification and event moderation agents run on n8n Cloud. Configure the webhook URLs in the chatbot configuration files to connect to n8n.

# Step 9: Access the Services
Semantic search and event creation AI run on the event VM (default port 8000). The chatbot and MCP tools run on the assistant VM (default port 8080). Webhooks from n8n will send email notifications and risk analysis results directly to these services.

# Step 10: Testing
Run the provided test scripts to confirm connectivity and responses:
python test_retriever.py
python mcp_client.py
