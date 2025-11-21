from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText  
from email.mime.multipart import MIMEMultipart  
import os
from dotenv import load_dotenv
import logging
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailConfig:
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    EMAIL_USERNAME = os.getenv('EMAIL_USERNAME', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'gauravdhangar50@gmail.com')

def send_email(name, email, subject, message):
    """Send email notification for collaboration inquiry"""
    try:
        print(f"📧 Attempting to send email from {name} ({email})")
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EmailConfig.EMAIL_USERNAME
        msg['To'] = EmailConfig.ADMIN_EMAIL
        msg['Subject'] = f"🎯 Portfolio Collaboration: {subject}"
        
        # HTML email template
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
        
        print(f"🔗 Connecting to {EmailConfig.SMTP_SERVER}:{EmailConfig.SMTP_PORT}")
        server = smtplib.SMTP(EmailConfig.SMTP_SERVER, EmailConfig.SMTP_PORT)
        server.starttls()
        print("🔐 Attempting login...")
        server.login(EmailConfig.EMAIL_USERNAME, EmailConfig.EMAIL_PASSWORD)
        print("📤 Sending email...")
        server.send_message(msg)
        server.quit()
        
        print("✅ Email sent successfully!")
        logger.info(f"Email sent successfully for inquiry from {name}")
        return True
        
    except Exception as e:
        error_msg = f"Failed to send email: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(error_msg)
        return False

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
    """Handle collaboration inquiry form submissions"""
    try:
        # Get form data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data received'
            }), 400
        
        # Extract form fields
        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        subject = data.get('subject', '').strip()
        message = data.get('message', '').strip()
        
        # Validate required fields
        if not all([name, email, subject, message]):
            return jsonify({
                'success': False,
                'message': 'All fields are required'
            }), 400
        
        # Validate email format
        if '@' not in email or '.' not in email:
            return jsonify({
                'success': False,
                'message': 'Please enter a valid email address'
            }), 400
        
        # Log the inquiry
        print(f"📨 New inquiry from {name} ({email}): {subject}")
        logger.info(f"New inquiry from {name} ({email}): {subject}")
        
        # Save to database
        save_to_database(name, email, subject, message)
        
        # Send email notification
        email_sent = send_email(name, email, subject, message)
        
        if email_sent:
            return jsonify({
                'success': True,
                'message': 'Thank you for your message! I\'ll get back to you soon.'
            })
        else:
            return jsonify({
                'success': True,
                'message': 'Message received! There was an issue with email notification, but your inquiry has been logged.'
            })
            
    except Exception as e:
        error_msg = f"Error processing contact form: {str(e)}"
        print(f"❌ {error_msg}")
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
        'ADMIN_EMAIL': EmailConfig.ADMIN_EMAIL
    })
    
@app.route('/api/test-form', methods=['POST'])
def test_form():
    """Test endpoint to check form data reception"""
    try:
        data = request.get_json()
        print("📨 Received form data:", data)
        
        return jsonify({
            'success': True,
            'message': 'Form data received successfully!',
            'received_data': data
        })
    except Exception as e:
        print("❌ Error in test form:", e)
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
