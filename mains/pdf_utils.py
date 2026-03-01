import os
import pdfplumber
import pytesseract
import re
from PIL import Image

# 1. Path Auto-Config
if os.name == 'nt':
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def clean_text(text):
    """Clean extra spaces and junk characters"""
    if not text: return ""
    # Remove CID artifacts
    text = re.sub(r"\(cid:\d+\)", "", text)
    # Remove non-printable characters
    text = "".join(ch for ch in text if ch.isprintable() or ch in "\n\t")
    # Simplify whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def extract_text_from_pdf(file):
    """Optimized for Long PDFs (20+ Pages)"""
    file.seek(0)
    text = ""

    # Strategy 1: Digital Stream (Sabse Fast & Memory Efficient)
    try:
        with pdfplumber.open(file) as pdf:
            print(f"📄 Extracting text from {len(pdf.pages)} pages...")
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"❌ Digital extraction error: {e}")

    # Strategy 2: OCR Fallback (Sirf tab use karo jab digital fail ho jaye)
    # WARNING: 20+ pages ka OCR Render Free Tier par Memory Crash kar sakta hai!
    if not text.strip() or len(text.strip()) < 50:
        print("⚠️ Text not found. Digital PDF check failed. Check if it's a scanned image.")
        # Agar aap Docker use nahi kar rahe, toh Render pe ye line error degi.
        # Aap yahan user ko error dikha sakte ho: "Scanned PDFs not supported on Free Tier"
    
    return clean_text(text)