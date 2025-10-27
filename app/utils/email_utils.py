from flask import current_app
from flask_mail import Message
from datetime import datetime

def send_email(to_email, subject, body, html_body=None):
    """Send email using Flask-Mail"""
    try:
        mail = current_app.mail
        msg = Message(
            subject=subject,
            recipients=[to_email],
            body=body,
            html=html_body
        )
        mail.send(msg)
        
        # Log email
        from models.database import execute_query
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        execute_query(
            '''INSERT INTO email_logs (recipient_email, subject, body, status, sent_at)
               VALUES (?, ?, ?, ?, ?)''',
            (to_email, subject, body, 'sent', datetime.now())
        )
        return True
    except Exception as e:
        # Log error
        from models.database import execute_query
        db_path = current_app.config.get('DATABASE_PATH', 'gym_management.db')
        execute_query(
            '''INSERT INTO email_logs (recipient_email, subject, body, status, error_message)
               VALUES (?, ?, ?, ?, ?)''',
            (to_email, subject, body, 'failed', str(e))
        )
        return False

def send_password_change_notification(email, full_name):
    """Send password change notification"""
    subject = "Password Changed - FitZone Gym"
    body = f"""
    Dear {full_name},
    
    Your password has been successfully changed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.
    
    If you did not make this change, please contact our support team immediately.
    
    Best regards,
    FitZone Gym Team
    """
    
    html_body = f"""
    <html>
    <body>
        <h2>Password Changed Successfully</h2>
        <p>Dear <strong>{full_name}</strong>,</p>
        <p>Your password has been successfully changed on <strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong>.</p>
        <p><strong>If you did not make this change, please contact our support team immediately.</strong></p>
        <br>
        <p>Best regards,<br>
        <strong>FitZone Gym Team</strong></p>
    </body>
    </html>
    """
    
    return send_email(email, subject, body, html_body)

def send_membership_renewal_reminder(email, full_name, expiry_date, days_remaining):
    """Send membership renewal reminder"""
    subject = f"Membership Expiring Soon - {days_remaining} Days Remaining"
    body = f"""
    Dear {full_name},
    
    This is a friendly reminder that your gym membership will expire on {expiry_date}.
    
    You have {days_remaining} days remaining. Please renew your membership to continue enjoying our facilities.
    
    Visit our gym or contact us to renew your membership today!
    
    Best regards,
    FitZone Gym Team
    """
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #1a73e8;">Membership Expiring Soon</h2>
            <p>Dear <strong>{full_name}</strong>,</p>
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>⚠️ Your gym membership will expire on {expiry_date}</strong></p>
                <p style="font-size: 18px; color: #d63031;">You have <strong>{days_remaining} days</strong> remaining.</p>
            </div>
            <p>Please renew your membership to continue enjoying our facilities and services.</p>
            <div style="text-align: center; margin: 30px 0;">
                <p style="background-color: #1a73e8; color: white; padding: 15px; border-radius: 5px; display: inline-block;">
                    Visit our gym or contact us to renew your membership today!
                </p>
            </div>
            <p>Best regards,<br>
            <strong>FitZone Gym Team</strong></p>
        </div>
    </body>
    </html>
    """
    
    return send_email(email, subject, body, html_body)

def send_payment_reminder(email, full_name, amount, due_date):
    """Send payment reminder"""
    subject = "Payment Reminder - FitZone Gym"
    body = f"""
    Dear {full_name},
    
    This is a reminder that you have an outstanding payment of ${amount} due on {due_date}.
    
    Please make your payment at your earliest convenience to avoid any service interruptions.
    
    You can pay at our gym reception or contact us for online payment options.
    
    Best regards,
    FitZone Gym Team
    """
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #e74c3c;">Payment Reminder</h2>
            <p>Dear <strong>{full_name}</strong>,</p>
            <div style="background-color: #ffebee; border: 1px solid #e57373; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>💳 Outstanding Payment: ${amount}</strong></p>
                <p><strong>📅 Due Date: {due_date}</strong></p>
            </div>
            <p>Please make your payment at your earliest convenience to avoid any service interruptions.</p>
            <p>You can pay at our gym reception or contact us for online payment options.</p>
            <p>Best regards,<br>
            <strong>FitZone Gym Team</strong></p>
        </div>
    </body>
    </html>
    """
    
    return send_email(email, subject, body, html_body)

def send_welcome_email(email, full_name, username, temporary_password):
    """Send welcome email to new members/trainers"""
    subject = "Welcome to FitZone Gym!"
    body = f"""
    Dear {full_name},
    
    Welcome to FitZone Gym! We're excited to have you as part of our fitness community.
    
    Your account has been created with the following credentials:
    Username: {username}
    Temporary Password: {temporary_password}
    
    Please log in and change your password immediately for security purposes.
    
    If you have any questions, please don't hesitate to contact our support team.
    
    Best regards,
    FitZone Gym Team
    """
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #1a73e8;">Welcome to FitZone Gym! 🏋️‍♂️</h2>
            <p>Dear <strong>{full_name}</strong>,</p>
            <p>Welcome to FitZone Gym! We're excited to have you as part of our fitness community.</p>
            
            <div style="background-color: #e3f2fd; border: 1px solid #2196f3; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="color: #1976d2;">Your Account Credentials:</h3>
                <p><strong>Username:</strong> {username}</p>
                <p><strong>Temporary Password:</strong> {temporary_password}</p>
            </div>
            
            <div style="background-color: #fff3e0; border: 1px solid #ff9800; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>🔒 Important:</strong> Please log in and change your password immediately for security purposes.</p>
            </div>
            
            <p>If you have any questions, please don't hesitate to contact our support team.</p>
            <p>Best regards,<br>
            <strong>FitZone Gym Team</strong></p>
        </div>
    </body>
    </html>
    """
    
    return send_email(email, subject, body, html_body)

def send_password_reset_email(email, reset_link):
    """Send password reset email"""
    subject = "Reset Your FitZone Gym Password"
    body = f"""
    Dear user,

    You requested a password reset on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.
    Click the link below to reset your password:

    {reset_link}

    This link will expire in 1 hour. If you did not request a password reset, please ignore this email.

    Best regards,
    FitZone Gym Team
    """
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2>Password Reset Request</h2>
            <p>You requested a password reset on <strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong>.</p>
            <p>Click the button below to reset your password. This link will expire in 1 hour.</p>
            <p style="text-align: center; margin: 20px 0;">
                <a href="{reset_link}" style="background-color: #1a73e8; color: white; padding: 15px 25px; text-decoration: none; border-radius: 5px;">Reset Password</a>
            </p>
            <p>If you did not request this, you can safely ignore this email.</p>
            <p>Best regards,<br>FitZone Gym Team</p>
        </div>
    </body>
    </html>
    """
    
    return send_email(email, subject, body, html_body)