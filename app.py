import io
import os
import random
from datetime import datetime
import pandas as pd
import streamlit as st

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSHEETS = True
except ImportError:
    HAS_GSHEETS = False

# ==========================================
# PAGE CONFIG & STYLING
# ==========================================
st.set_page_config(
    page_title="Indigo Park Canada - PO Generator & AI Search",
    page_icon="🎫",
    layout="wide"
)

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
        "cost_na_label": "Cost is N/A (Not Available / TBD)",
        "est_cost": "Estimated Cost ($ CAD)",
        "requested_by": "Requested By (Your Name)",
        "generate_btn": "Generate & Save PO",
        "success_msg": "PO Generated and Saved Successfully!",
        "search_label": "Filter by CMO Code or Vendor:",
        "download_excel": "📥 Download Full PO Log (Excel)",
        "delete_section": "🗑️ Erase a Mistaken PO",
        "select_po_delete": "Select PO Number to erase:",
        "delete_po_btn": "Erase Selected PO",
        "po_erased_msg": "Erased PO:",
        "ai_header": "Ask AI to Search POs",
        "ai_placeholder": "e.g., Find all POs for CMO 1851 or calls to Logic Control...",
        "ai_search_btn": "🔍 Search with AI",
        "ai_help_title": "What can the AI Search Assistant do?",
        "ai_help_body": (
            "The AI Search Assistant reads your saved Purchase Order log and answers questions in plain language:\n"
            "- **Find by CMO / Lot Code:** *\"Show all POs for 1851 Sherbrooke\"* or *\"List POs for Forum\"*\n"
            "- **Filter by Vendor:** *\"Which service calls did we log for Logic Control?\"*\n"
            "- **Search by Date or Priority:** *\"Show emergency POs from this month\"* or *\"POs created on 2026-11-19\"*\n"
            "- **Check Costs & Reasons:** *\"What was the estimated cost for gate repairs?\"*"
        ),
        "missing_secret": "Groq API key is not configured yet. Add `GROQ_API_KEY` in Streamlit Secrets to enable AI search.",
        "storage_cloud": "☁️ Persistent storage active (Google Sheets)",
        "storage_local": "💾 Local file mode (`po_log.xlsx`) — connect Google Sheets in Secrets to keep data across reboots/sleep."
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
        "cost_na_label": "Coût : N/A (Non disponible / À déterminer)",
        "est_cost": "Coût Estimé ($ CAD)",
        "requested_by": "Demandé par (Votre nom)",
        "generate_btn": "Générer et Enregistrer le PO",
        "success_msg": "PO généré et enregistré avec succès!",
        "search_label": "Filtrer par code CMO ou fournisseur:",
        "download_excel": "📥 Télécharger le registre complet (Excel)",
        "delete_section": "🗑️ Effacer un PO en cas d'erreur",
        "select_po_delete": "Choisir le numéro de PO à effacer :",
        "delete_po_btn": "Effacer le PO sélectionné",
        "po_erased_msg": "PO effacé :",
        "ai_header": "Interroger l'IA sur les PO",
        "ai_placeholder": "ex: Trouve tous les PO du CMO 1851 ou les appels faits à Logic Control...",
        "ai_search_btn": "🔍 Rechercher avec l'IA",
        "ai_help_title": "Que peut faire l'Assistant Recherche IA ?",
        "ai_help_body": (
            "L'Assistant Recherche IA lit votre registre de bons de commande et répond à vos questions :\n"
            "- **Recherche par code CMO / stationnement :** *« Montre tous les PO pour 1851 Sherbrooke »* ou *« PO du Forum »*\n"
            "- **Filtrer par fournisseur :** *« Quels appels de service avons-nous faits à Logic Control ? »*\n"
            "- **Recherche par date ou priorité :** *« Montre les PO urgents ou d'urgence »* ou *« PO du 2026-11-19 »*\n"
            "- **Vérifier coûts et raisons :** *« Quel est le coût estimé pour les réparations de barrières ? »*"
        ),
        "missing_secret": "La clé API Groq n'est pas encore configurée. Ajoutez `GROQ_API_KEY` dans les Secrets Streamlit pour activer la recherche IA.",
        "storage_cloud": "☁️ Stockage persistant actif (Google Sheets)",
        "storage_local": "💾 Mode fichier local (`po_log.xlsx`) — configurez Google Sheets dans les Secrets pour garder les PO après redémarrage/veille."
    }
}

COLUMNS = [
    "PO Number", "Date", "CMO Code", "Vendor", "Category",
    "Priority", "Estimated Cost ($)", "Reason", "Requested By", "Status"
]
EXCEL_FILE = "po_log.xlsx"
INDIGO_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Indigo_Group_logo.svg/320px-Indigo_Group_logo.svg.png"

# ==========================================
# GOOGLE SHEETS (PERSISTENT STORAGE)
# ==========================================
def get_gsheet_worksheet():
    """Returns gspread worksheet if GOOGLE_SERVICE_ACCOUNT and GSHEET_ID are configured in Secrets."""
    if not HAS_GSHEETS:
        return None
    try:
        sheet_id = st.secrets.get("GSHEET_ID", "")
        sa_info = st.secrets.get("GOOGLE_SERVICE_ACCOUNT", None)
        if not sheet_id or not sa_info:
            return None
        creds = Credentials.from_service_account_info(
            dict(sa_info),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(str(sheet_id).strip())
        try:
            return spreadsheet.worksheet("PO_Log")
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title="PO_Log", rows=1000, cols=15)
            ws.append_row(COLUMNS)
            return ws
    except Exception:
        return None

def load_po_data():
    """Loads PO records from Google Sheets if configured, else from local Excel file."""
    ws = get_gsheet_worksheet()
    if ws is not None:
        try:
            records = ws.get_all_records()
            if not records:
                return pd.DataFrame(columns=COLUMNS)
            df = pd.DataFrame(records)
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            return df[COLUMNS]
        except Exception:
            pass

    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[COLUMNS]

    df = pd.DataFrame(columns=COLUMNS)
    df.to_excel(EXCEL_FILE, index=False)
    return df

def save_po_data(df):
    """Saves PO records to local Excel backup and syncs to Google Sheets if configured."""
    clean_df = df[COLUMNS].copy() if not df.empty else pd.DataFrame(columns=COLUMNS)
    clean_df.to_excel(EXCEL_FILE, index=False)

    ws = get_gsheet_worksheet()
    if ws is not None:
        ws.clear()
        rows = [COLUMNS] + clean_df.fillna("").astype(str).values.tolist()
        ws.update(rows)

def build_excel_download_bytes(df):
    """Creates an in-memory Excel file (.xlsx) for downloading."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="PO_Log")
    return output.getvalue()

# ==========================================
# GROQ AI & PO HELPERS
# ==========================================
def get_groq_api_key():
    """Reads GROQ_API_KEY from Streamlit Secrets (or environment)."""
    try:
        if "GROQ_API_KEY" in st.secrets and st.secrets["GROQ_API_KEY"]:
            return str(st.secrets["GROQ_API_KEY"]).strip()
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY", "").strip()

def resolve_groq_model(client):
    """Finds an available chat model on the account using Groq's /models endpoint."""
    preferred_models = [
        "openai/gpt-oss-20b",
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
    ]
    try:
        models_resp = client.models.list()
        available_ids = [m.id for m in getattr(models_resp, "data", []) if getattr(m, "id", None)]

        for model_id in preferred_models:
            if model_id in available_ids:
                return model_id

        excluded_prefixes = ("whisper", "canopylabs", "meta-llama/llama-prompt-guard")
        for model_id in available_ids:
            if not model_id.startswith(excluded_prefixes):
                return model_id
    except Exception:
        pass

    return "openai/gpt-oss-20b"

def generate_po_number():
    """Generates standard PO-YYYYMMDD-XXXX format."""
    today = datetime.now().strftime("%Y%m%d")
    rand_id = random.randint(1000, 9999)
    return f"PO-{today}-{rand_id}"

def query_groq_ai(query, df, missing_secret_msg):
    """Answers search queries against PO log using Groq via Streamlit Secrets."""
    if df.empty:
        return "No PO records exist in the log yet."

    api_key = get_groq_api_key()
    if not api_key:
        return f"⚠️ {missing_secret_msg}"

    if not HAS_OPENAI:
        return "⚠️ The `openai` package is not installed. Add `openai` to `requirements.txt`."

    context_str = df.to_string(index=False)

    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        model_name = resolve_groq_model(client)

        prompt = f"""
        You are an operational PO search assistant for Indigo Park Canada.
        Here is the complete current Purchase Order dataset:

        {context_str}

        User Question: {query}

        Answer clearly and concisely. List matching PO Numbers, Dates, CMO Codes, Vendors, Costs, and Reason details.
        """

        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        answer = response.choices[0].message.content
        return f"{answer}\n\n*Model used: `{model_name}`*"
    except Exception as e:
        return f"⚠️ Groq API Connection Error: {str(e)}"

# ==========================================
# SESSION STATE INIT
# ==========================================
if "show_ai_help" not in st.session_state:
    st.session_state.show_ai_help = False

# ==========================================
# SIDEBAR (LOGO, LANGUAGE, STORAGE STATUS)
# ==========================================
st.sidebar.image(INDIGO_LOGO_URL, width=200)
st.sidebar.markdown("---")
lang = st.sidebar.radio("Language / Langue", ["EN", "FR"], horizontal=True)
t = TEXTS[lang]

st.sidebar.markdown("---")
if get_gsheet_worksheet() is not None:
    st.sidebar.success(t["storage_cloud"])
else:
    st.sidebar.info(t["storage_local"])

# ==========================================
# MAIN PAGE LAYOUT
# ==========================================
st.title(t["title"])
st.caption(t["subtitle"])

tab1, tab2, tab3 = st.tabs([t["new_po_tab"], t["history_tab"], t["ai_tab"]])

# --- TAB 1: CREATE NEW PO ---
with tab1:
    st.subheader(t["po_details"])

    cost_is_na = st.checkbox(t["cost_na_label"], value=False)

    with st.form("po_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            cmo_code = st.text_input(t["cmo_code"], placeholder="e.g. CMO-1851, Forum, Medifice").upper()
            vendor = st.selectbox(
                t["service_provider"],
                [
                    "Logic Control", "Amano", "Stanley / Door Automation",
                    "HVAC / Climate Controls", "Elevator Service",
                    "Electrical / Lighting", "Plumbing", "Other"
                ]
            )
            if vendor == "Other":
                vendor = st.text_input("Specify Vendor Name")

            category = st.selectbox(
                t["category"],
                [
                    "Gate & Equipment Repair", "Software / Network Call",
                    "HVAC Maintenance", "General Repairs", "Emergency Fix"
                ]
            )

        with col2:
            priority = st.select_slider(t["priority"], options=["Normal", "Urgent", "Emergency"])
            if cost_is_na:
                st.text_input(t["est_cost"], value="N/A", disabled=True)
                est_cost_value = "N/A"
            else:
                est_cost_num = st.number_input(t["est_cost"], min_value=0.0, step=50.0, value=0.0)
                est_cost_value = round(float(est_cost_num), 2)
            requested_by = st.text_input(t["requested_by"], value="")

        work_reason = st.text_area(
            t["work_reason"],
            placeholder="Explain why Logic Control or the service vendor was requested..."
        )

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
                "Estimated Cost ($)": est_cost_value,
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
            filtered_df = df[
                df["CMO Code"].astype(str).str.contains(search_query, na=False)
                | df["Vendor"].astype(str).str.contains(search_query, case=False, na=False)
            ]
        else:
            filtered_df = df

        st.dataframe(filtered_df, use_container_width=True)

        st.download_button(
            label=t["download_excel"],
            data=build_excel_download_bytes(df),
            file_name=f"Indigo_PO_Log_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.markdown("---")
        st.markdown(f"**{t['delete_section']}**")
        po_list = df["PO Number"].dropna().astype(str).tolist()
        if po_list:
            col_del1, col_del2 = st.columns([3, 1])
            with col_del1:
                po_to_erase = st.selectbox(t["select_po_delete"], po_list, label_visibility="collapsed")
            with col_del2:
                if st.button(t["delete_po_btn"], use_container_width=True):
                    updated_df = df[df["PO Number"].astype(str) != po_to_erase].reset_index(drop=True)
                    save_po_data(updated_df)
                    st.success(f"{t['po_erased_msg']} {po_to_erase}")
                    st.rerun()

# --- TAB 3: AI SEARCH ASSISTANT (GROQ) ---
with tab3:
    st.subheader(t["ai_tab"])

    col_q_input, col_q_btn = st.columns([11, 1])
    with col_q_input:
        ai_query = st.text_input(t["ai_header"], placeholder=t["ai_placeholder"])
    with col_q_btn:
        st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("?", key="ai_help_btn", help=t["ai_help_title"], use_container_width=True):
            st.session_state.show_ai_help = not st.session_state.show_ai_help

    if st.session_state.show_ai_help:
        with st.container(border=True):
            st.markdown(f"**{t['ai_help_title']}**")
            st.markdown(t["ai_help_body"])

    if st.button(t["ai_search_btn"], use_container_width=True):
        if not ai_query:
            st.warning("Please enter a search question.")
        else:
            df = load_po_data()
            with st.spinner("Asking AI Assistant..."):
                result = query_groq_ai(ai_query, df, t["missing_secret"])

                if isinstance(result, str):
                    st.markdown(result)
                else:
                    st.dataframe(result, use_container_width=True)
