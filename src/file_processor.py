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
    
    def encode_file(self, file_path, mode, str_encoding, use_key=False, key_text=""):
        """
        Encode file in chunks and display progress.
        
        :param file_path: Path to file to encode
        :param mode: Encoding module (base64, base32, ...)
        :param str_encoding: String encoding
        :param use_key: Whether to use key or not
        :param key_text: Key for XOR encoding
        :return: Encoded string
        """
        self.is_running = True
        self.exception = None
        
        # Get file info
        name, ext, file_size = util.get_file_info(file_path)
        
        # Create progress handler if doesn't exist
        if not self.progress_handler:
            self.progress_handler = ProgressHandler("Encoding File", file_size)
        
        # Create thread for processing
        thread = threading.Thread(target=self._encode_worker, 
                                 args=(file_path, mode, str_encoding, use_key, key_text))
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
    
    def _encode_worker(self, file_path, mode, str_encoding, use_key, key_text):
        """
        Worker thread to encode file.
        """
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
            self.result = mode.encode(full_data, encoding=str_encoding)
            
            # Complete the progress
            if self.progress_handler:
                self.progress_handler.complete(success=True)
                
        except Exception as e:
            self.exception = e
            if self.progress_handler:
                # Mark as error and close progress bar
                self.progress_handler.complete(success=False, error_msg=str(e))
    
    def decode_file(self, file_path, mode, key_text=""):
        """
        Decode file in chunks and display progress.
        
        :param file_path: Path to file to decode
        :param mode: Decoding module (base64, base32, ...)
        :param key_text: Key for XOR decoding
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
                                 args=(file_path, mode, key_text))
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
    
    def _decode_worker(self, file_path, mode, key_text):
        """
        Worker thread to decode file.
        """
        try:
            # Get file size
            file_size = os.path.getsize(file_path)
            processed_size = 0
            
            # Check if we're using image mode
            is_image_mode = False
            # Check if the module is image_mode
            if hasattr(mode, '__name__'):
                is_image_mode = mode.__name__ == 'image_mode'
            # Check module object itself 
            elif hasattr(mode, 'image_mode'):
                is_image_mode = True
            # Check file extension as a fallback
            elif file_path.lower().endswith('.png'):
                is_image_mode = True
                # If we detected via file extension, make sure we're using the image_mode module
                from src import image_mode
                mode = image_mode
            
            if is_image_mode:
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
                        if self.progress_handler:
                            self.progress_handler.update_progress(processed_size, file_size)
            
            # Notify start of decoding
            if self.progress_handler:
                self.progress_handler.update_additional_status("Decoding data...")
                
            # Notify processing status
            if self.progress_handler:
                self.progress_handler.update_additional_status("Decoding data...")
            
            # Decode data
            decoded = mode.decode(data_str, encoding="utf-8")
            
            # Apply XOR if key is provided
            if key_text:
                if self.progress_handler:
                    self.progress_handler.update_additional_status("Decrypting with key...")
                from src import key_cipher
                decoded = key_cipher.apply_xor(decoded, key_text)
            
            # Split metadata and raw data
            if self.progress_handler:
                self.progress_handler.update_additional_status("Processing results...")
            
            # Create metadata and raw data directly for image mode
            is_image_mode = False
            if hasattr(mode, '__name__'):
                is_image_mode = mode.__name__ == 'image_mode'
            elif hasattr(mode, 'image_mode'):
                is_image_mode = True
            
            if is_image_mode:
                # For image mode, we create the metadata format ourselves
                # since the image encoding doesn't preserve the header format
                name, ext, _ = util.get_file_info(file_path)
                # Create a fake metadata line similar to what other modes produce
                metadata = f"{name}{ext}|{len(decoded)}|binary".encode('utf-8')
                self.result = (metadata, decoded)
                
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
                    raise ValueError("Invalid file format!")
            
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
