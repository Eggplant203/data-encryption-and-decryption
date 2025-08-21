# File Encoder/Decoder GUI
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from src import util, base64_mode, base85_mode, base32_mode, base91_mode
from src import hex_mode, image_mode, binary_mode, zero_width_mode, key_cipher, random_name, qr_code_mode, emoji_mode, uuid_mode, braille_mode, sound_mode, sudoku_mode, chess_mode, barcode_mode
from src.sudoku_viewer import show_sudoku_viewer
from src.chess_viewer import show_chess_viewer
from src.file_processor import ChunkProcessor
from src.progress_handler import ProgressHandler
import subprocess
import sys
import tempfile

MODES = {
    "Base32": base32_mode,
    "Base64": base64_mode,
    "Base85": base85_mode,
    "Base91": base91_mode,
    "Barcode": barcode_mode,
    "Binary": binary_mode,
    "Braille": braille_mode,
    "Chess": chess_mode,
    "Hex": hex_mode,
    "Image": image_mode,
    "QR Code": qr_code_mode,
    "Sound": sound_mode,
    "Sudoku": sudoku_mode,
    "Zero-Width": zero_width_mode,
    "Emoji": emoji_mode,
    "UUID": uuid_mode
}

STRING_ENCODINGS = ["ascii", "latin-1", "utf-8"]

MACHINE_FILES_DIR = os.path.abspath("machine_files")
HUMAN_FILES_DIR = os.path.abspath("human_files")
os.makedirs(MACHINE_FILES_DIR, exist_ok=True)
os.makedirs(HUMAN_FILES_DIR, exist_ok=True)

def get_mode_options(mode_name):
    """Get options for a specific mode"""
    if mode_name in MODES:
        mode = MODES[mode_name]
        if hasattr(mode, 'get_options'):
            return mode.get_options()
    return {}

def open_file(path):
    """Open file in system default application"""
    try:
        if sys.platform.startswith("darwin"):
            subprocess.call(["open", path])
        elif os.name == "nt":
            os.startfile(path)  # type: ignore
        elif os.name == "posix":
            subprocess.call(["xdg-open", path])
    except Exception as e:
        messagebox.showerror("Error", f"Could not open file:\n{str(e)}")

def process_encode(file_path, mode_name, str_encoding, use_key, key_text, use_random, uuid_options=None, mode_options=None):
    processor = None
    progress_handler = None
    try:
        mode = MODES[mode_name]
        name, ext, size = util.get_file_info(file_path)
        
        # Use ChunkProcessor to handle large files with progress bar
        progress_handler = ProgressHandler("Encoding File", size)
        processor = ChunkProcessor(progress_handler)
        
        # Prepare options for specific modes
        extra_options = {}
        if uuid_options and mode_name == "UUID":
            extra_options.update(uuid_options)
        if mode_options:
            extra_options.update(mode_options)
        
        encoded_str = processor.encode_file(file_path, mode, str_encoding, use_key, key_text, **extra_options)
        
        # Handle filename generation
        if use_random:
            # For QR Code and Barcode, always use custom override or datetime format
            if mode_name in ["QR Code", "Barcode"]:
                # Check for custom override first
                if hasattr(random_name, 'custom_name_override') and random_name.custom_name_override:
                    out_name = random_name.custom_name_override
                else:
                    # Generate timestamp-based name: qr_YYYYMMDD_HHMMSSmm or barcode_YYYYMMDD_HHMMSSmm
                    import datetime
                    now = datetime.datetime.now()
                    if mode_name == "QR Code":
                        out_name = f"qr_{now.strftime('%Y%m%d_%H%M%S%f')[:-4]}"
                    else:  # Barcode
                        out_name = f"barcode_{now.strftime('%Y%m%d_%H%M%S%f')[:-4]}"
            else:
                # For other modes, use standard random name
                out_name = random_name.generate_filename(len(name))
        elif mode_name in ["QR Code", "Barcode"]:
            # Even if random name is not checked, we still use timestamp for QR Code and Barcode
            import datetime
            now = datetime.datetime.now()
            if mode_name == "QR Code":
                out_name = f"qr_{now.strftime('%Y%m%d_%H%M%S%f')[:-4]}"
            else:  # Barcode
                out_name = f"barcode_{now.strftime('%Y%m%d_%H%M%S%f')[:-4]}"
        else:
            # For other modes, use original name if random is not selected
            out_name = name
            
        # For image mode, QR Code mode, or Barcode mode, save as PNG file
        if mode_name in ["Image", "QR Code", "Barcode"]:
            out_name = f"{out_name}.png"
            output_path = os.path.join(MACHINE_FILES_DIR, out_name)
            
            if progress_handler:
                progress_handler.update_additional_status("Saving image file...")
            
            # Save the image
            if mode_name == "Image":
                image_mode.save_image(encoded_str, output_path)
            elif mode_name == "QR Code":
                qr_code_mode.save_qr_image(encoded_str, output_path)
            elif mode_name == "Barcode":
                barcode_mode.save_barcode_image(encoded_str, output_path)
        elif mode_name == "Sound":
            # For sound mode, save as MIDI file
            out_name = f"{out_name}.mid"
            output_path = os.path.join(MACHINE_FILES_DIR, out_name)
            
            if progress_handler:
                progress_handler.update_additional_status("Saving MIDI file...")
            
            # Save the MIDI file (encoded_str is bytes for sound mode)
            sound_mode.save_midi_file(encoded_str, output_path)
        else:
            # For other modes, save as txt
            out_name = f"{out_name}.txt"
            output_path = os.path.join(MACHINE_FILES_DIR, out_name)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(encoded_str)
            
        # Display success result in progress window
        if progress_handler and hasattr(progress_handler, 'window') and progress_handler.window.winfo_exists():
            progress_handler.complete(success=True, output_file=output_path)
        else:
            # Fallback if progress window was closed
            ProgressHandler.show_success("File encoded", output_path)
    except Exception as e:
        # Display error message in progress window
        if progress_handler and hasattr(progress_handler, 'window') and progress_handler.window.winfo_exists():
            progress_handler.complete(success=False, error_msg=str(e))
        else:
            # Fallback if progress window was closed
            messagebox.showerror("Error", f"Encoding failed:\n{str(e)}")

def process_decode(file_path, mode, key_text, mode_options=None):
    processor = None
    progress_handler = None
    try:
        # Check if the file exists and is readable
        if not os.path.isfile(file_path):
            messagebox.showerror("Error", f"File not found: {file_path}")
            return
        
        # Special handling for QR Code decoding - we'll display the text in the result text area
        qr_result_text = None
            
        # Get the mode name based on the module
        mode_name = None
        for name, module in MODES.items():
            if module == mode:
                mode_name = name
                break
        
        # Verify the selected mode matches the file type
        if file_path.lower().endswith('.png') and mode_name not in ["Image", "QR Code", "Barcode"]:
            # For PNG files, offer Image, QR Code, or Barcode mode
            options = ["Image", "QR Code", "Barcode", "Cancel"]
            result = messagebox.askquestion("Mode Selection", 
                                  "You selected a PNG file. Would you like to treat it as an Image, QR Code, or Barcode?",
                                  type="custom",
                                  options=options)
            if result == "Image":
                mode = MODES["Image"]
                mode_name = "Image"
            elif result == "QR Code":
                mode = MODES["QR Code"]
                mode_name = "QR Code"
            elif result == "Barcode":
                mode = MODES["Barcode"]
                mode_name = "Barcode"
            else:
                # User chose to cancel
                return
        elif file_path.lower().endswith(('.mid', '.midi')) and mode_name != "Sound":
            # For MIDI files, suggest Sound mode
            if messagebox.askyesno("Mode Selection", 
                                  "You selected a MIDI file. Would you like to use Sound mode?"):
                mode = MODES["Sound"]
                mode_name = "Sound"
            else:
                # User chose to continue with current mode - this may fail
                pass
        elif not file_path.lower().endswith(('.mid', '.midi')) and mode_name == "Sound":
            if messagebox.askyesno("Mode Mismatch", 
                                  "You selected Sound mode but not a MIDI file. Choose a different mode?"):
                # User chose Yes - cancel operation
                return
            else:
                # User chose No - continue with different mode (Base64 for non-MIDI files)
                mode = MODES["Base64"]
                mode_name = "Base64"
        elif not file_path.lower().endswith('.png') and mode_name == "Image":
            if messagebox.askyesno("Mode Mismatch", 
                                  "You selected Image mode but not a PNG file. Choose a different mode?"):
                # User chose Yes - cancel operation  
                return
            else:
                # User chose No - continue with different mode (Base64 for non-PNG files)
                mode = MODES["Base64"]
                mode_name = "Base64"
        file_size = os.path.getsize(file_path)
        
        # Use ChunkProcessor to handle large files with progress bar
        progress_handler = ProgressHandler("Decoding File", file_size)
        processor = ChunkProcessor(progress_handler)
        
        try:
            # Prepare extra options for specific modes
            extra_options = {}
            if mode_options:
                extra_options.update(mode_options)
                
            meta, raw = processor.decode_file(file_path, mode, key_text, **extra_options)
        except Exception as decode_error:
            print(f"Decode error: {decode_error}")
            if progress_handler:
                progress_handler.complete(success=False, error_msg=str(decode_error))
            raise decode_error
        
        # Handle metadata parsing
        try:
            # For QR Code mode, we expect meta to already be in the correct format
            if isinstance(meta, bytes):
                parts = meta.decode("utf-8").split("|")
            else:
                parts = str(meta).split("|")
                
            if len(parts) >= 3:
                name_ext, size_str, str_encoding = parts[0], parts[1], parts[2]
                name, ext = os.path.splitext(name_ext)
                size = int(size_str)
                
                if len(raw) != size:
                    # Size mismatch but continue anyway - could be due to encoding differences
                    print(f"Warning: Size mismatch - expected {size}, got {len(raw)}")
                    
                # Use original name with extension
                output_path = os.path.join(HUMAN_FILES_DIR, f"{name}{ext}")
            else:
                # Not enough parts - create default name
                print(f"Warning: Not enough metadata parts - got {len(parts)}, expected 3")
                name = "decoded_content"
                ext = ".txt" if mode_name == "QR Code" else ".bin"
                output_path = os.path.join(HUMAN_FILES_DIR, f"{name}{ext}")
        except Exception as e:
            # If any error occurs during metadata parsing, use a default name
            print(f"Error parsing metadata: {e}")
            name = "decoded_content"  
            ext = ".txt" if mode_name == "QR Code" else ".bin"
            output_path = os.path.join(HUMAN_FILES_DIR, f"{name}{ext}")
            
        # Special handling for QR Code mode
        if mode_name == "QR Code":
            try:
                # For QR Code, we directly use the raw data (decoded QR content)
                if isinstance(raw, bytes):
                    qr_result_text = raw.decode("utf-8", errors="replace")
                else:
                    qr_result_text = str(raw)
                
                # For QR Code mode: Don't save to file, just show result in Success window
                # Display success result with QR content directly in progress window
                if progress_handler and hasattr(progress_handler, 'window') and progress_handler.window.winfo_exists():
                    progress_handler.complete(success=True, qr_content=qr_result_text)
                else:
                    # Fallback if progress window was closed
                    ProgressHandler.show_success("QR Code decoded", qr_result_text, is_qr_content=True)
                
                # Early return to skip file creation and normal success handling
                return
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to display QR code content:\n{str(e)}")
                return
        # Special handling for Barcode mode
        elif mode_name == "Barcode":
            try:
                # For Barcode, we directly use the raw data (decoded Barcode content)
                if isinstance(raw, bytes):
                    barcode_result_text = raw.decode("utf-8", errors="replace")
                else:
                    barcode_result_text = str(raw)
                
                # For Barcode mode: Don't save to file, just show result in Success window
                # Display success result with Barcode content directly in progress window
                if progress_handler and hasattr(progress_handler, 'window') and progress_handler.window.winfo_exists():
                    progress_handler.complete(success=True, qr_content=barcode_result_text)
                else:
                    # Fallback if progress window was closed
                    ProgressHandler.show_success("Barcode decoded", barcode_result_text, is_qr_content=True)
                
                # Early return to skip file creation and normal success handling
                return
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to display Barcode content:\n{str(e)}")
                return
        else:
            # Hide QR result display for other modes (no longer needed)
            pass
        
        # Normal file handling for non-QR modes
        util.write_file_binary(output_path, raw)
                
        # Display success result in progress window
        if progress_handler and hasattr(progress_handler, 'window') and progress_handler.window.winfo_exists():
            progress_handler.complete(success=True, output_file=output_path)
        else:
            # Fallback if progress window was closed
            ProgressHandler.show_success("File decoded", output_path)
    except Exception as e:
        # Display error message in progress window
        if progress_handler and hasattr(progress_handler, 'window') and progress_handler.window.winfo_exists():
            progress_handler.complete(success=False, error_msg=str(e))
        else:
            # Fallback if progress window was closed
            messagebox.showerror("Error", f"Decoding failed:\n{str(e)}")
        
def start_gui():
    global qr_result_frame, qr_result_display
    
    root = tk.Tk()
    root.title("File Encoder/Decoder")
    root.geometry("700x280")
    root.resizable(True, True)  # Allow window to be resized if needed
    
    # Set minimum window size to prevent collapse
    root.minsize(550, 280)
    
    # Configure grid columns to expand properly
    root.grid_columnconfigure(0, minsize=50)  # Fixed width for labels
    root.grid_columnconfigure(1, weight=1, minsize=50)  # Make column 1 (main content) expandable with minimum width
    root.grid_columnconfigure(2, minsize=80)  # Fixed width for buttons
    
    # Center the window on the screen
    # Get the screen width and height
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    
    # Calculate the position coordinates (position window higher on screen)
    x = (screen_width - 700) // 2
    y = max(50, (screen_height - 420) // 2 - 80)  # Move window up by 80px, minimum 50px from top
    
    # Set the position of the window
    root.geometry(f"700x350+{x}+{y}")
    
    # Store base window dimensions for dynamic resizing
    base_height = 200  # Further increased base height to accommodate all UI elements
    field_height = 35  # Height per additional field
    
    def update_window_height():
        """Update window height based on visible fields"""
        additional_fields = 0
        
        # Count visible additional fields
        if use_key_var.get():
            additional_fields += 1
        if use_random_var.get() and (mode_combo.get() == "QR Code" or mode_combo.get() == "Barcode") and mode_var.get() == "encode":
            additional_fields += 1
        if mode_combo.get() == "UUID" and mode_var.get() == "encode":
            additional_fields += 2  # UUID options frame takes about 2 field heights
        
        # Check if mode options frame is visible (even if empty)
        selected_mode = mode_combo.get()
        operation = mode_var.get()
        modes_with_decode_options = ["Emoji", "Sudoku", "Chess", "Barcode"]
        
        show_mode_options = ((operation == "encode" and selected_mode != "UUID" and selected_mode in MODES and hasattr(MODES[selected_mode], 'get_options')) or 
                           (operation == "decode" and selected_mode in modes_with_decode_options))
        
        if show_mode_options:
            if mode_options_vars:  # If there are actual options
                additional_fields += len(mode_options_vars)  # Each option adds a field
                # Add extra space for modes with many options like Barcode
                if selected_mode == "Barcode" and operation == "encode":
                    additional_fields += 2  # Extra buffer for Barcode mode + Start button
            else:  # If frame is shown but empty (like Barcode decode)
                additional_fields += 1  # Add space for the frame header
                
        # Always add extra space for Start button and Note section
        additional_fields += 1
            
        new_height = base_height + (additional_fields * field_height)
        
        # Ensure minimum height to show all basic elements including Start button
        min_height = 550  # Further increased to ensure Start button is always visible
        new_height = max(new_height, min_height)
        
        current_geometry = root.geometry()
        width = current_geometry.split('x')[0]
        
        # Keep window positioned higher on screen when resizing
        if '+' in current_geometry:
            position_parts = '+'.join(current_geometry.split('+')[1:])
            # Extract current x position, keep y position relatively high
            current_x = current_geometry.split('+')[1] if '+' in current_geometry else str((root.winfo_screenwidth() - 700) // 2)
            new_y = max(50, (root.winfo_screenheight() - new_height) // 2 - 80)
            position = f'+{current_x}+{new_y}'
        else:
            position = ''
            
        root.geometry(f"700x{new_height}{position}")

    # --- Operation
    mode_var = tk.StringVar(value="encode")
    tk.Label(root, text="Operation:").grid(row=0, column=0, sticky="w")
    tk.Radiobutton(root, text="Encode", variable=mode_var, value="encode").grid(row=0, column=1, sticky="w")
    tk.Radiobutton(root, text="Decode", variable=mode_var, value="decode").grid(row=0, column=2, sticky="w")

    # --- File selection or text input
    input_label = tk.Label(root, text="Select File:")
    input_label.grid(row=1, column=0, sticky="w")
    file_var = tk.StringVar()
    file_entry = tk.Entry(root, textvariable=file_var, state="readonly", width=50)
    file_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
    
    # Text input for QR Code
    text_var = tk.StringVar()
    text_entry = tk.Entry(root, textvariable=text_var, width=50)
    # Initially hidden, will be shown when QR Code mode is selected
    
    # Multiline text input for QR Code (for longer texts)
    text_scroll = tk.Scrollbar(root)
    text_multiline = tk.Text(root, height=5, width=47)
    text_multiline.config(yscrollcommand=text_scroll.set)
    text_scroll.config(command=text_multiline.yview)
    # Initially hidden
    
    text_length_var = tk.StringVar(value="0/1000 characters")
    text_length_label = tk.Label(root, textvariable=text_length_var, fg="gray", font=("Arial", 8))
    
    def update_char_count(*args):
        # Update character count for QR Code text input
        text = text_multiline.get("1.0", "end-1c")  # Get text without final newline
        max_len = qr_code_mode.get_max_text_length()
        current_len = len(text)
        text_length_var.set(f"{current_len}/{max_len} characters")
        
        # Enable/disable the start button based on text length
        if 0 < current_len <= max_len:
            start_btn.config(state="normal")
        else:
            start_btn.config(state="disabled")
    
    def browse_file():
        if mode_var.get() == "encode":
            path = filedialog.askopenfilename(initialdir=HUMAN_FILES_DIR, title="Select file to encode")
        else:
            # Allow selecting specific file types based on mode when decoding
            if mode_combo.get() in ["Image", "QR Code", "Barcode"]:
                path = filedialog.askopenfilename(initialdir=MACHINE_FILES_DIR, title="Select encoded PNG file", 
                                                filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
            elif mode_combo.get() == "Sound":
                path = filedialog.askopenfilename(initialdir=MACHINE_FILES_DIR, title="Select encoded MIDI file", 
                                                filetypes=[("MIDI files", "*.mid;*.midi"), ("All files", "*.*")])
            else:
                path = filedialog.askopenfilename(initialdir=MACHINE_FILES_DIR, title="Select encoded txt file", 
                                                filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            file_var.set(path)
            start_btn.config(state="normal")

    def open_viewer_file():
        """Open and view file in appropriate viewer based on selected mode"""
        selected_mode = mode_combo.get()
        
        if selected_mode == "Sudoku":
            path = filedialog.askopenfilename(
                initialdir=MACHINE_FILES_DIR, 
                title="Select Sudoku file to view", 
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if path:
                try:
                    show_sudoku_viewer(path, root)
                except Exception as e:
                    messagebox.showerror("Error", f"Cannot open file as Sudoku:\n{str(e)}")
        elif selected_mode == "Chess":
            path = filedialog.askopenfilename(
                initialdir=MACHINE_FILES_DIR, 
                title="Select Chess file to view", 
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if path:
                try:
                    show_chess_viewer(path, root)
                except Exception as e:
                    messagebox.showerror("Error", f"Cannot open file as Chess:\n{str(e)}")

    def open_sudoku_file():
        """Open and view a Sudoku file directly in the viewer"""
        path = filedialog.askopenfilename(
            initialdir=MACHINE_FILES_DIR, 
            title="Select Sudoku file to view", 
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            try:
                # Try to show the file in Sudoku viewer
                show_sudoku_viewer(path, root)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot open file as Sudoku:\n{str(e)}")

    def open_chess_file():
        """Open and view a Chess file directly in the viewer"""
        path = filedialog.askopenfilename(
            initialdir=MACHINE_FILES_DIR, 
            title="Select Chess file to view", 
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            try:
                # Try to show the file in Chess viewer
                show_chess_viewer(path, root)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot open file as Chess:\n{str(e)}")

    def example_file():
        """Create or select example.txt file for encoding modes"""
        selected_mode = mode_combo.get()
        operation = mode_var.get()
        
        if selected_mode in TEXT_INPUT_MODES and operation == "encode":
            # For QR Code mode, set the text directly
            text_multiline.delete("1.0", "end")
            text_multiline.insert("1.0", "Hello World!")
            update_char_count()
        else:
            # For other modes, create/select example.txt file
            example_path = os.path.join(HUMAN_FILES_DIR, "example.txt")
            
            # Create the file if it doesn't exist
            if not os.path.exists(example_path):
                try:
                    with open(example_path, 'w', encoding='utf-8') as f:
                        f.write("Hello World!")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not create example file:\n{str(e)}")
                    return
            
            # Set the file path
            file_var.set(example_path)
            start_btn.config(state="normal")

    browse_btn = tk.Button(root, text="Browse", command=browse_file)
    browse_btn.grid(row=1, column=2, padx=5, pady=5)
    
    # Create Example button (initially hidden)
    example_btn = tk.Button(root, text="Example", command=example_file)
    # Don't grid it initially - it will be shown/hidden by toggle_input_mode
    
    # Create Open button for Sudoku/Chess mode (initially hidden)
    open_btn = tk.Button(root, text="Open", command=open_viewer_file)
    # Don't grid it initially - it will be shown/hidden by toggle_input_mode
    
    def toggle_input_mode(*args):
        # Get the mode name string, not the actual module
        selected_mode = mode_combo.get()
        operation = mode_var.get()
        
        # Hide all input elements first
        file_entry.grid_remove()
        browse_btn.grid_remove()
        example_btn.grid_remove()  # Hide Example button by default
        open_btn.grid_remove()  # Hide Open button by default
        text_multiline.grid_remove()
        text_scroll.grid_remove()
        text_length_label.grid_remove()
        
        if selected_mode in TEXT_INPUT_MODES and operation == "encode":
            # Show text input for QR Code encoding
            input_label.config(text="Enter Text:")
            text_multiline.delete("1.0", "end")  # Clear previous text
            text_multiline.grid(row=1, column=1, padx=5, pady=5)
            text_scroll.grid(row=1, column=2, sticky="ns")
            text_length_label.grid(row=1, column=3, sticky="w", padx=5)
            example_btn.grid(row=1, column=4, padx=5, pady=5)  # Show Example button for QR Code
            update_char_count()  # Initialize character count
            start_btn.config(state="disabled")  # Disable until text is entered
            
            # Update custom filename field visibility
            toggle_custom_filename()
        elif selected_mode in TEXT_INPUT_MODES and operation == "decode":
            # For decoding QR Code, still need file input to select the QR image
            input_label.config(text="Select QR Image:")
            file_entry.grid()
            browse_btn.grid()
            
            # Hide custom filename field in decode mode
            custom_filename_label.grid_remove()
            custom_filename_entry.grid_remove()
        elif selected_mode == "Sudoku" and operation == "decode":
            # Special case for Sudoku decode mode - show both Browse and Open buttons
            input_label.config(text="Select Sudoku File:")
            file_entry.grid()
            browse_btn.grid(row=1, column=2, padx=(5,2), pady=5)  # Adjust padding
            open_btn.grid(row=1, column=3, padx=(2,5), pady=5)   # Show Open button
            
            # Hide custom filename field in decode mode
            custom_filename_label.grid_remove()
            custom_filename_entry.grid_remove()
        elif selected_mode == "Chess" and operation == "decode":
            # Special case for Chess decode mode - show both Browse and Open buttons
            input_label.config(text="Select Chess File:")
            file_entry.grid()
            browse_btn.grid(row=1, column=2, padx=(5,2), pady=5)  # Adjust padding
            open_btn.grid(row=1, column=3, padx=(2,5), pady=5)   # Show Open button
            
            # Hide custom filename field in decode mode
            custom_filename_label.grid_remove()
            custom_filename_entry.grid_remove()
        elif operation == "encode":
            # Standard file input for other modes (encoding only shows Example button)
            input_label.config(text="Select File:")
            file_entry.grid()
            browse_btn.grid(row=1, column=2, padx=(5,2), pady=5)  # Adjust padding for Example button
            example_btn.grid(row=1, column=3, padx=(2,5), pady=5)  # Show Example button for encoding
            
            # Hide custom filename field for non-QR modes
            custom_filename_label.grid_remove()
            custom_filename_entry.grid_remove()
        else:
            # Standard file input for decoding modes (no Example button)
            input_label.config(text="Select File:")
            file_entry.grid()
            browse_btn.grid()
            
            # Hide custom filename field for non-QR modes
            custom_filename_label.grid_remove()
            custom_filename_entry.grid_remove()
            
    # Bind text change events
    text_multiline.bind("<KeyRelease>", update_char_count)

    # --- Encoding mode
    tk.Label(root, text="Mode:").grid(row=2, column=0, sticky="w")
    mode_combo = ttk.Combobox(root, values=sorted(MODES.keys()), state="readonly")
    mode_combo.current(0)
    mode_combo.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
    mode_combo.bind("<KeyPress>", lambda e: "break")
    
    def search_mode():
        """Open mode search dialog"""
        search_window = tk.Toplevel(root)
        search_window.title("Search Mode")
        search_window.geometry("480x380")  # Increase height to ensure buttons are visible
        search_window.resizable(False, False)
        search_window.grab_set()  # Make it modal
        search_window.transient(root)  # Keep it on top of main window
        
        # Center the search window
        search_window.update_idletasks()
        x = (search_window.winfo_screenwidth() // 2) - 240  # Adjust for new width
        y = (search_window.winfo_screenheight() // 2) - 190  # Adjust for new height
        search_window.geometry(f"480x380+{x}+{y}")
        
        # Search entry
        tk.Label(search_window, text="Search for mode:", font=("Arial", 10, "bold")).pack(pady=5)
        search_var = tk.StringVar()
        search_entry = tk.Entry(search_window, textvariable=search_var, font=("Arial", 10), width=40)
        search_entry.pack(pady=5, padx=10, fill="x")
        search_entry.focus()
        
        # Results display with colored text (Text widget instead of Listbox)
        tk.Label(search_window, text="Results:", font=("Arial", 9)).pack(pady=(10,2), anchor="w", padx=10)
        
        list_frame = tk.Frame(search_window)
        list_frame.pack(pady=5, padx=10, fill="both", expand=False)  # Don't expand to leave space for buttons
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        # Use Text widget for colored text with limited height to ensure buttons are visible
        results_text = tk.Text(list_frame, yscrollcommand=scrollbar.set, font=("Arial", 10),
                              wrap=tk.WORD, cursor="hand2", state="disabled", height=12)
        results_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=results_text.yview)
        
        # Configure text tags for coloring
        results_text.tag_configure("mode_name", foreground="#0066CC", font=("Arial", 10, "bold"))
        results_text.tag_configure("description", foreground="#666666", font=("Arial", 10))
        results_text.tag_configure("selected", background="#E6F3FF")
        
        # Store mode data for selection
        mode_data = []
        current_selection = 0
        
        # Mode descriptions for better search (shortened for readability)
        mode_descriptions = {
            "Base32": "RFC 4648 encoding, case-insensitive",
            "Base64": "Standard encoding for binary data",
            "Base85": "Compact ASCII85 encoding",
            "Base91": "Highly efficient 91-character encoding",
            "Barcode": "Professional 1D barcodes with custom text",
            "Binary": "Convert to 0s and 1s",
            "Braille": "Braille Unicode characters",
            "Chess": "Chess piece positions",
            "Hex": "Hexadecimal representation",
            "Image": "PNG pixel steganography",
            "QR Code": "Generate scannable QR codes",
            "Sound": "MIDI musical notes",
            "Sudoku": "Puzzle grid coordinates",
            "Zero-Width": "Invisible Unicode steganography",
            "Emoji": "Emoji sequence encoding",
            "UUID": "UUID sequence embedding"
        }
        
        def update_results(*args):
            """Update search results based on input"""
            search_text = search_var.get().lower()
            results_text.config(state="normal")
            results_text.delete("1.0", tk.END)
            mode_data.clear()
            
            matches = []
            
            if not search_text:
                # Show all modes if search is empty
                matches = [(mode_name, mode_descriptions.get(mode_name, "")) for mode_name in sorted(MODES.keys())]
            else:
                # Filter modes based on search
                for mode_name in sorted(MODES.keys()):
                    desc = mode_descriptions.get(mode_name, "")
                    if (search_text in mode_name.lower() or 
                        search_text in desc.lower()):
                        matches.append((mode_name, desc))
            
            # Display results with colored text
            for i, (mode_name, desc) in enumerate(matches):
                mode_data.append(mode_name)
                
                # Add mode name in blue
                start_pos = results_text.index(tk.INSERT)
                results_text.insert(tk.INSERT, mode_name)
                end_pos = results_text.index(tk.INSERT)
                results_text.tag_add("mode_name", start_pos, end_pos)
                
                # Add separator and description in gray
                results_text.insert(tk.INSERT, " - ")
                start_desc_pos = results_text.index(tk.INSERT)
                results_text.insert(tk.INSERT, desc)
                end_desc_pos = results_text.index(tk.INSERT)
                results_text.tag_add("description", start_desc_pos, end_desc_pos)
                
                # Add newline except for last item
                if i < len(matches) - 1:
                    results_text.insert(tk.INSERT, "\n")
            
            results_text.config(state="disabled")
            
            # Auto-select first item if available
            if mode_data:
                nonlocal current_selection
                current_selection = 0
                highlight_selection(0)
        
        def highlight_selection(index):
            """Highlight selected line in text widget"""
            # Remove previous selection
            results_text.tag_remove("selected", "1.0", tk.END)
            
            if 0 <= index < len(mode_data):
                # Highlight current selection
                start_line = f"{index + 1}.0"
                end_line = f"{index + 2}.0"
                results_text.tag_add("selected", start_line, end_line)
                results_text.see(start_line)
        
        def select_mode():
            """Select the chosen mode and close dialog"""
            if 0 <= current_selection < len(mode_data):
                mode_name = mode_data[current_selection]
                
                # Find the index in the combo box and set it
                mode_values = list(mode_combo['values'])
                if mode_name in mode_values:
                    mode_combo.current(mode_values.index(mode_name))
                    # Trigger the mode change event
                    combined_mode_update()
                
                search_window.destroy()
        
        def on_text_click(event):
            """Handle click on text widget"""
            # Get the line number where user clicked
            line_index = int(results_text.index(tk.CURRENT).split('.')[0]) - 1
            if 0 <= line_index < len(mode_data):
                nonlocal current_selection
                current_selection = line_index
                highlight_selection(line_index)
        
        def on_double_click(event):
            """Handle double-click on text widget"""
            on_text_click(event)
            select_mode()
        
        def on_enter_key(event):
            """Handle Enter key in search entry"""
            if mode_data:
                select_mode()
        
        def on_up_down_keys(event):
            """Handle Up/Down keys in search entry to navigate results"""
            nonlocal current_selection
            if mode_data:
                if event.keysym == "Down":
                    if current_selection < len(mode_data) - 1:
                        current_selection += 1
                        highlight_selection(current_selection)
                elif event.keysym == "Up":
                    if current_selection > 0:
                        current_selection -= 1
                        highlight_selection(current_selection)
                return "break"  # Prevent default behavior
        
        # Bind events
        search_var.trace_add("write", update_results)
        results_text.bind("<Button-1>", on_text_click)
        results_text.bind("<Double-Button-1>", on_double_click)
        search_entry.bind("<Return>", on_enter_key)
        search_entry.bind("<Up>", on_up_down_keys)
        search_entry.bind("<Down>", on_up_down_keys)
        
        # Initialize with all modes
        update_results()
        
        # Buttons with improved height - ensure they are always visible
        btn_frame = tk.Frame(search_window)
        btn_frame.pack(side="bottom", pady=15, padx=10)  # Use side="bottom" to ensure visibility
        
        select_btn = tk.Button(btn_frame, text="Select", command=select_mode, 
                              font=("Arial", 10), height=2, width=10)
        select_btn.pack(side="left", padx=5)
        
        cancel_btn = tk.Button(btn_frame, text="Cancel", command=search_window.destroy, 
                              font=("Arial", 10), height=2, width=10)
        cancel_btn.pack(side="left", padx=5)
        
        # Handle keyboard shortcuts
        search_window.bind("<Escape>", lambda e: search_window.destroy())
        search_window.bind("<Control-f>", lambda e: search_entry.focus())
    
    # Add search button next to mode combo (match Browse button style)
    search_btn = tk.Button(root, text="🔍 Search", command=search_mode)
    search_btn.grid(row=2, column=2, padx=5, pady=5)

    # --- String encoding
    tk.Label(root, text="String Encoding:").grid(row=3, column=0, sticky="w")
    strenc_combo = ttk.Combobox(root, values=sorted(STRING_ENCODINGS), state="readonly")
    strenc_combo.current(0)
    strenc_combo.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
    strenc_combo.bind("<KeyPress>", lambda e: "break")

    # --- Key Option + Custom/Random Option
    option_frame = tk.Frame(root)
    option_frame.grid(row=4, column=0, columnspan=3, sticky="w")

    use_key_var = tk.BooleanVar(value=False)
    key_check = tk.Checkbutton(option_frame, text="Use Key", variable=use_key_var)
    key_check.pack(side="left", padx=5)
    
    # Custom filename input (for QR Code and Barcode) - using grid layout for better alignment
    custom_filename_label = tk.Label(root, text="Filename:")
    custom_filename_var = tk.StringVar()
    custom_filename_entry = tk.Entry(root, textvariable=custom_filename_var, width=50)
    
    # Define toggle_custom_filename BEFORE using it
    def toggle_custom_filename(*args):
        if use_random_var.get() and (mode_combo.get() == "QR Code" or mode_combo.get() == "Barcode") and mode_var.get() == "encode":
            # Dynamic row positioning based on visible frames
            filename_row = calculate_row_position(6)  # Base row after option_frame and potential key field
                
            # Check if key field is visible
            if use_key_var.get():
                filename_row += 1
                
            custom_filename_label.grid(row=filename_row, column=0, sticky="w", padx=5, pady=5)
            custom_filename_entry.grid(row=filename_row, column=1, sticky="ew", padx=5, pady=5)
        else:
            custom_filename_label.grid_remove()
            custom_filename_entry.grid_remove()
        update_window_height()  # Update window size
        update_output_label_position()  # Update output label position

    use_random_var = tk.BooleanVar(value=False)
    random_check = tk.Checkbutton(option_frame, text="Custom Filename", variable=use_random_var, 
                                 command=toggle_custom_filename)
    random_check.pack(side="left", padx=5)
    
    # Bind use_random_var to update UI
    use_random_var.trace_add("write", toggle_custom_filename)

    # --- UUID Options
    uuid_options_frame = tk.LabelFrame(root, text="UUID Options (Encoding Only)", padx=5, pady=5)
    # Initially hidden
    
    # UUID Version selection
    tk.Label(uuid_options_frame, text="UUID Version:").grid(row=0, column=0, sticky="w")
    uuid_version_var = tk.StringVar(value="4")
    uuid_version_combo = ttk.Combobox(uuid_options_frame, textvariable=uuid_version_var, 
                                     values=["1", "3", "4", "5"], state="readonly", width=10)
    uuid_version_combo.grid(row=0, column=1, padx=5, sticky="w")
    
    # Namespace UUID input (for versions 3 and 5)
    tk.Label(uuid_options_frame, text="Namespace UUID:").grid(row=1, column=0, sticky="w")
    uuid_namespace_var = tk.StringVar()
    uuid_namespace_entry = tk.Entry(uuid_options_frame, textvariable=uuid_namespace_var, width=40)
    uuid_namespace_entry.grid(row=1, column=1, padx=5, sticky="w")
    uuid_namespace_label = tk.Label(uuid_options_frame, text="(Optional for v3/v5)", fg="gray", font=("Arial", 8))
    uuid_namespace_label.grid(row=1, column=2, sticky="w", padx=5)
    
    # Tooltip class for UUID options
    class ToolTip:
        def __init__(self, widget, text):
            self.widget = widget
            self.text = text
            self.tooltip = None
            self.widget.bind("<Enter>", self.on_enter)
            self.widget.bind("<Leave>", self.on_leave)
        
        def on_enter(self, event=None):
            x, y, _, _ = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25
            
            self.tooltip = tk.Toplevel(self.widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(self.tooltip, text=self.text, justify='left',
                           background='lightyellow', relief='solid', borderwidth=1,
                           font=("Arial", 9), wraplength=300)
            label.pack()
        
        def on_leave(self, event=None):
            if self.tooltip:
                self.tooltip.destroy()
                self.tooltip = None
    
    # Add tooltips for UUID options
    ToolTip(uuid_version_combo, 
            "UUID Version (Encoding Only):\n" +
            "• Version 1: Time-based UUID (uses current timestamp)\n" +
            "• Version 3: Name-based UUID using MD5 hash\n" +
            "• Version 4: Random UUID (default, most common)\n" +
            "• Version 5: Name-based UUID using SHA-1 hash\n\n" +
            "Note: These options are only needed for encoding.\n" +
            "Decoding works automatically with any UUID version.")
    
    ToolTip(uuid_namespace_entry,
            "Namespace UUID (Encoding Only):\n" +
            "Required for versions 3 and 5. Provides a namespace context for name-based UUIDs.\n" +
            "Example: 6ba7b810-9dad-11d1-80b4-00c04fd430c8\n" +
            "Leave empty to auto-generate a random namespace.\n\n" +
            "Note: Not needed for decoding - UUID metadata is embedded in the encoded data.")
    
    # Add tooltip for search button
    ToolTip(search_btn, "Search and filter encoding modes\nKeyboard shortcut: Ctrl+F")
    
    def toggle_uuid_namespace(*args):
        version = uuid_version_var.get()
        if version in ["3", "5"]:
            uuid_namespace_entry.config(state="normal")
            uuid_namespace_label.config(text="(Optional for v3/v5)")
        else:
            uuid_namespace_entry.config(state="disabled")
            uuid_namespace_var.set("")
            uuid_namespace_label.config(text="(Not used for v" + version + ")")
    
    uuid_version_var.trace_add("write", toggle_uuid_namespace)
    uuid_version_combo.bind("<<ComboboxSelected>>", toggle_uuid_namespace)
    
    # --- Mode-specific Options (Dynamic)
    mode_options_frame = tk.LabelFrame(root, text="Mode Options", padx=5, pady=5)
    mode_options_widgets = {}  # Store dynamically created widgets
    mode_options_vars = {}     # Store variables for options
    
    def calculate_row_position(base_row):
        """Calculate the actual row position based on visible frames"""
        row = base_row
        selected_mode = mode_combo.get()
        operation = mode_var.get()
        
        # Check if UUID options frame is visible
        if selected_mode == "UUID" and operation == "encode":
            row += 1
        
        # Check if mode options frame is visible
        try:
            modes_with_decode_options = ["Emoji", "Sudoku", "Chess", "Barcode"]
            show_mode_options = (mode_options_vars and 
                               ((operation == "encode" and selected_mode != "UUID") or 
                                (operation == "decode" and selected_mode in modes_with_decode_options)))
            if show_mode_options:
                row += 1
        except:
            # If there's any error (e.g., during initialization), skip this check
            pass
        
        return row
    
    def create_mode_options(mode_name, operation):
        """Create dynamic options widgets for the selected mode"""
        # Clear existing widgets
        for widget_list in mode_options_widgets.values():
            for widget in widget_list:
                widget.destroy()
        mode_options_widgets.clear()
        mode_options_vars.clear()
        
        # Only show options for encoding, except for modes that need options for both operations
        modes_with_decode_options = ["Emoji", "Sudoku", "Chess", "Barcode"]
        if operation != "encode" and not (operation == "decode" and mode_name in modes_with_decode_options):
            return
        
        # Skip UUID mode since it has its own dedicated options frame
        if mode_name == "UUID":
            return
            
        options = get_mode_options(mode_name)
        if not options:
            return
        
        # Filter options based on operation for modes that support decode options
        if operation == "decode" and mode_name in modes_with_decode_options:
            if mode_name == "Barcode":
                # Barcode doesn't need options for decoding - options are auto-detected from image
                options = {}
            else:
                # Only show options that are required for decoding
                filtered_options = {}
                for option_name, option_config in options.items():
                    if option_config.get('decode_required', False):
                        filtered_options[option_name] = option_config
                options = filtered_options
            
        # Update frame title
        if mode_name in modes_with_decode_options:
            if mode_name == "Barcode" and operation == "decode":
                mode_options_frame.config(text=f"{mode_name} Options (Auto-detected from image)")
            else:
                mode_options_frame.config(text=f"{mode_name} Options")
        else:
            mode_options_frame.config(text=f"{mode_name} Options (Encoding Only)")
        
        row = 0
        for option_name, option_config in options.items():
            widgets = []
            
            # Create label
            label = tk.Label(mode_options_frame, text=f"{option_config.get('description', option_name)}:")
            label.grid(row=row, column=0, sticky="w")
            widgets.append(label)
            
            # Create input widget based on type
            if option_config.get('type') == 'choice' or (option_config.get('type') == 'str' and 'choices' in option_config):
                # Combobox for choices
                var = tk.StringVar(value=str(option_config.get('default', '')))
                combo = ttk.Combobox(mode_options_frame, textvariable=var, 
                                   values=option_config['choices'], state="readonly", width=15)
                combo.grid(row=row, column=1, padx=5, sticky="w")
                widgets.append(combo)
                mode_options_vars[option_name] = var
                
            elif option_config.get('type') == 'bool':
                # Checkbutton for boolean values
                var = tk.BooleanVar(value=option_config.get('default', False))
                check = tk.Checkbutton(mode_options_frame, variable=var)
                check.grid(row=row, column=1, padx=5, sticky="w")
                widgets.append(check)
                mode_options_vars[option_name] = var
                
            elif option_config.get('type') == 'int':
                # Spinbox for integers
                var = tk.IntVar(value=option_config.get('default', 0))
                spinbox = tk.Spinbox(mode_options_frame, textvariable=var,
                                   from_=option_config.get('min', 0),
                                   to=option_config.get('max', 100), width=10)
                spinbox.grid(row=row, column=1, padx=5, sticky="w")
                widgets.append(spinbox)
                mode_options_vars[option_name] = var
                
            elif option_config.get('type') == 'float':
                # Spinbox for float values - use DoubleVar for float support
                var = tk.DoubleVar(value=option_config.get('default', 0.0))
                # Use Entry with validation for better float input control
                entry = tk.Entry(mode_options_frame, textvariable=var, width=10)
                # Set initial value
                var.set(option_config.get('default', 0.0))
                entry.grid(row=row, column=1, padx=5, sticky="w")
                widgets.append(entry)
                mode_options_vars[option_name] = var
                
            elif option_config.get('type') == 'str':
                # Entry for string input
                var = tk.StringVar(value=str(option_config.get('default', '')))
                entry = tk.Entry(mode_options_frame, textvariable=var, width=30)
                
                # Add placeholder support if specified and no default value
                default_val = option_config.get('default', '')
                placeholder = option_config.get('placeholder', '')
                
                if placeholder and not default_val:
                    entry.config(fg='gray')
                    entry.insert(0, placeholder)
                    
                    # Handle focus events for placeholder
                    def on_focus_in(event, e=entry, v=var, placeholder=placeholder):
                        if e.get() == placeholder and e.cget('fg') == 'gray':
                            e.delete(0, tk.END)
                            e.config(fg='black')
                    
                    def on_focus_out(event, e=entry, v=var, placeholder=placeholder):
                        if not e.get():
                            e.config(fg='gray')
                            e.insert(0, placeholder)
                            v.set('')  # Keep variable empty for proper encoding
                    
                    entry.bind('<FocusIn>', on_focus_in)
                    entry.bind('<FocusOut>', on_focus_out)
                
                entry.grid(row=row, column=1, padx=5, sticky="w")
                widgets.append(entry)
                mode_options_vars[option_name] = var
            
            # Add tooltip if available
            if 'description' in option_config and widgets:
                tooltip_text = option_config['description']
                if 'choices' in option_config:
                    choices_str = [str(choice) for choice in option_config['choices']]
                    tooltip_text += f"\nChoices: {', '.join(choices_str)}"
                if 'min' in option_config or 'max' in option_config:
                    min_val = option_config.get('min', 'N/A')
                    max_val = option_config.get('max', 'N/A')
                    tooltip_text += f"\nRange: {min_val} - {max_val}"
                if 'example' in option_config:
                    tooltip_text += f"\nExamples: {option_config['example']}"
                if 'note' in option_config:
                    tooltip_text += f"\n\nNote: {option_config['note']}"
                ToolTip(widgets[-1], tooltip_text)
            
            mode_options_widgets[option_name] = widgets
            row += 1
        
        # Special setup for Barcode mode after all widgets are created
        if mode_name == "Barcode" and operation == "encode":
            # Check if both hide_text and custom_text_content options exist
            if 'hide_text' in mode_options_vars and 'custom_text_content' in mode_options_vars:
                hide_text_var = mode_options_vars['hide_text']
                
                def toggle_hide_text(*args):
                    # When hide_text is enabled, disable custom_text_content
                    custom_text_widgets = mode_options_widgets.get('custom_text_content', [])
                    if hide_text_var.get():
                        # Disable custom text entry
                        for widget in custom_text_widgets:
                            if hasattr(widget, 'config'):
                                widget.config(state='disabled')
                        # Clear the custom text
                        mode_options_vars['custom_text_content'].set('')
                    else:
                        # Enable custom text entry
                        for widget in custom_text_widgets:
                            if hasattr(widget, 'config'):
                                widget.config(state='normal')
                
                # Bind the callback
                hide_text_var.trace_add("write", toggle_hide_text)
                
                # Set initial state based on hide_text value
                if hide_text_var.get():
                    # If hide_text is initially True, disable custom text entry
                    custom_text_widgets = mode_options_widgets.get('custom_text_content', [])
                    for widget in custom_text_widgets:
                        if hasattr(widget, 'config'):
                            widget.config(state='disabled')
                    mode_options_vars['custom_text_content'].set('')
    
    def toggle_mode_options(*args):
        selected_mode = mode_combo.get()
        operation = mode_var.get()
        
        # Create options for the selected mode
        create_mode_options(selected_mode, operation)
        
        # Modes that show options in both encode and decode operations
        modes_with_decode_options = ["Emoji", "Sudoku", "Chess", "Barcode"]
        
        # Show mode options frame if there are options and appropriate operation
        # UUID mode uses its own dedicated frame, so exclude it
        show_mode_options = (mode_options_vars and 
                           ((operation == "encode" and selected_mode != "UUID") or 
                            (operation == "decode" and selected_mode in modes_with_decode_options)))
        
        if show_mode_options:
            mode_options_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
            option_frame.grid(row=5, column=0, columnspan=3, sticky="w")
        else:
            mode_options_frame.grid_remove()
            # Reset positioning based on UUID options visibility
            if selected_mode == "UUID" and operation == "encode":
                option_frame.grid(row=5, column=0, columnspan=3, sticky="w")
            else:
                option_frame.grid(row=4, column=0, columnspan=3, sticky="w")
        update_window_height()
        update_output_label_position()  # Update output label position
        # Re-trigger key field and custom filename positioning when mode options change
        toggle_key_field()
        toggle_custom_filename()
    
    def toggle_uuid_options(*args):
        selected_mode = mode_combo.get()
        operation = mode_var.get()
        # Only show UUID options for UUID mode AND encode operation
        if selected_mode == "UUID" and operation == "encode":
            uuid_options_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        else:
            uuid_options_frame.grid_remove()
        
        # Update mode options positioning after UUID options change
        toggle_mode_options()
    
    def combined_mode_update(*args):
        update_mode_info()
        toggle_uuid_options()
        toggle_mode_options()
        toggle_input_mode()  # Add input mode toggle here
        # Re-trigger key field and custom filename positioning
        toggle_key_field()
        toggle_custom_filename()
    
    mode_combo.bind("<<ComboboxSelected>>", combined_mode_update)
    # Also update options when switching between encode/decode
    mode_var.trace_add("write", toggle_uuid_options)
    mode_var.trace_add("write", toggle_mode_options)
    mode_var.trace_add("write", toggle_input_mode)  # Add input mode toggle

    # --- Key input
    key_label = tk.Label(root, text="Key:")
    key_entry = tk.Entry(root, show="*", width=50)  # Increased width
    show_btn = tk.Button(root, text="Show")

    def toggle_key_field(*args):
        if use_key_var.get():
            # Dynamic row positioning based on visible frames
            key_row = calculate_row_position(5)  # Base row after option_frame
                
            key_label.grid(row=key_row, column=0, sticky="w", padx=5, pady=5)
            key_entry.grid(row=key_row, column=1, sticky="ew", padx=5, pady=5)
            show_btn.grid(row=key_row, column=2, sticky="w", padx=5, pady=5)
        else:
            key_entry.delete(0, tk.END)
            key_label.grid_remove()
            key_entry.grid_remove()
            show_btn.grid_remove()
        update_window_height()  # Update window size
        update_output_label_position()  # Update output label position

    use_key_var.trace_add("write", toggle_key_field)

    def toggle_show():
        if key_entry.cget("show") == "":
            key_entry.config(show="*")
            show_btn.config(text="Show")
        else:
            key_entry.config(show="")
            show_btn.config(text="Hide")

    show_btn.config(command=toggle_show)

    # --- Output folder label
    output_dir_var = tk.StringVar(value=f"Output folder: {MACHINE_FILES_DIR}")
    output_dir_label = tk.Label(root, textvariable=output_dir_var, fg="gray")
    
    # Explanation label for encoding modes
    encoding_info_var = tk.StringVar(value="")
    encoding_info_label = tk.Label(root, textvariable=encoding_info_var, fg="blue", wraplength=350, justify="left")
    
    # Create start button early so it can be referenced
    start_btn = tk.Button(root, text="Start", state="disabled")
    
    def update_output_label_position():
        # Dynamic row positioning based on visible frames
        output_row = calculate_row_position(6)  # Base row after option_frame
            
        # Check if key field is visible
        if use_key_var.get():
            output_row += 1
            
        # Check if custom filename field is visible
        if use_random_var.get() and (mode_combo.get() == "QR Code" or mode_combo.get() == "Barcode") and mode_var.get() == "encode":
            output_row += 1
        
        # Remove existing widgets first to avoid duplicates
        output_dir_label.grid_remove()
        encoding_info_label.grid_remove()
        start_btn.grid_remove()
        
        # Position output directory label
        output_dir_label.grid(row=output_row, column=0, columnspan=3, sticky="w", padx=5)
        
        # Update encoding info label position
        encoding_row = output_row + 1
        encoding_info_label.grid(row=encoding_row, column=0, columnspan=3, sticky="w", padx=5)
        
        # Update start button position
        start_row = encoding_row + 1
        start_btn.grid(row=start_row, column=1, pady=15)
    
    # Initial label will be created by update_output_label_position()

    # Dictionary of mode explanations
    MODE_INFO = {
        "Base32": "Note: Base32 encoding uses 32 ASCII characters (A-Z, 2-7). More efficient than hex but less efficient than Base64. Suitable for case-insensitive systems.",
        "Base64": "Note: Standard Base64 encoding uses 64 ASCII characters (A-Z, a-z, 0-9, +, /). Commonly used for encoding binary data in email and web applications.",
        "Base85": "Note: Base85 encoding uses 85 ASCII characters, providing ~25% better compression than Base64. Often used in PDF files and Git.",
        "Base91": "Note: Base91 is a binary-to-text encoding that uses 91 printable ASCII characters, providing better efficiency than Base64.",
        "Barcode": "Note: Barcode encoding converts text into various barcode formats (Code128, Code39, EAN, UPC, etc.). Supports different barcode types with customizable dimensions and error correction. Limited to approximately 80 characters depending on barcode type.",
        "Binary": "Note: Binary encoding significantly increases output file size (8x larger) as each byte is represented by 8 binary digits (0s and 1s).",
        "Braille": "Note: Braille encoding converts data into Unicode Braille patterns. Uses 6-dot (traditional) or 8-dot (modern) Braille systems. Supports custom mapping for additional obfuscation.",
        "Hex": "Note: Hexadecimal encoding represents each byte as two hex digits (0-9, A-F). Simple but results in 2x larger file size.",
        "Image": "Note: Image encoding stores data as RGB pixel values in a PNG image. Good for visual steganography but requires image viewing software.",
        "QR Code": "Note: QR Code encoding converts text into a scannable QR code image. Limited to approximately 1000 characters of text. Ideal for URLs or short messages.",
        "Sound": "Note: Sound encoding converts data into MIDI musical notes. Each byte becomes one or more musical notes. Supports different encoding methods (single, dual, chord) and musical scales. Creates playable MIDI files.",
        "Sudoku": "Note: Sudoku encoding converts data into Sudoku grid positions and values. Each byte maps to row-column-value coordinates. Uses grid seeds and shuffle keys for security. Supports multiple output formats.",
        "Chess": "Note: Chess encoding converts data into chess board positions using FEN notation. Each byte maps to row-column-piece coordinates with sequence numbers. Uses FEN positions and shuffle keys for security. Supports multiple output formats.",
        "Zero-Width": "Note: Zero-Width encoding uses invisible Unicode characters to hide data in plain text. Excellent for steganography but may be affected by text processing.",
        "Emoji": "Note: Emoji encoding converts each byte into a corresponding emoji character. Uses a key to shuffle the emoji table for added security. Fun and visually appealing output.",
        "UUID": "Note: UUID encoding converts data into universally unique identifiers (UUIDs). Each 16-byte chunk becomes a UUID. Supports multiple UUID versions (1, 3, 4, 5) with optional namespace for versions 3 and 5."
    }

    # List of modes where string encoding has no significant effect
    ENCODING_INDEPENDENT_MODES = ["Hex", "Binary", "Image", "QR Code", "Barcode", "Emoji", "Braille", "Sound", "Sudoku", "Chess"]
    
    # List of modes that use text input instead of file input
    TEXT_INPUT_MODES = ["QR Code", "Barcode"] # This needs to match the keys in the MODES dictionary
    
    def update_mode_info(*args):
        selected_mode = mode_combo.get()
        
        # Always show the info label and set the relevant message
        info_text = MODE_INFO.get(selected_mode, "")
        encoding_info_var.set(info_text)
        
        # Only show the label if there's content
        if info_text:
            # Position will be updated by update_output_label_position
            pass
        else:
            encoding_info_label.grid_forget()
            
        # Enable/disable string encoding based on selected mode
        if mode_var.get() == "encode" and selected_mode in ENCODING_INDEPENDENT_MODES:
            strenc_combo.config(state="disabled")
        elif mode_var.get() == "encode":
            strenc_combo.config(state="readonly")
        # Note: For decode mode, string encoding is always disabled (handled in toggle_strenc)
        
        # Update custom filename label for QR Code and Barcode modes
        if (selected_mode == "QR Code" or selected_mode == "Barcode") and mode_var.get() == "encode":
            random_check.config(text="Custom Filename")
        else:
            random_check.config(text="Random Name")
            
        # Toggle between file input and text input based on mode
        toggle_input_mode()
        
        # Update custom filename field visibility
        toggle_custom_filename()
        
        # Update positions
        update_output_label_position()
        
        # Update window height based on current field visibility
        update_window_height()

    def toggle_strenc(*args):
        # Get the mode name string, not the actual module
        selected_mode = mode_combo.get()
        
        if mode_var.get() == "encode":
            # Don't enable string encoding here - let update_mode_info handle it
            # based on the selected mode
            random_check.config(state="normal")   # enable random
            output_dir_var.set(f"Output folder: {MACHINE_FILES_DIR}")
            # QR result display no longer needed
        else:
            strenc_combo.config(state="disabled")
            random_check.config(state="disabled") # disable random
            use_random_var.set(False)
            output_dir_var.set(f"Output folder: {HUMAN_FILES_DIR}")

        # Update info and string encoding state based on the currently selected mode
        update_mode_info()
        
        # Reset file or text input
        file_var.set("")
        text_multiline.delete("1.0", "end")
        # QR result display no longer needed
        start_btn.config(state="disabled")
        
        # Update custom filename field visibility
        toggle_custom_filename()
        
        # Update window height based on current field visibility
        update_window_height()

    mode_var.trace_add("write", toggle_strenc)

    # Set initial string encoding state
    update_mode_info()
    
    # --- Start button
    def start_process():
        # Get the selected mode string and convert to the actual module
        mode_name = mode_combo.get()
        selected_mode = MODES[mode_name]
        operation = mode_var.get()
        
        # Handle QR Code text input when encoding
        if mode_name == "QR Code" and operation == "encode":
            text_content = text_multiline.get("1.0", "end-1c")  # Get text without final newline
            
            if not text_content:
                messagebox.showerror("Error", "No text entered!")
                return
                
            # Check text length
            max_len = qr_code_mode.get_max_text_length()
            if len(text_content) > max_len:
                messagebox.showerror("Error", f"Text too long! Maximum {max_len} characters.")
                return
            
            # Check if custom filename is required but empty
            if use_random_var.get() and custom_filename_var.get().strip() == "":
                messagebox.showerror("Error", "Please enter a filename or uncheck 'Custom Filename' option.")
                return
                
            # For QR Code, we'll process the text directly
            
            # Set utf-8 encoding
            str_enc = "utf-8"  # Always use utf-8 for QR text
            
            # For QR Code and Barcode, we always want to either use custom filename or timestamp format
            # So we'll force use_random=True and handle the naming ourselves
            
            # If custom filename is provided, use it
            if use_random_var.get() and custom_filename_var.get().strip():
                # Set a custom name that will be used 
                filename = custom_filename_var.get().strip()
            else:
                # Generate timestamp-based name: qr_YYYYMMDD_HHMMSSmm
                import datetime
                now = datetime.datetime.now()
                filename = f"qr_{now.strftime('%Y%m%d_%H%M%S%f')[:-4]}"
            
            # Create processor with progress bar
            progress_handler = ProgressHandler("Creating QR Code", 100)
            processor = ChunkProcessor(progress_handler)
            
            # Process the text directly
            try:
                # Convert text to bytes
                text_bytes = text_content.encode(str_enc)
                
                # Apply XOR if needed
                if use_key_var.get() and key_entry.get():
                    from src import key_cipher
                    progress_handler.update_additional_status("Encrypting with key...")
                    text_bytes = key_cipher.apply_xor(text_bytes, key_entry.get())
                
                # Generate QR code directly
                progress_handler.update_additional_status("Creating QR code...")
                encoded_qr = selected_mode.encode(text_bytes, str_enc)
                
                # Get the output path
                output_path = os.path.join(os.path.abspath("machine_files"), 
                                          filename + ".png")
                
                # Update progress
                progress_handler.update_progress(75, 100)
                progress_handler.update_additional_status("Saving QR code...")
                
                # Save the QR code directly
                if selected_mode.save_qr_image(encoded_qr, output_path):
                    # Display success in the progress handler
                    progress_handler.complete(success=True, output_file=output_path)
                else:
                    # Show error message
                    progress_handler.complete(success=False, error_msg="Failed to save QR code")
            except Exception as e:
                # Show error message
                progress_handler.complete(success=False, error_msg=str(e))
        # Handle Barcode text input when encoding
        elif mode_name == "Barcode" and operation == "encode":
            text_content = text_multiline.get("1.0", "end-1c")  # Get text without final newline
            
            if not text_content:
                messagebox.showerror("Error", "No text entered!")
                return
                
            # Check text length
            max_len = barcode_mode.get_max_text_length()
            if len(text_content) > max_len:
                messagebox.showerror("Error", f"Text too long! Maximum {max_len} characters.")
                return
            
            # Check if custom filename is required but empty
            if use_random_var.get() and custom_filename_var.get().strip() == "":
                messagebox.showerror("Error", "Please enter a filename or uncheck 'Custom Filename' option.")
                return
                
            # For Barcode, we'll process the text directly
            
            # Set utf-8 encoding
            str_enc = "utf-8"  # Always use utf-8 for Barcode text
            
            # For Barcode, we always want to either use custom filename or timestamp format
            # So we'll force use_random=True and handle the naming ourselves
            
            # If custom filename is provided, use it
            if use_random_var.get() and custom_filename_var.get().strip():
                # Set a custom name that will be used 
                filename = custom_filename_var.get().strip()
            else:
                # Generate timestamp-based name: barcode_YYYYMMDD_HHMMSSmm
                import datetime
                now = datetime.datetime.now()
                filename = f"barcode_{now.strftime('%Y%m%d_%H%M%S%f')[:-4]}"
            
            # Create processor with progress bar
            progress_handler = ProgressHandler("Creating Barcode", 100)
            processor = ChunkProcessor(progress_handler)
            
            # Process the text directly
            try:
                # Convert text to bytes
                text_bytes = text_content.encode(str_enc)
                
                # Apply XOR if needed
                if use_key_var.get() and key_entry.get():
                    from src import key_cipher
                    progress_handler.update_additional_status("Encrypting with key...")
                    text_bytes = key_cipher.apply_xor(text_bytes, key_entry.get())
                
                # Get barcode options
                barcode_opts = {}
                for option_name, var in mode_options_vars.items():
                    if isinstance(var, (tk.IntVar, tk.DoubleVar, tk.BooleanVar)):
                        barcode_opts[option_name] = var.get()
                    else:
                        value = var.get()
                        # Only add non-empty values, and check for placeholder text
                        if value and value.strip():  # Ensure non-empty and not just whitespace
                            # For custom_text_content, make sure it's not the placeholder text
                            if option_name == "custom_text_content":
                                # Check if the entry is showing placeholder text
                                custom_text_widgets = mode_options_widgets.get('custom_text_content', [])
                                is_placeholder = False
                                for widget in custom_text_widgets:
                                    if hasattr(widget, 'cget') and hasattr(widget, 'get'):
                                        widget_text = widget.get().strip()
                                        if (widget.cget('fg') == 'gray' and 
                                            widget_text == "Enter custom text"):
                                            is_placeholder = True
                                            break
                                # Only add if it's not placeholder text
                                if not is_placeholder and value.strip() != "Enter custom text":
                                    barcode_opts[option_name] = value.strip()
                            else:
                                barcode_opts[option_name] = value
                
                # Generate Barcode directly
                progress_handler.update_additional_status("Creating barcode...")
                encoded_barcode = selected_mode.encode(text_bytes, str_enc, **barcode_opts)
                
                # Get the output path
                output_path = os.path.join(os.path.abspath("machine_files"), 
                                          filename + ".png")
                
                # Update progress
                progress_handler.update_progress(75, 100)
                progress_handler.update_additional_status("Saving barcode...")
                
                # Save the Barcode directly
                if selected_mode.save_barcode_image(encoded_barcode, output_path):
                    # Display success in the progress handler
                    progress_handler.complete(success=True, output_file=output_path)
                else:
                    # Show error message
                    progress_handler.complete(success=False, error_msg="Failed to save barcode")
            except Exception as e:
                # Show error message
                progress_handler.complete(success=False, error_msg=str(e))
        else:
            # Standard file handling for other modes
            path = file_var.get()
            if not path:
                messagebox.showerror("Error", "No file selected!")
                return
            
            if operation == "encode":
                # If string encoding is disabled (for modes where it doesn't matter),
                # use "utf-8" as default
                str_enc = strenc_combo.get() if strenc_combo.cget("state") == "readonly" else "utf-8"
                
                # Prepare UUID options if UUID mode is selected
                uuid_opts = None
                if mode_name == "UUID":
                    uuid_opts = {
                        'version': int(uuid_version_var.get()),
                    }
                    # Add namespace if provided and version supports it
                    namespace = uuid_namespace_var.get().strip()
                    if namespace and uuid_version_var.get() in ["3", "5"]:
                        uuid_opts['namespace_uuid'] = namespace
                
                # Get mode options
                mode_opts = {}
                for option_name, var in mode_options_vars.items():
                    if isinstance(var, tk.IntVar):
                        mode_opts[option_name] = var.get()
                    else:
                        value = var.get()
                        if value:  # Only add non-empty values
                            mode_opts[option_name] = value
                
                process_encode(path, mode_name, str_enc,
                               use_key_var.get(), key_entry.get(),
                               use_random_var.get(), uuid_opts, mode_opts)
            else:
                # Get mode options for decode as well (needed for Emoji shuffle key)
                mode_opts = {}
                for option_name, var in mode_options_vars.items():
                    if isinstance(var, tk.IntVar):
                        mode_opts[option_name] = var.get()
                    else:
                        value = var.get()
                        if value:  # Only add non-empty values
                            mode_opts[option_name] = value
                            
                process_decode(path, selected_mode, key_entry.get(), mode_opts)

    start_btn.config(command=start_process)
    
    # Add keyboard shortcuts
    root.bind("<Control-f>", lambda e: search_mode())
    root.bind("<Control-F>", lambda e: search_mode())  # Also handle uppercase
    
    # Initialize UI elements
    toggle_strenc()
    update_mode_info()
    combined_mode_update()  # Initialize options and window size properly
    root.mainloop()
