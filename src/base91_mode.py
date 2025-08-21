# src/base91_mode.py

# Base91 encoding alphabet (extended ASCII)
BASE91_ALPHABET = [
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
    'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '!', '#', '$',
    '%', '&', '(', ')', '*', '+', ',', '.', '/', ':', ';', '<', '=',
    '>', '?', '@', '[', ']', '^', '_', '`', '{', '|', '}', '~', '"'
]


def encode(data: bytes, encoding: str = "utf-8") -> str:
    """
    Encode binary data using Base91 encoding.
    
    :param data: Binary data to encode
    :param encoding: String encoding (only used for the return value)
    :return: Base91 encoded string
    """
    result = []
    queue = 0
    bits = 0
    
    for byte in data:
        queue |= byte << bits
        bits += 8
        
        if bits >= 13:  # 13 bits can represent values up to 8191, just shy of 91^2=8281
            val = queue & 8191  # 0b1111111111111 (13 bits)
            
            # Encode as two Base91 characters
            quotient, remainder = divmod(val, 91)
            result.append(BASE91_ALPHABET[quotient])
            result.append(BASE91_ALPHABET[remainder])
            
            queue >>= 13
            bits -= 13
    
    # Handle remaining bits if any
    if bits > 0:
        val = queue & 8191
        quotient, remainder = divmod(val, 91)
        result.append(BASE91_ALPHABET[quotient])
        # If we have at least 7 bits, we need the second character too
        if bits > 7 or val > 90:
            result.append(BASE91_ALPHABET[remainder])
    
    return ''.join(result)


def decode(text: str, encoding: str = "utf-8") -> bytes:
    """
    Decode a Base91 encoded string.
    
    :param text: Base91 encoded string
    :param encoding: String encoding (not used in actual decoding)
    :return: Decoded binary data
    """
    # Create a reverse mapping from character to value
    char_to_val = {char: i for i, char in enumerate(BASE91_ALPHABET)}
    
    result = bytearray()
    queue = 0
    bits = 0
    value = -1
    
    for char in text:
        if char not in char_to_val:
            raise ValueError(f"Invalid Base91 character: {char}")
            
        # First value in pair or single remaining character
        if value == -1:
            value = char_to_val[char]
        # Second value in pair
        else:
            value = value * 91 + char_to_val[char]
            queue |= value << bits
            bits += 13  # Two Base91 characters represent 13 bits
            
            # Extract complete bytes
            while bits >= 8:
                result.append(queue & 255)  # Extract 8 bits
                queue >>= 8
                bits -= 8
            
            value = -1
    
    # Handle any remaining bits (should only happen if string length is odd)
    if value != -1:
        queue |= value << bits
        result.append(queue & 255)
    
    return bytes(result)
