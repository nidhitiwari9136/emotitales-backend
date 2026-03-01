import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
from PIL import Image, ImageOps
import re

# Tesseract path configuration
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def fix_cid_artifacts(text):
    """Remove PDF encoding junk like (cid:336)"""
    return re.sub(r"\(cid:\d+\)", "", text)

def fix_hindi_matra(text):
    """Correction for misplaced Devanagari matras"""
    text = re.sub(r"ि([क-ह])", r"\1ि", text)
    text = re.sub(r"े([क-ह])", r"\1े", text)
    text = re.sub(r"ै([क-ह])", r"\1ै", text)
    return text

def clean_text(text):
    """General text cleaning for symbols and extra whitespace"""
    text = text.replace("\n", " ")
    text = re.sub(r"[\x00-\x1F]", "", text)
    text = fix_hindi_matra(text)
    return " ".join(text.split()).strip()

def extract_text_from_pdf(file):
    """Extracts text using digital stream first, then falls back to batch OCR"""
    file.seek(0)
    pdf_bytes = file.read()
    text = ""

    # Step 1: Digital extraction
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t: text += t + "\n"
    except Exception as e:
        print(f"Digital extraction failed: {e}")

    # Step 2: OCR Fallback if text is garbled or empty
    if not text.strip() or "(cid:" in text or len(text.strip()) < 100:
        print("Starting batch OCR for long document...")
        # Using 250 DPI to balance speed and accuracy for 20-30 pages
        images = convert_from_bytes(pdf_bytes, dpi=250)
        text = ""
        for i, img in enumerate(images):
            # Process page by page to keep RAM usage low
            img = img.convert("L") 
            ocr_page = pytesseract.image_to_string(img, lang="eng+hin+mar+tam+tel+ben+guj+pan")
            text += ocr_page + "\n"
            img.close() # Explicitly close image handle

    return clean_text(text)

def extract_text_from_image(file):
    """OCR for standalone image files"""
    file.seek(0)
    img = Image.open(file).convert("L")
    text = pytesseract.image_to_string(img, lang="eng+hin+mar+tam+tel+ben+guj+pan")
    return clean_text(text)