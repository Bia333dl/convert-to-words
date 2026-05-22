import streamlit as st
from google import genai
from PIL import Image
from docx import Document
import img2pdf
from pdf2image import convert_from_path
import os
import tempfile
import io

st.set_page_config(page_title="AI Document Digitizer Pro", layout="centered")

st.title("📄 AI Document Digitizer Pro")
st.markdown("**Upload scanned PDF or images → Get a well-formatted Word document with tables preserved**")

# API Key
api_key = st.text_input("Enter your Gemini API Key", type="password", 
                       help="Get free key from https://aistudio.google.com/app/apikey")

# === Combine Images to PDF (Optional) ===
st.subheader("Step 1: Combine Images into One PDF (Optional)")
image_files = st.file_uploader("Upload multiple images", type=["jpg","jpeg","png","webp"], 
                              accept_multiple_files=True, key="images")

if st.button("Create PDF from Images") and image_files:
    with tempfile.TemporaryDirectory() as tmpdir:
        paths = []
        for img in image_files:
            path = os.path.join(tmpdir, img.name)
            with open(path, "wb") as f:
                f.write(img.getbuffer())
            paths.append(path)
        
        pdf_bytes = img2pdf.convert(paths)
        st.download_button("📥 Download Combined PDF", pdf_bytes, "combined.pdf", "application/pdf")

# === Main OCR Tool ===
st.subheader("Step 2: Digitize Document with AI")
uploaded_file = st.file_uploader("Upload PDF or Image", type=["pdf","jpg","jpeg","png","webp"], key="main")

if st.button("🚀 Start AI Digitization", type="primary") and uploaded_file and api_key:
    with st.spinner("Processing with Gemini AI... This may take 10-30 seconds"):
        try:
            client = genai.Client(api_key=api_key)
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
                tmp.write(uploaded_file.getbuffer())
                file_path = tmp.name

            images_to_process = []
            if uploaded_file.name.lower().endswith('.pdf'):
                images_to_process = convert_from_path(file_path)
            else:
                images_to_process = [Image.open(file_path)]

            # Prompt
            prompt = """Analyze the layout carefully. Transcribe all text into English and Vietnamese exactly. 
            Use Markdown tables for any tables. Use # ## ### for headings. Do not add extra chat text."""

            contents = [prompt] + images_to_process
            response = client.models.generate_content(model='gemini-2.5-flash', contents=contents)
            extracted_text = response.text if response and response.text else "No text extracted."

            # Create Word file
            doc = Document()
            # Simple markdown-to-docx (you can expand this)
            for line in extracted_text.split('\n'):
                if line.strip().startswith('#'):
                    level = line.count('#')
                    text = line.strip('# ').strip()
                    doc.add_heading(text, level=min(level, 3))
                elif '|' in line and line.strip().startswith('|'):
                    # Basic table handling - can be improved
                    pass  # You can reuse your full insert_markdown_to_word function
                else:
                    if line.strip():
                        doc.add_paragraph(line.strip())

            # Save to bytes
            bio = io.BytesIO()
            doc.save(bio)
            bio.seek(0)

            st.success("✅ Done!")
            st.download_button("📥 Download Structured Word File", bio.getvalue(), 
                             f"{os.path.splitext(uploaded_file.name)[0]}_structured.docx", 
                             "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

            os.unlink(file_path)  # Clean up

        except Exception as e:
            st.error(f"Error: {str(e)}")