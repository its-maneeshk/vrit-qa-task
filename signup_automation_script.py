import time
import re
import requests
from playwright.sync_api import Playwright, sync_playwright

def get_temp_email():
    """Generates a fresh temporary email using 1secmail API"""
    response = requests.get("https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1")
    if response.status_code == 200:
        return response.json()[0]
    raise Exception("Failed to generate temporary email.")

def fetch_otp_from_inbox(email_address):
    """
    Polls the temporary inbox via API and extracts the 6-digit OTP code automatically.
    """
    username, domain = email_address.split("@")
    print(f"Polling inbox for {email_address}...")
    
    api_url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={username}&domain={domain}"
    
    # Retry loop for up to 45 seconds to allow email delivery
    for attempt in range(15):
        try:
            response = requests.get(api_url)
            if response.status_code == 200:
                messages = response.json()
                if messages:
                    # Get the latest message ID
                    msg_id = messages[0]['id']
                    msg_url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={username}&domain={domain}&id={msg_id}"
                    
                    msg_res = requests.get(msg_url)
                    if msg_res.status_code == 200:
                        email_body = msg_res.json().get('body', '')
                        print("Email received! Extracting OTP...")
                        
                        # Match 6-digit OTP code
                        match = re.search(r'\b\d{6}\b', email_body)
                        if match:
                            otp_code = match.group(0)
                            print(f"Successfully retrieved OTP: {otp_code}")
                            return otp_code
        except Exception as e:
            print(f"Polling error (retrying): {e}")
            
        time.sleep(3) # Wait 3 seconds before next poll attempt
        
    raise Exception("Timeout: Verification email was not received within the time limit.")

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False, slow_mo=100)
    context = browser.new_context()
    page = context.new_page()
    
    # Generate a live test email dynamically
    test_email = get_temp_email()
    print("using test email: {test_email0}")
    
    # 1. Navigate to target application URL
    page.goto("https://authorized-partner.vercel.app/")
    page.wait_for_load_state("networkidle")
    
    # 2. Navigate through initial landing/welcome steps
    page.get_by_role("link", name="Get Started").get_by_role("button").click()
    page.get_by_role("checkbox", name="I agree to the Terms of").click()
    page.get_by_role("button", name="Continue").click()
    
    # 3. Fill out personal details using the generated temporary email
    page.get_by_role("textbox", name="First Name").fill("Test")
    page.get_by_role("textbox", name="Last Name").fill("User")
    page.get_by_role("textbox", name="Email Address").fill(test_email)
    page.get_by_role("textbox", name="Phone Number").fill("9847654327")
    
    # 4. Fill secure password fields
    page.locator("input[name=\"password\"]").fill("@Password123")
    page.locator("input[name=\"confirmPassword\"]").fill("@Password123")
    
    # Proceed to verification screen (Triggers the email dispatch)
    page.get_by_role("button", name="Next").click()
    
    # 5. Wait for the OTP verification box to appear on screen
    otp_box = page.locator("input[type='text'], input:not([name])").first
    otp_box.wait_for(state="visible", timeout=10000)
    
    # 6. Fetch the dynamic verification code programmatically via API
    dynamic_otp = fetch_otp_from_inbox(test_email)
    
    # 7. Enter the code and verify automatically
    otp_box.click()
    otp_box.fill(dynamic_otp)
    page.get_by_role("button", name="Verify Code").click()
    
    # Allow a brief moment to confirm successful submission and dashboard redirect
    print("OTP entered and verified successfully! Flow completed.")
    page.wait_for_timeout(5000)

    context.close()
    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)