from django.conf import settings
from itsdangerous import URLSafeTimedSerializer

from django.core.signing import TimestampSigner
from django.utils.timezone import now
from datetime import timedelta

SECRET_KEY = settings.SECRET_KEY
SALT = 'secure-media'

def generate_signed_token(file_path, expires_in=300):
    serializer = URLSafeTimedSerializer(SECRET_KEY, salt=SALT)
    return serializer.dumps(file_path)

def verify_signed_token(token, max_age=300):
    serializer = URLSafeTimedSerializer(SECRET_KEY, salt=SALT)
    return serializer.loads(token, max_age=max_age)


# Generate signed URL for secure file access
def get_signed_url(file_path,request):
    signer = TimestampSigner()
    signed_value = signer.sign(file_path)
    expiry_time = (now() + timedelta(minutes=10)).timestamp()  # Signed URL valid for 10 minutes
    base_url = request.build_absolute_uri('/')[:-1]
    return f"{base_url}/download/?file={signed_value}&expires={int(expiry_time)}"
