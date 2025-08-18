import random
import string

def generate_filename(max_length: int) -> str:
    """Generate random filename with length from 1 to max_length."""
    chars = string.ascii_letters + string.digits
    length = random.randint(1, max_length)  # randomly chosen length
    return "".join(random.choice(chars) for _ in range(length))
