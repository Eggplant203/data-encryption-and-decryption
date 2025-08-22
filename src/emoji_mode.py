# src/emoji_mode.py
import random
import math

# Emoji list for encoding (using 256 different emojis to represent each byte)
EMOJI_TABLE = [
    "😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😆", "😉", "😊", "😋", "😎", "😍", "😘", "🥰", "😗",
    "😙", "😚", "🙂", "🤗", "🤩", "🤔", "🤨", "😐", "😑", "😶", "🙄", "😏", "😣", "😥", "😮", "🤐",
    "😯", "😪", "😫", "😴", "😌", "😛", "😜", "😝", "🤤", "😒", "😓", "😔", "😕", "🙃", "🤑", "😲",
    "☹️", "🙁", "😖", "😞", "😟", "😤", "😢", "😭", "😦", "😧", "😨", "😩", "🤯", "😬", "😰", "😱",
    "🥵", "🥶", "😳", "🤪", "😵", "😡", "😠", "🤬", "😷", "🤒", "🤕", "🤢", "🤮", "🤧", "😇", "🤠",
    "🤡", "🥳", "🥴", "🥺", "🤥", "🤫", "🤭", "🧐", "🤓", "😈", "👿", "👹", "👺", "💀", "👻", "👽",
    "🤖", "💩", "😺", "😸", "😹", "😻", "😼", "😽", "🙀", "😿", "😾", "👶", "👧", "🧒", "👦", "👩",
    "🧑", "👨", "👵", "🧓", "👴", "👲", "👳", "🧕", "🤵", "👰", "🤰", "🤱", "👼", "🎅", "🤶", "🦸",
    "🦹", "🧙", "🧚", "🧛", "🧜", "🧝", "🧞", "🧟", "💆", "💇", "🚶", "🧍", "🧎", "🏃", "💃", "🕺",
    "🕴️", "👯", "🧖", "🧗", "🤺", "🏇", "⛷️", "🏂", "🏌️", "🏄", "🚣", "🏊", "⛹️", "🏋️", "🚴", "🚵",
    "🤸", "🤼", "🤽", "🤾", "🤹", "🧘", "🛀", "🛌", "👭", "👫", "👬", "💏", "💑", "👪", "👨‍👩‍👧", "👨‍👩‍👧‍👦",
    "👨‍👩‍👦‍👦", "👨‍👩‍👧‍👧", "👨‍👨‍👦", "👨‍👨‍👧", "👨‍👨‍👧‍👦", "👨‍👨‍👦‍👦", "👨‍👨‍👧‍👧", "👩‍👩‍👦", "👩‍👩‍👧", "👩‍👩‍👧‍👦",
    "👩‍👩‍👦‍👦", "👩‍👩‍👧‍👧", "👨‍👦", "👨‍👦‍👦", "👨‍👧", "👨‍👧‍👦", "👨‍👧‍👧", "👩‍👦", "👩‍👦‍👦", "👩‍👧",
    "👩‍👧‍👦", "👩‍👧‍👧", "🗣️", "👤", "👥", "👣", "🦰", "🦱", "🦳", "🦲", "🐵", "🐒", "🦍", "🦧",
    "🐶", "🐕", "🦮", "🐕‍🦺", "🐩", "🐺", "🦊", "🦝", "🐱", "🐈", "🦁", "🐯", "🐅", "🐆", "🐴", "🐎",
    "🦄", "🦓", "🦌", "🐮", "🐂", "🐃", "🐄", "🐷", "🐖", "🐗", "🐽", "🐏", "🐑", "🐐", "🐪", "🐫"
]

# Extend emoji table to 256 elements by adding more emojis
ADDITIONAL_EMOJIS = [
    "🦙", "🦒", "🐘", "🦏", "🦛", "🐭", "🐁", "🐀", "🐹", "🐰", "🐇", "🐿️", "🦔", "🦇", "🐻", "🐨",
    "🐼", "🦥", "🦦", "🦨", "🦘", "🦡", "🐾", "🦃", "🐔", "🐓", "🐣", "🐤", "🐥", "🐦", "🐧", "🕊️",
    "🦅", "🦆", "🦢", "🦉", "🦩", "🦚", "🦜", "🐸", "🐊", "🐢", "🦎", "🐍", "🐲", "🐉", "🦕", "🦖",
    "🐳", "🐋", "🐬", "🐟", "🐠", "🐡", "🦈", "🐙", "🐚", "🐌", "🦋", "🐛", "🐜", "🐝", "🐞", "🦗"
]

# Combine to have exactly 256 emojis
EMOJI_TABLE.extend(ADDITIONAL_EMOJIS)
EMOJI_TABLE = EMOJI_TABLE[:256]  # Take only the first 256 emojis

def shuffle_emoji_table(key: str = None):
    """Shuffle emoji table based on key to create randomness"""
    if key:
        # Use key to create seed for random
        seed = sum(ord(c) for c in key)
        random.seed(seed)
        shuffled = EMOJI_TABLE.copy()
        random.shuffle(shuffled)
        random.seed()  # Reset seed
        return shuffled
    return EMOJI_TABLE

def encode(data: bytes, encoding: str = "utf-8", key: str = None) -> str:
    """
    Mã hóa dữ liệu thành chuỗi emoji
    
    Args:
        data: Dữ liệu bytes cần mã hóa
        encoding: String encoding (không sử dụng trực tiếp nhưng cần để tương thích)
        key: Khóa để trộn bảng emoji (tùy chọn)
    
    Returns:
        Chuỗi emoji đã được mã hóa
    """
    if not data:
        return ""
    
    # Use original emoji table for encoding
    emoji_table = EMOJI_TABLE
    
    # Convert each byte to corresponding emoji
    result = ""
    for byte_val in data:
        result += emoji_table[byte_val]
    
    # If shuffle key provided, shuffle emoji order in result
    if key and key.strip():
        result = shuffle_emoji_sequence(result, key)
    
    return result

def shuffle_emoji_sequence(emoji_string: str, key: str) -> str:
    """
    Shuffle emoji order in string based on key
    """
    import random
    
    # Convert emoji string to list of individual emojis
    emoji_list = list(emoji_string)
    
    # Use key to create seed for random
    seed = sum(ord(c) for c in key)
    random.seed(seed)
    
    # Shuffle list
    random.shuffle(emoji_list)
    
    # Reset seed
    random.seed()
    
    # Join back to string
    return ''.join(emoji_list)

def unshuffle_emoji_sequence(shuffled_string: str, key: str) -> str:
    """
    Restore original order of emojis from shuffled string
    """
    import random
    
    # Convert string to list
    emoji_list = list(shuffled_string)
    
    # Create list of indices and shuffle with same seed
    indices = list(range(len(emoji_list)))
    seed = sum(ord(c) for c in key)
    random.seed(seed)
    random.shuffle(indices)
    random.seed()
    
    # Create result list with original order
    original_list = [''] * len(emoji_list)
    for i, shuffled_index in enumerate(indices):
        original_list[shuffled_index] = emoji_list[i]
    
    return ''.join(original_list)

def decode(text: str, encoding: str = "utf-8", key: str = None) -> bytes:
    """
    Decode emoji string back to original data
    
    Args:
        text: Emoji string to decode
        encoding: String encoding (not used directly but needed for compatibility)
        key: Key to restore emoji order (optional)
    
    Returns:
        Original bytes data
    """
    if not text:
        return b""
    
    # If shuffle key provided, restore original order first
    if key and key.strip():
        text = unshuffle_emoji_sequence(text, key)
    
    # Use original emoji table for decoding
    emoji_table = EMOJI_TABLE
    
    # Create reverse lookup table from emoji to index
    emoji_to_byte = {emoji: idx for idx, emoji in enumerate(emoji_table)}
    
    # Parse emojis from string and convert to bytes
    result = bytearray()
    i = 0
    while i < len(text):
        # Find longest matching emoji from current position
        found_emoji = None
        max_len = 0
        
        # Check from maximum possible length (some emojis may be longer than 1 Unicode character)
        for length in range(1, min(8, len(text) - i + 1)):
            potential_emoji = text[i:i+length]
            if potential_emoji in emoji_to_byte:
                if length > max_len:
                    found_emoji = potential_emoji
                    max_len = length
        
        if found_emoji:
            result.append(emoji_to_byte[found_emoji])
            i += max_len
        else:
            # Skip unrecognized character
            i += 1
    
    return bytes(result)

def get_info():
    """Return information about emoji mode"""
    return {
        "name": "Emoji",
        "description": "Encode data using emojis",
        "supports_key": True,
        "supports_encoding": False,  # No need for string encoding as always outputs emojis
        "file_extension": ".txt"
    }

def get_options():
    """
    Return available options for Emoji encoding.
    
    Returns:
        Dictionary of options with their descriptions and default values
    """
    return {
        "key": {
            "description": "Shuffle pattern to randomize emoji order in result",
            "type": "str",
            "default": "",
            "required": False,
            "decode_required": True,
            "example": "rainbow, animals, faces, secret123, mypattern",
            "note": "DIFFERENT from 'Use Key' (XOR encryption)! Shuffle Key reorders emojis in result. Example: 😵😪😪 → 😪😵😪. Leave empty = keep original order."
        }
    }
