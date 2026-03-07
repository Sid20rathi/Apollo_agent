import resend
from config import config

class ResendClient:
    def __init__(self):
        resend.api_key = config.RESEND_API_KEY
        self.sender = f"{config.COMPANY_NAME} <{config.SENDER_EMAIL}>"

    def send_pitch_email(self, to_email, subject, html_body):
        """
        Send an email via the Resend API
        """
        try:
            params = {
                "from": self.sender,
                "to": [to_email],
                "subject": subject,
                "html": html_body
            }
            
            response = resend.Emails.send(params)
            print(f"Email sent successfully to {to_email}. ID: {response.get('id')}")
            return True, response.get('id')
        except Exception as e:
            print(f"Error sending email to {to_email}: {str(e)}")
            return False, str(e)
