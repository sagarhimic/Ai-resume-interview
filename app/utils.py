import random
from datetime import datetime

def generate_random_meeting_id():
    numbers = "23456789"
    # Shuffle and pick 6 digits
    meeting_numbers = ''.join(random.sample(numbers, 6))
    # Shuffle again for extra randomness
    meeting_id = ''.join(random.sample(meeting_numbers, len(meeting_numbers)))
    return meeting_id

def generate_random_password():
    chars = "abcdefghijklmnopqrstuvwxyz"
    numbers = "23456789"

    # Pick 4 random letters
    pwd1 = ''.join(random.sample(chars, 4))
    # Pick 2 random digits
    pwd2 = ''.join(random.sample(numbers, 2))
    # Shuffle combined password
    password_list = list(pwd1 + pwd2)
    random.shuffle(password_list)

    password = ''.join(password_list)
    return password

def clean_utf8(text):
    if not text:
        return ""
    return text.encode("utf-8", errors="ignore").decode("utf-8")

def format_interview_date(value):
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value))
    return dt.strftime("%d %b %Y %I:%M %p")
