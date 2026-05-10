"""Email notification service for notifying authorities — async with aiosmtplib."""

import aiosmtplib
from email.message import EmailMessage
import logging
from app.config import get_settings
from app.models.client import Client # 🚀 NEW: ক্লায়েন্টের ডাটা আনার জন্য

settings = get_settings()
logger = logging.getLogger(__name__)

class EmailService:
    async def send_notification(self, subject: str, content: str, attachment_base64: str = None, client: Client = None):
        """Send an email notification to the authority (truly async, non-blocking)."""
        
        # 🚀 THE MASTERSTROKE: Dynamic SaaS Email Configuration
        # প্রথমে সে ক্লায়েন্টের ড্যাশবোর্ড (ডাটাবেস) থেকে ইমেইল খুঁজবে, না পেলে সিস্টেমের ডিফল্ট (.env) ব্যবহার করবে।
        
        smtp_user = None
        smtp_pass = None
        admin_email = None
        
        # ১. ক্লায়েন্ট যদি তার ড্যাশবোর্ডে ইমেইল সেট করে থাকে:
        if client and client.config:
            smtp_user = client.config.get("smtp_sender")
            smtp_pass = client.config.get("smtp_password")
            admin_email = client.config.get("fallback_email")
            
        # ২. যদি ক্লায়েন্ট সেট না করে, তবে .env থেকে সিস্টেমের ডিফল্ট নেবে (Fallback):
        if not smtp_user or not smtp_pass:
            smtp_user = settings.SMTP_USER
            smtp_pass = settings.SMTP_PASSWORD
            
        if not admin_email:
            admin_email = getattr(settings, 'ADMIN_EMAIL', None) or getattr(settings, 'AUTHORITY_EMAIL', None) or smtp_user

        # ৩. যদি কোথাও কোনো ইমেইল না থাকে, তবে ফেইল করবে:
        if not smtp_user or not smtp_pass:
            logger.warning("Email not configured in Dashboard or .env. Skipping notification.")
            return False

        try:
            msg = EmailMessage()
            corporate_note = "\n\n=======================================================\n[System Note: A payment receipt has been uploaded by the customer. \nPlease log in to the Admin Dashboard to view and verify the document.]\n======================================================="

            msg.set_content(content + corporate_note)
            msg['Subject'] = subject
            msg['From'] = smtp_user
            msg['To'] = admin_email

            # Truly async email sending
            await aiosmtplib.send(
                msg,
                hostname=getattr(settings, 'SMTP_HOST', 'smtp.gmail.com'),
                port=getattr(settings, 'SMTP_PORT', 587),
                start_tls=True,
                username=smtp_user,
                password=smtp_pass,
            )

            logger.info(f"Email sent: {subject} | To: {admin_email} | Sender: {smtp_user}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

email_service = EmailService()