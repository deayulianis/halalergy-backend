from flask import Flask, request, jsonify
import cv2
import json
import pytesseract
import pandas as pd
import re
import os
from rapidfuzz import process, fuzz
import numpy as np

# Logika deteksi OS
if os.name == 'nt':  # Kalau jalan di Windows (Laptop Kamu)
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
else:  # Kalau jalan di Linux (Render Docker)
    pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

app = Flask(__name__)

# =====================================================
# LOAD DATASET
# =====================================================
URL_DATASET = "https://raw.githubusercontent.com/deayulianis/coba-skripsi/refs/heads/main/komposisi.json"

try:
    df = pd.read_json(URL_DATASET)
    df = df.rename(columns={0: "ingredients_text"})
    print("Dataset berhasil dimuat.")
except Exception as e:
    print(f"Gagal memuat dataset online: {e}")
    df = pd.DataFrame(columns=["ingredients_text"])

# =====================================================
# CLEAN TEXT
# =====================================================
def clean_text(text):
    if pd.isna(text):
        return ""

    text = text.lower()

    garbage_phrases = [
        r'cetak tebal.*',
        r'komposise',
        r'that also process',
        r'mengandung alergen.*',
        r'tanpa bahan pengawet.*',
        r'tanpa penguat rasa.*',
        r'tanpa pemanis buatan.*',
        r'komposisi',
        r'komposis',
        r'mungkin mengandung.*',
        r'ingredients*'
    ]

    for phrase in garbage_phrases:
        text = re.sub(phrase, '', text)

    # hapus persentase
    text = re.sub(r'\d+(\.\d+)?\s?%?', '', text)

    text = text.replace('(', ',').replace(')', ',')
    text = text.replace('.', ',')

    text = re.sub(r'[^a-z0-9,\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\s*,\s*', ',', text)

    return text

# =====================================================
# ALLERGEN DICTIONARY
# =====================================================
allergen_dict = {
    "Susu": [
        "milk", "whole milk", "skim milk", "milk powder", "milk solids", "milk powder", "milk fat", "buttermilk", "milk protein", "milk concentrate", "skimmed milk",
        "whey", "whey powder", "whey protein", "casein", "caseinate", "lactose", "butter", "butterfat", "butter oil",
        "cream", "cheese", "yogurt", "sodium caseinate", "calcium caseinate", "ceddar", "mozarella", "yogurt", "kefir",
        "susu", "lemak susu", "mentega", "keju", "susu bubuk", "lemak susu", "krim", "yoghurt",
    ],

    "Telur": [
        "egg", "egg powder", "egg white", "egg yolk", "ovomucoid", "ovotransferrin", "ovovitellin",
        "albumin", "lysozyme", "ovalbumin", "ovoglobulin", "egg lecithin", "egg solids",
        "telur", "putih telur", "kuning telur"
    ],

    "Ikan": [
        "fish", "fish oil", "fish extract", "fish protein", "surimi",
        "fish sauce", "fish gelatin",  "fish sauce", "isinglass",
        "anchovy", "tuna", "salmon",  "sardine",  "cod", "pollock", "haddock",
        "ikan", "minyak ikan", "ekstrak ikan"
    ],

    "Krustasea & Moluska": [
        "shrimp", "prawn", "crab", "lobster",  "crayfish", "krill", "shellfish",
        "squid", "octopus", "clam", "oyster",  "mussel", "scallop",
        "udang", "kepiting", "cumi", "kerang", "gurita", "lobster"
    ],

    "Kacang Tanah": [
        "peanut", "groundnut", "peanut butter",  "peanut oil",  "peanut flour", "peanut paste", "peanut protein",
        "kacang tanah", "selai kacang", "minyak kacang"
    ],

    "Kacang Pohon": [
        "almond", "walnut", "cashew",
        "hazelnut", "pistachio", "brazil nut", "pine nut", "tree nut",
        "pecan", "macadamia", "kacang almond", "kacang mete"
    ],

    "Gandum & Gluten": [
        "wheat", "wheat flour", "gluten", "vital gluten"
        "barley", "rye", "oats", "oat", "spelt", "oat",
        "malt", "breadcrumb", "triticale", "semolina", "breadcrumb", "bread crumbs",
        "gandum", "tepung gandum", "malt extract", "malt flavor",
        "tepung terigu", "durum wheat", "gandum", "tepung gandum"
    ],

    "Kedelai": [
        "soy", "soya", "soybean", "soy isolate", "soy concentrate",
        "soy protein", "soy lecithin", "textured vegetable protein",
        "tvp", "soy sauce", "miso", "natto", "soy milk", "tofu", "tempe", "kedelai", "susu kedelai"
    ],

    "Wijen": [
        "sesame", "sesame seed", "sesame oil", "tahini", "wijen", "minyak wijen"
    ],

    "Sulfit": [
        "sulfite", "sulphite", "sodium metabisulfite", "sulfur dioxide", "sodium bisulfite",
        "sodium sulfite", "sulfit", "potassium metabisulfite",
        "e220", "e221", "e223", "e224", "e226", "e227", "e228"
    ]
}

# =====================================================
# NON HALAL & CRITICAL
# =====================================================
NON_HALAL = [
    "pork", "pig", "swine", "lard", "bacon", "ham", "prosciutto", "beer extract", "wine extract",
    "salami", "porcine", "alcohol", "ethanol", "wine", "beer", "rum", "ethyl alcohol", "cooking wine", "rum extract",
    "whisky", "vodka", "brandy", "liqueur", "blood", "mirin", "sake", "blood plasma", "hemoglobin",
    "pork fat", "wine extract", "porcine gelatin", "porcine collagen", "porcine enzyme", "dog meat", "carnivore meat"
]

CRITICAL_HALAL = [
    "gelatin", "enzyme", "rennet", "pepsin", "lipase", "protease", "food gelatin", "hydrolyzed collagen",
    "maltodextrin", "mono diglyceride", "e471", "e472", "emulsifier", "e471", "e472", "e473", "e477",
    "stabilizer", "animal fat", "shortening", "collagen", "flavor",  "mono and diglycerides",
    "flavour", "glycerin", "glycerol", "stearic acid", "magnesium stearate",  "emulsifier", "marshmallow",
    "acidity regulator", "natural flavor", "synthetic flavour", "perisa sintetik", "artificial flavor", "pengatur keasaman", "maltodekstrin", "processing aid"
]

# =====================================================
# MASTER INGREDIENTS
# =====================================================
MASTER_INGREDIENTS = []

if not df.empty:
    for t in df['ingredients_text']:
        cleaned = clean_text(t)
        ingredients = [i.strip() for i in cleaned.split(',') if i.strip()]
        MASTER_INGREDIENTS.extend(ingredients)

for values in allergen_dict.values():
    MASTER_INGREDIENTS.extend(values)

MASTER_INGREDIENTS.extend(NON_HALAL)
MASTER_INGREDIENTS.extend(CRITICAL_HALAL)
MASTER_INGREDIENTS = list(set(MASTER_INGREDIENTS))

# =====================================================
# NORMALIZATION
# =====================================================
def normalize_ingredient(ingredient):
    numbers = re.findall(r'\d+\.?\d*%?', ingredient)
    clean_name = re.sub(r'\d+\.?\d*%?', '', ingredient).strip()

    if clean_name in MASTER_INGREDIENTS:
        return ingredient

    match = process.extractOne(
        clean_name,
        MASTER_INGREDIENTS,
        scorer=fuzz.token_sort_ratio
    )

    if match and match[1] >= 80:
        result = match[0]
        if numbers:
            return f"{result} {' '.join(numbers)}"
        return result

    return ingredient

# =====================================================
# DETECT ALLERGEN
# =====================================================
def detect_allergen(ingredients):
    detected = set()
    for ing in ingredients:
        ing_lower = ing.lower()
        words = re.findall(r'\b\w+\b', ing_lower)

        for allergen, keywords in allergen_dict.items():
            for keyword in keywords:
                keyword = keyword.lower()
                if ' ' in keyword:
                    if keyword in ing_lower:
                        detected.add(allergen)
                else:
                    if keyword in words:
                        detected.add(allergen)
    return list(detected)

# =====================================================
# DETECT HALAL STATUS
# =====================================================
def detect_halal_status(ingredients):
    haram_found = set()
    critical_found = set()

    for ing in ingredients:
        ing_lower = ing.lower()
        # Ambil daftar kata individual untuk pengecekan kata tunggal
        words = re.findall(r'\b\w+\b', ing_lower)

        # 1. Cek Bahan Haram
        for haram in NON_HALAL:
            haram = haram.lower()
            if ' ' in haram: # Jika keyword lebih dari 1 kata (contoh: 'pork fat')
                if haram in ing_lower:
                    haram_found.add(ing)
            else: # Jika keyword hanya 1 kata (contoh: 'pork')
                if haram in words:
                    haram_found.add(ing)

        # 2. Cek Bahan Titik Kritis
        for critical in CRITICAL_HALAL:
            critical = critical.lower()
            if ' ' in critical:
                if critical in ing_lower:
                    critical_found.add(ing)
            else:
                if critical in words:
                    critical_found.add(ing)

    # --- FORMAT OUTPUT UNTUK TAMPIL DI FLUTTER ---
    if haram_found:
        # Menampilkan: NON-HALAL (Terdeteksi: lard, bacon)
        return f"NON-HALAL (Terdeteksi: {', '.join(haram_found)})", list(critical_found), list(haram_found)
    
    elif critical_found:
        # Menampilkan: BUTUH PENGECEKAN (Bahan Kritis: gelatin, emulsifier)
        return f"BUTUH PENGECEKAN ({', '.join(critical_found)})", list(critical_found), []
    
    return "HALAL", [], []

# =====================================================
# OCR ACCURACY
# =====================================================
def calculate_ocr_accuracy(thresh):
    ocr_data = pytesseract.image_to_data(
        thresh,
        config='--oem 3 --psm 6',
        lang='ind+eng',
        output_type=pytesseract.Output.DICT
    )

    confidences = []
    for conf in ocr_data['conf']:
        try:
            conf = float(conf)
            if conf > 0:
                confidences.append(conf)
        except:
            pass

    if len(confidences) == 0:
        return 0

    return round(sum(confidences) / len(confidences), 2)

# =====================================================
# API ENDPOINT
# =====================================================
import numpy as np # Tambahkan ini di bagian paling atas app.py

@app.route('/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files['image']
    
    # Ambil data alergi dari Flutter
    user_preferences = request.form.get('allergies', '[]')
    try:
        user_allergies_list = json.loads(user_preferences) 
    except:
        user_allergies_list = []
    
    try:
        # --- PERBAIKAN: Baca gambar langsung dari memori (Tanpa save file) ---
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({"error": "Gagal mendekode gambar. Pastikan formatnya benar."}), 400

        # 1. IMAGE PROCESSING & OCR
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoise = cv2.fastNlMeansDenoising(gray, h=10)
        _, thresh = cv2.threshold(denoise, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Gunakan lang='ind+eng' hanya jika tesseract-ocr-ind sudah terpasang di Render
        raw_text = pytesseract.image_to_string(thresh, config='--oem 3 --psm 6', lang='ind+eng')

        # 2. HITUNG AKURASI
        ocr_accuracy = calculate_ocr_accuracy(thresh)
        ocr_quality = "Tinggi" if ocr_accuracy >= 80 else "Sedang" if ocr_accuracy >= 60 else "Rendah"

        # 3. CLEANING & NORMALISASI
        cleaned = clean_text(raw_text)
        ingredients = [i.strip() for i in cleaned.split(',') if i.strip()]
        normalized = [normalize_ingredient(i) for i in ingredients]

        # 4. DETEKSI
        allergens = detect_allergen(normalized) 
        status_halal, critical_list, haram_list = detect_halal_status(normalized)

        # 5. LOGIKA PERSONALISASI
        personal_allergen_alert = [a for a in allergens if a in user_allergies_list]
        is_personal_allergy = len(personal_allergen_alert) > 0

        is_low_quality = len(cleaned.split(',')) < 3
        is_haram = "NON-HALAL" in status_halal
        is_critical = "BUTUH PENGECEKAN" in status_halal

        final_status = ""
        final_message = ""

        if is_low_quality:
            final_status = "SCAN RENDAH"
            final_message = "Kualitas teks kurang jelas. Silakan scan ulang dengan cahaya yang lebih terang."
        elif is_haram:
            final_status = "BAHAYA: NON-HALAL"
            final_message = f"Ditemukan bahan non-halal: {', '.join(haram_list)}. Hindari konsumsi."
        elif is_personal_allergy:
            final_status = "PERINGATAN: ALERGI ANDA TERDETEKSI"
            final_message = f"Hati-hati! Produk ini mengandung {', '.join(personal_allergen_alert)} yang terdaftar di profil alergi Anda."
        elif is_critical:
            final_status = "PERLU VERIFIKASI"
            final_message = f"Mengandung bahan titik kritis ({', '.join(critical_list)}). Cek label Halal resmi pada kemasan."
        elif len(allergens) > 0:
            final_status = "AMAN (DENGAN CATATAN)"
            final_message = f"Produk terindikasi Halal, namun mengandung alergen umum: {', '.join(allergens)}."
        else:
            final_status = "AMAN"
            final_message = "Tidak ditemukan bahan berbahaya atau alergi. Aman untuk dikonsumsi."

        return jsonify({
            "ocr_text": cleaned,
            "ingredients": ingredients,
            "allergens": allergens,
            "user_specific_allergies": personal_allergen_alert,
            "halal_status": status_halal,
            "ocr_accuracy": ocr_accuracy,
            "ocr_quality": ocr_quality,
            "conclusion": {
                "status": final_status,
                "message": final_message
            }
        })

    except Exception as e:
        # Agar error detail muncul di Logs Render
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)