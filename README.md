# File Encoder/Decoder

A powerful and user-friendly application for encoding files into various formats and decoding them back to their original state. This tool provides multiple encoding methods with optional encryption for secure file transformation.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Encoding Modes](#encoding-modes)
  - [Text-Based Encoding](#text-based-encoding)
  - [Image Encoding](#image-encoding)
- [Security](#security)
- [Directory Structure](#directory-structure)
- [Requirements](#requirements)

## Overview

This application transforms files between human-readable and machine-readable formats using multiple encoding algorithms. It provides a graphical user interface for easy interaction and supports various encoding methods including Base32, Base64, Base85, Hex, and image-based encoding.

## Features

- **Multiple Encoding Methods**: Support for Base32, Base64, Base85, Hex, and image-based encoding
- **XOR Encryption**: Optional encryption using a custom key for added security
- **Randomized Filenames**: Option to generate random filenames for output files
- **Progress Tracking**: Real-time progress monitoring with detailed status updates
- **Chunk Processing**: Efficient handling of large files through chunk-based processing
- **Intuitive UI**: User-friendly interface with clear operation controls
- **Error Handling**: Comprehensive error detection and user notifications

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/Eggplant203/data-encryption-and-decryption.git
   cd data-encryption-and-decryption
   ```

2. Install required packages:

   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python main.py
   ```

## Usage

1. **Select Operation**: Choose between Encode or Decode
2. **Select File**: Browse for the input file
3. **Choose Encoding Mode**: Select from Base32, Base64, Base85, Hex, or Image
4. **Configure Options**: Set string encoding, enable encryption, or use random filenames
5. **Process**: Click Start to begin the encoding or decoding process
6. **View Results**: After processing, you can open the resulting file directly

## Encoding Modes

### Text-Based Encoding

- **Base32**: RFC 4648 compliant Base32 encoding, suitable for case-insensitive systems
- **Base64**: Standard Base64 encoding for binary data
- **Base85**: More compact than Base64, using 85 characters for representation
- **Hex**: Simple hexadecimal representation of binary data

### Image Encoding

The Image encoding mode converts binary data into color pixels in a PNG image:

- Each pixel stores 3 bytes of data (one byte per RGB channel)
- The image dimensions are calculated to create a roughly square image
- Metadata about the original file is embedded for proper decoding
- String encoding settings affect only metadata, not the pixel data itself
- XOR encryption can be applied before pixel conversion for enhanced security

## Security

- **XOR Encryption**: Simple but effective when combined with a strong key
- **Random Names**: Hide the original filename for additional obscurity
- **Format Obfuscation**: Image encoding hides data in visually neutral pixel patterns

## Directory Structure

- **human_files/**: Storage for original, human-readable files
- **machine_files/**: Storage for encoded, machine-readable files
- **src/**: Source code for the application modules

## Requirements

- Python 3.6+
- Pillow 9.0.0+ (for image processing)
- NumPy 1.21.0+ (for array operations)
- Standard library modules (tkinter, os, io, sys, etc.)

## License

The project is distributed under the MIT license. See the `LICENSE` file for details.

## Author

© 2025 - Developed by Eggpant203 🍆
