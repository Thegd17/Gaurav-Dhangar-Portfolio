from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText  
from email.mime.multipart import MIMEMultipart  
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
from celery import Celery # ⬅️ New Import

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Celery Configuration ---
# ⚠️ IMPORTANT: Set REDIS_URL in your environment variables
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0') 

celery_app = Celery(
    'portfolio_tasks',
    broker=REDIS_URL,
    backend=REDIS_URL # Optional, for storing task results
)
# ----------------------------

app = Flask(__name__)
CORS(app)

class EmailConfig:
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    EMAIL_USERNAME = os.getenv('EMAIL_USERNAME', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'gauravdhangar50@gmail.com')


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(self, name, email, subject, message):
    """
    Celery task to handle sending the email in the background.
    Uses 'bind=True' to access the task instance ('self') for retries.
    """
    try:
        logger.info(f"📧 Attempting to send email in background from {name} ({email})")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EmailConfig.EMAIL_USERNAME
        msg['To'] = EmailConfig.ADMIN_EMAIL
        msg['Subject'] = f"🎯 Portfolio Collaboration: {subject}"
        
        # HTML email template (same as before)
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                    <h2 style="color: #3B82F6; border-bottom: 2px solid #3B82F6; padding-bottom: 10px;">
                        🚀 New Collaboration Inquiry
                    </h2>
                    
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <h3 style="color: #111827; margin-top: 0;">Contact Details:</h3>
                        <p><strong>👤 Name:</strong> {name}</p>
                        <p><strong>📧 Email:</strong> <a href="mailto:{email}">{email}</a></p>
                        <p><strong>📋 Subject:</strong> {subject}</p>
                    </div>
                    
                    <div style="background: #eef2ff; padding: 15px; border-radius: 5px;">
                        <h3 style="color: #111827; margin-top: 0;">Message:</h3>
                        <p style="white-space: pre-line;">{message}</p>
                    </div>
                    
                    <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666;">
                        <p>This inquiry was submitted through your portfolio website at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                        <p>💼 <strong>Gaurav Dhangar - AIML Portfolio</strong></p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        logger.info(f"🔗 Connecting to {EmailConfig.SMTP_SERVER}:{EmailConfig.SMTP_PORT}")
        # Add a timeout to the SMTP connection to avoid indefinite hanging
        server = smtplib.SMTP(EmailConfig.SMTP_SERVER, EmailConfig.SMTP_PORT, timeout=30) 
        server.starttls()
        logger.info("🔐 Attempting login...")
        server.login(EmailConfig.EMAIL_USERNAME, EmailConfig.EMAIL_PASSWORD)
        logger.info("📤 Sending email...")
        server.send_message(msg)
        server.quit()
        
        logger.info("✅ Email sent successfully in background!")
        return True
        
    except Exception as exc:
        logger.error(f"❌ Failed to send email (Task ID: {self.request.id}): {str(exc)}")
        # Attempt to retry the task on failure
        raise self.retry(exc=exc) 

def save_to_database(name, email, subject, message):
    """Save inquiry to a simple text file (can be replaced with real database)"""
    try:
        with open('inquiries.txt', 'a', encoding='utf-8') as f:
            f.write(f"Name: {name}\n")
            f.write(f"Email: {email}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"Message: {message}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 50 + "\n")
        logger.info(f"Inquiry saved to database for {name}")
        return True
    except Exception as e:
        logger.error(f"Failed to save to database: {str(e)}")
        return False

@app.route('/')
def serve_portfolio():
    """Serve the main portfolio page"""
    return render_template('index.html')

@app.route('/api/contact', methods=['POST'])
def handle_contact():
    """Handle collaboration inquiry form submissions - now triggers task asynchronously"""
    try:
        data = request.get_json()
        
        if not data or not all([data.get('name'), data.get('email'), data.get('subject'), data.get('message')]):
             return jsonify({
                'success': False,
                'message': 'All fields are required'
            }), 400
        
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        subject = data.get('subject', '').strip()
        message = data.get('message', '').strip()
        
        # Validate email format
        if '@' not in email or '.' not in email:
            return jsonify({
                'success': False,
                'message': 'Please enter a valid email address'
            }), 400
        
        # Log and Save (Fast operations)
        logger.info(f"New inquiry received from {name} ({email}): {subject}")
        save_to_database(name, email, subject, message)
        
        # 💥 NEW: Trigger the email sending as an asynchronous task
        send_email_task.delay(name, email, subject, message)
        
        # Return success immediately (Crucial to avoid worker timeout!)
        return jsonify({
            'success': True,
            'message': 'Thank you for your message! Your inquiry has been logged, and the email notification is being processed.'
        })
            
    except Exception as e:
        error_msg = f"Error processing contact form: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your request. Please try again later.'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Portfolio backend is running'})

@app.route('/api/debug-email')
def debug_email():
    """Debug endpoint to check email configuration"""
    return jsonify({
        'SMTP_SERVER': EmailConfig.SMTP_SERVER,
        'SMTP_PORT': EmailConfig.SMTP_PORT,
        'EMAIL_USERNAME': EmailConfig.EMAIL_USERNAME,
        'EMAIL_PASSWORD_SET': bool(EmailConfig.EMAIL_PASSWORD),
        'ADMIN_EMAIL': EmailConfig.ADMIN_EMAIL,
        'CELERY_BROKER': REDIS_URL
    })

# --- Test Task for Celery Debugging ---
@celery_app.task
def test_email(to_email):
    try:
        msg = MIMEMultipart()
        msg['From'] = EmailConfig.EMAIL_USERNAME
        msg['To'] = to_email
        msg['Subject'] = "Celery Test Success"
        msg.attach(MIMEText("This is a test email sent asynchronously via Celery.", 'plain'))

        server = smtplib.SMTP(EmailConfig.SMTP_SERVER, EmailConfig.SMTP_PORT, timeout=10)
        server.starttls()
        server.login(EmailConfig.EMAIL_USERNAME, EmailConfig.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"Test email successfully sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Test email failed: {str(e)}")
        return False

@app.route('/api/test-email-trigger', methods=['GET'])
def trigger_test_email():
    """Endpoint to trigger a test email via Celery"""
    test_email_to = EmailConfig.ADMIN_EMAIL
    test_email.delay(test_email_to)
    return jsonify({
        'success': True, 
        'message': f'Test email task triggered for {test_email_to}. Check Celery worker logs for status.'
    })
# ---------------------------------------

# if __name__ == '__main__':
#     # NOTE: In production (Render/Gunicorn), this block is usually not used.
#     # Gunicorn or your specific hosting platform should handle running the app.
#     app.run(debug=True, host='0.0.0.0', port=5000)
