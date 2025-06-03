# mail_test.py
# This script is for testing mail server functionality (SMTP send and IMAP check).
# WARNING: This script contains hardcoded credentials and is for testing purposes only.
# Do not use in a production environment with real credentials.

import smtplib
import imaplib
import time
from email.mime.text import MIMEText

# --- Configuration Variables ---
MAIL_SERVER = 'webmail.xr-kafka.sbs'
SMTP_PORT = 587  # Standard port for SMTP with STARTTLS
IMAP_PORT = 993  # Standard port for IMAPS (IMAP over SSL)
EMAIL_ADDRESS = 'info@webmail.xr-kafka.sbs'
EMAIL_PASSWORD = 'test123456'  # WARNING: Hardcoded password
TEST_RECIPIENT_EMAIL = 'info@webmail.xr-kafka.sbs' # Sending to self for this test
TEST_EMAIL_SUBJECT = "Mail Server Test Email"

# --- Send Email Function ---
def send_test_email():
    """
    Connects to the SMTP server, logs in, and sends a test email.
    """
    print(f"\nAttempting to send a test email from {EMAIL_ADDRESS} to {TEST_RECIPIENT_EMAIL} via {MAIL_SERVER}:{SMTP_PORT}...")
    try:
        # Create message
        msg = MIMEText("This is a test email from the mail_test.py script.")
        msg['Subject'] = TEST_EMAIL_SUBJECT
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = TEST_RECIPIENT_EMAIL

        # Connect to server
        print(f"Connecting to SMTP server {MAIL_SERVER} on port {SMTP_PORT}...")
        server = smtplib.SMTP(MAIL_SERVER, SMTP_PORT)
        server.set_debuglevel(0) # Set to 1 for detailed SMTP logs

        # Start TLS encryption
        print("Starting TLS encryption...")
        server.starttls()

        # Login
        print(f"Logging in as {EMAIL_ADDRESS}...")
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

        # Send email
        print(f"Sending email to {TEST_RECIPIENT_EMAIL}...")
        server.sendmail(EMAIL_ADDRESS, TEST_RECIPIENT_EMAIL, msg.as_string())
        print("Email sent successfully!")

        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Error: {e}. Check email address and password.")
    except smtplib.SMTPServerDisconnected as e:
        print(f"SMTP Server Disconnected: {e}. Check if the server is running or if the port is correct.")
    except smtplib.SMTPConnectError as e:
        print(f"SMTP Connection Error: {e}. Check mail server address and port.")
    except Exception as e:
        print(f"An error occurred while sending email: {e}")
    finally:
        if 'server' in locals() and server:
            print("Closing SMTP connection.")
            server.quit()
    return False

# --- Check Email Function ---
def check_test_email():
    """
    Connects to the IMAP server, logs in, and checks for the test email.
    """
    print(f"\nAttempting to check for the test email in INBOX for {EMAIL_ADDRESS} via {MAIL_SERVER}:{IMAP_PORT}...")
    search_criteria = f'(UNSEEN SUBJECT "{TEST_EMAIL_SUBJECT}")' # More specific: search for unread with specific subject
    # Fallback criteria if needed:
    # search_criteria = f'(SUBJECT "{TEST_EMAIL_SUBJECT}")' # Search any email with the subject
    # search_criteria = 'UNSEEN' # Search for any unread email

    try:
        # Connect to server using SSL
        print(f"Connecting to IMAP server {MAIL_SERVER} on port {IMAP_PORT} using SSL...")
        mail = imaplib.IMAP4_SSL(MAIL_SERVER, IMAP_PORT)
        mail.debug = 0 # Set to 4 for detailed IMAP logs

        # Login
        print(f"Logging in as {EMAIL_ADDRESS}...")
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

        # Select INBOX
        print("Selecting INBOX...")
        status, messages = mail.select('INBOX')
        if status != 'OK':
            print(f"Error selecting INBOX: {messages}")
            return False
        print(f"INBOX selected. Total messages: {messages[0].decode()}")

        # Search for the email
        print(f"Searching for email with criteria: {search_criteria}...")
        status, data = mail.search(None, search_criteria)
        if status != 'OK':
            print(f"Error searching for email: {data}")
            return False

        email_ids = data[0].split()
        if email_ids:
            print(f"Success! Found {len(email_ids)} email(s) matching the criteria.")
            # Optionally, fetch and display email subjects or other details
            # for msg_id in email_ids:
            #     status, msg_data = mail.fetch(msg_id, '(RFC822)')
            #     print(f"Email ID {msg_id}: {msg_data[0][1][:100]}...") # Print first 100 bytes
            return True
        else:
            print(f"No email found matching the criteria: {search_criteria}")
            print("This could be due to delivery delay or the email not being found.")
            return False

    except imaplib.IMAP4.error as e:
        print(f"IMAP Error: {e}. Check credentials, server details, or if IMAP is enabled.")
    except Exception as e:
        print(f"An error occurred while checking email: {e}")
    finally:
        if 'mail' in locals() and mail.state != 'LOGOUT':
            print("Logging out and closing IMAP connection.")
            try:
                mail.close() # Close selected mailbox
                mail.logout()
            except Exception as e_logout:
                print(f"Error during IMAP logout/close: {e_logout}")
    return False

# --- Main Execution Block ---
if __name__ == "__main__":
    print("--- Mail Server Test Script ---")
    print("WARNING: This script uses hardcoded credentials and is for testing purposes only.")

    if send_test_email():
        delay_seconds = 15
        print(f"\nWaiting for {delay_seconds} seconds for email delivery before checking...")
        time.sleep(delay_seconds)
        check_test_email()
    else:
        print("\nSkipping email check because sending failed.")

    print("\n--- Test Script Finished ---")
