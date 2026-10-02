"""Streamlit Web UI for docconv: upload, options, preview, and download."""

from __future__ import annotations

import io
import shutil
import tempfile
import zipfile
from pathlib import Path
import traceback

import streamlit as st

from docconv.config import AppConfig
from docconv.pipeline import ConversionPipeline
from docconv.registry import list_supported_extensions

st.set_page_config(
    page_title="docconv — Modern Document Converter",
    page_icon=":material/auto_awesome:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern UI
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Main container max-width */
    .block-container {
        max-width: 1100px;
        padding-top: 3rem;
        padding-bottom: 3rem;
    }

    /* Header typography */
    h1 {
        font-weight: 800;
        letter-spacing: -0.5px;
        color: #111827;
    }
    .subtitle {
        font-size: 1.15rem;
        color: #4B5563;
        margin-bottom: 2.5rem;
        line-height: 1.6;
    }

    /* Hide default header/footer for app feel */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}

    /* Modern Card UI for File Uploader */
    [data-testid="stFileUploadDropzone"] {
        border: 2px dashed #CBD5E1 !important;
        border-radius: 16px !important;
        background-color: #F8FAFC !important;
        padding: 2rem !important;
        transition: all 0.2s ease;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        border-color: #3B82F6 !important;
        background-color: #EFF6FF !important;
    }

    /* Modern Buttons */
    .stButton>button {
        border-radius: 12px;
        font-weight: 600;
        padding: 0.5rem 1rem;
        border: none;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: all 0.2s ease;
    }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #3B82F6, #2563EB);
        color: white;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    
    /* Download Buttons */
    .stDownloadButton>button {
        border-radius: 12px;
        font-weight: 600;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        transition: all 0.2s ease;
    }
    .stDownloadButton>button:hover {
        border-color: #3B82F6;
        color: #3B82F6;
        transform: translateY(-1px);
    }

    /* Expanders (Results) */
    .streamlit-expanderHeader {
        border-radius: 12px;
        font-weight: 600;
        font-size: 1.05rem;
        background-color: white;
        border: 1px solid #E2E8F0;
        padding: 1rem;
    }
    [data-testid="stExpander"] {
        background-color: white;
        border-radius: 12px;
        box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);
        margin-bottom: 1rem;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

def cleanup_temp_dirs():
    """Hapus direktori sementara (temp) dari proses konversi sebelumnya agar tidak memenuhi disk."""
    if "temp_in_dir" in st.session_state:
        d = st.session_state["temp_in_dir"]
        if isinstance(d, Path) and d.exists():
            shutil.rmtree(d, ignore_errors=True)
    if "temp_out_dir" in st.session_state:
        d = st.session_state["temp_out_dir"]
        if isinstance(d, Path) and d.exists():
            shutil.rmtree(d, ignore_errors=True)

# --- Header Section ---
col1, col2 = st.columns([3, 1])
with col1:
    st.title(":material/auto_awesome: docconv")
    st.markdown("<div class='subtitle'>Ubah dokumen (PDF, Word, Excel, PPT, Gambar) menjadi teks Markdown yang bersih dan terstruktur secara instan.</div>", unsafe_allow_html=True)
with col2:
    st.info(":material/lightbulb: **Tip:** Gunakan sidebar di kiri untuk mengubah pengaturan konversi dan OCR sebelum mengunggah file.")

# --- Sidebar Configuration ---
with st.sidebar:
    st.title(":material/settings: Pengaturan")
    
    st.subheader(":material/tune: Umum", divider="gray")
    pdf_engine = st.selectbox(
        "PDF Engine", 
        options=["pymupdf4llm", "docling"], 
        index=0,
        help="Pilih mesin untuk memproses PDF."
    )
    extract_images = st.toggle("Ekstrak Gambar", value=True, help="Simpan gambar yang ada di dalam dokumen ke dalam folder assets.")

    st.subheader(":material/document_scanner: OCR & Gambar", divider="gray")
    ocr_enabled = st.toggle("Aktifkan OCR", value=True, help="Ekstrak teks dari halaman hasil scan dan gambar.")
    ocr_lang = st.text_input("Bahasa OCR", value="ind+eng", help="Kode bahasa untuk Tesseract (contoh: ind+eng).")
    
    st.subheader(":material/cleaning_services: Pembersihan", divider="gray")
    strip_hf = st.checkbox("Hapus Header/Footer", value=True, help="Hapus header dan footer yang berulang di setiap halaman.")
    dehyphenate_flag = st.checkbox("Gabungkan Kata Berpotong", value=True, help="Gabungkan kata yang terpotong oleh tanda hubung di akhir baris.")

    st.markdown("---")
    exts = list_supported_extensions()
    st.caption(f"**Format didukung:** {', '.join(exts)}")


# --- Main Content ---
st.markdown("### :material/upload_file: Unggah Dokumen")
uploaded_files = st.file_uploader(
    "Tarik dan lepas (drag & drop) file Anda di sini",
    type=[e.lstrip(".") for e in exts],
    accept_multiple_files=True,
    help="Anda bisa mengunggah beberapa file sekaligus untuk diproses secara massal (batch)."
)

# Auto clear results if all files are removed
if not uploaded_files and "results" in st.session_state:
    del st.session_state["results"]
    cleanup_temp_dirs()

if uploaded_files:
    col_btn, _ = st.columns([2, 8])
    with col_btn:
        start_conversion = st.button(":material/rocket_launch: Mulai Konversi", type="primary", use_container_width=True)
    
    if start_conversion:
        st.markdown("---")
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Clean up old dirs before making new ones
        cleanup_temp_dirs()

        # Temporary working directories
        temp_input_dir = Path(tempfile.mkdtemp(prefix="docconv_in_"))
        temp_output_dir = Path(tempfile.mkdtemp(prefix="docconv_out_"))
        
        # Save to session state for later cleanup
        st.session_state["temp_in_dir"] = temp_input_dir
        st.session_state["temp_out_dir"] = temp_output_dir

        try:
            # Configure pipeline
            cfg = AppConfig()
            cfg.ocr.enabled = ocr_enabled
            cfg.ocr.lang = ocr_lang
            cfg.images.extract = extract_images
            cfg.pdf.engine = pdf_engine
            cfg.cleaning.strip_headers_footers = strip_hf
            cfg.cleaning.dehyphenate = dehyphenate_flag
            cfg.output_dir = temp_output_dir

            pipeline = ConversionPipeline(cfg)

            saved_files = []
            for uf in uploaded_files:
                target_path = temp_input_dir / uf.name
                target_path.write_bytes(uf.getbuffer())
                saved_files.append(target_path)

            converted_results = []
            total = len(saved_files)

            with st.spinner("Memproses dokumen..."):
                for idx, file_path in enumerate(saved_files):
                    status_text.info(f":material/sync: Memproses **{file_path.name}** ({idx + 1}/{total})...")
                    res = pipeline.convert_file(file_path)
                    converted_results.append(res)
                    progress_bar.progress((idx + 1) / total)

            status_text.success(":material/check_circle: Semua dokumen berhasil diproses!")
            st.session_state["results"] = converted_results
            st.session_state["out_dir"] = temp_output_dir
            
        except Exception as e:
            status_text.error(f":material/error: Terjadi kesalahan sistem: {str(e)}")
            st.error(f"```python\n{traceback.format_exc()}\n```")

# --- Display Results ---
if "results" in st.session_state:
    results = st.session_state["results"]
    out_dir: Path = st.session_state.get("out_dir")

    st.markdown("---")
    col_res_header, col_zip = st.columns([3, 1])
    with col_res_header:
        st.subheader(":material/list_alt: Hasil Konversi")
    
    # Zip download for all outputs including assets (if out_dir exists)
    if out_dir and out_dir.exists():
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in out_dir.rglob("*"):
                if p.is_file():
                    zf.write(p, arcname=p.relative_to(out_dir))

        with col_zip:
            st.download_button(
                label=":material/download: Unduh Semua (.zip)",
                data=zip_buffer.getvalue(),
                file_name="docconv_converted.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True
            )

    for item in results:
        icon = ":material/check_circle:" if item.success else ":material/cancel:"
        
        with st.expander(f"{icon} {item.source_path.name}", expanded=item.success):
            if item.success and item.output_path and item.output_path.exists():
                md_text = item.output_path.read_text(encoding="utf-8", errors="replace")

                tab_preview, tab_raw = st.tabs([":material/visibility: Tampilan (Rendered)", ":material/code: Kode Markdown (Raw)"])
                with tab_preview:
                    st.markdown(md_text, unsafe_allow_html=True)
                with tab_raw:
                    st.code(md_text, language="markdown")

                st.markdown("<br>", unsafe_allow_html=True)
                # Single file download
                st.download_button(
                    label=f":material/download: Unduh {item.output_path.name}",
                    data=md_text.encode("utf-8"),
                    file_name=item.output_path.name,
                    mime="text/markdown",
                    key=f"dl_{item.output_path.name}",
                )
            else:
                st.error(f"Gagal memproses dokumen.\n\n**Detail Error:**\n{item.error}", icon="🚨")
