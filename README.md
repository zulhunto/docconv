# docconv 📄➡️📝

**docconv** adalah konverter dokumen ke Markdown lokal dan *offline-first*. Dirancang untuk memproses dokumen kantor, presentasi, lembar kerja, halaman web, buku elektronik, dan hasil scan menjadi Markdown bersih dengan struktur rapi, metadata YAML front matter, serta manajemen aset gambar.

---

## 🚀 Fitur Utama

- **100% Lokal & Offline:** Dokumen Anda tidak pernah dikirim ke server pihak ketiga.
- **Ekstensi Lengkap:**
  - 📄 **PDF:** `pymupdf4llm` (bawaan) dan opsi `docling` untuk dokumen kompleks.
  - 📝 **Word:** `.docx` dengan dukungan heading, format tebal/miring, tabel (termasuk deteksi merged cell), gambar, dan catatan kaki (*footnotes*).
  - 📊 **PowerPoint:** `.pptx` (slide, judul, bullet point, tabel, gambar, catatan pembicara / *speaker notes*).
  - 📈 **Excel & CSV:** `.xlsx`, `.xlsm`, `.csv`, `.tsv` dengan penanganan *merged cells* otomatis fallback ke HTML table.
  - 🌐 **HTML:** Pembersihan skrip/gaya, parsing tabel terstruktur, dan markdownify.
  - 📚 **EPUB:** Konversi bab demi bab dan ekstraksi gambar sampul/isi.
  - 🖼️ **Gambar & Scan:** OCR dengan `pytesseract` dan `OCRmyPDF` (Bahasa Indonesia `ind` + Inggris `eng`).
  - 📜 **Teks & JSON:** `.txt`, `.json`, `.log`.
- **Pembersihan Otomatis:**
  - Menghilangkan *header* dan *footer* berulang serta nomor halaman pada PDF.
  - *Dehyphenation:* menyambung kata yang terpotong strip di ujung baris.
  - Perapian spasi dan baris kosong berlebih (blok kode tetap aman).
- **Batch Rekursif & Isolasi Error:** Kerusakan pada satu file tidak menghentikan proses konversi dokumen lainnya.
- **CLI & Web UI:** Antarmuka terminal interaktif dengan Typer + Rich, serta Web UI visual berbasis Streamlit.
- **Pengukuran Kualitas (`docconv eval`):** Menghitung retensi struktur (heading, tabel, gambar, tautan, kata) dari dokumen sumber ke Markdown.

---

## 📦 Instalasi

### 1. Prasyarat Sistem

#### Windows
- **Python 3.10+**
- **Tesseract OCR (Opsional untuk fitur OCR):**
  - Unduh installer dari [UB-Mannheim Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki).
  - Tambahkan path instalasi (misalnya `C:\Program Files\Tesseract-OCR`) ke `PATH` sistem Anda.
  - Unduh file bahasa `ind.traineddata` dan letakkan di folder `tessdata`.
- **Ghostscript (Opsional untuk OCRmyPDF):**
  - Unduh dari situs resmi [Ghostscript](https://ghostscript.com/releases/gsdnld.html).

#### Ubuntu / Debian
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-ind ocrmypdf ghostscript
```

### 2. Instalasi Paket docconv

```bash
cd docconv
pip install -e .
```

Untuk menyertakan dependensi pengujian dan ekstra:
```bash
pip install -e .[ocr,dev]
```

---

## 💻 Penggunaan CLI

### Konversi Dokumen Tunggal
```bash
docconv dokumen.pdf -o ./output
```

### Konversi Folder (Batch Rekursif)
```bash
docconv ./kumpulan_dokumen -o ./output --ocr --lang ind+eng --images
```

### Opsi CLI yang Tersedia
- `-o, --output-dir PATH`: Direktori tujuan output Markdown dan folder `assets/`.
- `--ocr / --no-ocr`: Mengaktifkan atau menonaktifkan deteksi dan proses OCR.
- `--lang CODE`: Kode bahasa OCR (default: `ind+eng`).
- `--images / --no-images`: Ekstraksi gambar yang disematkan ke dalam folder `assets/`.
- `--pdf-engine [pymupdf4llm|docling]`: Pilihan mesin konversi PDF.
- `--recursive / --no-recursive`: Menelusuri sub-folder secara rekursif.
- `-c, --config PATH`: Menggunakan file konfigurasi YAML kustom.
- `--log-file PATH`: Lokasi file log konversi (default: `conversion.log`).

### Evaluasi Kualitas Konversi
Bandingkan jumlah heading, tabel, gambar, tautan, dan kata antara dokumen asli dan file Markdown hasil:
```bash
docconv eval dokumen.docx ./output/dokumen.md
```

### Menampilkan Format yang Didukung
```bash
docconv formats
```

---

## 🌐 Menjalankan Web UI (Streamlit)

Jalankan antarmuka grafis drag-and-drop:
```bash
streamlit run src/docconv/webui/app.py
```
Fitur Web UI:
- Drag-and-drop banyak file sekaligus.
- Pratinjau visual Markdown (Rendered & Raw).
- Download langsung file `.md` atau bundel `.zip` (beserta aset gambar).

---

## ⚙️ Konfigurasi (`config.yaml`)

Anda dapat menyesuaikan konfigurasi default melalui `config.yaml`:

```yaml
output_dir: ./out
ocr:
  enabled: true
  lang: ind+eng
  auto_detect: true
  min_chars_per_page: 25
images:
  extract: true
  folder: assets
  min_size_px: 64
pdf:
  engine: pymupdf4llm   # atau: docling
cleaning:
  strip_headers_footers: true
  dehyphenate: true
  max_blank_lines: 1
tables:
  fallback_html_on_merged_cells: true
batch:
  recursive: true
  continue_on_error: true
```

---

## 🧪 Menjalankan Pengujian (Testing)

Jalankan generator fixture dan uji otomatis pytest:
```bash
python tests/make_fixtures.py
pytest
```

---

## 📜 Lisensi
MIT License.
