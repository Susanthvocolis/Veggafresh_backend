import random
import smtplib
from django.utils import timezone

from svv_store import settings
from svv_store.settings import SMS_API_URL, SMS_USERNAME, SMS_PASSWORD, SMS_SENDER_ID, SMS_PEID, SMS_OTP_TPID
from utils.template_utils import EMAIL_OTP_TEMPLATE
from .models import OTP
import requests

from django.core.mail import send_mail


def generate_unique_otp(identifier):
    for _ in range(5):  # max 5 tries
        otp = str(random.randint(100000, 999999))
        exists = OTP.objects.filter(
            identifier=identifier,
            otp=otp,
            is_used=False,
            expired_at__gt=timezone.now()
        ).exists()
        if not exists:
            return otp
    raise Exception("Unable to generate unique OTP")



def send_sms_notification(identifier, otp, user):
    """
    Send OTP SMS and return message ID
    """
    user_name = user.first_name if user and user.first_name else "User"
    message = f"Hi {user_name}, Your Shadow App account OTP is: {otp}. Thanks, Team Shadow INTECH"

    final_url = (
        f"{SMS_API_URL}"
        f"?userid={SMS_USERNAME}&password={SMS_PASSWORD}&sender={SMS_SENDER_ID}"
        f"&mobileno={identifier}&msg={message}"  # Changed mobile to identifier
        f"&peid={SMS_PEID}&tpid={SMS_OTP_TPID}"
    )

    try:
        response = requests.get(final_url, timeout=10)
        response.raise_for_status()

        if response.text.startswith("Success"):
            message_id = response.text.split(":")[-1].strip()
            return message_id
        return None
    except requests.RequestException as e:
        print(f"SMS sending failed: {e}")
        return None


def send_email_otp(email, otp, user):
    """
    Send OTP via email with improved error handling
    """
    user_name = user.first_name if user and user.first_name else "User"

    subject = EMAIL_OTP_TEMPLATE['subject']
    html_message = EMAIL_OTP_TEMPLATE['body'].format(user_name=user_name, otp=otp)
    plain_message = EMAIL_OTP_TEMPLATE['text_body'].format(user_name=user_name, otp=otp)

    try:
        # Test SMTP connection first
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)

        # If connection test passes, send the email
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False
        )
        return True
    except smtplib.SMTPException as e:
        print(f"SMTP Error sending email: {e}")
        raise e

    except Exception as e:
        print(f"Unexpected error sending email: {e}")
        raise e
    return False


def create_or_update_otp(identifier, identifier_type, user):
    """Create or update OTP for a given identifier (email or mobile)"""
    otp = generate_unique_otp(identifier)

    # Mark old OTPs as used
    OTP.objects.filter(identifier=identifier, is_used=False).update(is_used=True)

    # Send OTP based on type
    if identifier_type == 'mobile':
        message_id = send_sms_notification(identifier, otp, user)
    else:  # email
        success = send_email_otp(identifier, otp, user)
        message_id = "email_sent" if success else None

    # Save OTP object
    otp_obj = OTP.objects.create(
        identifier=identifier,
        identifier_type=identifier_type,
        otp=otp,
        message_id=message_id
    )
    return otp_obj