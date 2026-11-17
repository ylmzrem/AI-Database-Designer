# 🚀 AI-Powered Database Design Assistant 🤖🗄️

A Flask-based web application that automates database design from natural language requirements using Google Gemini AI. This tool guides users through the entire modeling process, from extracting business rules to generating a fully structured MySQL database, achieving a seamless 0NF to 3NF transition.

### ✨ Key Features
*   **🛠️ Business Rule Extraction:** Analyzes structured text inputs to extract core organizational principles and database constraints.
*   **🔍 Missing Rule Detection:** Uses AI to identify weak, vague, or missing rules and suggests critical edge cases for data integrity.
*   **🔄 Step-by-Step Normalization:** Automatically generates detailed explanations for the normalization process (0NF &rarr; 1NF &rarr; 2NF &rarr; 3NF) tailored to the specific domain.
*   **🏗️ Structural Analysis:** Evaluates the database model to identify the central entity, pinpoint the most computationally expensive rules, and provide denormalization tips for performance.
*   **📊 Visual ER Diagrams:** Interactively renders entity-relationship diagrams using Crow's Foot notation directly in the browser via Mermaid.js.
*   **⚙️ Auto-SQL Generation & Execution:** Produces complete, raw MySQL scripts (CREATE TABLE, constraints, dummy data) and can automatically execute them on a connected phpMyAdmin/MySQL server.
*   **📈 Complex Reporting Queries:** Generates advanced SQL `SELECT` queries (including `JOIN`s, `GROUP BY`s, and `HAVING` clauses) tailored to your specific reporting needs.

### 💻 Tech Stack
*   **Backend:** 🐍 Python, Flask, MySQL Connector
*   **AI Engine:** 🧠 Google Generative AI (Gemini Flash Lite)
*   **Frontend:** 🌐 HTML5, Bootstrap 5, Mermaid.js

### 🚀 Setup & Installation
1. **📂 Clone the Repository:**
   ```bash
   git clone https://github.com/ylmzrem/AI-Database-Designer.git
   cd AI-Database-Designer
   ```
2. **📦 Install Dependencies:**
   ```bash
   pip install flask google-generativeai mysql-connector-python
   ```
3. **🔑 Configuration:**
   Open `app.py` and configure your credentials:
   *   Set `GEMINI_API_KEY` to your valid Google Gemini API key.
   *   Update the `DB_CONFIG` dictionary with your MySQL hosting details (`host`, `user`, `password`, `database`).
4. **🏃‍♂️ Run the Application:**
   ```bash
   python app.py
   ```
5. **🌐 Access the App:**
   Open your web browser and navigate to `http://localhost:5000`.

---

# 🚀 Yapay Zeka Destekli Veritabanı Tasarım Asistanı 🤖🗄️

Google Gemini yapay zekasını kullanarak metinsel gereksinimlerden otomatik veritabanı tasarımı yapan Flask tabanlı bir web uygulamasıdır. Bu araç, iş kurallarının çıkarılmasından tam yapılandırılmış bir MySQL veritabanının oluşturulmasına kadar tüm süreci (0NF'den 3NF'ye) adım adım yönetir.

### ✨ Temel Özellikler
*   **🛠️ İş Kuralları Analizi (Business Rules):** Verilen proje tanımını analiz ederek organizasyonun veri perspektifini ve temel veritabanı kısıtlamalarını çıkarır.
*   **🔍 Eksik Kural Tespiti:** Yapay zeka ile mevcut kuralları değerlendirir; zayıf, belirsiz veya eksik olan kritik iş kurallarını (edge cases) tespit edip öneriler sunar.
*   **🔄 Adım Adım Normalizasyon:** Projenin domainine özel olarak 0NF'den 3NF'ye kadar olan normalizasyon sürecini detaylı ve açıklayıcı bir şekilde sunar.
*   **🏗️ Yapısal ve Performans Analizi:** Merkezi varlığı (Central Entity) belirler, sistem kaynaklarını en çok zorlayacak pahalı kuralları analiz eder ve performans optimizasyonu için denormalizasyon ipuçları verir.
*   **📊 Görsel ER Diyagramları:** Mermaid.js kullanarak tarayıcı üzerinde Crow's Foot (Karga Ayağı) notasyonu ile interaktif Varlık-İlişki (ER) diyagramları çizer.
*   **⚙️ Otomatik SQL Üretimi ve Çalıştırma:** Tablo oluşturma (CREATE TABLE), ilişkiler ve test verilerini içeren MySQL betikleri üretir; istenirse doğrudan phpMyAdmin/MySQL veritabanınıza bağlanarak bu tabloları otomatik oluşturur.
*   **📈 Karmaşık Raporlama Sorguları:** Proje ihtiyaçlarına göre şekillenmiş, `JOIN`, `GROUP BY` ve `HAVING` içeren gelişmiş SQL `SELECT` sorguları üretir.

### 💻 Kullanılan Teknolojiler
*   **Backend:** 🐍 Python, Flask, MySQL Connector
*   **Yapay Zeka:** 🧠 Google Generative AI (Gemini Flash Lite)
*   **Frontend:** 🌐 HTML5, Bootstrap 5, Mermaid.js

### 🚀 Kurulum Adımları
1. **📂 Repoyu Klonlayın:**
   ```bash
   git clone https://github.com/ylmzrem/AI-Database-Designer.git
   cd AI-Database-Designer
   ```
2. **📦 Gerekli Kütüphaneleri Yükleyin:**
   ```bash
   pip install flask google-generativeai mysql-connector-python
   ```
3. **🔑 Ayarları Yapılandırın:**
   `app.py` dosyasını açarak API ve veritabanı ayarlarını güncelleyin:
   *   `GEMINI_API_KEY` değişkenine kendi Google Gemini API anahtarınızı girin.
   *   `DB_CONFIG` sözlüğünü MySQL sunucu bilgilerinize göre (`host`, `user`, `password`, `database`) düzenleyin.
4. **🏃‍♂️ Uygulamayı Başlatın:**
   ```bash
   python app.py
   ```
5. **🌐 Arayüze Erişin:**
   Tarayıcınızda `http://localhost:5000` adresine gidin.
