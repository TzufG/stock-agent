"""
Email sender using Gmail SMTP.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class EmailSender:
    """Sends emails via Gmail SMTP."""

    def __init__(
        self,
        smtp_email: str,
        smtp_password: str,
        to_email: str,
    ):
        self.smtp_email = smtp_email
        self.smtp_password = smtp_password
        self.to_email = to_email
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587

    def send(self, subject: str, body: str) -> bool:
        """
        Send an email.
        Returns True if successful.
        """
        if not self.smtp_email or not self.smtp_password or not self.to_email:
            print("Email not configured")
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_email
            msg["To"] = self.to_email

            # Plain text version
            text_part = MIMEText(body, "plain")
            msg.attach(text_part)

            # Connect and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.sendmail(self.smtp_email, self.to_email, msg.as_string())

            print(f"Email sent to {self.to_email}")
            return True

        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    def send_alert(self, ticker: str, body: str) -> bool:
        """Send a price alert email."""
        subject = f"🚨 Price Alert: {ticker}"
        return self.send(subject, body)

    def send_morning_report(self, body: str) -> bool:
        """Send the morning briefing email."""
        subject = "📊 Stock Agent - Morning Briefing"
        return self.send(subject, body)
