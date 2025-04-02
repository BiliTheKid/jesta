import requests
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def send_message(to: str, body: str) -> bool:
    """
    Sends a message to the specified recipient with the given body.

    Args:
        to (str): The recipient's address (e.g., phone number or user ID).
        body (str): The content of the message to be sent.

    Returns:
        bool: True if the message was sent successfully, False if it failed.
    """
    # Retrieve token from environment variables (dynamic value)
    token = os.getenv('TOKEN')
    if not token:
        logger.error("Authorization token is missing. Please check the environment variables.")
        return False

    # API URL (static)
    url = os.getenv('API_URL').rstrip('/')
    url_with_type = url + '/messages/text'    

    print(url_with_type )
    # Prepare payload
    payload = {
        "to": to,
        "body": body
    }

    # Static headers + dynamic authorization header
    headers = {
        "accept": "application/json",         # Static
        "content-type": "application/json",   # Static
        "authorization": f"Bearer {token}"    # Dynamic (loaded from environment)
    }

    try:
        # Send POST request
        response = requests.post(url_with_type , json=payload, headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            logger.info(f"Message successfully sent to {to}.")
            return True
        else:
            logger.error(f"Failed to send message. Status code: {response.status_code}, Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        # Log any request exceptions
        logger.error(f"An error occurred while sending the message: {e}")
        return False
    except Exception as e:
        # Log unexpected errors
        logger.error(f"An unexpected error occurred: {e}")
        return False
