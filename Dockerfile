# 1. Gunakan base image Python yang ringan
FROM python:3.10-slim

# 2. Instal dependencies sistem (Tesseract & OpenCV requirements)
# Ini langkah yang selalu gagal di Render biasa, tapi di Docker PASTI JALAN
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-ind \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3. Set folder kerja di dalam container
WORKDIR /app

# 4. Copy file requirements dulu agar build lebih cepat (caching)
COPY requirements.txt .

# 5. Instal library Python
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy seluruh sisa kode aplikasi kamu ke dalam container
COPY . .

# 7. Port yang digunakan Render
EXPOSE 10000

# 8. Perintah untuk menjalankan aplikasi
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]