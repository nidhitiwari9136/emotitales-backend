import pdfplumber
import re
import os

def clean_text(text):
    """
    Cleans junk characters, CID artifacts, and fixes whitespace.
    Works for Hindi, English, and other regional languages.
    """
    if not text:
        return ""

    # 1. Remove PDF encoding artifacts like (cid:123)
    text = re.sub(r"\(cid:\d+\)", "", text)

    # 2. Fix whitespace: Replace multiple spaces/newlines with a single space
    text = re.sub(r'\s+', ' ', text)

    # 3. Keep only printable characters (removes control codes that break JSON)
    text = "".join(ch for ch in text if ch.isprintable() or ch in "\n\t")

    return text.strip()

def extract_text_from_pdf(file):
    """
    Fast & Memory-efficient extraction for long PDFs (20-100+ pages).
    No OCR, no heavy RAM usage.
    """
    # Reset file pointer to start
    file.seek(0)
    extracted_text = []

    try:
        with pdfplumber.open(file) as pdf:
            total_pages = len(pdf.pages)
            print(f"📄 Processing Digital PDF: {total_pages} pages detected.")

            for i, page in enumerate(pdf.pages):
                # Extract text from each page
                page_content = page.extract_text()
                if page_content:
                    extracted_text.append(page_content)
                
                # Progress log for large files (visible in Render logs)
                if (i + 1) % 10 == 0:
                    print(f"✅ Extracted {i + 1}/{total_pages} pages...")

        full_text = "\n".join(extracted_text)
        return clean_text(full_text)

    except Exception as e:
        print(f"❌ PDF Extraction Failed: {str(e)}")
        return ""

def extract_text_from_txt(file):
    """Simple extraction for .txt files"""
    try:
        file.seek(0)
        content = file.read().decode("utf-8")
        return clean_text(content)
    except Exception as e:
        print(f"❌ TXT Extraction Failed: {str(e)}")
        return ""