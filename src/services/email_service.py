from flask_mail import Message
from src.config.config import Config
from src import mail

def send_otp_email(email, otp_code, purpose):
    subject = 'Email Verification' if purpose == 'register' else 'Password Reset'
    msg = Message(subject,
                  sender=Config.MAIL_DEFAULT_SENDER,
                  recipients=[email])
    # HTML template cho email OTP
    msg.html = f'''
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: auto; border: 1px solid #eee; border-radius: 8px; box-shadow: 0 2px 8px #f0f0f0; padding: 32px 24px; background: #fff;">
        <h2 style="color: #2d8cf0; text-align: center;">{subject}</h2>
        <p style="font-size: 16px; color: #333; text-align: center;">Your verification code is:</p>
        <div style="font-size: 32px; font-weight: bold; color: #2d8cf0; text-align: center; letter-spacing: 8px; margin: 24px 0;">{otp_code}</div>
        <p style="font-size: 15px; color: #555; text-align: center;">This code will expire in <b>1 minutes</b>.</p>
        <hr style="margin: 32px 0; border: none; border-top: 1px solid #eee;">
        <p style="font-size: 13px; color: #999; text-align: center;">If you did not request this code, please ignore this email.</p>
        <p style="font-size: 13px; color: #bbb; text-align: center; margin-top: 16px;">&copy; {subject} - Travel Assistant Chatbot</p>
    </div>
    '''
    msg.body = f"Your verification code is: {otp_code}\n\nThis code will expire in 1 minutes.\n\nIf you did not request this code, please ignore this email."
    mail.send(msg)

def send_notification_email(email, title, message, user_name):
    """
    Send notification email to user
    
    Args:
        email (str): User's email address
        title (str): Email title
        message (str): Email message content
        user_name (str): User's name
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        msg = Message(title,
                     sender=Config.MAIL_DEFAULT_SENDER,
                     recipients=[email])
        
        # HTML template cho notification email
        msg.html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #eee; border-radius: 8px; box-shadow: 0 2px 8px #f0f0f0; padding: 32px 24px; background: #fff;">
            <h2 style="color: #2d8cf0; text-align: center;">{title}</h2>
            <p style="font-size: 16px; color: #333; margin: 20px 0;">Hello {user_name},</p>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 6px; margin: 20px 0;">
                <p style="font-size: 16px; color: #333; margin: 0; line-height: 1.6;">{message}</p>
            </div>
            <p style="font-size: 15px; color: #555; margin: 20px 0;">Thank you for using Travel Assistant Chatbot!</p>
            <hr style="margin: 32px 0; border: none; border-top: 1px solid #eee;">
            <p style="font-size: 13px; color: #999; text-align: center;">This is an automated notification from Travel Assistant Chatbot</p>
            <p style="font-size: 13px; color: #bbb; text-align: center; margin-top: 16px;">&copy; Travel Assistant Chatbot - Your Travel Companion</p>
        </div>
        '''
        
        msg.body = f"Hello {user_name},\n\n{message}\n\nThank you for using Travel Assistant Chatbot!\n\nThis is an automated notification from Travel Assistant Chatbot"
        
        mail.send(msg)
        return True
        
    except Exception as e:
        print(f"Error sending notification email to {email}: {e}")
        return False