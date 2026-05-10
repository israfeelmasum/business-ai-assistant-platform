"""Seed ICT Bangladesh knowledge base with Q&A pairs."""
import requests, json

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjMjZmM2JkYi02Zjc2LTRiNTctYmM0MC03ZDc4ODNjNTgzMjAiLCJyb2xlIjoibWVtYmVyIiwiZW1haWwiOiJpY3RhZG1pbkB0ZXN0LmNvbSIsImV4cCI6MTc3NjU2Nzg3MCwiaWF0IjoxNzc2NTY0MjcwLCJ0eXBlIjoiYWNjZXNzIn0.m-o2knLk-WINEX0159QLNMYJei1_YB6aRIgOxR380Sc"
ORG_ID = "25d58968-0fae-48b6-9898-748534ce86c2"
KB_ID = "f5753f29-300d-4410-b865-e2b670d6bf01"
BASE = "http://localhost:9000"
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

qa_pairs = [
    {
        "question": "What courses does ICT Bangladesh offer?",
        "answer": (
            "ICT Bangladesh offers two flagship courses:\n\n"
            "1. **AI Based Professional Software Engineering** - Learn Python/C#, databases, "
            "web/mobile development with React & Flutter, and software engineering best practices. "
            "14 sections, 70 lectures.\n"
            "   Enroll: https://ictbangladesh.com.bd/course/ai-based-professional-software-engineering\n\n"
            "2. **Professional AI Engineer** - Master AI architecture, LLMs, prompt engineering, "
            "RAG systems, vector databases, vision AI, automation, and cloud deployment. 12 sections.\n"
            "   Enroll: https://ictbangladesh.com.bd/course/professional-ai-engineer\n\n"
            "Both courses are 1 month duration, beginner to advanced level, priced at 10,000 BDT "
            "(50% off from 20,000 BDT)."
        ),
        "tags": ["courses", "overview"]
    },
    {
        "question": "How can I enroll in ICT Bangladesh?",
        "answer": (
            "You can enroll in our courses directly from our website:\n\n"
            "**AI Based Professional Software Engineering:**\n"
            "https://ictbangladesh.com.bd/course/ai-based-professional-software-engineering\n"
            "Click the \"Enroll Now\" button on the course page.\n\n"
            "**Professional AI Engineer:**\n"
            "https://ictbangladesh.com.bd/course/professional-ai-engineer\n"
            "Click the \"Enroll Now\" button on the course page.\n\n"
            "For assistance with enrollment, you can also:\n"
            "- Call us: +880 9613-820011\n"
            "- Email: info@ictbangladesh.com.bd\n"
            "- Visit: https://ictbangladesh.com.bd"
        ),
        "tags": ["enrollment", "how-to-join", "registration"]
    },
    {
        "question": "What is the course fee / price?",
        "answer": (
            "Both courses are currently offered at a special 50% discount:\n\n"
            "- Regular Price: 20,000 BDT\n"
            "- **Current Price: 10,000 BDT** (50% OFF)\n\n"
            "This applies to both:\n"
            "1. AI Based Professional Software Engineering\n"
            "2. Professional AI Engineer\n\n"
            "For payment details and options, contact us at +880 9613-820011 or info@ictbangladesh.com.bd."
        ),
        "tags": ["price", "fee", "cost", "discount"]
    },
    {
        "question": "How long are the courses?",
        "answer": (
            "Both courses at ICT Bangladesh are **1 month** in duration.\n\n"
            "- AI Based Professional Software Engineering: 1 Month (14 sections, 70 lectures, beginner to advanced)\n"
            "- Professional AI Engineer: 1 Month (12 sections, beginner to advanced)\n\n"
            "The courses are designed to be intensive, covering everything from fundamentals to "
            "advanced topics in just one month."
        ),
        "tags": ["duration", "time", "schedule", "how-long"]
    },
    {
        "question": "What is the AI Based Professional Software Engineering course about?",
        "answer": (
            "The AI Based Professional Software Engineering course is a comprehensive 1-month program:\n\n"
            "**Course Details:**\n"
            "- Duration: 1 Month | Level: Beginner to Advanced\n"
            "- Price: 10,000 BDT (50% off from 20,000 BDT)\n"
            "- Structure: 14 Sections, 70 Lectures\n\n"
            "**Curriculum:**\n"
            "1. Python & C# Object-Oriented Programming\n"
            "2. Database Design & SQL (PostgreSQL, MySQL)\n"
            "3. Software Engineering: SDLC, Agile, Git/GitHub, Figma UI/UX\n"
            "4. Mobile App Development with Flutter\n"
            "5. Web Development with React\n"
            "6. Career guidance, portfolio building, interview preparation\n"
            "7. Final Capstone Project\n\n"
            "**Enroll Now:** https://ictbangladesh.com.bd/course/ai-based-professional-software-engineering"
        ),
        "tags": ["software-engineering", "course-details", "curriculum"]
    },
    {
        "question": "What is the Professional AI Engineer course about?",
        "answer": (
            "The Professional AI Engineer course is a comprehensive 1-month AI specialization:\n\n"
            "**Course Details:**\n"
            "- Duration: 1 Month | Level: Beginner to Advanced\n"
            "- Price: 10,000 BDT (50% off from 20,000 BDT)\n"
            "- Structure: 12 Sections\n\n"
            "**Curriculum:**\n"
            "1. AI & Large Language Model (LLM) Architecture\n"
            "2. Local AI setup with Ollama and LMStudio\n"
            "3. Advanced Prompt Engineering techniques\n"
            "4. RAG (Retrieval-Augmented Generation) systems\n"
            "5. Vector Databases: FAISS, ChromaDB, Pinecone\n"
            "6. Vision AI and OCR for image/document processing\n"
            "7. AI Automation with n8n, Make, Zapier\n"
            "8. Building Autonomous AI Agents\n"
            "9. Cloud AI Deployment on AWS & GCP\n"
            "10. Final AI Capstone Project\n\n"
            "**Enroll Now:** https://ictbangladesh.com.bd/course/professional-ai-engineer"
        ),
        "tags": ["ai-engineer", "course-details", "curriculum", "llm", "rag"]
    },
    {
        "question": "Who is the instructor at ICT Bangladesh?",
        "answer": (
            "ICT Bangladesh courses are taught by **Israfeel Masum**, an expert in AI engineering "
            "and software development. With extensive experience in modern technology stacks, he brings "
            "both theoretical knowledge and practical industry experience to the curriculum.\n\n"
            "ICT Bangladesh has trained 3,800+ students with partnerships spanning 100+ universities "
            "across Bangladesh."
        ),
        "tags": ["instructor", "teacher", "trainer", "israfeel"]
    },
    {
        "question": "What is ICT Bangladesh?",
        "answer": (
            "ICT Bangladesh (ictbangladesh.com.bd) is a leading technology education institute in "
            "Bangladesh focused on preparing professionals for the modern tech industry.\n\n"
            "**Key Facts:**\n"
            "- 3,800+ students trained\n"
            "- 100+ university partnerships across Bangladesh\n"
            "- Instructor: Israfeel Masum\n"
            "- Focus: AI, Software Engineering, and emerging technologies\n\n"
            "**Contact:**\n"
            "- Phone: +880 9613-820011\n"
            "- Email: info@ictbangladesh.com.bd\n"
            "- Website: https://ictbangladesh.com.bd"
        ),
        "tags": ["about", "ict-bangladesh", "organization", "overview"]
    },
    {
        "question": "How do I contact ICT Bangladesh?",
        "answer": (
            "You can reach ICT Bangladesh through the following channels:\n\n"
            "- **Phone:** +880 9613-820011\n"
            "- **Email:** info@ictbangladesh.com.bd\n"
            "- **Website:** https://ictbangladesh.com.bd\n\n"
            "Our team is available to help you with course enrollment, payment, scheduling, "
            "and any other questions."
        ),
        "tags": ["contact", "phone", "email", "reach-us"]
    },
    {
        "question": "Which course should I choose - Software Engineering or AI Engineer?",
        "answer": (
            "Both courses are designed for **beginners to advanced** learners!\n\n"
            "**Choose AI Based Professional Software Engineering if you:**\n"
            "- Want to become a full-stack developer\n"
            "- Are interested in building web and mobile applications\n"
            "- Plan to work as a developer or software engineer\n\n"
            "**Choose Professional AI Engineer if you:**\n"
            "- Are fascinated by artificial intelligence\n"
            "- Want to build AI-powered applications and chatbots\n"
            "- Are interested in automation and intelligent systems\n\n"
            "**Many students take both courses** to become well-rounded tech professionals. "
            "Both are 1 month and 10,000 BDT each.\n\n"
            "For personalized advice: +880 9613-820011 or info@ictbangladesh.com.bd"
        ),
        "tags": ["comparison", "which-course", "recommendation", "beginners"]
    },
    {
        "question": "Is there a certificate after completing the course?",
        "answer": (
            "Yes! Upon successful completion of ICT Bangladesh courses, students receive a "
            "**professional certificate** that validates their skills.\n\n"
            "For detailed information about certification:\n"
            "- Call: +880 9613-820011\n"
            "- Email: info@ictbangladesh.com.bd\n"
            "- Visit: https://ictbangladesh.com.bd"
        ),
        "tags": ["certificate", "certification", "completion"]
    },
    {
        "question": "Can I learn online or is it in-person?",
        "answer": (
            "For the most current information about our learning format (online, in-person, or hybrid), "
            "please contact ICT Bangladesh directly:\n\n"
            "- **Phone:** +880 9613-820011\n"
            "- **Email:** info@ictbangladesh.com.bd\n"
            "- **Website:** https://ictbangladesh.com.bd\n\n"
            "Our team will provide you with the latest schedule and mode of delivery options."
        ),
        "tags": ["online", "offline", "in-person", "format"]
    },
    {
        "question": "আমি কিভাবে ভর্তি হতে পারি?",
        "answer": (
            "ICT Bangladesh-এ ভর্তি হওয়া খুবই সহজ!\n\n"
            "**AI Based Professional Software Engineering কোর্সে ভর্তি:**\n"
            "https://ictbangladesh.com.bd/course/ai-based-professional-software-engineering\n"
            "\"Enroll Now\" বাটনে ক্লিক করুন।\n\n"
            "**Professional AI Engineer কোর্সে ভর্তি:**\n"
            "https://ictbangladesh.com.bd/course/professional-ai-engineer\n"
            "\"Enroll Now\" বাটনে ক্লিক করুন।\n\n"
            "**সাহায্যের জন্য যোগাযোগ:**\n"
            "- ফোন: +880 9613-820011\n"
            "- ইমেইল: info@ictbangladesh.com.bd\n\n"
            "উভয় কোর্সের মূল্য মাত্র ১০,০০০ টাকা (৫০% ছাড়ে)।"
        ),
        "tags": ["enrollment", "bangla", "registration"]
    },
    {
        "question": "কোর্স ফি কত?",
        "answer": (
            "ICT Bangladesh-এর কোর্স ফি:\n\n"
            "- নিয়মিত মূল্য: ২০,০০০ টাকা\n"
            "- **বর্তমান মূল্য: ১০,০০০ টাকা** (৫০% ছাড়)\n\n"
            "এই মূল্য উভয় কোর্সের জন্য প্রযোজ্য:\n"
            "1. AI Based Professional Software Engineering\n"
            "2. Professional AI Engineer\n\n"
            "পেমেন্ট সম্পর্কে বিস্তারিত জানতে: +880 9613-820011"
        ),
        "tags": ["price", "fee", "bangla"]
    },
    {
        "question": "What career opportunities will I get after completing the course?",
        "answer": (
            "Graduates of ICT Bangladesh courses are prepared for high-demand technology careers:\n\n"
            "**After AI Based Professional Software Engineering:**\n"
            "- Junior/Senior Software Developer\n"
            "- Full-Stack Web Developer\n"
            "- Mobile App Developer (Flutter/React Native)\n"
            "- Backend Engineer (Python/Node.js)\n"
            "- UI/UX Developer\n\n"
            "**After Professional AI Engineer:**\n"
            "- AI/ML Engineer\n"
            "- Prompt Engineer\n"
            "- AI Solutions Architect\n"
            "- RAG Systems Developer\n"
            "- AI Automation Specialist\n"
            "- LLM Application Developer\n\n"
            "With 3,800+ students trained, ICT Bangladesh has an established network to help "
            "graduates connect with employers.\n\n"
            "For more career guidance: +880 9613-820011 | info@ictbangladesh.com.bd"
        ),
        "tags": ["career", "jobs", "opportunities", "after-course"]
    },
    {
        "question": "What is RAG and will I learn it in the AI course?",
        "answer": (
            "**RAG (Retrieval-Augmented Generation)** is a powerful AI technique that combines "
            "large language models with a knowledge base to provide accurate, context-aware answers. "
            "It is widely used in building intelligent chatbots, document Q&A systems, and enterprise AI.\n\n"
            "Yes! The **Professional AI Engineer** course at ICT Bangladesh includes a dedicated "
            "section on RAG systems, covering:\n"
            "- Building RAG pipelines from scratch\n"
            "- Vector databases (FAISS, ChromaDB, Pinecone)\n"
            "- Embedding models and similarity search\n"
            "- Production RAG deployment\n\n"
            "Enroll: https://ictbangladesh.com.bd/course/professional-ai-engineer"
        ),
        "tags": ["rag", "ai", "technical", "vector-db"]
    },
    {
        "question": "Do I need prior programming experience to join?",
        "answer": (
            "No prior programming experience is required! Both ICT Bangladesh courses are designed "
            "for **beginners to advanced** learners.\n\n"
            "The courses start from the fundamentals and progressively build to advanced topics, "
            "so complete beginners are welcome.\n\n"
            "If you already have some experience, the advanced sections will still provide "
            "valuable, up-to-date industry skills.\n\n"
            "For more information:\n"
            "- Call: +880 9613-820011\n"
            "- Email: info@ictbangladesh.com.bd\n"
            "- Enroll: https://ictbangladesh.com.bd"
        ),
        "tags": ["prerequisites", "beginner", "requirements", "experience"]
    }
]

success = 0
for qa in qa_pairs:
    resp = requests.post(
        f"{BASE}/api/v1/organizations/{ORG_ID}/knowledge-bases/{KB_ID}/qa-pairs",
        headers=H,
        json=qa
    )
    if resp.status_code in (200, 201):
        success += 1
        print(f"  OK [{success}] {qa['question'][:65]}")
    else:
        print(f"  FAIL ({resp.status_code}): {qa['question'][:65]}")
        print("    Error:", resp.text[:200])

print(f"\nCreated {success}/{len(qa_pairs)} QA pairs successfully")
