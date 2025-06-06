import smtplib
from email.message import EmailMessage
from loguru import logger

from app.core.config import settings # To get notification and SMTP settings
from app.db.models import AgentTask, TaskStatus # Import enums for type checking

class NotificationService:
    def __init__(self):
        self.config = settings.notifications
        self.is_configured = all([
            self.config.enabled,
            self.config.recipient_email,
            settings.SMTP_HOST,
            settings.SMTP_USER,
            settings.SMTP_PASSWORD,
            settings.SMTP_SENDER_NAME # Ensure sender name is part of the check
        ])
        if self.config.enabled and not self.is_configured:
            logger.warning(
                "Email notifications are enabled in config.yml, but critical SMTP settings in .env "
                "(SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_SENDER_NAME) "
                "or recipient_email in config.yml are incomplete. No email notifications will be sent."
            )

    def _send_email(self, subject: str, content_html: str):
        if not self.is_configured:
            logger.debug("Email notifications not sent: Service not configured or explicitly disabled.")
            return

        msg = EmailMessage()
        msg.add_alternative(content_html, subtype='html') # Set HTML content
        
        msg['Subject'] = f"[{settings.APP_NAME}] {subject}"
        # SMTPlib uses the login user (settings.SMTP_USER) as the 'technical' sender.
        # The 'From' header is for display purposes.
        from_email_address = settings.SMTP_USER # This must be the authenticated email usually
        msg['From'] = f"{settings.SMTP_SENDER_NAME} <{from_email_address}>"
        msg['To'] = str(self.config.recipient_email) # Ensure it's a string

        try:
            logger.info(f"Attempting to send email notification to {self.config.recipient_email} with subject: {subject}")
            # Note: SMTP_SSL should be used for port 465, SMTP with starttls for port 587
            if settings.SMTP_PORT == 465:
                with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.login(str(settings.SMTP_USER), str(settings.SMTP_PASSWORD))
                    server.send_message(msg)
            else: # Default to port 587 with STARTTLS
                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.starttls() # Secure the connection
                    server.login(str(settings.SMTP_USER), str(settings.SMTP_PASSWORD))
                    server.send_message(msg)
            logger.info(f"Email sent successfully to {self.config.recipient_email}.")
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication Error: Failed to send email. Check credentials. Error: {e}")
        except smtplib.SMTPConnectError as e:
            logger.error(f"SMTP Connection Error: Failed to connect to SMTP server {settings.SMTP_HOST}:{settings.SMTP_PORT}. Error: {e}")
        except smtplib.SMTPSenderRefused as e:
             logger.error(f"SMTP Sender Refused: Address <{from_email_address}> refused by server. Error: {e.sender}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}", exc_info=True)

    def notify_task_status_change(self, task: AgentTask, base_app_url: str = "http://localhost"): # base_app_url should ideally come from settings for production
        """Checks config and sends a notification for a task status change with HTML content."""
        if not self.is_configured or not self.config.enabled:
            return

        subject = ""
        message_html_body = ""
        should_send = False
        
        # Ensure task status is a string for comparison if it's an Enum object
        current_task_status_str = task.status.value if isinstance(task.status, enum.Enum) else task.status

        task_link = f"{base_app_url}/admin/agent/task/{task.id}" # Example link

        common_style = "font-family: Arial, sans-serif; line-height: 1.6; color: #333;"
        p_style = "margin: 10px 0;"
        strong_style = "font-weight: bold;"
        link_style = "color: #007bff; text-decoration: none;"
        
        header_html = f"<h2 style='color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px;'>Frankie AI Agent Notification</h2>"
        footer_html = f"<p style='{p_style} font-size: 0.9em; color: #777; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px;'>This is an automated notification from {settings.APP_NAME}.</p>"

        if current_task_status_str == TaskStatus.AWAITING_REVIEW.value and self.config.notify_on.awaits_review:
            should_send = True
            subject = f"Task #{task.id} ({task.plugin_id}) Requires Review"
            message_html_body = f"""
            <div style="{common_style}">
                {header_html}
                <p style="{p_style}">Hello Administrator,</p>
                <p style="{p_style}">The agent task <strong style="{strong_style}">#{task.id}</strong> using plugin <strong style="{strong_style}">'{task.plugin_id}'</strong> has completed its processing and now <strong style="{strong_style}">requires your review and approval</strong>.</p>
                <ul style="list-style-type: none; padding-left: 0;">
                    <li style="{p_style}"><strong style="{strong_style}">Task ID:</strong> {task.id}</li>
                    <li style="{p_style}"><strong style="{strong_style}">Plugin:</strong> {task.plugin_id}</li>
                    <li style="{p_style}"><strong style="{strong_style}">Prompt:</strong> {task.prompt}</li>
                    <li style="{p_style}"><strong style="{strong_style}">Test Status:</strong> {task.test_status.value if isinstance(task.test_status, enum.Enum) else task.test_status}</li>
                </ul>
                <p style="{p_style}">Please log in to the admin panel to review the proposed changes:</p>
                <p style="{p_style}"><a href="{task_link}" style="{link_style}">Review Task #{task.id}</a></p>
                {footer_html}
            </div>
            """
        elif current_task_status_str == TaskStatus.APPLIED.value and self.config.notify_on.applied:
            should_send = True
            subject = f"Task #{task.id} ({task.plugin_id}) Successfully Applied"
            message_html_body = f"""
            <div style="{common_style}">
                {header_html}
                <p style="{p_style}">Hello Administrator,</p>
                <p style="{p_style}">The changes for agent task <strong style="{strong_style}">#{task.id}</strong> (Plugin: <strong style="{strong_style}">'{task.plugin_id}'</strong>) have been approved and successfully applied.</p>
                <ul style="list-style-type: none; padding-left: 0;">
                    <li style="{p_style}"><strong style="{strong_style}">Task ID:</strong> {task.id}</li>
                    <li style="{p_style}"><strong style="{strong_style}">Plugin:</strong> {task.plugin_id}</li>
                    {f'<li style="{p_style}"><strong style="{strong_style}">Commit Hash:</strong> {task.commit_hash}</li>' if task.commit_hash else ""}
                </ul>
                <p style="{p_style}">The system has been updated. If this involved code changes, you might need to rebuild and restart application services.</p>
                {footer_html}
            </div>
            """
        elif current_task_status_str == TaskStatus.ERROR.value and self.config.notify_on.error:
            should_send = True
            subject = f"Task #{task.id} ({task.plugin_id}) Encountered an Error"
            message_html_body = f"""
            <div style="{common_style}">
                {header_html}
                <p style="{p_style}">Hello Administrator,</p>
                <p style="{p_style}">The agent task <strong style="{strong_style}">#{task.id}</strong> (Plugin: <strong style="{strong_style}">'{task.plugin_id}'</strong>) failed with an error during processing.</p>
                 <ul style="list-style-type: none; padding-left: 0;">
                    <li style="{p_style}"><strong style="{strong_style}">Task ID:</strong> {task.id}</li>
                    <li style="{p_style}"><strong style="{strong_style}">Plugin:</strong> {task.plugin_id}</li>
                    <li style="{p_style}"><strong style="{strong_style}">Prompt:</strong> {task.prompt}</li>
                    <li style="{p_style}"><strong style="{strong_style}">Error Message:</strong> <pre style="background-color: #f8f8f8; border: 1px solid #ddd; padding: 10px; border-radius: 4px; white-space: pre-wrap;">{task.error_message}</pre></li>
                </ul>
                <p style="{p_style}">Please log in to the admin panel to review the task details and logs:</p>
                <p style="{p_style}"><a href="{task_link}" style="{link_style}">Review Task #{task.id}</a></p>
                {footer_html}
            </div>
            """
        
        if should_send:
            self._send_email(subject, message_html_body.strip())

# Global instance for easy access, will be used by other services/endpoints
notification_service = NotificationService()