# Test Files Guide

This directory contains various test files designed to help you test different encoding modes in the Data Encryption and Decryption application.

# 📁 Available Test Files:

📄 simple_text.txt
Purpose: Basic text for testing fundamental modes
Best for: Base64, Base32, Binary, Hex, Zero Width
Content: Simple English text

📄 unicode_test.txt  
 Purpose: Unicode and special character testing
Best for: All text modes, especially with international text
Content: Multiple languages, emojis, special symbols

📄 test_data.json
Purpose: Structured data testing
Best for: All modes, particularly good for QR codes
Content: JSON configuration data

📄 sudoku_test_data.txt
Purpose: Optimized for Sudoku encoding mode
Best for: Sudoku mode testing with various data types
Content: Mixed alphanumeric and text data

📄 braille_test_input.txt
Purpose: Braille mode testing
Best for: Braille encoding mode
Content: Text optimized for Braille conversion

📄 chess_test_data.txt
Purpose: Chess mode testing
Best for: Chess encoding mode
Content: Chess notation and related text

📄 emoji_test_data.txt
Purpose: Emoji mode testing
Best for: Emoji encoding mode
Content: Various text types for emoji conversion

📄 quick_test.txt
Purpose: Fast functionality testing
Best for: All modes (quick verification)
Content: Short, simple test data

📄 math_test_data.txt
Purpose: Numerical and mathematical data testing
Best for: All modes, especially those handling numbers well
Content: Mathematical sequences and expressions

📄 security_test_data.txt
Purpose: Testing encryption with keys
Best for: All modes with key-based encryption enabled
Content: Fake sensitive data (safe for testing)

# 🚀 How to Use:

1. Launch the Data Encryption and Decryption application
2. Select your desired encoding mode
3. Click "Browse" and select one of these test files
4. Configure any mode-specific options
5. Enable key encryption if testing with security_test_data.txt
6. Click "Encode" to process the file
7. Check the output in the machine_files directory
8. Test decoding by selecting the generated file and clicking "Decode"

# 💡 Tips:

- Start with quick_test.txt for initial functionality verification
- Use unicode_test.txt to test international character support
- Try security_test_data.txt with different encryption keys
- Compare output file sizes between different modes
- Test the same input with multiple modes to see differences
- Use mode-specific test files for optimized results

# ⚠️ Important Notes:

- All data in these files is fake and safe for testing
- Output files will be saved in the machine_files directory
- Some modes produce text output, others produce images
- Always test both encoding and decoding for complete verification
- Large files may take longer to process with some modes

Happy testing! 🎉
