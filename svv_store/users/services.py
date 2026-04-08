import random
import smtplib
from django.utils import timezone

from svv_store import settings
from svv_store.settings import (
    SMS_API_URL, SMS_USERNAME, SMS_PASSWORD, SMS_SENDER_ID, SMS_TMID,
    SMS_OTP_ENTITYID, SMS_OTP_TPID,
    SMS_ORDER_ENTITYID, SMS_ORDER_TPID,
    SMS_DELIVERY_ENTITYID, SMS_DELIVERY_TPID,
)
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


def _send_sms(params):
    """
    Send SMS via connectbind API.
    Builds URL manually to prevent urllib from percent-encoding the comma in
    tmid (e.g. '123,456' must stay literal, not become '123%2C456'), which
    causes PE_TM_HASH_NOT_REGISTERED on the DLT system.
    """
    import urllib.parse
    tmid = params.pop('tmid')
    query = urllib.parse.urlencode(params)
    url = f"{SMS_API_URL}?{query}&tmid={tmid}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text.strip() or None
    except requests.RequestException as e:
        print(f"SMS sending failed: {e}")
        raise


def _format_destination(mobile):
    """Ensure mobile number has 91 country code prefix."""
    mobile = str(mobile).strip()
    if mobile.startswith('+'):
        mobile = mobile[1:]
    if not mobile.startswith('91'):
        mobile = '91' + mobile
    return mobile


def send_sms_notification(identifier, otp, user):
    """
    Send OTP SMS and return message ID
    """
    message = (
        f"Your Vegga Fresh OTP is {otp} for login. "
        f"Do not share this code with anyone. "
        f"This OTP is valid for 5 minutes. -Vegga Fresh"
    )

    params = {
        'username': SMS_USERNAME,
        'password': SMS_PASSWORD,
        'type': '0',
        'dlr': '1',
        'destination': _format_destination(identifier),
        'source': SMS_SENDER_ID,
        'message': message,
        'entityid': SMS_OTP_ENTITYID,
        'tempid': SMS_OTP_TPID,
        'tmid': SMS_TMID,
    }

    return _send_sms(params)


def send_order_placed_sms(mobile, user_name, order_id, total_amount):
    """
    Send Order Placed confirmation SMS
    """
    message = (
        f"Hi {user_name}, your order {order_id} has been successfully placed on Vegga Fresh. "
        f"Total Amount: {total_amount:.2f} "
        f"We will notify you once it's out for delivery. -Vegga Fresh"
    )

    params = {
        'username': SMS_USERNAME,
        'password': SMS_PASSWORD,
        'type': '0',
        'dlr': '1',
        'destination': _format_destination(mobile),
        'source': SMS_SENDER_ID,
        'message': message,
        'entityid': SMS_ORDER_ENTITYID,
        'tempid': SMS_ORDER_TPID,
        'tmid': SMS_TMID,
    }

    return _send_sms(params)


def send_out_for_delivery_sms(mobile, user_name, order_id):
    """
    Send Out for Delivery SMS
    """
    message = (
        f"Hi {user_name}, your Vegga Fresh order {order_id} is out for delivery. "
        f"It will reach you shortly. Please keep cash ready if COD. -Vegga Fresh"
    )

    params = {
        'username': SMS_USERNAME,
        'password': SMS_PASSWORD,
        'type': '0',
        'dlr': '1',
        'destination': _format_destination(mobile),
        'source': SMS_SENDER_ID,
        'message': message,
        'entityid': SMS_DELIVERY_ENTITYID,
        'tempid': SMS_DELIVERY_TPID,
        'tmid': SMS_TMID,
    }

    return _send_sms(params)


def send_email_otp(email, otp, user):
    """
    Send OTP via email with clear error handling.
    Returns True on success, raises on failure.
    """
    user_name = user.first_name if user and user.first_name else "User"

    subject = EMAIL_OTP_TEMPLATE['subject']
    html_message = EMAIL_OTP_TEMPLATE['body'].format(user_name=user_name, otp=otp)
    plain_message = EMAIL_OTP_TEMPLATE['text_body'].format(user_name=user_name, otp=otp)

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False
        )
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP authentication failed — check EMAIL_HOST_USER/PASSWORD: {e}")
        raise

    except smtplib.SMTPConnectError as e:
        print(f"SMTP connection failed — check EMAIL_HOST/PORT: {e}")
        raise

    except smtplib.SMTPRecipientsRefused as e:
        print(f"Recipient address rejected by server ({email}): {e}")
        raise

    except smtplib.SMTPException as e:
        print(f"SMTP error while sending email: {e}")
        raise

    except Exception as e:
        print(f"Unexpected error sending email to {email}: {e}")
        raise


def create_or_update_otp(identifier, identifier_type, user):
    """
    Create or update OTP for a given identifier (email or mobile).
    Only saves to DB if sending succeeds.
    """
    otp = generate_unique_otp(identifier)

    try:
        # Send OTP first — before touching the DB
        if identifier_type == 'mobile':
            message_id = send_sms_notification(identifier, otp, user)
        else:  # email
            send_email_otp(identifier, otp, user)
            message_id = "email_sent"

    except smtplib.SMTPAuthenticationError:
        raise ValueError("Email service authentication failed. Please contact support.")

    except smtplib.SMTPConnectError:
        raise ValueError("Unable to reach email server. Please try again later.")

    except smtplib.SMTPRecipientsRefused:
        raise ValueError(f"The email address '{identifier}' was rejected. Please check and try again.")

    except smtplib.SMTPException as e:
        raise ValueError(f"Failed to send OTP email: {e}")

    except Exception as e:
        raise ValueError(f"Failed to send OTP: {e}")

    # Only reach here if sending succeeded — now safe to update DB
    OTP.objects.filter(identifier=identifier, is_used=False).update(is_used=True)

    otp_obj = OTP.objects.create(
        identifier=identifier,
        identifier_type=identifier_type,
        otp=otp,
        message_id=message_id
    )
    return otp_obj