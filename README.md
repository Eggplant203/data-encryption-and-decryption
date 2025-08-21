# Data Encryption and Decryption Tool

A comprehensive application for encoding and decoding files using 15 different methods with advanced options and security features.

## 🚀 Quick Start

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**

   ```bash
   python main.py
   ```

3. **Usage:**
   - Select Encode/Decode operation
   - Browse for input file or enter text directly
   - Choose from 15 encoding modes
   - Configure options and click Start

## 📋 Encoding Modes

### Text-Based

- **Base32/64/85/91**: Standard text encoding formats
- **Binary/Hex**: Simple binary representations
- **Braille**: Unicode Braille character mapping

### Visual

- **QR Code**: Scannable 2D codes with error correction
- **Barcode**: Professional 1D barcodes with custom text
- **Image**: Data encoded as RGB pixels in PNG
- **Chess**: Interactive chess board positions
- **Sudoku**: Puzzle grid coordinates

### Audio/Creative

- **Sound (MIDI)**: Musical note sequences
- **Emoji**: Emoji character sequences
- **UUID**: UUID-embedded data

### Steganographic

- **Zero-Width**: Invisible Unicode characters
- **Image Steganography**: Hidden pixel data

## ⚙️ Key Features

- **🔍 Smart Search**: Find modes quickly with Ctrl+F
- **🔐 XOR Encryption**: Optional key-based security
- **📊 Interactive Viewers**: Chess and Sudoku visualization
- **⚡ Progress Tracking**: Real-time processing feedback
- **🎨 Dynamic Options**: Context-sensitive settings
- **📁 Auto Organization**: Separate human/machine file directories

## 🛠️ Mode Options

Different modes offer specific customization options:

- **QR Code**: Error correction level, size, border
- **Barcode**: Type, dimensions (mm), custom text, font size (pt)
- **Sound**: Encoding method, tempo, note duration
- **Sudoku**: Grid seed, shuffle key, format style
- **Chess**: Interactive viewer, PNG export
- **Emoji**: Shuffle patterns for obfuscation
- **Image**: PNG compression levels (0-9)

## 🔒 Security

- **XOR Encryption**: Apply to any mode using custom keys
- **Random Filenames**: Hide original file names
- **Steganographic Modes**: Multiple hidden data techniques
- **Visual Obfuscation**: Emoji shuffling, chess positions

## 📁 Directory Structure

```
├── main.py              # Application entry point
├── human_files/         # Original files (input)
├── machine_files/       # Encoded files (output)
├── chess_images/        # Chess viewer exports
├── fonts/               # FiraCode font files
├── src/                 # Source code modules
└── requirements.txt     # Dependencies
```

## 📦 Requirements

- Python 3.6+
- Pillow (image processing)
- qrcode (QR code generation)
- pyzbar (barcode reading)
- tkinter (GUI - included with Python)

## 📖 Test Files

The `human_files/` directory includes sample test files for trying different encoding modes:

- `simple_text.txt` - Basic text for all modes
- `unicode_test.txt` - Multi-language and emoji content
- `quick_test.txt` - Small file for fast testing
- Mode-specific test files for optimal results
- `README_TEST_FILES.md` - Detailed usage guide

## 🎯 Performance Tips

- **Small files** (<100KB): All settings work well
- **Large files** (>1MB): Use optimized settings for MIDI mode
- **MIDI playback**: Default ultra-fast settings reduce hours to minutes
- **Search**: Use Ctrl+F to quickly find the right encoding mode

## 📄 License

MIT License - see `LICENSE` file for details.

## 👤 Author

© 2025 - Developed by Eggplant203 🍆

---

_For detailed technical documentation and advanced options, see the source code comments and mode-specific help tooltips in the application._
