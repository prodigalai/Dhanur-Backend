import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
import aiohttp
import asyncio

logger = logging.getLogger(__name__)

class EmailService:
    """Email service for sending various types of emails."""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@dhanurai.com")
        self.from_name = os.getenv("FROM_NAME", "Dhanur AI")
        
        # Check if email service is configured
        self.is_configured = bool(self.smtp_username and self.smtp_password)
        
        logger.info(f"Email service configuration:")
        logger.info(f"  SMTP Server: {self.smtp_server}")
        logger.info(f"  SMTP Port: {self.smtp_port}")
        logger.info(f"  SMTP Username: {'***' if self.smtp_username else 'Not set'}")
        logger.info(f"  SMTP Password: {'***' if self.smtp_password else 'Not set'}")
        logger.info(f"  From Email: {self.from_email}")
        logger.info(f"  From Name: {self.from_name}")
        logger.info(f"  Is Configured: {self.is_configured}")
        
        if not self.is_configured:
            logger.warning("Email service not configured. Using mock email service.")
    
    async def send_team_invitation_email(
        self, 
        to_email: str, 
        brand_name: str, 
        inviter_name: str,
        role: str, 
        message: str, 
        invitation_url: str, 
        expires_at
    ) -> bool:
        """Send team invitation email."""
        try:
            if not self.is_configured:
                return await self._send_mock_email(to_email, brand_name, inviter_name, role, message, invitation_url, expires_at)
            
            subject = f"You're invited to join {brand_name} on Dhanur AI"
            
            # Create HTML email template
            html_content = self._create_invitation_email_template(
                brand_name, inviter_name, role, message, invitation_url, expires_at
            )
            
            # Send email
            return await self._send_email(to_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Error sending team invitation email: {e}")
            return False
    
    async def send_password_reset_email(
        self, 
        to_email: str, 
        reset_url: str, 
        expires_at
    ) -> bool:
        """Send password reset email."""
        try:
            if not self.is_configured:
                return await self._send_mock_password_reset_email(to_email, reset_url, expires_at)
            
            subject = "Reset Your Password - Dhanur AI"
            
            # Create HTML email template
            html_content = self._create_password_reset_email_template(reset_url, expires_at)
            
            # Send email
            return await self._send_email(to_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Error sending password reset email: {e}")
            return False
    
    def _create_invitation_email_template(
        self, 
        brand_name: str, 
        inviter_name: str,
        role: str, 
        message: str, 
        invitation_url: str, 
        expires_at
    ) -> str:
        """Create HTML email template for team invitation."""
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Team Invitation - {brand_name}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f4f4f4;
                }}
                .container {{
                    background: white;
                    border-radius: 10px;
                    padding: 30px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    text-align: center;
                    border-bottom: 2px solid #007bff;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #007bff;
                    margin-bottom: 10px;
                }}
                .invitation-box {{
                    background: #f8f9fa;
                    border-left: 4px solid #007bff;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 5px;
                }}
                .cta-button {{
                    display: inline-block;
                    background: #007bff;
                    color: white;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                    text-align: center;
                }}
                .cta-button:hover {{
                    background: #0056b3;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    text-align: center;
                    color: #666;
                    font-size: 14px;
                }}
                .role-badge {{
                    background: #28a745;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 15px;
                    font-size: 12px;
                    font-weight: bold;
                    text-transform: uppercase;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🚀 Dhanur AI</div>
                    <p>AI-Powered Content Creation Platform</p>
                </div>
                
                <h2>You're invited to join a team!</h2>
                
                <div class="invitation-box">
                    <h3>📧 Invitation Details</h3>
                    <p><strong>Brand:</strong> {brand_name}</p>
                    <p><strong>Invited by:</strong> {inviter_name}</p>
                    <p><strong>Role:</strong> <span class="role-badge">{role}</span></p>
                    <p><strong>Expires:</strong> {expires_at.strftime('%B %d, %Y at %I:%M %p UTC')}</p>
                    {f'<p><strong>Message:</strong> "{message}"</p>' if message else ''}
                </div>
                
                <p>You've been invited to join <strong>{brand_name}</strong> as a <strong>{role}</strong> on Dhanur AI. 
                This will give you access to collaborate on campaigns, manage content, and work with the team.</p>
                
                <div style="text-align: center;">
                    <a href="{invitation_url}" class="cta-button">Accept Invitation</a>
                </div>
                
                <p><strong>What you can do as a {role}:</strong></p>
                <ul>
                    {self._get_role_permissions_html(role)}
                </ul>
                
                <div class="footer">
                    <p>This invitation will expire on {expires_at.strftime('%B %d, %Y at %I:%M %p UTC')}.</p>
                    <p>If you didn't expect this invitation, you can safely ignore this email.</p>
                    <p>© 2025 Dhanur AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def _create_password_reset_email_template(
        self, 
        reset_url: str, 
        expires_at
    ) -> str:
        """Create HTML email template for password reset."""
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Reset Your Password - Dhanur AI</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f4f4f4;
                }}
                .container {{
                    background: white;
                    border-radius: 10px;
                    padding: 30px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    text-align: center;
                    border-bottom: 2px solid #007bff;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                .logo {{
                    font-size: 28px;
                    font-weight: bold;
                    color: #007bff;
                    margin-bottom: 10px;
                }}
                .reset-box {{
                    background: #f8f9fa;
                    border-left: 4px solid #dc3545;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 5px;
                }}
                .cta-button {{
                    display: inline-block;
                    background: #dc3545;
                    color: white;
                    padding: 15px 30px;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                    margin: 20px 0;
                    text-align: center;
                }}
                .cta-button:hover {{
                    background: #c82333;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    text-align: center;
                    color: #666;
                    font-size: 14px;
                }}
                .warning {{
                    background: #fff3cd;
                    border: 1px solid #ffeaa7;
                    color: #856404;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">🔐 Dhanur AI</div>
                    <p>AI-Powered Content Creation Platform</p>
                </div>
                
                <h2>Reset Your Password</h2>
                
                <div class="reset-box">
                    <h3>🔑 Password Reset Request</h3>
                    <p>We received a request to reset your password for your Dhanur AI account.</p>
                    <p><strong>Reset Link Expires:</strong> {expires_at.strftime('%B %d, %Y at %I:%M %p UTC')}</p>
                </div>
                
                <p>Click the button below to reset your password. This link will expire in 1 hour for security reasons.</p>
                
                <div style="text-align: center;">
                    <a href="{reset_url}" class="cta-button">Reset Password</a>
                </div>
                
                <div class="warning">
                    <strong>⚠️ Security Notice:</strong>
                    <ul>
                        <li>This link will expire in 1 hour</li>
                        <li>If you didn't request this reset, please ignore this email</li>
                        <li>Your password will remain unchanged until you create a new one</li>
                    </ul>
                </div>
                
                <p><strong>Having trouble?</strong> If the button doesn't work, copy and paste this link into your browser:</p>
                <p style="word-break: break-all; background: #f8f9fa; padding: 10px; border-radius: 5px; font-family: monospace;">{reset_url}</p>
                
                <div class="footer">
                    <p>This email was sent because a password reset was requested for your account.</p>
                    <p>If you didn't request this, you can safely ignore this email.</p>
                    <p>© 2025 Dhanur AI. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def _get_role_permissions_html(self, role: str) -> str:
        """Get HTML list of permissions for a role."""
        permissions = {
            "admin": [
                "Create and manage campaigns",
                "Invite and manage team members", 
                "View analytics and reports",
                "Manage brand settings",
                "Full access to all features"
            ],
            "editor": [
                "Create and edit campaigns",
                "View analytics and reports",
                "Collaborate with team members"
            ],
            "viewer": [
                "View campaigns and content",
                "View analytics and reports",
                "Read-only access"
            ]
        }
        
        role_perms = permissions.get(role, ["Basic access"])
        return "".join([f"<li>{perm}</li>" for perm in role_perms])
    
    async def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send email using SMTP."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def _send_mock_email(
        self, 
        to_email: str, 
        brand_name: str, 
        inviter_name: str,
        role: str, 
        message: str, 
        invitation_url: str, 
        expires_at
    ) -> bool:
        """Send mock email (for development/testing)."""
        try:
            logger.info("=" * 60)
            logger.info("📧 MOCK EMAIL SENT")
            logger.info("=" * 60)
            logger.info(f"To: {to_email}")
            logger.info(f"Subject: You're invited to join {brand_name} on Dhanur AI")
            logger.info(f"From: {self.from_name} <{self.from_email}>")
            logger.info("-" * 60)
            logger.info(f"Brand: {brand_name}")
            logger.info(f"Invited by: {inviter_name}")
            logger.info(f"Role: {role}")
            logger.info(f"Message: {message}")
            logger.info(f"Invitation URL: {invitation_url}")
            logger.info(f"Expires: {expires_at}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in mock email: {e}")
            return False
    
    async def _send_mock_password_reset_email(
        self, 
        to_email: str, 
        reset_url: str, 
        expires_at
    ) -> bool:
        """Send mock password reset email (for development/testing)."""
        try:
            logger.info("=" * 60)
            logger.info("📧 MOCK PASSWORD RESET EMAIL SENT")
            logger.info("=" * 60)
            logger.info(f"To: {to_email}")
            logger.info(f"Subject: Reset Your Password - Dhanur AI")
            logger.info(f"From: {self.from_name} <{self.from_email}>")
            logger.info("-" * 60)
            logger.info(f"Reset URL: {reset_url}")
            logger.info(f"Expires: {expires_at}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in mock password reset email: {e}")
            return False

# Global email service instance
email_service = EmailService()