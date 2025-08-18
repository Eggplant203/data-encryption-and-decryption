# main_gui.py
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from src import util, base64_mode, base85_mode, base32_mode, hex_mode, image_mode, key_cipher, random_name
from src.file_processor import ChunkProcessor
from src.progress_handler import ProgressHandler
import subprocess
import sys

MODES = {
    "Base32": base32_mode,
    "Base64": base64_mode,
    "Base85": base85_mode,
    "Hex": hex_mode,
    "Image": image_mode
}

STRING_ENCODINGS = ["ascii", "latin-1", "utf-8"]

MACHINE_FILES_DIR = os.path.abspath("machine_files")
HUMAN_FILES_DIR = os.path.abspath("human_files")
os.makedirs(MACHINE_FILES_DIR, exist_ok=True)
os.makedirs(HUMAN_FILES_DIR, exist_ok=True)

def open_file(path: str):
    try:
        if sys.platform.startswith("darwin"):
            subprocess.call(["open", path])
        elif os.name == "nt":
            os.startfile(path)  # type: ignore
        elif os.name == "posix":
            subprocess.call(["xdg-open", path])
    except Exception as e:
        messagebox.showerror("Error", f"Could not open file:\n{str(e)}")

# Removed the show_success function - using ProgressHandler.show_success instead

def process_encode(file_path, mode_name, str_encoding, use_key, key_text, use_random):
    processor = None
    progress_handler = None
    try:
        mode = MODES[mode_name]
        name, ext, size = util.get_file_info(file_path)
        
        # Use ChunkProcessor to handle large files with progress bar
        progress_handler = ProgressHandler("Encoding File", size)
        processor = ChunkProcessor(progress_handler)
        encoded_str = processor.encode_file(file_path, mode, str_encoding, use_key, key_text)
        
        # Use random filename if random option is enabled
        if use_random:
            out_name = random_name.generate_filename(len(name))
        else:
            out_name = name
            
        # For image mode, save as PNG file
        if mode_name == "Image":
            out_name = f"{out_name}.png"
            output_path = os.path.join(MACHINE_FILES_DIR, out_name)
            
            if progress_handler:
                progress_handler.update_additional_status("Saving image file...")
                
            # Save the image
            image_mode.save_image(encoded_str, output_path)
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

def process_decode(file_path, mode_name, key_text):
    processor = None
    progress_handler = None
    try:
        # Check if the file exists and is readable
        if not os.path.isfile(file_path):
            messagebox.showerror("Error", f"File not found: {file_path}")
            return
            
        # Verify the selected mode matches the file type
        if file_path.lower().endswith('.png') and mode_name != "Image":
            if messagebox.askyesno("Mode Mismatch", 
                                  "You selected a PNG file but not Image mode. Switch to Image mode?"):
                mode_name = "Image"
        elif not file_path.lower().endswith('.png') and mode_name == "Image":
            if messagebox.askyesno("Mode Mismatch", 
                                  "You selected Image mode but not a PNG file. Choose a different mode?"):
                # Default to Base64 for non-PNG files
                mode_name = "Base64"
            
        mode = MODES[mode_name]
        file_size = os.path.getsize(file_path)
        
        # Use ChunkProcessor to handle large files with progress bar
        progress_handler = ProgressHandler("Decoding File", file_size)
        processor = ChunkProcessor(progress_handler)
        meta, raw = processor.decode_file(file_path, mode, key_text)
        
        parts = meta.decode("utf-8").split("|")
        name_ext, size_str, str_encoding = parts
        name, ext = os.path.splitext(name_ext)
        size = int(size_str)
        
        if len(raw) != size:
            raise ValueError("Decoded file size mismatch!")
            
        output_path = os.path.join(HUMAN_FILES_DIR, f"{name}{ext}")
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
    root = tk.Tk()
    root.title("File Encoder/Decoder")

    # --- Operation
    mode_var = tk.StringVar(value="encode")
    tk.Label(root, text="Operation:").grid(row=0, column=0, sticky="w")
    tk.Radiobutton(root, text="Encode", variable=mode_var, value="encode").grid(row=0, column=1, sticky="w")
    tk.Radiobutton(root, text="Decode", variable=mode_var, value="decode").grid(row=0, column=2, sticky="w")

    # --- File selection
    tk.Label(root, text="Select File:").grid(row=1, column=0, sticky="w")
    file_var = tk.StringVar()
    file_entry = tk.Entry(root, textvariable=file_var, state="readonly", width=40)
    file_entry.grid(row=1, column=1, padx=5, pady=5)

    def browse_file():
        if mode_var.get() == "encode":
            path = filedialog.askopenfilename(initialdir=HUMAN_FILES_DIR, title="Select file to encode")
        else:
            # Allow selecting PNG files when Image mode is selected
            if mode_combo.get() == "Image":
                path = filedialog.askopenfilename(initialdir=MACHINE_FILES_DIR, title="Select encoded PNG file", 
                                                filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
            else:
                path = filedialog.askopenfilename(initialdir=MACHINE_FILES_DIR, title="Select encoded txt file", 
                                                filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if path:
            file_var.set(path)
            start_btn.config(state="normal")
            
            # Automatically select Image mode if decoding a PNG file
            if mode_var.get() == "decode" and path.lower().endswith('.png'):
                mode_combo.set("Image")

    browse_btn = tk.Button(root, text="Browse", command=browse_file)
    browse_btn.grid(row=1, column=2, padx=5, pady=5)

    # --- Encoding mode
    tk.Label(root, text="Mode:").grid(row=2, column=0, sticky="w")
    mode_combo = ttk.Combobox(root, values=sorted(MODES.keys()), state="readonly")
    mode_combo.current(0)
    mode_combo.grid(row=2, column=1, padx=5, pady=5)
    mode_combo.bind("<KeyPress>", lambda e: "break")

    # --- String encoding
    tk.Label(root, text="String Encoding:").grid(row=3, column=0, sticky="w")
    strenc_combo = ttk.Combobox(root, values=sorted(STRING_ENCODINGS), state="readonly")
    strenc_combo.current(0)
    strenc_combo.grid(row=3, column=1, padx=5, pady=5)
    strenc_combo.bind("<KeyPress>", lambda e: "break")

    # --- Key Option + Random Option
    option_frame = tk.Frame(root)
    option_frame.grid(row=4, column=0, columnspan=3, sticky="w")

    use_key_var = tk.BooleanVar(value=False)
    key_check = tk.Checkbutton(option_frame, text="Use Key", variable=use_key_var)
    key_check.pack(side="left", padx=5)

    use_random_var = tk.BooleanVar(value=False)
    random_check = tk.Checkbutton(option_frame, text="Random Name", variable=use_random_var)
    random_check.pack(side="left", padx=5)

    # --- Key input
    key_label = tk.Label(root, text="Key:")
    key_entry = tk.Entry(root, show="*")
    show_btn = tk.Button(root, text="Show")

    def toggle_key_field(*args):
        if use_key_var.get():
            key_label.grid(row=5, column=0, sticky="w")
            key_entry.grid(row=5, column=1, padx=5, pady=5, sticky="w")
            show_btn.grid(row=5, column=2, padx=5, pady=5, sticky="w")
        else:
            key_entry.delete(0, tk.END)
            key_label.grid_forget()
            key_entry.grid_forget()
            show_btn.grid_forget()

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
    tk.Label(root, textvariable=output_dir_var, fg="gray").grid(row=6, column=0, columnspan=3, sticky="w", padx=5)
    
    # Explanation label for string encoding and key usage
    encoding_info_var = tk.StringVar(value="")
    encoding_info_label = tk.Label(root, textvariable=encoding_info_var, fg="blue", wraplength=350, justify="left")
    encoding_info_label.grid(row=7, column=0, columnspan=3, sticky="w", padx=5)

    def update_mode_info(*args):
        # Don't show Image Note text as requested
        encoding_info_var.set("")
        encoding_info_label.grid_forget()

    mode_combo.bind("<<ComboboxSelected>>", update_mode_info)

    def toggle_strenc(*args):
        selected_mode = mode_combo.get()
        
        if mode_var.get() == "encode":
            strenc_combo.config(state="readonly")
            random_check.config(state="normal")   # enable random
            output_dir_var.set(f"Output folder: {MACHINE_FILES_DIR}")
        else:
            strenc_combo.config(state="disabled")
            random_check.config(state="disabled") # disable random
            use_random_var.set(False)
            output_dir_var.set(f"Output folder: {HUMAN_FILES_DIR}")

        # Update info based on the currently selected mode
        update_mode_info()
        
        file_var.set("")
        start_btn.config(state="disabled")

    mode_var.trace_add("write", toggle_strenc)

    # --- Start button
    def start_process():
        path = file_var.get()
        if not path:
            messagebox.showerror("Error", "No file selected!")
            return
        if mode_var.get() == "encode":
            process_encode(path, mode_combo.get(), strenc_combo.get(),
                           use_key_var.get(), key_entry.get(),
                           use_random_var.get())
        else:
            process_decode(path, mode_combo.get(), key_entry.get())

    start_btn = tk.Button(root, text="Start", command=start_process, state="disabled")
    start_btn.grid(row=8, column=1, pady=10)

    toggle_strenc()
    root.mainloop()
