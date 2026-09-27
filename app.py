from flask import Flask, render_template, request
import google.generativeai as genai
import io
import csv
import json
import re
import mysql.connector  

app = Flask(__name__)

# SETTINGS (PLEASE CHECK)
# 1. Your API Key
GEMINI_API_KEY = "KENDI_API_ANAHTARINIZI_GIRIN" 

# 2. phpMyAdmin (MySQL) Connection Details
# If you are using XAMPP, the password is usually empty.
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',      
    'password': '',      # Usually empty in XAMPP/WAMP. If you have one, enter it here.
    'database': 'proje_veritabani' 
}

# 3. API Configuration
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # 'flash-lite' might occasionally throw errors, 'gemini-2.5-flash' is generally the most stable.
    model = genai.GenerativeModel('gemini-flash-lite-latest')
except:
    model = None

#  GEMINI OUTPUT CLEANER (FIXED)
def clean_gemini_output(text):
    """Cleans extra tags like ```json added by the AI."""
    if not text: return ""
    text = text.replace("```json", "").replace("```sql", "").replace("```mysql", "").replace("```mermaid", "").replace("```csv", "").replace("```", "")
    # Clean up possible explanation text around the Mermaid diagram
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
        print(f"API ERROR: {e}")
        return None

#  PHPMYADMIN SAVER
def save_to_mysql(sql_script):
    """Saves the generated SQL script directly to phpMyAdmin."""
    status_msg = ""
    conn = None
    try:
        # 1. Connect to MySQL server
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()

        # 2. Create the database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        cursor.execute(f"USE {DB_CONFIG['database']}")
        
        # 3. Execute SQL Commands
        # Split commands by ';' and execute them individually
        commands = sql_script.split(';')
        
        count = 0
        for command in commands:
            if command.strip():
                try:
                    cursor.execute(command)
                    count += 1
                except Exception as e:
                    print(f"SQL Warning (Skipped line): {e}")
        
        conn.commit()
        status_msg = f"✅ SUCCESS: Tables saved to phpMyAdmin ({DB_CONFIG['database']})! ({count} commands executed)"
        print(status_msg)

    except mysql.connector.Error as err:
        status_msg = f"❌ MySQL Error: {err}"
        print(status_msg)
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            
    return status_msg

# 1. REAL DATA FUNCTIONS (WITH PARSE FIXES)
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
    # Prompt to guarantee JSON structure (RESOLVES PREVIOUS ERRORS)
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
        # JSON parsing and cleaning
        start = res.find('[')
        end = res.rfind(']') + 1
        if start != -1 and end != -1:
            json_str = res[start:end]
            tables = json.loads(json_str)
            
            # Data Validation & Correction
            for t in tables:
                for col in t.get('columns', []):
                    # If 'name' key is missing, check for alternatives and fix
                    if 'name' not in col:
                        for bad_key in ['field', 'column', 'attribute', 'Field', 'Name']:
                            if bad_key in col:
                                col['name'] = col[bad_key]; break
                    # Convert constraints to string if provided as a list
                    if isinstance(col.get('constraints'), list):
                        col['constraints'] = ", ".join(col['constraints'])
            return tables
    except: return get_sim_tables()
    return get_sim_tables()

def get_real_sql(data):
    # MySQL Compatible Prompt
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
    # Clean up to prevent "Syntax Error"
    idx = res.find("erDiagram")
    return res[idx:] if idx != -1 else res

# UPDATED FUNCTION: ID-BASED RULE ANALYSIS
def get_missing_rules(data, current_rules):
    """
    Analyzes existing rules:
    1. Suggests improvements for weak rules (e.g., ID 4).
    2. Suggests completely new rules for missing constraints (ID: NEW).
    """
    # Convert existing rules into a text format for the AI to analyze
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

#  NORMALIZATION STEPS
def get_normalization_steps(data):
    """Explains the normalization process from 0NF to 3NF specifically for the domain."""
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

#  DETAILED MODEL ANALYSIS 
def get_model_analysis(data):
    """
    Answers specific exam questions regarding Central Entity (B1) and Expensive Rule (A3).
    """
    prompt = f"""
    Analyze the database model for '{data['domain']}' and provided constraints.
    Provide a structured analysis answering these specific questions from a database exam:
    
    1. **Central Entity:** Which entity is structurally most central? (Explain based on relationship degree/FKs).
    2. **Most Expensive Rule:** Which business rule is computationally most expensive to enforce? (Explain in terms of JOINs/Aggregations).
    3. **Trade-off:** Give one example where Denormalization might improve performance for this specific domain.

    Output format: Return ONLY a Python dictionary.
    Keys: "central_entity", "expensive_rule", "denormalization_tip"
    """
    res = ask_gemini("You are a Database Architect.", prompt)
    if not res: return None
    
    try:
        # Dictionary/JSON parsing
        start = res.find('{')
        end = res.rfind('}') + 1
        return eval(res[start:end])
    except:
        return None

# REPORTING QUERIES
def get_reporting_queries(data):
    """
    Generates complex SELECT queries based on the user's reporting requirements.
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

# 2. SIMULATION DATA (FALLBACK)
def get_sim_rules(): return [{'id': 'ERR', 'type': '-', 'statement': 'API Error', 'component': '-', 'tip': '-', 'rationale': '-'}]
def get_sim_tables(): return []
def get_sim_sql(): return "-- API Error"
def get_sim_diagram(): return "erDiagram\n ERROR"

# MAIN FLASK ROUTE
@app.route('/', methods=['GET', 'POST'])
def index():
    # Initialize variables as None
    rules, tables, sql, diagram, db_status = None, None, None, None, None
    missing_rules, normalization_html = None, None 

    analysis_data = None
    reporting_queries = None
    
    if request.method == 'POST':
        data = {k: request.form.get(k) for k in ['domain', 'primary_entity', 'constraints', 'advanced_features', 'security', 'reporting', 'common_tasks']}
        
        print("1. Extracting Business Rules...")
        rules = get_real_rules(data)

        print("2. Searching for Missing Rules...")
        missing_rules = get_missing_rules(data, rules) 
        
        print("3. Generating Normalization Steps...")
        normalization_html = get_normalization_steps(data) 

        print("3.1 Performing Model Analysis (B1 & A3)...")
        analysis_data = get_model_analysis(data)

        print("4. Creating Tables...")
        tables = get_real_tables(data)
        
        print("5. Preparing SQL and Entity-Relationship Diagram...")
        sql = get_real_sql(data)
        diagram = get_real_diagram(data)

        print("5.1 Preparing Reporting Queries (E6)...")
        reporting_queries = get_reporting_queries(data)
        
        # Use fallback simulation data in case of failure
        if not rules: 
            rules, tables, sql, diagram = get_sim_rules(), get_sim_tables(), get_sim_sql(), get_sim_diagram()

        # Automatic Database Saving
        if sql and "CREATE TABLE" in sql:
            print("6. Executing and Saving to phpMyAdmin...")
            db_status = save_to_mysql(sql)
        else:
            db_status = "⚠️ SQL could not be generated, saving failed."

    # Render template with all generated variables
    return render_template('index.html',
                           analysis_data=analysis_data,      
                           reporting_queries=reporting_queries,
                           rules=rules, 
                           missing_rules=missing_rules,     
                           normalization_html=normalization_html, 
                           tables=tables, 
                           sql_code=sql, 
                           diagram_code=diagram, 
                           db_status=db_status)

if __name__ == '__main__':
    app.run(debug=True)
