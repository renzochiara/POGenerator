import base64
import io
import json
import os
import random
import urllib.parse
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# ==========================================
# PAGE CONFIG & STYLING
# ==========================================
st.set_page_config(
    page_title="Indigo Park Canada - PO Management System",
    page_icon="🎫",
    layout="wide"
)

st.markdown("""
    <style>
    .stButton>button, .stLinkButton>a {
        background-color: #581c87;
        color: white !important;
        font-weight: bold;
        border-radius: 8px;
        text-decoration: none;
    }
    .stButton>button:hover, .stLinkButton>a:hover {
        background-color: #7e22ce;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

PAYMENT_CATEGORIES = ["Paid", "Partially Paid", "Pending"]

# English / French UI Dictionary
TEXTS = {
    "EN": {
        "title": "Indigo Park Canada - Service PO Generator",
        "subtitle": "Create, log, export PDF, and audit Purchase Orders for service calls",
        "login_title": "🔐 Login to Indigo PO Portal",
        "username": "Username",
        "password": "Password",
        "login_btn": "Sign In",
        "logout_btn": "Sign Out",
        "invalid_login": "Invalid username or password.",
        "invalid_cost": "Please enter a valid non-negative number (e.g. 250.00) or NA.",
        "missing_secret": "GROQ_API_KEY is missing in Streamlit Secrets.",
        "new_po_tab": "➕ Create PO & PDF",
        "history_tab": "📋 PO Log",
        "ai_tab": "🤖 AI Search Assistant",
        "users_tab": "👤 Manage Users",
        "po_details": "PO General Details",
        "cmo_code": "CMO / Parking Lot Code",
        "service_provider": "Service Provider / Vendor",
        "vendor_other_label": "Specify Custom Vendor Name",
        "work_reason": "Reason for Service Call / Work Details",
        "category": "Maintenance Category",
        "cat_other_label": "Specify Custom Category Name",
        "priority": "Priority Level",
        "est_cost": "Estimated Cost ($ CAD) — enter amount or NA",
        "user_email": "Your Email Address (Requester)",
        "supplier_email": "Supplier / Vendor Email Address",
        "requested_by": "Requested By (Your Name)",
        "generate_btn": "Generate & Save PO",
        "success_msg": "PO Generated and Saved Successfully!",
        "draft_note": "Download the PDF with the PDF button and open your email link to launch your email draft with the supplier and user emails filled in, then attach the PDF before sending.",
        "open_email_btn": "✉️ Open Email Link",
        "search_label": "Search POs (PO #, CMO, Vendor, Email, Reason, Requester):",
        "delete_section": "🗑️ Erase a Mistaken PO",
        "select_po_delete": "Select PO Number to erase:",
        "delete_po_btn": "Erase Selected PO",
        "po_erased_msg": "Erased PO:",
        "pdf_section": "📄 Download Readable PO PDF",
        "select_po_pdf": "Select PO Number for PDF:",
        "download_pdf_btn": "📄 Download PDF",
        "ai_header": "Ask AI to Search POs",
        "ai_placeholder": "e.g., Find all POs for CMO 1851 or calls to Logic Control...",
        "ai_search_btn": "🔍 Search with AI",
        "admin_audit_title": "⚙️ Admin Audit & Payment Groups",
        "actual_cost_label": "Actual Cost ($ CAD)",
        "payment_status_label": "Assign Status Category (Required)",
        "select_category_err": "Please select a payment status category before updating.",
        "update_po_btn": "Update PO & Assign Category",
        "create_user_header": "Create New User Account",
        "new_username_label": "New Username",
        "new_password_label": "New Password",
        "new_role_label": "Account Role",
        "create_user_btn": "➕ Create User",
        "user_created_msg": "User account created:",
        "user_exists_err": "That username already exists.",
        "user_fields_err": "Please enter both a username and a password.",
        "existing_users_header": "Existing Accounts"
    },
    "FR": {
        "title": "Indigo Park Canada - Générateur de Bon de Commande",
        "subtitle": "Créer, consigner, exporter en PDF et auditer les bons de commande",
        "login_title": "🔐 Connexion Portail PO Indigo",
        "username": "Nom d'utilisateur",
        "password": "Mot de passe",
        "login_btn": "Se connecter",
        "logout_btn": "Se déconnecter",
        "invalid_login": "Nom d'utilisateur ou mot de passe invalide.",
        "invalid_cost": "Veuillez entrer un montant positif valide (ex. 250.00) ou NA.",
        "missing_secret": "GROQ_API_KEY est manquant dans les Secrets Streamlit.",
        "new_po_tab": "➕ Créer PO & PDF",
        "history_tab": "📋 Registre PO",
        "ai_tab": "🤖 Assistant Recherche IA",
        "users_tab": "👤 Gestion Utilisateurs",
        "po_details": "Détails du Bon de Commande",
        "cmo_code": "Code CMO / Code du Stationnement",
        "service_provider": "Fournisseur de Service / Vendeur",
        "vendor_other_label": "Préciser le nom du fournisseur personnalisé",
        "work_reason": "Raison de l'appel de service / Détails du travail",
        "category": "Catégorie d'entretien",
        "cat_other_label": "Préciser la catégorie personnalisée",
        "priority": "Niveau de Priorité",
        "est_cost": "Coût Estimé ($ CAD) — entrer un montant ou NA",
        "user_email": "Votre courriel (Demandeur)",
        "supplier_email": "Courriel du Fournisseur",
        "requested_by": "Demandé par (Votre nom)",
        "generate_btn": "Générer et Enregistrer le PO",
        "success_msg": "PO généré et enregistré avec succès!",
        "draft_note": "Téléchargez le PDF avec le bouton PDF et ouvrez le lien courriel pour lancer votre brouillon avec les courriels du fournisseur et de l'utilisateur remplis, puis joignez le PDF avant d'envoyer.",
        "open_email_btn": "✉️ Ouvrir le lien courriel",
        "search_label": "Rechercher PO (N° PO, CMO, Fournisseur, Courriel, Raison) :",
        "delete_section": "🗑️ Effacer un PO en cas d'erreur",
        "select_po_delete": "Choisir le numéro de PO à effacer :",
        "delete_po_btn": "Effacer le PO sélectionné",
        "po_erased_msg": "PO effacé :",
        "pdf_section": "📄 Télécharger le PO en PDF lisible",
        "select_po_pdf": "Choisir le numéro de PO pour le PDF :",
        "download_pdf_btn": "📄 Télécharger PDF",
        "ai_header": "Interroger l'IA sur les PO",
        "ai_placeholder": "ex: Trouve tous les PO du CMO 1851 ou les appels faits à Logic Control...",
        "ai_search_btn": "🔍 Rechercher avec l'IA",
        "admin_audit_title": "⚙️ Audit Admin & Groupes de Paiement",
        "actual_cost_label": "Coût Réel ($ CAD)",
        "payment_status_label": "Catégorie de Statut Requise",
        "select_category_err": "Veuillez choisir une catégorie de statut avant de mettre à jour.",
        "update_po_btn": "Mettre à jour & Classer le PO",
        "create_user_header": "Créer un nouveau compte utilisateur",
        "new_username_label": "Nouveau nom d'utilisateur",
        "new_password_label": "Nouveau mot de passe",
        "new_role_label": "Rôle du compte",
        "create_user_btn": "➕ Créer l'utilisateur",
        "user_created_msg": "Compte utilisateur créé :",
        "user_exists_err": "Ce nom d'utilisateur existe déjà.",
        "user_fields_err": "Veuillez entrer un nom d'utilisateur et un mot de passe.",
        "existing_users_header": "Comptes existants"
    }
}

COLUMNS = [
    "PO Number", "Date", "CMO Code", "Vendor", "Category",
    "Priority", "Estimated Cost ($)", "Actual Cost ($)",
    "Requester Email", "Supplier Email", "Reason", "Requested By", "Payment Status"
]
EXCEL_FILE = "po_log.xlsx"
USERS_FILE = "users_store.json"
INDIGO_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Indigo_Group_logo.svg/320px-Indigo_Group_logo.svg.png"

DEFAULT_USERS = {
    "user": {"password": "user123", "role": "user"},
    "admin": {"password": "admin123", "role": "admin"}
}

# ==========================================
# GITHUB STORAGE HELPERS
# ==========================================
def get_github_config():
    token = str(st.secrets.get("GITHUB_TOKEN", "") or "").strip()
    repo = str(st.secrets.get("GITHUB_REPO", "") or "").strip()
    branch = str(st.secrets.get("GITHUB_BRANCH", "main") or "main").strip()
    if not token or not repo:
        return None
    return {"token": token, "repo": repo, "branch": branch}

def github_get_file_bytes(repo_path):
    cfg = get_github_config()
    if cfg is None:
        return None
    url = f"https://api.github.com/repos/{cfg['repo']}/contents/{repo_path}"
    headers = {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github+json"
    }
    params = {"ref": cfg["branch"]}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            encoded = str(data.get("content", "")).replace("\n", "")
            if encoded:
                return base64.b64decode(encoded)
        return None
    except Exception:
        return None

def github_put_file_bytes(repo_path, content_bytes, commit_message):
    cfg = get_github_config()
    if cfg is None:
        return False, "GitHub secrets not configured."

    url = f"https://api.github.com/repos/{cfg['repo']}/contents/{repo_path}"
    headers = {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github+json"
    }

    sha = None
    try:
        get_resp = requests.get(url, headers=headers, params={"ref": cfg["branch"]}, timeout=15)
        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha")
    except Exception:
        pass

    payload = {
        "message": commit_message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": cfg["branch"]
    }
    if sha:
        payload["sha"] = sha

    try:
        put_resp = requests.put(url, headers=headers, json=payload, timeout=15)
        if put_resp.status_code in (200, 201):
            return True, None
        return False, f"GitHub API ({put_resp.status_code}): {put_resp.text}"
    except Exception as e:
        return False, f"GitHub sync error: {str(e)}"

# ==========================================
# USER MANAGEMENT HELPERS
# ==========================================
def load_users_store():
    users = {k: dict(v) for k, v in DEFAULT_USERS.items()}

    secrets_users = st.secrets.get("USERS", {})
    if isinstance(secrets_users, dict):
        for uname, uinfo in secrets_users.items():
            if isinstance(uinfo, dict) and "password" in uinfo:
                users[str(uname)] = {
                    "password": str(uinfo["password"]),
                    "role": str(uinfo.get("role", "user"))
                }

    gh_users_bytes = github_get_file_bytes(USERS_FILE)
    if gh_users_bytes:
        try:
            loaded = json.loads(gh_users_bytes.decode("utf-8"))
            if isinstance(loaded, dict):
                for uname, uinfo in loaded.items():
                    if isinstance(uinfo, dict) and "password" in uinfo:
                        users[str(uname)] = {
                            "password": str(uinfo["password"]),
                            "role": str(uinfo.get("role", "user")).lower()
                        }
        except Exception:
            pass

    if "custom_users" in st.session_state:
        for uname, uinfo in st.session_state.custom_users.items():
            users[uname] = dict(uinfo)

    return users

def create_user_account(username, password, role):
    clean_user = str(username).strip()
    clean_pass = str(password).strip()
    clean_role = "admin" if str(role).strip().lower() == "admin" else "user"

    if "custom_users" not in st.session_state:
        st.session_state.custom_users = {}

    st.session_state.custom_users[clean_user] = {
        "password": clean_pass,
        "role": clean_role
    }

    all_users = load_users_store()
    custom_only = {
        u: info for u, info in all_users.items() if u not in DEFAULT_USERS
    }
    encoded_json = json.dumps(custom_only, indent=2).encode("utf-8")
    ok, err = github_put_file_bytes(USERS_FILE, encoded_json, f"Update users store ({clean_user})")
    if not ok and get_github_config() is not None:
        st.warning(err)

def authenticate(username, password):
    users = load_users_store()
    u = str(username or "").strip()
    if u in users and users[u]["password"] == password:
        return users[u]["role"]
    return None

def normalize_payment_status(raw_status):
    s = str(raw_status or "").strip().lower()
    if s == "paid":
        return "Paid"
    if s in ("partially paid", "partial paid", "partial"):
        return "Partially Paid"
    return "Pending"

def sanitize_po_dataframe(raw_df):
    """Enforces exact column names, string values, and valid payment status per column."""
    if raw_df is None or raw_df.empty:
        return pd.DataFrame(columns=COLUMNS)

    df = raw_df.copy()
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[COLUMNS].fillna("")

    for col in COLUMNS:
        df[col] = df[col].apply(lambda x: "" if str(x).strip().lower() == "nan" else str(x).strip())

    df["Payment Status"] = df["Payment Status"].apply(normalize_payment_status)
    return df

# ==========================================
# PDF & EMAIL DRAFT HELPERS
# ==========================================
def generate_po_pdf_bytes(po_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=colors.HexColor("#581c87"),
        spaceAfter=6
    )
    cell_style = ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontSize=10,
        leading=13
    )
    reason_style = ParagraphStyle(
        "ReasonText",
        parent=styles["Normal"],
        fontSize=10,
        leading=14
    )

    story = []
    story.append(Paragraph("INDIGO PARK CANADA", title_style))
    story.append(Paragraph(f"<b>PURCHASE ORDER:</b> {po_data.get('PO Number', '')}", styles["Heading2"]))
    story.append(Spacer(1, 10))

    rows_data = [
        [Paragraph("<b>Field</b>", cell_style), Paragraph("<b>Details</b>", cell_style)],
        [Paragraph("<b>PO Number</b>", cell_style), Paragraph(str(po_data.get("PO Number", "")), cell_style)],
        [Paragraph("<b>Date</b>", cell_style), Paragraph(str(po_data.get("Date", "")), cell_style)],
        [Paragraph("<b>CMO / Lot Code</b>", cell_style), Paragraph(str(po_data.get("CMO Code", "")), cell_style)],
        [Paragraph("<b>Vendor / Supplier</b>", cell_style), Paragraph(str(po_data.get("Vendor", "")), cell_style)],
        [Paragraph("<b>Category</b>", cell_style), Paragraph(str(po_data.get("Category", "")), cell_style)],
        [Paragraph("<b>Priority Level</b>", cell_style), Paragraph(str(po_data.get("Priority", "")), cell_style)],
        [Paragraph("<b>Estimated Cost ($)</b>", cell_style), Paragraph(str(po_data.get("Estimated Cost ($)", "N/A")), cell_style)],
        [Paragraph("<b>Actual Cost ($)</b>", cell_style), Paragraph(str(po_data.get("Actual Cost ($)", "N/A")), cell_style)],
        [Paragraph("<b>Requested By</b>", cell_style), Paragraph(str(po_data.get("Requested By", "")), cell_style)],
        [Paragraph("<b>Requester Email</b>", cell_style), Paragraph(str(po_data.get("Requester Email", "")), cell_style)],
        [Paragraph("<b>Supplier Email</b>", cell_style), Paragraph(str(po_data.get("Supplier Email", "")), cell_style)],
        [Paragraph("<b>Payment Status</b>", cell_style), Paragraph(str(po_data.get("Payment Status", "Pending")), cell_style)],
        [Paragraph("<b>Reason / Work Details</b>", cell_style), Paragraph(str(po_data.get("Reason", "")).replace("\n", "<br/>"), reason_style)],
    ]

    table = Table(rows_data, colWidths=[150, 380], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#581c87")),
        ("TEXTCOLOR", (0, 0), (1, 0), colors.whitesmoke),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f5fc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8b4fe")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    story.append(table)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def build_language_mailto_url(po_data, lang_code):
    """Builds a friendly mailto link strictly in EN or FR with supplier name, PO number, customer name, PDF note, and thank-you."""
    to_addr = str(po_data.get("Supplier Email", "") or "").strip()
    req_email = str(po_data.get("Requester Email", "") or "").strip()
    po_num = str(po_data.get("PO Number", "") or "").strip()
    customer_name = str(po_data.get("CMO Code", "") or "").strip()
    supplier_name = str(po_data.get("Vendor", "") or "").strip()

    if lang_code == "FR":
        subject = f"Bon de commande {po_num} - {customer_name}"
        body = (
            f"Bonjour {supplier_name},\n\n"
            f"Numéro de PO : {po_num}\n"
            f"Client : {customer_name}\n"
            f"Ci-joint le bon de commande PDF.\n\n"
            f"Merci beaucoup pour votre collaboration !"
        )
    else:
        subject = f"Purchase Order {po_num} - {customer_name}"
        body = (
            f"Hello {supplier_name},\n\n"
            f"PO Number: {po_num}\n"
            f"Customer: {customer_name}\n"
            f"See PDF PO attached.\n\n"
            f"Thank you very much for your support!"
        )

    params = {"subject": subject, "body": body}
    if req_email:
        params["cc"] = req_email
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"mailto:{urllib.parse.quote(to_addr)}?{query}"

def render_pdf_download_bar(df_source, pdf_label, select_label, key_prefix):
    po_list = df_source["PO Number"].dropna().astype(str).tolist()
    if not po_list:
        return
    st.markdown("---")
    st.markdown(f"**{pdf_label}**")
    c_pdf1, c_pdf2 = st.columns([3, 1])
    with c_pdf1:
        chosen_po = st.selectbox(select_label, po_list, key=f"{key_prefix}_select", label_visibility="collapsed")
    row_match = df_source[df_source["PO Number"].astype(str) == chosen_po]
    if not row_match.empty:
        po_dict = row_match.iloc[0].to_dict()
        pdf_bytes = generate_po_pdf_bytes(po_dict)
        with c_pdf2:
            st.download_button(
                label=f"{TEXTS[st.session_state.get('lang', 'EN')]['download_pdf_btn']} ({chosen_po})",
                data=pdf_bytes,
                file_name=f"{chosen_po}.pdf",
                mime="application/pdf",
                key=f"{key_prefix}_btn",
                use_container_width=True
            )

# ==========================================
# COST PARSER & DATA HELPERS
# ==========================================
def parse_cost_input(raw_cost):
    cleaned = str(raw_cost or "").strip().replace("$", "").replace(",", "").replace(" ", "")
    if cleaned == "" or cleaned.upper() in ("NA", "N/A", "NONE"):
        return "N/A", True
    try:
        val = float(cleaned)
        if val < 0:
            return None, False
        return f"{val:.2f}", True
    except ValueError:
        return None, False

def dataframe_to_excel_bytes(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="PO_Log")
    buf.seek(0)
    return buf.getvalue()

def load_po_data():
    gh_bytes = github_get_file_bytes(EXCEL_FILE)
    if gh_bytes:
        try:
            df = pd.read_excel(io.BytesIO(gh_bytes), dtype=str)
            clean_df = sanitize_po_dataframe(df)
            clean_df.to_excel(EXCEL_FILE, index=False)
            return clean_df
        except Exception:
            pass

    if os.path.exists(EXCEL_FILE):
        try:
            df = pd.read_excel(EXCEL_FILE, dtype=str)
            return sanitize_po_dataframe(df)
        except Exception:
            pass

    df = pd.DataFrame(columns=COLUMNS)
    df.to_excel(EXCEL_FILE, index=False)
    return df

def save_po_data(df, commit_msg="Update po_log.xlsx"):
    clean_df = sanitize_po_dataframe(df)
    clean_df.to_excel(EXCEL_FILE, index=False)

    if get_github_config() is not None:
        excel_bytes = dataframe_to_excel_bytes(clean_df)
        ok, err = github_put_file_bytes(EXCEL_FILE, excel_bytes, commit_msg)
        if not ok:
            st.warning(err)

def generate_po_number():
    today = datetime.now().strftime("%Y%m%d")
    rand_id = random.randint(1000, 9999)
    return f"PO-{today}-{rand_id}"

def query_groq_ai(query, df, missing_secret_msg):
    if df.empty:
        return "No PO records exist in the log yet."

    api_key = st.secrets.get("GROQ_API_KEY", "") if "GROQ_API_KEY" in st.secrets else ""
    if not api_key:
        return f"⚠️ {missing_secret_msg}"

    if not HAS_OPENAI:
        return "⚠️ The `openai` package is not installed. Add `openai` to `requirements.txt`."

    context_str = df.to_string(index=False)

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        prompt = f"""
        You are an operational PO search assistant for Indigo Park Canada.
        Dataset:
        {context_str}

        User Question: {query}
        Answer clearly and concisely.
        """
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Groq API Error: {str(e)}"

def filter_po_dataframe(df, query_text):
    q = str(query_text or "").strip().lower()
    if not q:
        return df
    mask = pd.Series(False, index=df.index)
    for col in COLUMNS:
        mask = mask | df[col].astype(str).str.lower().str.contains(q, na=False, regex=False)
    return df[mask]

# ==========================================
# SESSION STATE & AUTH FLOW
# ==========================================
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "auth_user" not in st.session_state:
    st.session_state.auth_user = None
if "custom_users" not in st.session_state:
    st.session_state.custom_users = {}
if "last_created_po" not in st.session_state:
    st.session_state.last_created_po = None
if "last_selected_admin_po" not in st.session_state:
    st.session_state.last_selected_admin_po = None

st.sidebar.image(INDIGO_LOGO_URL, width=200)
st.sidebar.markdown("---")
lang = st.sidebar.radio("Language / Langue", ["EN", "FR"], horizontal=True, key="lang")
t = TEXTS[lang]

if not st.session_state.user_role:
    st.title(t["login_title"])
    with st.form("login_form"):
        u_input = st.text_input(t["username"])
        p_input = st.text_input(t["password"], type="password")
        sub_login = st.form_submit_button(t["login_btn"], use_container_width=True)

        if sub_login:
            role = authenticate(u_input, p_input)
            if role:
                st.session_state.user_role = role
                st.session_state.auth_user = u_input.strip()
                st.rerun()
            else:
                st.error(t["invalid_login"])
    st.stop()

st.sidebar.markdown(f"**Logged in as:** `{st.session_state.auth_user}` ({st.session_state.user_role.upper()})")
if get_github_config() is not None:
    st.sidebar.caption("☁️ GitHub Sync: Active")
else:
    st.sidebar.caption("⚠️ GitHub Sync: Add GITHUB_TOKEN & GITHUB_REPO to Secrets")

if st.sidebar.button(t["logout_btn"], use_container_width=True):
    st.session_state.user_role = None
    st.session_state.auth_user = None
    st.rerun()

st.title(t["title"])
st.caption(t["subtitle"])

# ==========================================
# ADMIN VIEW vs REGULAR USER VIEW
# ==========================================
if st.session_state.user_role == "admin":
    tab_log, tab_ai, tab_users = st.tabs([t["history_tab"], t["ai_tab"], t["users_tab"]])

    with tab_log:
        st.subheader(t["admin_audit_title"])
        df = load_po_data()

        if df.empty:
            st.info("No PO records found.")
        else:
            search_q = st.text_input(t["search_label"], "")
            filtered_df = filter_po_dataframe(df, search_q)

            g_pending, g_partial, g_paid = st.tabs([
                f"⏳ Pending ({len(filtered_df[filtered_df['Payment Status'] == 'Pending'])})",
                f"🌓 Partially Paid ({len(filtered_df[filtered_df['Payment Status'] == 'Partially Paid'])})",
                f"✅ Paid ({len(filtered_df[filtered_df['Payment Status'] == 'Paid'])})"
            ])

            with g_pending:
                st.dataframe(
                    filtered_df[filtered_df["Payment Status"] == "Pending"],
                    use_container_width=True
                )
            with g_partial:
                st.dataframe(
                    filtered_df[filtered_df["Payment Status"] == "Partially Paid"],
                    use_container_width=True
                )
            with g_paid:
                st.dataframe(
                    filtered_df[filtered_df["Payment Status"] == "Paid"],
                    use_container_width=True
                )

            st.markdown("---")
            st.markdown("### Update PO & Assign Category")
            all_po_list = df["PO Number"].dropna().astype(str).tolist()

            if all_po_list:
                c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
                with c1:
                    selected_po = st.selectbox("Select PO Number", all_po_list, key="admin_update_po_select")

                current_row = df[df["PO Number"].astype(str) == selected_po].iloc[0]
                current_actual = str(current_row.get("Actual Cost ($)", "")).strip()
                default_actual = "" if current_actual.upper() in ("", "N/A", "NA", "NONE") else current_actual

                if st.session_state.last_selected_admin_po != selected_po:
                    st.session_state.last_selected_admin_po = selected_po
                    st.session_state.admin_actual_cost_in = default_actual

                with c2:
                    actual_cost_in = st.text_input(
                        t["actual_cost_label"],
                        placeholder="e.g. 450.00 or NA",
                        key="admin_actual_cost_in"
                    )
                with c3:
                    category_options = ["— Select Category —"] + PAYMENT_CATEGORIES
                    chosen_category = st.selectbox(
                        t["payment_status_label"],
                        category_options,
                        index=0,
                        key="admin_payment_cat_select"
                    )
                with c4:
                    st.markdown("<div style='padding-top: 25px;'></div>", unsafe_allow_html=True)
                    if st.button(t["update_po_btn"], use_container_width=True, key="admin_update_po_btn"):
                        parsed_act, act_ok = parse_cost_input(actual_cost_in)
                        if chosen_category not in PAYMENT_CATEGORIES:
                            st.error(t["select_category_err"])
                        elif not act_ok:
                            st.error(t["invalid_cost"])
                        else:
                            idx = df[df["PO Number"].astype(str) == selected_po].index
                            if not idx.empty:
                                df.loc[idx, "Actual Cost ($)"] = parsed_act
                                df.loc[idx, "Payment Status"] = chosen_category
                                save_po_data(df, f"Update {selected_po} -> {chosen_category}")
                                st.success(f"Updated {selected_po} -> {chosen_category}")
                                st.rerun()

                render_pdf_download_bar(
                    filtered_df if not filtered_df.empty else df,
                    t["pdf_section"],
                    t["select_po_pdf"],
                    "admin_po_pdf"
                )

    with tab_ai:
        st.subheader(t["ai_tab"])
        ai_query = st.text_input(t["ai_header"], placeholder=t["ai_placeholder"])
        if st.button(t["ai_search_btn"], use_container_width=True):
            if ai_query:
                df = load_po_data()
                with st.spinner("Analyzing POs..."):
                    st.markdown(query_groq_ai(ai_query, df, t["missing_secret"]))

    with tab_users:
        st.subheader(t["create_user_header"])
        with st.form("create_user_form", clear_on_submit=True):
            u_col1, u_col2, u_col3 = st.columns(3)
            with u_col1:
                new_uname = st.text_input(t["new_username_label"])
            with u_col2:
                new_upass = st.text_input(t["new_password_label"], type="password")
            with u_col3:
                new_urole = st.selectbox(t["new_role_label"], ["user", "admin"])

            create_sub = st.form_submit_button(t["create_user_btn"], use_container_width=True)
            if create_sub:
                clean_u = new_uname.strip()
                clean_p = new_upass.strip()
                all_existing = load_users_store()
                if not clean_u or not clean_p:
                    st.error(t["user_fields_err"])
                elif clean_u in all_existing:
                    st.error(t["user_exists_err"])
                else:
                    create_user_account(clean_u, clean_p, new_urole)
                    st.success(f"{t['user_created_msg']} `{clean_u}` ({new_urole})")

        st.markdown("---")
        st.markdown(f"**{t['existing_users_header']}**")
        users_snapshot = load_users_store()
        users_table = pd.DataFrame([
            {"Username": u, "Role": info["role"]}
            for u, info in users_snapshot.items()
        ])
        st.dataframe(users_table, use_container_width=True)

else:
    tab1, tab2 = st.tabs([t["new_po_tab"], t["history_tab"]])

    with tab1:
        st.subheader(t["po_details"])
        with st.form("user_po_form"):
            col1, col2 = st.columns(2)

            with col1:
                cmo_code = st.text_input(t["cmo_code"], placeholder="e.g. CMO-1851").upper()

                vendor_choice = st.selectbox(
                    t["service_provider"],
                    [
                        "Logic Control", "Amano", "Stanley / Door Automation",
                        "HVAC / Climate Controls", "Elevator Service",
                        "Electrical / Lighting", "Plumbing", "Other"
                    ]
                )
                vendor_other = ""
                if vendor_choice == "Other":
                    vendor_other = st.text_input(t["vendor_other_label"])

                cat_choice = st.selectbox(
                    t["category"],
                    [
                        "Gate & Equipment Repair", "Software / Network Call",
                        "HVAC Maintenance", "General Repairs", "Emergency Fix",
                        "Other"
                    ]
                )
                cat_other = ""
                if cat_choice == "Other":
                    cat_other = st.text_input(t["cat_other_label"])

                requester_email = st.text_input(t["user_email"], placeholder="you@company.com")

            with col2:
                priority = st.select_slider(t["priority"], options=["Normal", "Urgent", "Emergency"])
                est_cost_raw = st.text_input(t["est_cost"], value="NA")
                supplier_email = st.text_input(t["supplier_email"], placeholder="vendor@supplier.com")
                requested_by = st.text_input(t["requested_by"], value=st.session_state.auth_user)

            work_reason = st.text_area(t["work_reason"])

            sub_gen = st.form_submit_button(t["generate_btn"], use_container_width=True)

        if sub_gen:
            final_vendor = vendor_other if vendor_choice == "Other" else vendor_choice
            final_cat = cat_other if cat_choice == "Other" else cat_choice
            parsed_cost, cost_ok = parse_cost_input(est_cost_raw)

            if not cmo_code or not work_reason or not requested_by or not final_vendor:
                st.error("Please fill in CMO Code, Vendor, Reason, and Requested By.")
            elif not cost_ok:
                st.error(t["invalid_cost"])
            else:
                po_num = generate_po_number()
                date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

                new_record = {
                    "PO Number": po_num,
                    "Date": date_str,
                    "CMO Code": cmo_code,
                    "Vendor": final_vendor,
                    "Category": final_cat,
                    "Priority": priority,
                    "Estimated Cost ($)": parsed_cost,
                    "Actual Cost ($)": "N/A",
                    "Requester Email": requester_email.strip(),
                    "Supplier Email": supplier_email.strip(),
                    "Reason": work_reason,
                    "Requested By": requested_by,
                    "Payment Status": "Pending"
                }

                df = load_po_data()
                df = pd.concat([pd.DataFrame([new_record]), df], ignore_index=True)
                save_po_data(df, f"Add {po_num}")

                pdf_bytes = generate_po_pdf_bytes(new_record)
                st.session_state.last_created_po = {
                    "record": new_record,
                    "pdf_bytes": pdf_bytes
                }
                st.success(f"{t['success_msg']} **PO #: {po_num}**")

        if st.session_state.last_created_po:
            created_rec = st.session_state.last_created_po["record"]
            created_pdf = st.session_state.last_created_po["pdf_bytes"]
            st.markdown("---")
            st.info(t["draft_note"])
            b_col1, b_col2 = st.columns(2)
            with b_col1:
                st.download_button(
                    label=f"{t['download_pdf_btn']} ({created_rec['PO Number']})",
                    data=created_pdf,
                    file_name=f"{created_rec['PO Number']}.pdf",
                    mime="application/pdf",
                    key="re_dl_created_pdf",
                    use_container_width=True
                )
            with b_col2:
                mailto_href = build_language_mailto_url(created_rec, lang)
                st.link_button(
                    label=t["open_email_btn"],
                    url=mailto_href,
                    use_container_width=True
                )

    with tab2:
        st.subheader(t["history_tab"])
        df = load_po_data()
        if not df.empty:
            user_search = st.text_input(t["search_label"], "", key="user_log_search")
            user_filtered_df = filter_po_dataframe(df, user_search)
            st.dataframe(user_filtered_df, use_container_width=True)

            po_list = df["PO Number"].dropna().astype(str).tolist()
            if po_list:
                st.markdown("---")
                st.markdown(f"**{t['delete_section']}**")
                c_del1, c_del2 = st.columns([3, 1])
                with c_del1:
                    po_del = st.selectbox(t["select_po_delete"], po_list, label_visibility="collapsed")
                with c_del2:
                    if st.button(t["delete_po_btn"], use_container_width=True):
                        updated_df = df[df["PO Number"].astype(str) != po_del].reset_index(drop=True)
                        save_po_data(updated_df, f"Erase {po_del}")
                        st.success(f"{t['po_erased_msg']} {po_del}")
                        st.rerun()

            render_pdf_download_bar(
                user_filtered_df if not user_filtered_df.empty else df,
                t["pdf_section"],
                t["select_po_pdf"],
                "user_po_pdf"
            )
