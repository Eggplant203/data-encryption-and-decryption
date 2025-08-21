# src/sound_mode.py
import struct
import math
import io
import os

# MIDI constants
MIDI_HEADER = b'MThd\x00\x00\x00\x06\x00\x00\x00\x01\x01\xE0'  # MIDI header: format 0, 1 track, 480 ticks/quarter
TRACK_HEADER = b'MTrk'
NOTE_ON = 0x90
NOTE_OFF = 0x80
END_OF_TRACK = b'\x00\xFF\x2F\x00'

# Musical notes mapping (C4 to B6 range for better sound quality)
# Using 88 different notes (full piano range from A0 to C8)
NOTE_RANGE_START = 21  # A0
NOTE_RANGE_END = 108   # C8
TOTAL_NOTES = NOTE_RANGE_END - NOTE_RANGE_START + 1  # 88 notes

# Note names for debugging/display
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

def get_note_name(midi_note):
    """Convert MIDI note number to note name with octave"""
    if midi_note < 0 or midi_note > 127:
        return "Unknown"
    octave = (midi_note // 12) - 1
    note_name = NOTE_NAMES[midi_note % 12]
    return f"{note_name}{octave}"

def byte_to_notes(byte_val, encoding_method="single", scale_type="chromatic"):
    """
    Convert a single byte (0-255) to MIDI note(s)
    
    Args:
        byte_val: Byte value (0-255)
        encoding_method: "single", "dual", "chord"
        scale_type: "chromatic", "major", "minor", "pentatonic"
    
    Returns:
        List of MIDI note numbers
    """
    if encoding_method == "single":
        # For single note encoding, we need to encode full 8 bits
        # Use dual notes: first note for high part, second for low part
        # This ensures we can represent all 256 values uniquely
        high_part = byte_val // TOTAL_NOTES  # How many full cycles through note range
        low_part = byte_val % TOTAL_NOTES    # Position within note range
        
        # Use two notes: one for the octave multiplier, one for the note within octave
        note1 = NOTE_RANGE_START + min(high_part, TOTAL_NOTES - 1)
        note2 = NOTE_RANGE_START + low_part
        return [note1, note2]
    
    elif encoding_method == "dual":
        # Split byte into two 4-bit values and map to two notes
        high_nibble = (byte_val >> 4) & 0x0F  # Upper 4 bits (0-15)
        low_nibble = byte_val & 0x0F          # Lower 4 bits (0-15)
        
        note1 = NOTE_RANGE_START + high_nibble  # First 16 notes
        note2 = NOTE_RANGE_START + 16 + low_nibble  # Next 16 notes
        return [note1, note2]
    
    elif encoding_method == "chord":
        # Create a chord that preserves full byte information
        # Use root note for high bits, interval for low bits
        high_part = byte_val >> 4    # Upper 4 bits (0-15)
        low_part = byte_val & 0x0F   # Lower 4 bits (0-15)
        
        root_note = NOTE_RANGE_START + high_part  # Use first 16 notes
        # Create chord with intervals that encode the low part
        third_offset = 3 + (low_part % 4)     # Major/minor third variation (3-6)
        fifth_offset = 6 + (low_part // 4)    # Perfect/augmented fifth variation (6-9) 
        
        notes = [
            root_note,
            root_note + third_offset,
            root_note + fifth_offset
        ]
        # Ensure notes don't exceed range
        notes = [min(note, NOTE_RANGE_END) for note in notes]
        return notes
    
    return [NOTE_RANGE_START + (byte_val % TOTAL_NOTES)]

def notes_to_byte(notes, encoding_method="single"):
    """
    Convert MIDI note(s) back to original byte value
    
    Args:
        notes: List of MIDI note numbers
        encoding_method: "single", "dual", "chord"
    
    Returns:
        Byte value (0-255)
    """
    if not notes:
        return 0
    
    if encoding_method == "single":
        if len(notes) >= 2:
            note1, note2 = notes[0], notes[1]
            high_part = (note1 - NOTE_RANGE_START)
            low_part = (note2 - NOTE_RANGE_START) 
            byte_val = (high_part * TOTAL_NOTES + low_part) % 256
            return byte_val
        else:
            # Fallback for single note
            note = notes[0]
            return (note - NOTE_RANGE_START) % 256
    
    elif encoding_method == "dual" and len(notes) >= 2:
        note1, note2 = notes[0], notes[1]
        high_nibble = (note1 - NOTE_RANGE_START) & 0x0F
        low_nibble = (note2 - NOTE_RANGE_START - 16) & 0x0F
        return (high_nibble << 4) | low_nibble
    
    elif encoding_method == "chord" and len(notes) >= 3:
        root_note, second_note, third_note = notes[0], notes[1], notes[2]
        
        # Decode the high and low parts
        high_part = (root_note - NOTE_RANGE_START) & 0x0F
        third_offset = (second_note - root_note) 
        fifth_offset = (third_note - root_note)
        
        # Reverse the encoding logic
        low_part_a = (third_offset - 3) % 4    # Extract from third interval
        low_part_b = (fifth_offset - 6)        # Extract from fifth interval  
        low_part = (low_part_b * 4 + low_part_a) & 0x0F
        
        return (high_part << 4) | low_part
    
    # Fallback
    return 0

def create_variable_length_quantity(value):
    """Create MIDI variable length quantity"""
    bytes_list = []
    bytes_list.append(value & 0x7F)
    value >>= 7
    while value > 0:
        bytes_list.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(bytes_list))

def create_midi_event(delta_time, event_type, channel, note, velocity):
    """Create a MIDI event"""
    event = create_variable_length_quantity(delta_time)
    event += bytes([event_type | channel, note, velocity])
    return event

def encode(data: bytes, encoding: str = "utf-8", **kwargs) -> bytes:
    """
    Encode data as MIDI file with musical notes representing bytes
    
    Args:
        data: The bytes data to encode
        encoding: String encoding (not used for MIDI output)
        **kwargs: Additional options
    
    Returns:
        MIDI file as bytes
    """
    if not data:
        return b''
    
    # Get options from kwargs
    encoding_method = kwargs.get('encoding_method', 'single')
    scale_type = kwargs.get('scale_type', 'chromatic')
    tempo = kwargs.get('tempo', 400)  # Ultra-fast tempo for shortest playback
    note_duration = kwargs.get('note_duration', 30)  # Ultra-short notes
    channel = kwargs.get('channel', 0)
    velocity = kwargs.get('velocity', 80)
    add_metadata = kwargs.get('add_metadata', True)
    overlap_notes = kwargs.get('overlap_notes', True)  # Allow notes to overlap for faster playback
    
    # Start building MIDI file
    midi_data = io.BytesIO()
    
    # Write proper MIDI header (format 0, 1 track, 480 ticks per quarter note)
    midi_data.write(b'MThd')           # Header chunk type
    midi_data.write(b'\x00\x00\x00\x06')  # Header length (6 bytes)
    midi_data.write(b'\x00\x00')      # Format type 0 (single track)
    midi_data.write(b'\x00\x01')      # Number of tracks (1)
    midi_data.write(b'\x01\xE0')      # Time division (480 ticks per quarter note)
    
    # Calculate track data
    track_data = io.BytesIO()
    
    # Set tempo meta event (always include for compatibility)
    microseconds_per_quarter = int(60000000 / tempo)
    tempo_event = b'\x00\xFF\x51\x03' + struct.pack('>I', microseconds_per_quarter)[1:]
    track_data.write(tempo_event)
    
    # Add time signature meta event (4/4 time)
    time_sig_event = b'\x00\xFF\x58\x04\x04\x02\x18\x08'
    track_data.write(time_sig_event)
    
    # Add metadata comment if requested
    if add_metadata:
        comment = f"Data encoded with sound_mode.py - Method: {encoding_method}, Bytes: {len(data)}"
        comment_bytes = comment.encode('utf-8')
        comment_event = b'\x00\xFF\x01' + create_variable_length_quantity(len(comment_bytes)) + comment_bytes
        track_data.write(comment_event)
    
    # Convert each byte to musical notes
    for i, byte_val in enumerate(data):
        notes = byte_to_notes(byte_val, encoding_method, scale_type)
        
        if overlap_notes:
            # Overlapping mode: start new notes before previous ones end
            # This dramatically reduces total playback time
            overlap_time = note_duration // 5  # 80% overlap (only 20% gap)
            
            # Play notes (note on events)
            for j, note in enumerate(notes):
                delta = 0 if j > 0 else (overlap_time if i > 0 else 0)
                event = create_midi_event(delta, NOTE_ON, channel, note, velocity)
                track_data.write(event)
            
            # Stop notes after short duration (only for the first byte to establish timing)
            if i == 0:
                for j, note in enumerate(notes):
                    delta = note_duration if j == 0 else 0
                    event = create_midi_event(delta, NOTE_OFF, channel, note, 0)
                    track_data.write(event)
        else:
            # Non-overlapping mode: traditional sequential playback
            # Play notes (note on events) - all notes start at the same time
            for j, note in enumerate(notes):
                delta = 0 if j > 0 else (note_duration if i > 0 else 0)
                event = create_midi_event(delta, NOTE_ON, channel, note, velocity)
                track_data.write(event)
            
            # Stop notes (note off events) - after note duration
            for j, note in enumerate(notes):
                delta = note_duration if j == 0 else 0
                event = create_midi_event(delta, NOTE_OFF, channel, note, 0)
                track_data.write(event)
    
    # If using overlap mode, stop all remaining notes at the end
    if overlap_notes and len(data) > 0:
        # Stop all notes that might still be playing
        final_byte = data[-1]
        final_notes = byte_to_notes(final_byte, encoding_method, scale_type)
        for j, note in enumerate(final_notes):
            delta = note_duration if j == 0 else 0
            event = create_midi_event(delta, NOTE_OFF, channel, note, 0)
            track_data.write(event)
    
    # End of track
    track_data.write(END_OF_TRACK)
    
    # Get track data
    track_bytes = track_data.getvalue()
    track_data.close()
    
    # Write track header with length
    midi_data.write(TRACK_HEADER)
    midi_data.write(struct.pack('>I', len(track_bytes)))
    midi_data.write(track_bytes)
    
    result = midi_data.getvalue()
    midi_data.close()
    
    return result

def decode(midi_data: bytes, encoding: str = "utf-8", **kwargs) -> bytes:
    """
    Decode MIDI file back to original data
    
    Args:
        midi_data: MIDI file as bytes
        encoding: String encoding (not used)
        **kwargs: Additional options
    
    Returns:
        Original data as bytes
    """
    if not midi_data or len(midi_data) < 14:
        return b''
    
    # Get options from kwargs
    encoding_method = kwargs.get('encoding_method', 'single')
    
    try:
        # Parse MIDI header
        if midi_data[:4] != b'MThd':
            raise ValueError("Invalid MIDI file header")
        
        # Find track data
        track_start = midi_data.find(b'MTrk')
        if track_start == -1:
            raise ValueError("No MIDI track found")
        
        track_start += 4  # Skip 'MTrk'
        track_length = struct.unpack('>I', midi_data[track_start:track_start+4])[0]
        track_data = midi_data[track_start+4:track_start+4+track_length]
        
        # Parse MIDI events to extract notes
        decoded_bytes = []
        pos = 0
        
        def read_variable_length(data, pos):
            """Read MIDI variable length quantity"""
            value = 0
            while pos < len(data):
                byte = data[pos]
                pos += 1
                value = (value << 7) | (byte & 0x7F)
                if not (byte & 0x80):
                    break
            return value, pos
        
        # Track note groups - each group represents one byte
        note_groups = []
        current_note_group = []
        notes_expected = 2 if encoding_method == "single" else (2 if encoding_method == "dual" else 3)
        
        while pos < len(track_data):
            # Read delta time
            if pos >= len(track_data):
                break
            delta_time, pos = read_variable_length(track_data, pos)
            
            if pos >= len(track_data):
                break
            
            # Read event
            event_byte = track_data[pos]
            pos += 1
            
            if event_byte == 0xFF:  # Meta event
                if pos >= len(track_data):
                    break
                meta_type = track_data[pos]
                pos += 1
                length, pos = read_variable_length(track_data, pos)
                pos += length  # Skip meta data
                
                if meta_type == 0x2F:  # End of track
                    break
            
            elif event_byte & 0xF0 == NOTE_ON:  # Note on
                if pos + 1 >= len(track_data):
                    break
                note = track_data[pos]
                velocity = track_data[pos + 1]
                pos += 2
                
                if velocity > 0:  # Actual note on
                    current_note_group.append(note)
                    
                    # Check if we have enough notes for this encoding method
                    if len(current_note_group) >= notes_expected:
                        note_groups.append(current_note_group[:notes_expected])
                        current_note_group = []
            
            elif event_byte & 0xF0 == NOTE_OFF:  # Note off
                if pos + 1 >= len(track_data):
                    break
                note = track_data[pos]
                velocity = track_data[pos + 1]
                pos += 2
                # We don't need to do anything special for note off in this simple decode
            
            else:
                # Other events - skip
                if pos + 1 < len(track_data):
                    pos += 2
        
        # Convert note groups back to bytes
        for note_group in note_groups:
            if note_group:
                byte_val = notes_to_byte(note_group, encoding_method)
                decoded_bytes.append(byte_val)
        
        return bytes(decoded_bytes)
    
    except Exception as e:
        raise ValueError(f"Failed to decode MIDI file: {str(e)}")

def save_midi_file(midi_data: bytes, output_path: str):
    """Save MIDI data to file"""
    with open(output_path, 'wb') as f:
        f.write(midi_data)

def get_mode_info():
    """Return information about this encoding mode"""
    return {
        "name": "Sound (MIDI)",
        "description": "Encodes data as MIDI musical notes",
        "supports_encoding": False,  # No need for string encoding as outputs binary MIDI
        "file_extension": ".mid"
    }

def get_options():
    """
    Return available options for Sound/MIDI encoding.
    
    Returns:
        Dictionary of options with their descriptions and default values
    """
    return {
        "encoding_method": {
            "description": "Method for converting bytes to musical notes",
            "type": "choice",
            "choices": ["single", "dual", "chord"],
            "default": "single",
            "required": True,
            "note": "Single: 1 byte = 1 note. Dual: 1 byte = 2 notes. Chord: 1 byte = 3-note chord. Dual and chord create richer music but larger files."
        },
        "scale_type": {
            "description": "Musical scale type for note selection",
            "type": "choice", 
            "choices": ["chromatic", "major", "minor", "pentatonic"],
            "default": "chromatic",
            "required": False,
            "note": "Chromatic uses all notes. Other scales create more musical sound but may reduce encoding precision."
        },
        "tempo": {
            "description": "Playback tempo in beats per minute (BPM)",
            "type": "int",
            "default": 400,  # Very fast tempo for much shorter playback
            "min": 60,
            "max": 500,      # Allow ultra-fast tempo
            "required": False,
            "note": "Controls playback speed. Higher tempo = shorter file duration. Does not affect encoding/decoding."
        },
        "note_duration": {
            "description": "Duration of each note in MIDI ticks",
            "type": "int", 
            "default": 30,   # Ultra-short notes for maximum speed
            "min": 10,       # Allow extremely short notes
            "max": 960,
            "required": False,
            "note": "Shorter durations create faster playback. 30 ticks = ultra-fast, 120 = fast, 480 = standard."
        },
        "velocity": {
            "description": "Note velocity (volume) from 1-127",
            "type": "int",
            "default": 80,
            "min": 1,
            "max": 127,
            "required": False,
            "note": "Higher values create louder notes. Does not affect encoding/decoding."
        },
        "add_metadata": {
            "description": "Add encoding information as MIDI comment",
            "type": "bool",
            "default": True,
            "required": False,
            "note": "Includes encoding method and file info in MIDI metadata. Helpful for debugging but not required for decoding."
        },
        "overlap_notes": {
            "description": "Allow notes to overlap for much faster playback",
            "type": "bool",
            "default": True,
            "required": False,
            "note": "When enabled, dramatically reduces playback time by overlapping notes. Recommended for large files. Does not affect encoding/decoding accuracy."
        }
    }
