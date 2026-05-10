"""Chat orchestration service - the main chatbot brain."""

import uuid
import logging
import re
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.client import Client
from app.models.conversation import Conversation
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.entity_type_repository import EntityTypeRepository
from app.repositories.ai_knowledge_repository import AIKnowledgeRepository
from app.schemas.conversation import ChatRequest, ChatResponse
from app.core.ai_client import ai_client
from app.core.exceptions import AIProviderError
from app.config import get_settings
from app.services.email_service import email_service

logger = logging.getLogger(__name__)
settings = get_settings()

class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.type_repo = EntityTypeRepository(db)
        self.knowledge_repo = AIKnowledgeRepository(db)

    async def handle_message_stream(self, client: Client, request: ChatRequest):
        conversation = await self._get_or_create_conversation(client, request)

       # 1. 🚀 LAISA'S FIX: Tri-Party Chat Logic (Silence the bot, let humans talk!)
        if conversation.status == "human_escalated":
            now = datetime.now(timezone.utc).isoformat()
            
            # Save ONLY the user's message to DB (Bot stays completely silent)
            updated_messages = conversation.messages + [
                {"role": "user", "content": request.message, "timestamp": now}
            ]
            # Trim old messages to prevent unbounded growth
            if len(updated_messages) > settings.MAX_CONVERSATION_MESSAGES:
                updated_messages = updated_messages[-settings.MAX_CONVERSATION_MESSAGES:]

            await self.conversation_repo.db.execute(
                __import__('sqlalchemy').update(Conversation)
                .where(Conversation.id == conversation.id)
                .values(messages=updated_messages)
            )
            await self.conversation_repo.db.commit()
            
            # Yield nothing (Empty stream) so frontend knows the bot is quiet
            yield "data: [DONE]\n\n"
            return

        # =====================================================================
        # 🚀 ASYNC IMAGE PROCESSING (USER GETS INSTANT REPLY, EMAIL KEEPS FORMAT)
        # =====================================================================
        image_base64 = getattr(request, 'image_base64', None)
        
        if image_base64:
            import json
            import asyncio
            
            order_id = f"ICT-{uuid.uuid4().hex[:6].upper()}"
            
            # 🌍 Multilingual instant reply based on user's recent input
            is_bengali = False
            if conversation.messages:
                last_user_msg = next((m['content'] for m in reversed(conversation.messages) if m['role'] == 'user'), "")
                if any(char in last_user_msg for char in "অআইঈউঊঋঌএঐওঔকখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহড়ঢ়য়ৎংঃঁ"):
                    is_bengali = True
            
            if is_bengali:
                success_msg = f"✅ আপনার পেমেন্ট রিসিটটি আমরা পেয়েছি! Order ID: {order_id}. খুব শীঘ্রই আমাদের সাপোর্ট টিম যোগাযোগ করবে।"
            else:
                success_msg = f"✅ We have received your payment receipt! Order ID: {order_id}. Our support team will verify and contact you shortly."
            
            # 1. INSTANT UI RESPONSE
            yield f"data: {json.dumps({'content': success_msg})}\n\n"
            yield "data: [DONE]\n\n"
            
            # 2. DB UPDATE
            now = datetime.now(timezone.utc).isoformat()
            updated_messages = conversation.messages + [
                {"role": "user", "content": "📷 [Payment Receipt Uploaded]", "timestamp": now},
                {"role": "assistant", "content": success_msg, "timestamp": now}
            ]
            if len(updated_messages) > settings.MAX_CONVERSATION_MESSAGES:
                updated_messages = updated_messages[-settings.MAX_CONVERSATION_MESSAGES:]
            await self.conversation_repo.update_messages(conversation.id, updated_messages, None)
            
            # 🚀 FIX: ডাটাবেস সেশন ক্লোজ হওয়ার আগেই মেসেজগুলো মেমোরিতে নিয়ে নিচ্ছি
            recent_msgs = updated_messages[-8:] if updated_messages else []
            phone_number = conversation.user_phone or 'Unknown'
            
            # 3. ✉️ BACKGROUND WORKER:
            async def process_vision_and_email(msgs, phone):
                try:
                    # a) Vision Analysis
                    model_name = client.provider.model_name if client.provider else "qwen3-vl:latest"
                    analysis_result = await ai_client.analyze_receipt_image(image_base64, model_name=model_name)
                    
                    # b) Chat History Extraction
                    recent_context = "\n".join([f"{'User' if m['role']=='user' else 'Bot'}: {m['content']}" for m in msgs])

                    extraction_prompt = f"""
                    Analyze the following chat history and payment receipt analysis. Extract the order details exactly in the requested format.
                    
                    Chat History:
                    {recent_context}
                    
                    Vision Analysis:
                    {analysis_result}
                    
                    FORMAT EXACTLY LIKE THIS:
                    SUBJECT: 🚀 New Order: [Course/Service Name] - [User Name]
                    BODY:
                    🔔 [NEW ORDER ALERT]
                    ==================================================
                    Customer: [User Name] ({phone})
                    Item: [Course/Service Name]
                    Amount: [Amount from receipt]
                    Payment Method: [Method e.g., bKash, Bank]
                    Transaction ID: [Transaction ID]
                    Payment Proof: Attached
                    Status: Pending Verification
                    ==================================================
                    """
                    
                    subject_line = f"🚀 New Order Alert - {phone}"
                    body_text = f"Payment uploaded. Analysis:\n{analysis_result}"
                    
                    # c) Formatting with LLM
                    try:
                        if client.provider:
                            ai_extracted = await ai_client.chat(
                                provider_type=client.provider.provider_type,
                                model_name=client.provider.model_name,
                                system_prompt="You are a strict data extractor. Output ONLY the exact format requested.",
                                messages=[{"role": "user", "content": extraction_prompt}],
                                config={"temperature": 0.1}
                            )
                            if "SUBJECT:" in ai_extracted and "BODY:" in ai_extracted:
                                parts = ai_extracted.split("BODY:")
                                subject_line = parts[0].replace("SUBJECT:", "").strip()
                                body_text = parts[1].strip()
                    except Exception as e:
                        logger.error(f"AI Email formatting failed (falling back to raw): {e}")

                    # d) Final Email Send
                    await email_service.send_notification(subject=subject_line, content=body_text, attachment_base64=image_base64, client=client)
                except Exception as e:
                    logger.error(f"Background Vision/Email Failed: {e}")

            # Fire and forget! 
            asyncio.create_task(process_vision_and_email(recent_msgs, phone_number))
            
            # 4. End Stream
            return
        # =====================================================================

        entity_type_id = None
        if request.entity_type:
            entity_type = await self.type_repo.get_by_name(client.id, request.entity_type)
            if entity_type:
                entity_type_id = entity_type.id

        context = await self._search_knowledge(client.id, request.message, entity_type_id)
        # 🚀 THE MEMORY BRIDGE: ফ্রন্টএন্ড থেকে আসা হিস্ট্রি ব্যবহার করা হচ্ছে
        if request.messages:
            messages = request.messages
        else:
            messages = self._build_messages(conversation.messages, request.message)
        system_prompt = self._build_system_prompt(client, context, conversation)

        if not client.provider:
            yield f"data: {{\"content\": \"System Error: No AI provider configured for this client.\"}}\n\n"
            yield "data: [DONE]\n\n"
            return

        full_response = ""
        try:
            async for chunk in ai_client.stream_chat_generator(
                provider_type=client.provider.provider_type,
                model=client.provider.model_name,
                system_prompt=system_prompt,
                messages=messages,
                config=client.provider.config
            ):
                yield chunk
                if chunk.startswith("data: ") and "[DONE]" not in chunk:
                    try:
                        import json
                        parsed = json.loads(chunk[6:])
                        if "content" in parsed: full_response += parsed["content"]
                    except: pass
        except Exception as e:
            yield f"data: {{\"content\": \"\n\n[Connection interrupted...]\"}}\n\n"
            yield "data: [DONE]\n\n"

       # 3. 🚀 FIX: Natural language trigger (No more raw magic words streaming to UI)
        if full_response:
            full_response = re.sub(r'<think>.*?</think>', '', full_response, flags=re.DOTALL).strip()
            
            trigger_en = "transferred to a human agent"
            trigger_bn = "হিউম্যান এজেন্টের কাছে ট্রান্সফার"
            
            # যদি এআই (AI) এর উত্তরের মধ্যে ট্রান্সফারের কথাটি থাকে
            if trigger_en in full_response or trigger_bn in full_response:
                conversation.status = "human_escalated"
                
                # 🚀 PRO-LEVEL FIX: Dynamic Link Generation for Admin
                admin_link = f"https://bot.ictbangladesh.bd/admin.html?session_id={conversation.session_id}"
                
                # অ্যাডমিনকে ইমেইল পাঠানো হচ্ছে (Overriding old templates)
                await email_service.send_notification(
                    subject=f"🚨 URGENT: Human Assistance Needed",
                    content=f"""A user requires immediate human assistance.

Last message: {request.message}
Phone/ID: {conversation.user_phone or 'Unknown'}

👉 CLICK HERE TO JOIN THE CHAT:
{admin_link}

=======================================================
[System Note: This is an escalation request. Please click the link above to log in and reply directly to the customer. Ignore any previous payment receipt notices for this specific alert.]
=======================================================""",
                    client=client
                ) 

            now = datetime.now(timezone.utc).isoformat()
            updated_messages = conversation.messages + [
                {"role": "user", "content": request.message, "timestamp": now},
                {"role": "assistant", "content": full_response, "timestamp": now},
            ]
            if len(updated_messages) > settings.MAX_CONVERSATION_MESSAGES:
                updated_messages = updated_messages[-settings.MAX_CONVERSATION_MESSAGES:]

            user_info_dict = request.user_info.model_dump(exclude_none=True) if request.user_info else {}
            await self.conversation_repo.update_messages(conversation.id, updated_messages, user_info_dict or None)
            
            if conversation.status == "human_escalated":
                 await self.conversation_repo.db.execute(
                     __import__('sqlalchemy').update(Conversation)
                     .where(Conversation.id == conversation.id)
                     .values(status="human_escalated")
                 )
                 await self.conversation_repo.db.commit()

    async def handle_message(self, client: Client, request: ChatRequest) -> ChatResponse:
        pass 

    async def _get_or_create_conversation(self, client: Client, request: ChatRequest) -> Conversation:
        conversation = await self.conversation_repo.get_by_session(client.id, request.session_id)
        if not conversation:
            user_info = request.user_info.model_dump(exclude_none=True) if request.user_info else {}
            user_phone = request.session_id.split("_")[1] if len(request.session_id.split("_")) > 1 else None
            conversation = Conversation(client_id=client.id, session_id=request.session_id, user_phone=user_phone, user_info=user_info, messages=[])
            conversation = await self.conversation_repo.create(conversation)
        return conversation

    async def _search_knowledge(self, client_id: uuid.UUID, query: str, entity_type_id: uuid.UUID | None) -> str:
        try:
            query_embedding = await ai_client.generate_embedding(query)
            results = await self.knowledge_repo.search_similar(client_id=client_id, query_embedding=query_embedding, entity_type_id=entity_type_id, limit=2)
            if not results: return "No specific data found."
            
            # 🚀 THE ULTIMATE FIX: Fetching REAL JSON Data from ai_entities table
            from sqlalchemy import text
            
            context_lines = []
            for i, r in enumerate(results, 1):
                # সরাসরি ডাটাবেস থেকে আসল Description ও Price সম্বলিত data কলামটি টেনে আনা হচ্ছে
                entity_query = await self.db.execute(
                    text("SELECT data FROM ai_entities WHERE id = :eid"),
                    {"eid": r.entity_id}
                )
                entity_data = entity_query.scalar() # JSONB ডেটাটা ডিকশনারি হিসেবে আসবে
                
                # যদি entity_data পাওয়া যায়, তবে সেটাই এআই-কে দেওয়া হবে
                real_full_data = entity_data if entity_data else r.meta_data
                
                context_lines.append(f"--- ITEM {i} ---\nSummary: {r.summary}\nFull Data: {real_full_data}\n")
                
            return "\n".join(context_lines)
        except Exception as e: 
            logger.error(f"Search Knowledge Error: {e}")
            return ""

    def _build_system_prompt(self, client: Client, context: str, conversation: Conversation) -> str:
        order_id = f"ICT-{uuid.uuid4().hex[:6].upper()}"
        display_name = client.name.replace(" Official", "").strip()
        
        # 🚀 ড্যাশবোর্ড থেকে আসা কাস্টম প্রম্পট ডাটাবেস থেকে টেনে আনা হচ্ছে
        dashboard_prompt = ""
        if client.config and "system_prompt" in client.config:
            dashboard_prompt = client.config["system_prompt"]
        
        return f"""You are the strict AI Support Agent for {display_name}. YOU ARE NOT A HUMAN. NEVER output <think> tags.

# 🌍 MULTILINGUAL RULE (CRITICAL):
- If the user speaks Bengali, reply natively in Bengali.
- If the user speaks English, reply natively in English.
- STRICT PROHIBITION: You are STRICTLY FORBIDDEN from using any Chinese characters (汉字) or Chinese language. NEVER output Chinese under any circumstances.
- Keep your tone highly professional, welcoming, and organized. 

# ⚙️ CUSTOM ADMIN RULES (FROM DASHBOARD):
{dashboard_prompt}

# 🚦 CRITICAL RULES (OBEY EXACTLY):

# === NEW DEMO RULES (PRIORITY 1) ===
0.1 GREETING RULE (STRICT):
   - IF the user says "hi", "hello", "কেমন আছো" or similar greetings:
     - For Bengali users: Output EXACTLY "হ্যালো! আমি বাংলাদেশ থেকে ICT Bangladesh এর AI assistant বলছি, বলুন আপনাকে কিভাবে সহযোগিতা করতে পারি?"
     - For English users: Output EXACTLY "Hello! I am the AI assistant of ICT Bangladesh from Bangladesh. How can I assist you today?"
     - DO NOT output any other welcome text.

0.2 COURSE LINK RULE:
   - WHENEVER you provide details about courses, you MUST append this exact sentence and link at the very end of your entire response:
     - For Bengali users: "চাইলে এই লিঙ্কে ভিজিট করতে পারেন: <a href='http://ictbangladesh.com.bd/all/courses' target='_blank' rel='noopener noreferrer'>আমাদের কোর্সসমূহ</a>"
     - For English users: "You can visit this link for more details: <a href='http://ictbangladesh.com.bd/all/courses' target='_blank' rel='noopener noreferrer'>Our Courses</a>"

0.3 TEACHER/INSTRUCTOR RULE (HARDCODED):
   - IF the user asks about teachers, instructors, or who takes the classes, IGNORE ALL OTHER CONTEXT and output EXACTLY this text:
     - For Bengali users: "আমাদের প্রধান শিক্ষক/ইন্সট্রাক্টর হলেন Md. Israfeel Masum স্যার, তিনি অত্যন্ত দক্ষ একজন AI engineer, তিনি আমেরিকা থেকে ক্লাস নেন। চাইলে <a href='https://israfeelmasum.com' target='_blank' rel='noopener noreferrer'>এই লিঙ্কে ভিজিট করে</a> Israfeel Masum স্যারের বিস্তারিত জেনে নিতে পারেন। এছাড়া দক্ষ সফটওয়্যার ইঞ্জিনিয়ার হিসেবে আছেন Mahinur Rahman Hridoy সহ আরও অনেকে। আপনি আমাদের ওয়েবসাইট <a href='http://ictbangladesh.com.bd' target='_blank' rel='noopener noreferrer'>ictbangladesh.com.bd</a> তে গিয়ে যেকোনো কোর্সে ভিজিট করে পেজের নিচের দিকে স্ক্রল করলেই আমাদের শিক্ষক এবং সফল ছাত্রদের রিভিউ দেখতে পাবেন।"
     - For English users: "Our lead teacher/instructor is Md. Israfeel Masum sir. He is a highly skilled AI engineer and conducts classes from America. You can visit <a href='https://israfeelmasum.com' target='_blank' rel='noopener noreferrer'>his website</a> to know more about him. We also have skilled software engineers like Mahinur Rahman Hridoy and others. If you visit any course page on our <a href='http://ictbangladesh.com.bd' target='_blank' rel='noopener noreferrer'>website</a> and scroll down, you can see the reviews of our teachers and successful students."
     
# ===================================

1. INTENT-BASED FILTERING & FORMATTING (MANDATORY):
   - CAREFULLY analyze what the user is asking for.
   - IF the user asks specifically for "courses" (e.g., "tell me about your courses"), you MUST ONLY list the courses from the [RETRIEVED DATA]. IGNORE and DO NOT output any items marked as "Product" or "Service".
   - IF the user asks for "products", list ONLY products. 
   - IF they ask a general question ("what do you offer?"), list everything.
   - For EVERY SINGLE item you decide to list, you MUST strictly format your response exactly like this:
     📌 Name: [Extract from title]
     💰 Price: [Extract exact price and discount. NEVER say 'Not specified' if numbers exist in the description]
     📖 Details: [Short 1-2 line summary in the user's language]

2. SPECIFIC INQUIRY:
   - IF the user asks about a SPECIFIC course (e.g., "Professional AI Engineer"), provide detailed information ONLY about that course. DO NOT list all other courses.

3. DEEP PRICING EXTRACTION (CRITICAL):
   - Prices are often embedded INSIDE the "description" text (e.g., "Price: 20000.0 BDT (Discounted: 10000.0 BDT)"). 
   - You MUST deeply read and scan the entire description of EVERY course to find and display the exact price and any discounts.
   - NEVER say "pricing is not specified" if the price is written anywhere inside the description text.
   - Always mention prices using "BDT" or "৳" (e.g., 20,000 BDT). NEVER use the Dollar ($) sign.

4. REGISTRATION TRIGGER:
   - IF the user asks to ENROLL, ADMIT, BUY, or PURCHASE a course/product/service:
   - For English users, output EXACTLY this line (nothing else):
     "Great! To proceed with your enrollment, please provide your Name, Email, and Phone number."
   - For Bengali users, output EXACTLY this line (nothing else):
     "চমৎকার! রেজিস্ট্রেশন শুরু করতে অনুগ্রহ করে আপনার নাম, ইমেইল এবং ফোন নম্বর প্রদান করুন।"

5. 🔴 MOST IMPORTANT TRIGGER (PAYMENT DETAILS):
   - IF the user provides their NAME, EMAIL, and PHONE NUMBER, you MUST IMMEDIATELY provide the payment options.
   - For English users, output ONLY this text block:
Thank you for your details! To confirm your registration, please complete the payment.
Payment Options:
✅ Bank Transfer (City Bank) Acct Name: ICT Bangladesh Acct No: 1254658567001 Branch: Nikunja Routing: 225261279
✅ Bank Transfer (Brac Bank) Acct Name: Md Israfeel Acct No: 1531202910486001 Branch: Panthapath SME Routing: 060263629
✅ bKash/Nagad (Send Money): 01753060119
After payment, please reply here with a screenshot of the payment proof.

   - For Bengali users, output ONLY this text block:
আপনার তথ্যের জন্য ধন্যবাদ! রেজিস্ট্রেশন নিশ্চিত করতে অনুগ্রহ করে পেমেন্ট সম্পন্ন করুন।
পেমেন্ট অপশন:
✅ ব্যাংক ট্রান্সফার (City Bank) Acct Name: ICT Bangladesh Acct No: 1254658567001 Branch: Nikunja Routing: 225261279
✅ ব্যাংক ট্রান্সফার (Brac Bank) Acct Name: Md Israfeel Acct No: 1531202910486001 Branch: Panthapath SME Routing: 060263629
✅ বিকাশ/নগদ (Send Money): 01753060119
পেমেন্ট সম্পন্ন করার পর, প্রমাণস্বরূপ পেমেন্টের স্ক্রিনশট এখানে দিন।

6. HUMAN AGENT ESCALATION:
   - IF the user asks for a HUMAN, AGENT, or REAL PERSON:
   Reply EXACTLY: "I sincerely apologize for the inconvenience. Your chat is being transferred to a human agent, please wait a moment." (Or Bengali equivalent).
   
7. GENERAL Q&A (NO META-TALK):
   - For general questions (e.g., about teachers, location, etc.), answer politely and conversationally using the [RETRIEVED DATA].
   - NEVER act like a data analyst. NEVER mention internal formatting like "ITEM 1", "The provided text", "Retrieved data", or "JSON". 
   - Just give the answer directly to the user. If the information is not in the data, simply apologize and say you don't have that specific information right now.
   
[RETRIEVED DATA START]
{context}
[RETRIEVED DATA END]
"""

    def _build_messages(self, history: list[dict], new_message: str) -> list[dict]:
        optimized_history = history[-4:] if len(history) > 4 else history
        messages = [{"role": msg["role"], "content": msg["content"]} for msg in optimized_history]
        messages.append({"role": "user", "content": new_message})
        return messages