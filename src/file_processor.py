import os
import threading
import io
from src import util
from src.progress_handler import ProgressHandler

class ChunkProcessor:
    """
    Process large files in chunks to prevent system freezing.
    """
    def __init__(self, progress_handler=None, chunk_size=1024*1024):
        """
        Initialize processor with default chunk size of 1MB.
        
        :param progress_handler: Progress handler object
        :param chunk_size: Size of each chunk (bytes)
        """
        self.progress_handler = progress_handler
        self.chunk_size = chunk_size
        self.result = None
        self.is_running = False
        self.exception = None
    
    def encode_file(self, file_path, mode, str_encoding, use_key=False, key_text="", **kwargs):
        """
        Encode file in chunks and display progress.
        
        :param file_path: Path to file to encode
        :param mode: Encoding module (base64, base32, ...)
        :param str_encoding: String encoding
        :param use_key: Whether to use key or not
        :param key_text: Key for XOR encoding
        :param kwargs: Additional options for specific modes (e.g., UUID options)
        :return: Encoded string
        """
        self.is_running = True
        self.exception = None
        
        # Get file info
        name, ext, file_size = util.get_file_info(file_path)
        
        # Create progress handler if doesn't exist
        if not self.progress_handler:
            self.progress_handler = ProgressHandler("Encoding File", file_size)
            
        # Special case for QR Code mode direct text input
        if hasattr(mode, "__name__") and mode.__name__ == "qr_code_mode" and isinstance(file_path, str) and file_path.startswith("TEXT:"):
            # Direct text input for QR code mode
            text_content = file_path[5:]  # Remove TEXT: prefix
            self._encode_qr_text_worker(text_content, mode, str_encoding, use_key, key_text)
            return self.result
            
        # Create thread for processing
        thread = threading.Thread(target=self._encode_worker, 
                                 args=(file_path, mode, str_encoding, use_key, key_text, kwargs))
        thread.daemon = True
        thread.start()
        
        # Wait for thread to complete
        while thread.is_alive():
            # Update GUI
            if hasattr(threading, 'main_thread') and threading.current_thread() is threading.main_thread():
                import tkinter as tk
                tk._default_root.update()
        
        self.is_running = False
        
        # If there was an error, re-raise exception
        if self.exception:
            raise self.exception
        
        return self.result
    
    def _encode_qr_text_worker(self, text_content, mode, str_encoding, use_key, key_text):
        """
        Worker thread for direct text encoding to QR code without creating a file first.
        
        :param text_content: The text to encode in the QR code
        :param mode: The QR code mode module
        :param str_encoding: String encoding
        :param use_key: Whether to use key
        :param key_text: Key for XOR encoding
        """
        try:
            # Set initial progress
            if self.progress_handler:
                self.progress_handler.update_progress(0, 100)
                self.progress_handler.update_additional_status("Creating QR code...")
            
            # Convert text to bytes if needed
            if not isinstance(text_content, bytes):
                text_bytes = text_content.encode(str_encoding)
            else:
                text_bytes = text_content
                
            # Apply XOR if needed
            if use_key and key_text:
                from src import key_cipher
                if self.progress_handler:
                    self.progress_handler.update_additional_status("Encrypting with key...")
                text_bytes = key_cipher.apply_xor(text_bytes, key_text)
                
            # Update progress
            if self.progress_handler:
                self.progress_handler.update_progress(50, 100)
                self.progress_handler.update_additional_status("Generating QR code...")
                
            # Encode directly using the mode (qr_code_mode)
            import inspect
            sig = inspect.signature(mode.encode)
            if 'key' in sig.parameters and use_key and key_text:
                self.result = mode.encode(text_bytes, encoding=str_encoding, key=key_text)
            else:
                self.result = mode.encode(text_bytes, encoding=str_encoding)
            
            # Complete the progress
            if self.progress_handler:
                self.progress_handler.complete(success=True)
                
        except Exception as e:
            self.exception = e
            if self.progress_handler:
                self.progress_handler.complete(success=False, error_msg=str(e))
    
    def _encode_worker(self, file_path, mode, str_encoding, use_key, key_text, extra_options=None):
        """
        Worker thread to encode file.
        """
        if extra_options is None:
            extra_options = {}
            
        try:
            # Get file info
            name, ext, file_size = util.get_file_info(file_path)
            
            # Read file in chunks and encode
            processed_size = 0
            meta = f"{name}{ext}|{file_size}|{str_encoding}".encode("utf-8")
            
            # Use BytesIO to create in-memory buffer
            buffer = io.BytesIO()
            buffer.write(meta)
            buffer.write(b"\n")
            
            # Read and process file in chunks
            with open(file_path, "rb") as f:
                while chunk := f.read(self.chunk_size):
                    # Write chunk to buffer (not yet encoded)
                    buffer.write(chunk)
                    
                    # Update progress
                    processed_size += len(chunk)
                    if self.progress_handler:
                        self.progress_handler.update_progress(processed_size, file_size)
            
            # Notify user that file reading is complete, processing final steps
            if self.progress_handler:
                self.progress_handler.update_additional_status("Processing data...")
                
            # Get all data
            full_data = buffer.getvalue()
            
            # Apply XOR to entire data if key is provided (only once)
            if use_key and key_text:
                from src import key_cipher
                if self.progress_handler:
                    self.progress_handler.update_additional_status("Encrypting with key...")
                full_data = key_cipher.apply_xor(full_data, key_text)
            
            # Encode the entire data
            if self.progress_handler:
                self.progress_handler.update_additional_status("Encoding data...")
                
            # Check if the mode supports various parameters
            import inspect
            sig = inspect.signature(mode.encode)
            
            # Prepare encoding parameters
            encode_params = {
                'data': full_data,
                'encoding': str_encoding
            }
            
            # Add key parameter if supported and provided
            if 'key' in sig.parameters and use_key and key_text:
                encode_params['key'] = key_text
            
            # Add extra options if supported (for UUID mode and others)
            for param_name, param_value in extra_options.items():
                if param_name in sig.parameters:
                    encode_params[param_name] = param_value
            
            # Remove data parameter name and pass as first positional argument
            data_to_encode = encode_params.pop('data')
            
            # Call encode function with appropriate parameters
            self.result = mode.encode(data_to_encode, **encode_params)
            
            # Complete the progress
            if self.progress_handler:
                self.progress_handler.complete(success=True)
                
        except Exception as e:
            self.exception = e
            if self.progress_handler:
                # Mark as error and close progress bar
                self.progress_handler.complete(success=False, error_msg=str(e))
    
    def decode_file(self, file_path, mode, key_text="", **kwargs):
        """
        Decode file in chunks and display progress.
        
        :param file_path: Path to file to decode
        :param mode: Decoding module (base64, base32, ...)
        :param key_text: Key for XOR decoding
        :param kwargs: Additional options for specific modes (e.g., Emoji shuffle key)
        :return: Tuple (meta, raw_data)
        """
        self.is_running = True
        self.exception = None
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Create progress handler if doesn't exist
        if not self.progress_handler:
            self.progress_handler = ProgressHandler("Decoding File", file_size)
        
        # Create thread for processing
        thread = threading.Thread(target=self._decode_worker, 
                                 args=(file_path, mode, key_text, kwargs))
        thread.daemon = True
        thread.start()
        
        # Wait for thread to complete
        while thread.is_alive():
            # Update GUI
            if hasattr(threading, 'main_thread') and threading.current_thread() is threading.main_thread():
                import tkinter as tk
                tk._default_root.update()
        
        self.is_running = False
        
        # If there was an error, re-raise exception
        if self.exception:
            raise self.exception
        
        return self.result
    
    def _decode_worker(self, file_path, mode, key_text, kwargs=None):
        """
        Worker thread to decode file.
        """
        if kwargs is None:
            kwargs = {}
            
        try:
            # Get file size
            file_size = os.path.getsize(file_path)
            processed_size = 0
            
            # Check if we're using image mode or QR code mode or sound mode or barcode mode
            is_image_mode = False
            is_qr_code_mode = False
            is_sound_mode = False
            is_barcode_mode = False
            
            # Import necessary modules
            from src import image_mode, qr_code_mode, sound_mode, barcode_mode
            
            # Check if module is directly image_mode, qr_code_mode, sound_mode, or barcode_mode
            if mode == image_mode:
                is_image_mode = True
            elif mode == qr_code_mode:
                is_qr_code_mode = True
            elif mode == sound_mode:
                is_sound_mode = True
            elif mode == barcode_mode:
                is_barcode_mode = True
            # Check if the module has a __name__ attribute
            elif hasattr(mode, '__name__'):
                if mode.__name__ == 'image_mode':
                    is_image_mode = True
                elif mode.__name__ == 'qr_code_mode':
                    is_qr_code_mode = True
                elif mode.__name__ == 'sound_mode':
                    is_sound_mode = True
                elif mode.__name__ == 'barcode_mode':
                    is_barcode_mode = True
            
            # For QR Code mode, we need to handle PNG files differently
            if is_qr_code_mode and file_path.lower().endswith('.png'):
                # This is a PNG file being decoded as QR code
                # Read the PNG file and create QR_CODE format for qr_code_mode.decode()
                with open(file_path, "rb") as f:
                    png_data = f.read()
                    processed_size = len(png_data)
                    if self.progress_handler:
                        self.progress_handler.update_progress(processed_size, file_size)
                
                # Create the special QR_CODE format that qr_code_mode.decode expects
                data_str = f"QR_CODE:{len(png_data)}:{png_data.hex()}"
                
            elif is_sound_mode and file_path.lower().endswith(('.mid', '.midi')):
                # This is a MIDI file being decoded as sound
                # Read binary MIDI data
                with open(file_path, "rb") as f:
                    midi_data = f.read()
                    processed_size = len(midi_data)
                    if self.progress_handler:
                        self.progress_handler.update_progress(processed_size, file_size)
                
                # For sound mode, we pass the raw MIDI data directly
                data_str = midi_data
                
            elif is_barcode_mode and file_path.lower().endswith('.png'):
                # This is a PNG file being decoded as barcode
                # Read binary data for barcode PNG files
                with open(file_path, "rb") as f:
                    png_data = f.read()
                    processed_size = len(png_data)
                    if self.progress_handler:
                        self.progress_handler.update_progress(processed_size, file_size)
                
                # Create the special BARCODE format that barcode_mode.decode expects
                data_str = f"BARCODE:{len(png_data)}:{png_data.hex()}"
                
            elif is_image_mode and file_path.lower().endswith('.png'):
                # This is a PNG file being decoded as image
                # Read binary data for image files
                with open(file_path, "rb") as f:
                    img_data = f.read()
                    processed_size = len(img_data)
                    if self.progress_handler:
                        self.progress_handler.update_progress(processed_size, file_size)
                
                # Create the IMG_DATA format that image_mode.decode expects
                data_str = f"IMG_DATA:{len(img_data)}:{img_data.hex()}"
                
            elif file_path.lower().endswith('.png'):
                # PNG file but mode not specified - try to auto-detect
                try:
                    # First, try to decode as QR code
                    from pyzbar import pyzbar
                    from PIL import Image
                    img = Image.open(file_path)
                    decoded_objects = pyzbar.decode(img)
                    
                    if decoded_objects:
                        # This appears to be a QR code - create QR_CODE format
                        is_qr_code_mode = True
                        mode = qr_code_mode
                        
                        # Read the PNG file and create QR_CODE format for qr_code_mode.decode()
                        with open(file_path, "rb") as f:
                            png_data = f.read()
                            processed_size = len(png_data)
                            if self.progress_handler:
                                self.progress_handler.update_progress(processed_size, file_size)
                        
                        # Create the special QR_CODE format that qr_code_mode.decode expects
                        data_str = f"QR_CODE:{len(png_data)}:{png_data.hex()}"
                    else:
                        # Not a QR code, treat as regular image
                        is_image_mode = True
                        mode = image_mode
                        
                        # Read binary data for image files
                        with open(file_path, "rb") as f:
                            img_data = f.read()
                            processed_size = len(img_data)
                            if self.progress_handler:
                                self.progress_handler.update_progress(processed_size, file_size)
                        
                        # Create the IMG_DATA format that image_mode.decode expects
                        data_str = f"IMG_DATA:{len(img_data)}:{img_data.hex()}"
                except Exception as ex:
                    print(f"Error detecting QR code: {ex}")
                    # If any error occurs, default to image mode
                    is_image_mode = True
                    mode = image_mode
                    
                    # Read binary data for image files
                    with open(file_path, "rb") as f:
                        img_data = f.read()
                        processed_size = len(img_data)
                        if self.progress_handler:
                            self.progress_handler.update_progress(processed_size, file_size)
                    
                    # Create the IMG_DATA format that image_mode.decode expects
                    data_str = f"IMG_DATA:{len(img_data)}:{img_data.hex()}"
            else:
                # For text files, read as UTF-8
                try:
                    data_str = ""
                    with open(file_path, "r", encoding="utf-8") as f:
                        while chunk := f.read(self.chunk_size):
                            data_str += chunk
                            processed_size += len(chunk.encode('utf-8'))  # Calculate actual size
                            if self.progress_handler:
                                self.progress_handler.update_progress(processed_size, file_size)
                except UnicodeDecodeError:
                    # If we encounter UTF-8 decode error, it might be a binary file or different encoding
                    # Try to read it as binary and convert to hex string for safety
                    with open(file_path, "rb") as f:
                        binary_data = f.read()
                        processed_size = len(binary_data)
                        if self.progress_handler:
                            self.progress_handler.update_progress(processed_size, file_size)
                        # We'll try to guess if this is an image file
                        if binary_data.startswith(b'\x89PNG'):
                            # Looks like a PNG file, treat it as image
                            data_str = f"IMG_DATA:{len(binary_data)}:{binary_data.hex()}"
                            is_image_mode = True
                            from src import image_mode
                            mode = image_mode
                        else:
                            # Otherwise, just treat as a generic binary file
                            data_str = binary_data.hex()
                            raise ValueError("Could not decode file as UTF-8 text. File may be binary or corrupted.")
            
            # Notify start of decoding
            if self.progress_handler:
                self.progress_handler.update_additional_status("Decoding data...")
                
            # Decode data
            import inspect
            sig = inspect.signature(mode.decode)
            
            # Prepare decode arguments
            decode_args = {"encoding": "utf-8"}
            
            # Add key if supported and provided
            if 'key' in sig.parameters and key_text:
                decode_args['key'] = key_text
                
            # Add mode-specific options (kwargs)
            for key, value in kwargs.items():
                if key in sig.parameters:
                    decode_args[key] = value
            
            # For Sound mode, data_str is bytes, for other modes it's a string
            if is_sound_mode and isinstance(data_str, bytes):
                decoded = mode.decode(data_str, **decode_args)
            else:
                decoded = mode.decode(data_str, **decode_args)
            
            # Apply XOR if key is provided
            if key_text:
                if self.progress_handler:
                    self.progress_handler.update_additional_status("Decrypting with key...")
                from src import key_cipher
                decoded = key_cipher.apply_xor(decoded, key_text)
            
            # Split metadata and raw data
            if self.progress_handler:
                self.progress_handler.update_additional_status("Processing results...")
            
            # Check if this is QR code mode or Barcode mode for special handling
            # Image mode now handles metadata normally, so only QR code and Barcode need special handling
            is_special_mode = is_qr_code_mode or is_barcode_mode
            
            if is_special_mode:
                # For QR code and Barcode mode, we create the metadata format ourselves
                # since these modes don't preserve the header format
                name, ext, _ = util.get_file_info(file_path)
                
                if is_qr_code_mode:
                    # For QR code, the decoded data is just text - no metadata was included
                    if isinstance(decoded, bytes):
                        # Convert to string for display
                        decoded_text = decoded.decode('utf-8', errors='replace')
                    else:
                        decoded_text = str(decoded)
                    
                    # Create a metadata format for displaying purposes only
                    # This won't affect the QR content itself
                    metadata = f"qr_text.txt|{len(decoded_text.encode('utf-8'))}|utf-8".encode('utf-8')
                    raw_data = decoded if isinstance(decoded, bytes) else decoded_text.encode('utf-8')
                    self.result = (metadata, raw_data)
                elif is_barcode_mode:
                    # For Barcode, the decoded data is just text - no metadata was included
                    if isinstance(decoded, bytes):
                        # Convert to string for display
                        decoded_text = decoded.decode('utf-8', errors='replace')
                    else:
                        decoded_text = str(decoded)
                    
                    # Create a metadata format for displaying purposes only
                    # This won't affect the Barcode content itself
                    metadata = f"barcode_text.txt|{len(decoded_text.encode('utf-8'))}|utf-8".encode('utf-8')
                    raw_data = decoded if isinstance(decoded, bytes) else decoded_text.encode('utf-8')
                    self.result = (metadata, raw_data)
                
                # Skip the normal metadata splitting process
                if self.progress_handler:
                    self.progress_handler.complete(success=True)
                return
            else:
                # Ensure we're working with bytes for text-based modes
                if not isinstance(decoded, bytes):
                    decoded = decoded.encode("utf-8")
                    
                # Find the separator between metadata and data
                parts = decoded.split(b"\n", 1)
                if len(parts) != 2:
                    raise ValueError("Invalid file format - missing metadata separator!")
            
            meta, raw = parts
            self.result = (meta, raw)
            
            # Complete the progress
            if self.progress_handler:
                self.progress_handler.complete(success=True)
                
        except Exception as e:
            self.exception = e
            if self.progress_handler:
                # Mark as error and close progress bar
                self.progress_handler.complete(success=False, error_msg=str(e))

    def decode_barcode_png(self, png_file_path):
        """
        Decode PNG barcode file directly without threading to avoid GUI issues.
        
        :param png_file_path: Path to PNG barcode file
        :return: Decoded text content
        """
        try:
            # Update progress if handler exists
            if self.progress_handler:
                self.progress_handler.update_progress(25, 100)
                self.progress_handler.update_additional_status("Reading PNG file...")
            
            # Read PNG file
            with open(png_file_path, 'rb') as f:
                png_data = f.read()
                
            # Update progress
            if self.progress_handler:
                self.progress_handler.update_progress(75, 100)
                self.progress_handler.update_additional_status("Decoding barcode data...")
            
            # Create barcode format string
            barcode_format = f"BARCODE:{len(png_data)}:{png_data.hex()}"
            
            # Import barcode mode and decode
            from src import barcode_mode
            decoded_bytes = barcode_mode.decode(barcode_format)
            
            # Update progress to completion
            if self.progress_handler:
                self.progress_handler.update_progress(100, 100)
                self.progress_handler.update_additional_status("Barcode decoded successfully!")
            
            # Return as string
            return decoded_bytes.decode('utf-8')
            
        except Exception as e:
            raise ValueError(f"Failed to decode barcode PNG: {str(e)}")
