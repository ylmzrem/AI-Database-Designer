from flask import Flask, render_template, request
import google.generativeai as genai
import io
import csv
import json
import re
import mysql.connector  # <--- YENİ: MySQL kütüphanesi eklendi

app = Flask(__name__)

# ==========================================
# AYARLAR (LÜTFEN KONTROL EDİN)
# ==========================================
# 1. API Anahtarınız
GEMINI_API_KEY = "AIzaSyAksNUS8PcBfIfergQoGGyWO_snYHp3EoY" 

# 2. phpMyAdmin (MySQL) Bağlantı Bilgileri
# XAMPP kullanıyorsanız genelde şifre boştur.
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',      
    'password': '',      # XAMPP/WAMP'ta genelde boştur. Doluysa buraya yazın.
    'database': 'proje_veritabani' 
}

# 3. API Yapılandırması
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # 'flash-lite' bazen hata verebilir, 'gemini-2.5-flash' en kararlı olanıdır.
    model = genai.GenerativeModel('gemini-flash-lite-latest')
except:
    model = None

# ==========================================
# YARDIMCI: GEMINI TEMİZLEYİCİ (DÜZELTİLDİ)
# ==========================================
def clean_gemini_output(text):
    """Yapay zekanın fazladan eklediği ```json vb. işaretleri temizler."""
    if not text: return ""
    text = text.replace("```json", "").replace("```sql", "").replace("```mysql", "").replace("```mermaid", "").replace("```csv", "").replace("```", "")
    # Mermaid diyagramındaki olası açıklama metinlerini temizle
    if "erDiagram" in text:
        idx = text.find("erDiagram")
        text = text[idx:]
    return text.strip()

def ask_gemini(system, user):
    try:
        if not model: return None
        combined = f"{system}\n\nTask:\n{user}"
        response = model.generate_content(combined)
        return clean_gemini_output(response.text)
    except Exception as e:
        print(f"API HATASI: {e}")
        return None

# ==========================================
# YENİ ÖZELLİK: PHPMYADMIN KAYDEDİCİ
# ==========================================
def save_to_mysql(sql_script):
    """Gelen SQL kodunu phpMyAdmin'e kaydeder."""
    status_msg = ""
    conn = None
    try:
        # 1. Bağlan
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()

        # 2. Veritabanını oluştur
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        cursor.execute(f"USE {DB_CONFIG['database']}")
        
        # 3. SQL Komutlarını Çalıştır
        # Kodları ';' işaretinden bölüp tek tek çalıştırıyoruz
        commands = sql_script.split(';')
        
        count = 0
        for command in commands:
            if command.strip():
                try:
                    cursor.execute(command)
                    count += 1
                except Exception as e:
                    print(f"SQL Uyarısı (Satır atlandı): {e}")
        
        conn.commit()
        status_msg = f"✅ BAŞARILI: Tablolar phpMyAdmin'e ({DB_CONFIG['database']}) kaydedildi! ({count} komut çalıştı)"
        print(status_msg)

    except mysql.connector.Error as err:
        status_msg = f"❌ MySQL Hatası: {err}"
        print(status_msg)
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            
    return status_msg

# ==========================================
# 1. GERÇEK VERİ FONKSİYONLARI (PARSE DÜZELTMELİ)
# ==========================================

def get_real_rules(data):
    res = ask_gemini("You are a DB expert. Output ONLY raw CSV data.", 
                     f"Extract business rules from: {data}. Columns: ID, Type, Rule Statement, ER Component, Implementation Tip, Rationale")
    if not res: return get_sim_rules()
    
    rules = []
    try:
        reader = csv.reader(io.StringIO(res), skipinitialspace=True)
        for row in reader:
            if len(row) >= 6 and "ID" not in row[0]:
                rules.append({'id': row[0], 'type': row[1], 'statement': row[2], 'component': row[3], 'tip': row[4], 'rationale': row[5]})
    except: return get_sim_rules()
    return rules

def get_real_tables(data):
    # JSON yapısını garantiye alacak prompt (RESİM 1'DEKİ HATAYI ÇÖZER)
    prompt = f"""
    Create a database schema for {data['domain']}.
    Output ONLY a JSON list. 
    IMPORTANT: Use exactly these keys: "name", "columns". 
    For columns use keys: "name", "type", "constraints".
    Do not use "field" or "attribute", MUST use "name".
    Example:
    [
      {{"name": "Students", "columns": [{{"name": "student_id", "type": "INT", "constraints": "PK"}}] }}
    ]
    """
    res = ask_gemini("You are a SQL Architect. Output ONLY raw JSON.", prompt)
    if not res: return get_sim_tables()

    try:
        # JSON temizliği
        start = res.find('[')
        end = res.rfind(']') + 1
        if start != -1 and end != -1:
            json_str = res[start:end]
            tables = json.loads(json_str)
            
            # Veri Doğrulama ve Düzeltme
            for t in tables:
                for col in t.get('columns', []):
                    # Eğer 'name' anahtarı yoksa, 'field' vb. var mı diye bak ve düzelt
                    if 'name' not in col:
                        for bad_key in ['field', 'column', 'attribute', 'Field', 'Name']:
                            if bad_key in col:
                                col['name'] = col[bad_key]; break
                    # Constraints listeyse string'e çevir
                    if isinstance(col.get('constraints'), list):
                        col['constraints'] = ", ".join(col['constraints'])
            return tables
    except: return get_sim_tables()
    return get_sim_tables()

def get_real_sql(data):
    # MySQL Uyumlu Prompt
    prompt = f"""
    Write a complete MySQL script for '{data['domain']}'.
    Start with 'DROP TABLE IF EXISTS ...;' to prevent errors.
    Include CREATE TABLE statements.
    Include INSERT INTO statements with 3 dummy rows.
    Output ONLY the SQL code.
    """
    return ask_gemini("You are a SQL Expert.", prompt)

def get_real_diagram(data):
    res = ask_gemini("You are a Mermaid.js generator. Output ONLY the code.", 
                     f"Create an ER diagram for {data['domain']}. Start directly with 'erDiagram'. Use ||--o{{ notation.")
    if not res: return get_sim_diagram()
    # "Syntax Error" hatasını önlemek için temizlik
    idx = res.find("erDiagram")
    return res[idx:] if idx != -1 else res

# ==========================================
# YENİ FONKSİYON 1: EKSİK KURALLARI TESPİT ET
# ==========================================
'''
def get_missing_rules(data):
    """Kullanıcının girdiği verilere göre eksik olabilecek iş kurallarını tahmin eder."""
    prompt = f"""
    Analyze the database requirements for domain: '{data['domain']}'.
    Current constraints provided: '{data['constraints']}'.
    
    Identify 3 to 5 CRITICAL business rules or edge cases that the user might have forgotten.
    Focus on data integrity, logical relationships, and constraints.
    
    Output format: Return ONLY a Python list of strings.
    Example: ["Users must confirm email before login", "Product stock cannot be negative", "Order date cannot be in the future"]
    """
    res = ask_gemini("You are a Business Analyst.", prompt)
    if not res: return ["Analiz edilemedi."]
    
    try:
        # Basit bir liste temizliği
        if "[" in res and "]" in res:
            start = res.find('[')
            end = res.rfind(']') + 1
            return eval(res[start:end]) # Güvenli string listesi dönüşümü
        else:
            return [line.strip("- *") for line in res.split('\n') if line.strip()]
    except:
        return ["Eksik kurallar belirlenemedi."]
'''


# ==========================================
# GÜNCELLENMİŞ FONKSİYON: ID BAZLI ANALİZ
# ==========================================
def get_missing_rules(data, current_rules):
    """
    Mevcut kuralları analiz eder:
    1. Zayıf kurallar için (örn: ID 4) iyileştirme önerir.
    2. Eksik kurallar için (ID: NEW) yeni öneri sunar.
    """
    # Mevcut kuralları metne döküyoruz ki yapay zeka okuyabilsin
    if current_rules:
        rules_text = "\n".join([f"ID {r['id']}: {r['statement']}" for r in current_rules])
    else:
        rules_text = "No existing rules."

    prompt = f"""
    Analyze the following existing Business Rules for domain '{data['domain']}':
    {rules_text}
    
    Task:
    1. Identify WEAK, VAGUE or INCORRECT rules in the list above. Suggest a "better version" and reference their ID.
    2. Identify MISSING critical rules that are not in the list. Assign them ID "NEW".
    
    Output format: Return ONLY a Python list of dictionaries.
    Keys: "ref_id" (The ID of existing rule OR "NEW"), "issue" (Short explanation of what is wrong), "recommendation" (The improved or new rule text).
    
    Example:
    [
      {{"ref_id": "2", "issue": "Too vague", "recommendation": "Students can borrow max 5 books per term."}},
      {{"ref_id": "NEW", "issue": "Security missing", "recommendation": "Passwords must be hashed using bcrypt."}}
    ]
    """
    res = ask_gemini("You are a Senior Business Analyst.", prompt)
    if not res: return []
    
    try:
        start = res.find('[')
        end = res.rfind(']') + 1
        return eval(res[start:end])
    except:
        return []

# ==========================================
# YENİ FONKSİYON 2: NORMALİZASYON ADIMLARI
# ==========================================
def get_normalization_steps(data):
    """0NF'den 3NF'ye geçiş sürecini açıklar."""
    prompt = f"""
    Explain the normalization process for '{data['domain']}' specifically.
    
    Provide a brief breakdown:
    1. **Unnormalized Form (UNF):** Give an example of raw data mixing attributes.
    2. **1NF (First Normal Form):** Explain how to make it atomic / remove repeating groups.
    3. **2NF (Second Normal Form):** Explain removing partial dependencies.
    4. **3NF (Third Normal Form):** Explain removing transitive dependencies.
    
    Output format: HTML text using <h4>, <p>, and <ul> tags. Do NOT use ```html blocks. Just raw HTML code.
    """
    return ask_gemini("You are a Database Professor.", prompt)




# ==========================================
# YENİ FONKSİYON 3: DETAYLI MODEL ANALİZİ (B1 & A3 SORULARI İÇİN)
# ==========================================
def get_model_analysis(data):
    """
    Word dosyasındaki B1 (Merkezi Varlık) ve A3 (Pahalı Kural) sorularına cevap verir.
    """
    prompt = f"""
    Analyze the database model for '{data['domain']}' and provided constraints.
    Provide a structed analysis answering these specific questions from a database exam:
    
    1. **Central Entity:** Which entity is structurally most central? (Explain based on relationship degree/FKs).
    2. **Most Expensive Rule:** Which business rule is computationally most expensive to enforce? (Explain in terms of JOINs/Aggregations).
    3. **Trade-off:** Give one example where Denormalization might improve performance for this specific domain.

    Output format: Return ONLY a Python dictionary.
    Keys: "central_entity", "expensive_rule", "denormalization_tip"
    """
    res = ask_gemini("You are a Database Architect.", prompt)
    if not res: return None
    
    try:
        # JSON/Dict temizliği
        start = res.find('{')
        end = res.rfind('}') + 1
        return eval(res[start:end])
    except:
        return None

# ==========================================
# YENİ FONKSİYON 4: RAPORLAMA SORGULARI (E6 SORUSU İÇİN)
# ==========================================
def get_reporting_queries(data):
    """
    Kullanıcının raporlama isteklerine göre SELECT sorguları üretir.
    """
    prompt = f"""
    Based on the reporting requirement: "{data['reporting']}" for domain "{data['domain']}".
    
    Generate 3 complex SQL SELECT queries that would be needed for these reports.
    Include JOINs, GROUP BYs, and HAVING clauses where appropriate.
    
    Output format: Return ONLY a Python list of dictionaries.
    Keys: "title", "sql", "explanation"
    Example: [{{ "title": "Monthly Sales", "sql": "SELECT...", "explanation": "Aggregates sales by month..." }}]
    """
    res = ask_gemini("You are a SQL Data Analyst.", prompt)
    if not res: return []
    
    try:
        start = res.find('[')
        end = res.rfind(']') + 1
        return eval(res[start:end])
    except:
        return []


# ==========================================
# 2. SİMÜLASYON (YEDEK)
# ==========================================
def get_sim_rules(): return [{'id': 'ERR', 'type': '-', 'statement': 'API Error', 'component': '-', 'tip': '-', 'rationale': '-'}]
def get_sim_tables(): return []
def get_sim_sql(): return "-- API Error"
def get_sim_diagram(): return "erDiagram\n ERROR"


# ==========================================
# ANA ROUTE
# ==========================================

@app.route('/', methods=['GET', 'POST'])
def index():
    # Değişkenleri başlangıçta boş tanımla
    rules, tables, sql, diagram, db_status = None, None, None, None, None
    missing_rules, normalization_html = None, None # <--- YENİ DEĞİŞKENLER

    analysis_data = None
    reporting_queries = None
    
    if request.method == 'POST':
        data = {k: request.form.get(k) for k in ['domain', 'primary_entity', 'constraints', 'advanced_features', 'security', 'reporting', 'common_tasks']}
        
        print("1. İş Kuralları Çıkarılıyor...")
        rules = get_real_rules(data)

        print("2. Eksik Kurallar Aranıyor... (YENİ)")
        missing_rules = get_missing_rules(data, rules)  # <--- YENİ ÇAĞRI
        
        print("3. Normalizasyon Hesaplanıyor... (YENİ)")
        normalization_html = get_normalization_steps(data) # <--- YENİ ÇAĞRI

        print("3.1 Model Analizi Yapılıyor (B1 & A3)...")
        analysis_data = get_model_analysis(data)

        print("4. Tablolar Oluşturuluyor...")
        tables = get_real_tables(data)
        
        print("5. SQL ve Diyagram Hazırlanıyor...")
        sql = get_real_sql(data)
        diagram = get_real_diagram(data)

        print("5.1 Raporlama Sorguları Hazırlanıyor (E6)...")
        reporting_queries = get_reporting_queries(data)
        
        # Hata durumunda simülasyon verileri (Yedekler)
        if not rules: 
            rules, tables, sql, diagram = get_sim_rules(), get_sim_tables(), get_sim_sql(), get_sim_diagram()

        # Otomatik Kaydetme
        if sql and "CREATE TABLE" in sql:
            print("6. phpMyAdmin'e Kaydediliyor...")
            db_status = save_to_mysql(sql)
        else:
            db_status = "⚠️ SQL Oluşturulamadı, kaydedilemedi."

    # Şablona yeni değişkenleri (missing_rules, normalization_html) gönderiyoruz
    return render_template('index.html',
                           analysis_data=analysis_data,      
                           reporting_queries=reporting_queries,
                           rules=rules, 
                           missing_rules=missing_rules,     # <--- EKLENDİ
                           normalization_html=normalization_html, # <--- EKLENDİ
                           tables=tables, 
                           sql_code=sql, 
                           diagram_code=diagram, 
                           db_status=db_status)


if __name__ == '__main__':
    app.run(debug=True)