"""Add comprehensive ICT Bangladesh course document to knowledge base."""
import requests, sys
sys.stdout.reconfigure(encoding='utf-8')

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjMjZmM2JkYi02Zjc2LTRiNTctYmM0MC03ZDc4ODNjNTgzMjAiLCJyb2xlIjoibWVtYmVyIiwiZW1haWwiOiJpY3RhZG1pbkB0ZXN0LmNvbSIsImV4cCI6MTc3NjU2Nzg3MCwiaWF0IjoxNzc2NTY0MjcwLCJ0eXBlIjoiYWNjZXNzIn0.m-o2knLk-WINEX0159QLNMYJei1_YB6aRIgOxR380Sc"
ORG_ID = "25d58968-0fae-48b6-9898-748534ce86c2"
KB_ID = "f5753f29-300d-4410-b865-e2b670d6bf01"
BASE = "http://localhost:9000"
H = {"Authorization": f"Bearer {TOKEN}"}

content = """ICT Bangladesh - Complete Course Information Guide
====================================================

ABOUT ICT BANGLADESH
--------------------
ICT Bangladesh is a premier technology education institute dedicated to building skilled professionals
for the modern IT industry in Bangladesh. We have trained over 3,800 students across 100+ university
partnerships nationwide.

Website: https://ictbangladesh.com.bd
Phone: +880 9613-820011
Email: info@ictbangladesh.com.bd
Lead Instructor: Israfeel Masum

COURSE 1: AI BASED PROFESSIONAL SOFTWARE ENGINEERING
-----------------------------------------------------
Course URL: https://ictbangladesh.com.bd/course/ai-based-professional-software-engineering
Enrollment Link (click Enroll Now): https://ictbangladesh.com.bd/course/ai-based-professional-software-engineering

Duration: 1 Month
Level: Beginner to Advanced
Price: 10,000 BDT (50% Discount from 20,000 BDT)
Structure: 14 Sections, 70 Lectures

CURRICULUM:
- Python Programming: Variables, OOP, file handling, packages
- C# Programming: OOP concepts, .NET fundamentals
- Database Design & SQL: PostgreSQL, MySQL, normalization, queries
- Software Engineering: SDLC, Agile/Scrum, Git/GitHub, Figma UI/UX
- Mobile App Development: Flutter, Dart, cross-platform (Android & iOS), publishing
- Web Development: React.js, hooks, Redux, REST API integration, Tailwind CSS
- Career Development: Resume/portfolio building, LinkedIn, mock interviews, freelancing
- Final Capstone Project: Full-stack application with database, backend API, and frontend

TARGET CAREERS: Full-Stack Developer, Mobile App Developer, Software Engineer, Backend Developer


COURSE 2: PROFESSIONAL AI ENGINEER
------------------------------------
Course URL: https://ictbangladesh.com.bd/course/professional-ai-engineer
Enrollment Link (click Enroll Now): https://ictbangladesh.com.bd/course/professional-ai-engineer

Duration: 1 Month
Level: Beginner to Advanced
Price: 10,000 BDT (50% Discount from 20,000 BDT)
Structure: 12 Sections

CURRICULUM:
- AI & LLM Architecture: Transformer models, GPT-4, Claude, Llama, tokens, embeddings
- Local AI Setup: Ollama, LMStudio, running Llama/Mistral/Phi locally
- Prompt Engineering: Zero-shot, few-shot, CoT, role prompting, structured outputs
- RAG (Retrieval-Augmented Generation): Document ingestion, chunking, embedding, pipelines
- Vector Databases: FAISS, ChromaDB, Pinecone, Qdrant - indexing and search
- Vision AI & OCR: LLaVA, CLIP, Tesseract, document processing, multimodal AI
- AI Automation: n8n, Make (Integromat), Zapier - automated AI workflows
- Autonomous AI Agents: LangChain, CrewAI, tool calling, multi-agent systems
- Cloud AI Deployment: AWS SageMaker/Bedrock, Google Vertex AI, Docker, Kubernetes
- AI Application Development: FastAPI chatbots, streaming SSE, production monitoring
- Final AI Capstone: End-to-end RAG chatbot deployed to cloud

TARGET CAREERS: AI/ML Engineer, Prompt Engineer, AI Solutions Architect, RAG Developer,
AI Automation Specialist, LLM Application Developer


ENROLLMENT PROCESS
------------------
1. Visit the course page
2. Click the "Enroll Now" button
3. Fill in the registration form with your name, phone, and email
4. Complete payment: 10,000 BDT
5. Receive enrollment confirmation
6. Get access to course materials and schedule

For enrollment help:
- Phone: +880 9613-820011
- Email: info@ictbangladesh.com.bd
- Website: https://ictbangladesh.com.bd


KEY FACTS SUMMARY
-----------------
- Both courses: 1 month duration, beginner to advanced
- Both courses: 10,000 BDT (50% off from 20,000 BDT)
- No prior experience required
- Professional certificate upon completion
- 3,800+ students trained, 100+ university partners
- Instructor: Israfeel Masum
- Contact: +880 9613-820011 | info@ictbangladesh.com.bd
"""

resp = requests.post(
    f"{BASE}/api/v1/organizations/{ORG_ID}/knowledge-bases/{KB_ID}/documents/manual",
    headers=H,
    data={"title": "ICT Bangladesh Complete Course Guide", "content": content}
)
print("Status:", resp.status_code)
d = resp.json()
print("Doc ID:", d.get("id"), "| Status:", d.get("status"), "| Chunks:", d.get("chunk_count"))
if resp.status_code not in (200, 201):
    print("Error:", d)
