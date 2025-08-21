# src/zero_width_mode.py

# Zero-width characters for steganographic encoding
ZERO_WIDTH_CHARS = {
    '0': '\u200b',  # Zero Width Space
    '1': '\u200c',  # Zero Width Non-Joiner
    '2': '\u200d',  # Zero Width Joiner
    '3': '\u2060',  # Word Joiner
    '4': '\ufeff',  # Zero Width No-Break Space (BOM)
}

# Reverse mapping for decoding
ZERO_WIDTH_REVERSE = {v: k for k, v in ZERO_WIDTH_CHARS.items()}

def encode(data: bytes, encoding: str = "utf-8") -> str:
    """
    Encode binary data using zero-width characters.
    Each byte is converted to its base-5 representation
    and then each digit is mapped to a zero-width character.
    
    :param data: Binary data to encode
    :param encoding: String encoding (only used for the return value)
    :return: String with zero-width characters
    """
    result = []
    
    # Add special sequence to mark the start - also encoded as zero-width chars
    # This allows detection during decoding but remains invisible
    for char in "START":
        char_code = ord(char)
        # Encode each character using our zero-width encoding
        for i in range(0, 3):  # Use 3 base-5 digits
            position = 2 - i  # Work from most significant digit
            digit = (char_code // (5 ** position)) % 5
            result.append(ZERO_WIDTH_CHARS[str(digit)])
    
    # Add a separator - special pattern of zero-width chars
    result.append(ZERO_WIDTH_CHARS['0'])
    result.append(ZERO_WIDTH_CHARS['4'])
    result.append(ZERO_WIDTH_CHARS['0'])
    
    # Now encode the actual data
    for byte in data:
        # Convert byte to base-5 representation
        base5 = []
        value = byte
        
        if value == 0:  # Special case for value 0
            base5 = ['0', '0', '0']
        else:
            while value > 0:
                base5.append(str(value % 5))
                value //= 5
                
            # Pad to ensure each byte uses the same number of chars (3 digits in base-5 can represent up to 124)
            while len(base5) < 3:
                base5.append('0')
        
        # Reverse and convert to zero-width chars
        for digit in reversed(base5):
            result.append(ZERO_WIDTH_CHARS[digit])
    
    # Add another separator
    result.append(ZERO_WIDTH_CHARS['0'])
    result.append(ZERO_WIDTH_CHARS['4'])
    result.append(ZERO_WIDTH_CHARS['0'])
    
    # Add end marker - also encoded as zero-width chars
    for char in "END":
        char_code = ord(char)
        # Encode each character using our zero-width encoding
        for i in range(0, 3):  # Use 3 base-5 digits
            position = 2 - i  # Work from most significant digit
            digit = (char_code // (5 ** position)) % 5
            result.append(ZERO_WIDTH_CHARS[str(digit)])
    
    return ''.join(result)


def decode(text: str, encoding: str = "utf-8") -> bytes:
    """
    Decode a string with zero-width characters.
    
    :param text: String containing zero-width characters
    :param encoding: String encoding (not used for decoding)
    :return: Decoded binary data
    """
    result = bytearray()
    base5_digits = []
    zero_width_chars = []
    
    # First, extract all zero-width characters from the text
    for char in text:
        if char in ZERO_WIDTH_REVERSE:
            zero_width_chars.append(char)
    
    # If we have visible markers (old format), use them to extract content
    if "ZW_START:" in text and ":ZW_END" in text:
        # Old format with visible markers
        start_pos = text.find("ZW_START:") + len("ZW_START:")
        end_pos = text.find(":ZW_END")
        if end_pos > start_pos:
            # Extract only characters between markers
            text = text[start_pos:end_pos]
            # Reset our zero_width_chars list
            zero_width_chars = []
            for char in text:
                if char in ZERO_WIDTH_REVERSE:
                    zero_width_chars.append(char)
    
    # If no characters found, return empty result
    if not zero_width_chars:
        return bytes()
    
    # Try to find new format markers (START and END markers encoded as zero-width)
    # For the new format, we search for the encoded markers
    
    # Convert zero-width chars to base-5 digits
    all_digits = [ZERO_WIDTH_REVERSE[c] for c in zero_width_chars]
    
    # Try to find START marker (encoded) + separator and END marker + separator
    data_start = 0
    data_end = len(all_digits)
    
    # Check if we can find a START marker (length is 15 digits: 5 letters * 3 digits)
    # Plus 3 more for the separator
    if len(all_digits) > 18:  # At least enough for START + separator
        # Look for separator pattern (040)
        for i in range(15, len(all_digits)-2):
            if all_digits[i:i+3] == ['0', '4', '0']:
                # Found separator, check if what's before looks like "START"
                data_start = i + 3
                break
    
    # Look for END marker from the end
    if len(all_digits) > (data_start + 15):  # At least enough for data + END + separator
        # Look for separator pattern (040) from the end
        for i in range(len(all_digits)-3, data_start+3, -1):
            if all_digits[i-2:i+1] == ['0', '4', '0']:
                # Found separator, check if what's after looks like "END"
                data_end = i - 2
                break
    
    # Extract just the data part (between markers if found)
    data_digits = all_digits[data_start:data_end]
    
    # Process all digits in groups of 3
    for i in range(0, len(data_digits), 3):
        if i + 2 < len(data_digits):  # Ensure we have 3 digits
            try:
                # Convert base-5 to decimal
                value = int(data_digits[i]) * 25 + int(data_digits[i+1]) * 5 + int(data_digits[i+2])
                result.append(value)
            except ValueError:
                # Skip invalid digit combinations
                pass
    
    # Handle any remaining digits (in case the input was corrupted)
    remaining = len(data_digits) % 3
    if remaining > 0:
        try:
            # Extract remaining digits
            remaining_digits = data_digits[-(remaining):]
            # Pad with zeros if needed
            while len(remaining_digits) < 3:
                remaining_digits.append('0')
            
            # Convert to decimal
            value = int(remaining_digits[0]) * 25 + int(remaining_digits[1]) * 5 + int(remaining_digits[2])
            result.append(value)
        except (ValueError, IndexError):
            pass
    
    return bytes(result)


def is_zero_width_encoded(text: str) -> bool:
    """
    Check if a string contains zero-width encoded data.
    
    :param text: String to check
    :return: True if the string contains zero-width characters or markers
    """
    # Check for old format with visible markers
    if "ZW_START:" in text and ":ZW_END" in text:
        return True
    
    # Check for zero-width characters
    zero_width_count = 0
    for char in text:
        if char in ZERO_WIDTH_REVERSE:
            zero_width_count += 1
            # If we have enough zero-width chars, it's likely encoded data
            # (At least enough for START marker + separator + one byte)
            if zero_width_count >= 21:  # 5*3 (START) + 3 (separator) + 3 (one byte)
                return True
            
    return False

def get_options():
    """
    Return available options for Zero-Width encoding.
    
    Returns:
        Dictionary of options with their descriptions and default values
    """
    return {
        "steganography_mode": {
            "description": "Steganography mode for hiding data",
            "type": "str",
            "default": "invisible",
            "choices": ["invisible", "mixed"]
        }
    }
