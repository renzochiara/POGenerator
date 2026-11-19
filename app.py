import os
import random
from datetime import datetime
import pandas as pd
import streamlit as st

# LLM integration (compatible with Groq, Mistral, OpenAI)
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# ==========================================
# DEFAULT API KEY CONFIGURATION
# ==========================================
# Replace "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" with your actual key.
DEFAULT_AI_KEY = "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"

# ==========================================
# PAGE CONFIG & STYLING
# ==========================================
st.set_page_config(
    page_title="Indigo Park Canada - PO Generator & AI Search",
    page_icon="🎫",
    layout="wide"
)

# Custom Indigo Theme Styling
st.markdown("""
    <style>
    .stButton>button {
        background-color: #581c87;
        color: white;
        font-weight: bold;
        border-radius: 8px;
    }
    .stButton>button:hover {
        background-color: #7e22ce;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# English / French UI Dictionary
TEXTS = {
    "EN": {
        "title": "Indigo Park Canada - Service PO Generator",
        "subtitle": "Create, log, and search Purchase Orders for service calls (Logic Control, Gate, HVAC, etc.)",
        "new_po_tab": "➕ Create New PO",
        "history_tab": "📋 PO Log (Excel)",
        "ai_tab": "🤖 AI Search Assistant",
        "po_details": "PO General Details",
        "cmo_code": "CMO / Parking Lot Code",
        "service_provider": "Service Provider / Vendor",
        "work_reason": "Reason for Service Call / Work Details",
        "category": "Maintenance Category",
        "priority": "Priority Level",
        "est_cost": "Estimated Cost ($ CAD)",
        "requested_by": "Requested By (Your Name)",
        "generate_btn": "Generate & Save PO",
        "success_msg": "PO Generated and Saved Successfully!",
        "search_label": "Filter by CMO Code or Vendor:",
        "download_excel": "📥 Download Full PO Log (Excel)",
        "ai_header": "Ask AI to Search POs",
        "ai_placeholder": "e.g., Find all POs for CMO 1851 or calls to Logic Control...",
        "ai_key_label": "API Key (Optional override)",
        "ai_provider": "AI Provider Choice"
    },
    "FR": {
        "title": "Indigo Park Canada - Générateur de Bon de Commande",
        "subtitle": "Créer, consigner et rechercher des bons de commande pour appels de service (Logic Control, barrières, etc.)",
        "new_po_tab": "➕ Créer un PO",
        "history_tab": "📋 Registre PO (Excel)",
        "ai_tab": "🤖 Assistant Recherche IA",
        "po_details": "Détails du Bon de Commande",
        "cmo_code": "Code CMO / Code du Stationnement",
        "service_provider": "Fournisseur de Service / Vendeur",
        "work_reason": "Raison de l'appel de service / Détails du travail",
        "category": "Catégorie d'entretien",
        "priority": "Niveau de Priorité",
        "est_cost": "Coût Estimé ($ CAD)",
        "requested_by": "Demandé par (Votre nom)",
        "generate_btn": "Générer et Enregistrer le PO",
        "success_msg": "PO généré et enregistré avec succès!",
        "search_label": "Filtrer par code CMO ou fournisseur:",
        "download_excel": "📥 Télécharger le registre complet (Excel)",
        "ai_header": "Interroger l'IA sur les PO",
        "ai_placeholder": "ex: Trouve tous les PO du CMO 1851 ou les appels faits à Logic Control...",
        "ai_key_label": "Clé API (Optionnelle)",
        "ai_provider": "Choix du fournisseur IA"
    }
}

EXCEL_FILE = "po_log.xlsx"

# Embedded Indigo Park Canada Logo URL
INDIGO_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Indigo_Group_logo.svg/320px-Indigo_Group_logo.svg.png"

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def load_po_data():
    """Loads existing PO data from Excel or creates a new DataFrame."""
    if os.path.exists(EXCEL_FILE):
        return pd.read_excel(EXCEL_FILE)
    else:
        columns = ["PO Number", "Date", "CMO Code", "Vendor", "Category", "Priority", "Estimated Cost ($)", "Reason", "Requested By", "Status"]
        df = pd.DataFrame(columns=columns)
        df.to_excel(EXCEL_FILE, index=False)
        return df

def save_po_data(df):
    """Saves DataFrame to local Excel log."""
    df.to_excel(EXCEL_FILE, index=False)

def generate_po_number():
    """Generates standard PO-YYYYMMDD-XXXX format."""
    today = datetime.now().strftime("%Y%m%d")
    rand_id = random.randint(1000, 9999)
    return f"PO-{today}-{rand_id}"

def query_ai_assistant(query, df, user_key, provider):
    """Answers search queries against PO log using an LLM or local keyword fallback."""
    if df.empty:
        return "No PO records exist in the log yet."
    
    context_str = df.to_string(index=False)
    
    # Priority order: UI Input Key -> Hardcoded DEFAULT_AI_KEY -> Streamlit Secrets
    active_key = user_key or DEFAULT_AI_KEY or st.secrets.get("AI_API_KEY", "")

    if active_key and active_key != "YOUR_HARDCODED_API_KEY_HERE" and HAS_OPENAI:
        try:
            base_urls = {
                "Groq (Llama 3)": "https://api.groq.com/openai/v1",
                "Mistral AI": "https://api.mistral.ai/v1",
                "OpenAI": "https://api.openai.com/v1"
            }
            models = {
                "Groq (Llama 3)": "llama-3.3-70b-versatile",
                "Mistral AI": "mistral-small-latest",
                "OpenAI": "gpt-4o-mini"
            }
            
            client = OpenAI(api_key=active_key, base_url=base_urls.get(provider))
            
            prompt = f"""
            You are an operational PO search assistant for Indigo Park Canada.
            Here is the complete current Purchase Order dataset:
            
            {context_str}
            
            User Question: {query}
            
            Answer clearly and concisely. List matching PO Numbers, Dates, CMO Codes, Vendors, Costs, and Reason details.
            """
            
            response = client.chat.completions.create(
                model=models.get(provider, "mistral-small-latest"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"⚠️ API Error: {str(e)}\n\nRunning standard keyword search fallback..."

    # Fallback search if no key is provided
    query_lower = query.lower()
    matches = df[df.apply(lambda row: query_lower in str(row.values).lower(), axis=1)]
    
    if matches.empty:
        return f"No POs found matching: '{query}'"
    return matches

# ==========================================
# APP LAYOUT
# ==========================================

# Sidebar
st.sidebar.image(INDIGO_LOGO_URL, width=200)
st.sidebar.markdown("---")
lang = st.sidebar.radio("Language / Langue", ["EN", "FR"], horizontal=True)
t = TEXTS[lang]

st.title(t["title"])
st.caption(t["subtitle"])

tab1, tab2, tab3 = st.tabs([t["new_po_tab"], t["history_tab"], t["ai_tab"]])

# --- TAB 1: CREATE NEW PO ---
with tab1:
    st.subheader(t["po_details"])
    
    with st.form("po_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            cmo_code = st.text_input(t["cmo_code"], placeholder="e.g. CMO-1851, Forum, Medifice").upper()
            vendor = st.selectbox(t["service_provider"], ["Logic Control", "Amano", "Stanley / Door Automation", "HVAC / Climate Controls", "Elevator Service", "Electrical / Lighting", "Plumbing", "Other"])
            if vendor == "Other":
                vendor = st.text_input("Specify Vendor Name")
            
            category = st.selectbox(t["category"], ["Gate & Equipment Repair", "Software / Network Call", "HVAC Maintenance", "General Repairs", "Emergency Fix"])
        
        with col2:
            priority = st.select_slider(t["priority"], options=["Normal", "Urgent", "Emergency"])
            est_cost = st.number_input(t["est_cost"], min_value=0.0, step=50.0, value=0.0)
            requested_by = st.text_input(t["requested_by"], value="")
        
        work_reason = st.text_area(t["work_reason"], placeholder="Explain why Logic Control or the service vendor was requested...")
        
        submit_btn = st.form_submit_button(t["generate_btn"], use_container_width=True)

    if submit_btn:
        if not cmo_code or not work_reason or not requested_by:
            st.error("Please enter CMO Code, Work Reason, and Requested By.")
        else:
            po_num = generate_po_number()
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            new_record = {
                "PO Number": po_num,
                "Date": date_str,
                "CMO Code": cmo_code,
                "Vendor": vendor,
                "Category": category,
                "Priority": priority,
                "Estimated Cost ($)": est_cost,
                "Reason": work_reason,
                "Requested By": requested_by,
                "Status": "Pending Follow-up"
            }
            
            df = load_po_data()
            df = pd.concat([pd.DataFrame([new_record]), df], ignore_index=True)
            save_po_data(df)
            
            st.success(f"{t['success_msg']} **PO #: {po_num}**")

# --- TAB 2: PO HISTORY & LOG ---
with tab2:
    st.subheader(t["history_tab"])
    
    df = load_po_data()
    
    if df.empty:
        st.info("No PO records saved yet.")
    else:
        search_query = st.text_input(t["search_label"], "").upper()
        if search_query:
            filtered_df = df[df["CMO Code"].str.contains(search_query, na=False) | df["Vendor"].str.contains(search_query, case=False, na=False)]
        else:
            filtered_df = df
            
        st.dataframe(filtered_df, use_container_width=True)
        
        with open(EXCEL_FILE, "rb") as file:
            st.download_button(
                label=t["download_excel"],
                data=file,
                file_name=f"Indigo_PO_Log_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# --- TAB 3: AI SEARCH ASSISTANT ---
with tab3:
    st.subheader(t["ai_tab"])
    
    col_ai1, col_ai2 = st.columns([1, 2])
    with col_ai1:
        ai_provider = st.selectbox(t["ai_provider"], ["Mistral AI", "Groq (Llama 3)", "OpenAI"])
        user_key = st.text_input(t["ai_key_label"], type="password", help="Leave blank to use pre-configured key.")
    
    ai_query = st.text_input(t["ai_header"], placeholder=t["ai_placeholder"])
    
    if st.button("🔍 Search with AI", use_container_width=True):
        if not ai_query:
            st.warning("Please enter a search question.")
        else:
            df = load_po_data()
            with st.spinner("Analyzing PO database..."):
                result = query_ai_assistant(ai_query, df, user_key, ai_provider)
                
                if isinstance(result, str):
                    st.markdown(result)
                else:
                    st.dataframe(result, use_container_width=True)
