EMAIL_OTP_TEMPLATE = {
    'subject': 'Your OTP for Shadow App',
    'body': """
    <html>
        <body>
            <p>Hi {user_name},</p>
            <p>Your Shadow App account OTP is: <strong>{otp}</strong></p>
            <p>This OTP is valid for 10 minutes.</p>
            <p>Thanks,<br>Team Shadow INTECH</p>
        </body>
    </html>
    """,
    'text_body': """
    Hi {user_name},
    Your Shadow App account OTP is: {otp}
    This OTP is valid for 10 minutes.
    Thanks,
    Team Shadow INTECH
    """
}