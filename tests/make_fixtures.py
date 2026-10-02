"""Generate test document fixtures programmatically."""

from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DATA_DIR = Path(__file__).parent / "data"


def make_text_fixtures() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Plain text
    txt_path = DATA_DIR / "sample.txt"
    txt_path.write_text(
        "Catatan Rapat Strategi 2026\n\n"
        "1. Pendahuluan rencana transformasi digital.\n"
        "2. Implementasi pipeline AI lokal dan otomatisasi dokumen.\n",
        encoding="utf-8",
    )

    # 2. JSON
    json_path = DATA_DIR / "sample.json"
    json_path.write_text(
        json.dumps(
            {
                "project": "docconv",
                "version": "0.1.0",
                "features": ["local", "offline-first", "multi-format"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # 3. CSV
    csv_path = DATA_DIR / "sample.csv"
    csv_path.write_text(
        "Nama,Departemen,Gaji\n"
        "Andi,Engineering,15000000\n"
        "Budi,Product,14000000\n"
        "Citra,Design,13000000\n",
        encoding="utf-8",
    )

    # 4. HTML
    html_path = DATA_DIR / "sample.html"
    html_path.write_text(
        """<!DOCTYPE html>
<html>
<head>
    <title>Panduan Pengguna docconv</title>
    <meta name="author" content="Tim Developer">
</head>
<body>
    <h1>Pengantar docconv</h1>
    <p>docconv adalah alat konversi dokumen lokal ke <strong>Markdown</strong>.</p>
    <h2>Fitur Utama</h2>
    <ul>
        <li>Dukungan berbagai format dokumen</li>
        <li>Tabel rapi dan <a href="https://example.com">tautan aktif</a></li>
    </ul>
    <h2>Tabel Kompleks</h2>
    <table border="1">
        <tr>
            <th rowspan="2">Kategori</th>
            <th colspan="2">Detail</th>
        </tr>
        <tr>
            <th>Format</th>
            <th>Status</th>
        </tr>
        <tr>
            <td>Dokumen</td>
            <td>DOCX, PDF</td>
            <td>Didukung</td>
        </tr>
    </table>
</body>
</html>""",
        encoding="utf-8",
    )


def make_docx_fixture() -> None:
    try:
        import docx
        from docx import Document

        doc = Document()
        doc.core_properties.title = "Dokumen Uji Word"
        doc.core_properties.author = "Penulis Uji"

        doc.add_heading("Judul Utama DOCX", level=1)
        p = doc.add_paragraph("Ini adalah paragraf dengan kata ")
        p.add_run("tebal").bold = True
        p.add_run(" dan ")
        p.add_run("miring").italic = True
        p.add_run(".")

        doc.add_heading("Sub Bab Tabel", level=2)
        tbl = doc.add_table(rows=3, cols=2)
        tbl.cell(0, 0).text = "Header 1"
        tbl.cell(0, 1).text = "Header 2"
        tbl.cell(1, 0).text = "Baris 1 Kolom 1"
        tbl.cell(1, 1).text = "Baris 1 Kolom 2"
        tbl.cell(2, 0).text = "Baris 2 Kolom 1"
        tbl.cell(2, 1).text = "Baris 2 Kolom 2"

        doc.save(DATA_DIR / "sample.docx")
    except Exception as exc:
        print(f"Skipping DOCX fixture creation: {exc}")


def make_pptx_fixture() -> None:
    try:
        from pptx import Presentation
        from pptx.util import Inches

        prs = Presentation()
        prs.core_properties.title = "Presentasi Uji"

        # Slide 1: Title
        slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(slide_layout)
        title = slide.shapes.title
        subtitle = slide.placeholders[1]
        title.text = "Selamat Datang di docconv"
        subtitle.text = "Presentasi otomatisasi dokumen"

        # Slide 2: Bullets & Table
        bullet_layout = prs.slide_layouts[1]
        slide2 = prs.slides.add_slide(bullet_layout)
        slide2.shapes.title.text = "Keunggulan Sistem"
        tf = slide2.shapes.placeholders[1].text_frame
        tf.text = "Cepat dan ringan"
        p = tf.add_paragraph()
        p.text = "100% lokal dan offline"

        prs.save(DATA_DIR / "sample.pptx")
    except Exception as exc:
        print(f"Skipping PPTX fixture creation: {exc}")


def make_xlsx_fixture() -> None:
    try:
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Ringkasan"
        ws["A1"] = "Laporan Penjualan"
        ws.merge_cells("A1:B1")

        ws["A2"] = "Produk"
        ws["B2"] = "Jumlah"
        ws["A3"] = "Laptop"
        ws["B3"] = 10
        ws["A4"] = "Mouse"
        ws["B4"] = 50

        wb.save(DATA_DIR / "sample.xlsx")
    except Exception as exc:
        print(f"Skipping XLSX fixture creation: {exc}")


def make_pdf_fixture() -> None:
    try:
        import pymupdf as fitz

        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 72), "Dokumen Uji PDF", fontsize=18)
        page.insert_text((50, 110), "Ini adalah isi dokumen PDF untuk pengujian konversi teks ke Markdown.", fontsize=11)
        page.insert_text((50, 140), "Tabel Sederhana:", fontsize=13)
        page.insert_text((50, 160), "Kolom A   Kolom B\nData 1    Data 2", fontsize=10)
        doc.save(DATA_DIR / "sample.pdf")
        doc.close()
    except Exception as exc:
        print(f"Skipping PDF fixture creation: {exc}")


def make_image_fixture() -> None:
    try:
        img = Image.new("RGB", (400, 150), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 50), "Hello docconv OCR Test", fill=(0, 0, 0))
        img.save(DATA_DIR / "sample.png")
    except Exception as exc:
        print(f"Skipping Image fixture creation: {exc}")


def generate_all_fixtures() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    make_text_fixtures()
    make_docx_fixture()
    make_pptx_fixture()
    make_xlsx_fixture()
    make_pdf_fixture()
    make_image_fixture()
    print(f"All fixtures generated in {DATA_DIR}")


if __name__ == "__main__":
    generate_all_fixtures()
