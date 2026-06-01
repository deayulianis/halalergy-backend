# 1. Gunakan base image Python yang ringan
FROM python:3.10-slim

# 2. Instal dependencies sistem
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-ind \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3. Set folder kerja
WORKDIR /app

# 4. Copy requirements
COPY requirements.txt .

# 5. Instal library Python
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy kode aplikasi
COPY . .

# 7. Port Render
EXPOSE 10000

# 8. Jalankan aplikasi
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]