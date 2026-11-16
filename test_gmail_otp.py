# this will test gmail otp fetchup "gmail_otp.py" workin fine or not
from utils.gmail_otp import (
    get_last_email_uid,
    wait_for_otp
)

print("Connecting to Gmail...")

last_uid = get_last_email_uid()

print("Gmail connected.")
print("Latest email UID:", last_uid)

print("\nNow trigger an OTP email from the Vrit website.")
print("Waiting for the new email...")

try:
    otp = wait_for_otp(
        after_uid=last_uid,
        timeout=120,
        poll_interval=5
    )

    print("\nOTP successfully extracted:", otp)

except TimeoutError as error:
    print("\nOTP retrieval failed:", error)
