import io
import os
import random
import urllib.parse
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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
    page_title="Indigo Park Canada - PO Management System",
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
        "subtitle": "Create, log, export PDF, and audit Purchase Orders for service calls",
        "login_title": "🔐 Login to Indigo PO Portal",
        "username": "Username",
        "password": "Password",
        "login_btn": "Sign In",
        "logout_btn": "Sign Out",
        "invalid_login": "Invalid username or password.",
        "invalid_cost": "Please enter a valid non-negative number or NA.",
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
        "search_label": "Filter by CMO Code or Vendor:",
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
        "admin_audit_title": "⚙️ Admin Audit & Payment Management",
        "actual_cost_label": "Actual Cost ($ CAD)",
        "payment_status_label": "Payment Status",
        "update_po_btn": "Update PO Status & Actual Amount",
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
        "invalid_cost": "Veuillez entrer un montant positif valide ou NA.",
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
        "search_label": "Filtrer par code CMO ou fournisseur:",
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
        "admin_audit_title": "⚙️ Audit Admin & Gestion des Paiements",
        "actual_cost_label": "Coût Réel ($ CAD)",
        "payment_status_label": "Statut du Paiement",
        "update_po_btn": "Mettre à jour le PO",
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
INDIGO_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Indigo_Group_logo.svg/320px-Indigo_Group_logo.svg.png"

DEFAULT_USERS = {
    "user": {"password": "user123", "role": "user"},
    "admin": {"password": "admin123", "role": "admin"}
}

# ==========================================
# GOOGLE SHEETS & USER MANAGEMENT HELPERS
# ==========================================
def get_gsheet_spreadsheet():
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
        return client.open_by_key(str(sheet_id).strip())
    except Exception:
        return None

def get_gsheet_worksheet(title="PO_Log", headers=COLUMNS):
    spreadsheet = get_gsheet_spreadsheet()
    if spreadsheet is None:
        return None
    try:
        try:
            return spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=16)
            ws.append_row(headers)
            return ws
    except Exception:
        return None

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

    ws_users = get_gsheet_worksheet("Users", ["Username", "Password", "Role"])
    if ws_users is not None:
        try:
            for row in ws_users.get_all_records():
                uname = str(row.get("Username", "")).strip()
                pwd = str(row.get("Password", "")).strip()
                role = str(row.get("Role", "user")).strip().lower() or "user"
                if uname and pwd:
                    users[uname] = {"password": pwd, "role": role}
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

    ws_users = get_gsheet_worksheet("Users", ["Username", "Password", "Role"])
    if ws_users is not None:
        all_users = load_users_store()
        rows = [["Username", "Password", "Role"]] + [
            [u, info["password"], info["role"]] for u, info in all_users.items()
        ]
        ws_users.clear()
        ws_users.update(rows)

def authenticate(username, password):
    users = load_users_store()
    u = str(username or "").strip()
    if u in users and users[u]["password"] == password:
        return users[u]["role"]
    return None

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
    """Builds a mailto link strictly in EN or FR with PO number, customer/CMO name, and PDF attached note."""
    to_addr = str(po_data.get("Supplier Email", "") or "").strip()
    req_email = str(po_data.get("Requester Email", "") or "").strip()
    po_num = str(po_data.get("PO Number", "") or "").strip()
    customer_name = str(po_data.get("CMO Code", "") or "").strip()

    if lang_code == "FR":
        subject = f"Bon de commande {po_num} - {customer_name}"
        body = (
            f"Numéro de PO : {po_num}\n"
            f"Client : {customer_name}\n"
            f"Ci-joint le bon de commande PDF."
        )
    else:
        subject = f"Purchase Order {po_num} - {customer_name}"
        body = (
            f"PO Number: {po_num}\n"
            f"Customer: {customer_name}\n"
            f"See PDF PO attached."
        )

    params = {"subject": subject, "body": body}
    if req_email:
        params["cc"] = req_email
    query = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"mailto:{urllib.parse.quote(to_addr)}?{query}"

def render_email_link_button(po_data, lang_code, link_label):
    """Renders a direct top-level mailto link only (no automatic PDF download)."""
    mailto_href = build_language_mailto_url(po_data, lang_code)
    html_link = f"""
    <div style="width: 100%;">
      <a href="{mailto_href}" target="_top"
         style="display: block; width: 100%; text-align: center; background-color: #581c87;
                color: #ffffff; font-weight: bold; text-decoration: none;
                padding: 0.52rem 1rem; border-radius: 8px; box-sizing: border-box;
                font-family: sans-serif; font-size: 0.95rem;">
        {link_label}
      </a>
    </div>
    """
    components.html(html_link, height=52)

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

def load_po_data():
    ws = get_gsheet_worksheet("PO_Log", COLUMNS)
    if ws is not None:
        try:
            records = ws.get_all_records()
            if not records:
                return pd.DataFrame(columns=COLUMNS)
            df = pd.DataFrame(records, dtype=str)
            for col in COLUMNS:
                if col not in df.columns:
                    df[col] = ""
            return df[COLUMNS]
        except Exception:
            pass

    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE, dtype=str)
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df[COLUMNS]

    df = pd.DataFrame(columns=COLUMNS)
    df.to_excel(EXCEL_FILE, index=False)
    return df

def save_po_data(df):
    clean_df = df[COLUMNS].copy() if not df.empty else pd.DataFrame(columns=COLUMNS)
    clean_df = clean_df.astype(str)
    clean_df.to_excel(EXCEL_FILE, index=False)

    ws = get_gsheet_worksheet("PO_Log", COLUMNS)
    if ws is not None:
        ws.clear()
        rows = [COLUMNS] + clean_df.fillna("").values.tolist()
        ws.update(rows)

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
            search_q = st.text_input(t["search_label"], "").upper()
            filtered_df = (
                df[
                    df["CMO Code"].astype(str).str.contains(search_q, na=False)
                    | df["Vendor"].astype(str).str.contains(search_q, case=False, na=False)
                ]
                if search_q else df
            )

            st.dataframe(filtered_df, use_container_width=True)

            st.markdown("---")
            st.markdown("### Update Status & Actual Amount")
            po_list = filtered_df["PO Number"].dropna().astype(str).tolist()

            if po_list:
                c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
                with c1:
                    selected_po = st.selectbox("Select PO Number", po_list)
                with c2:
                    actual_cost_in = st.text_input(t["actual_cost_label"], value="", placeholder="e.g. 450.00 or NA")
                with c3:
                    pay_status = st.radio(
                        t["payment_status_label"],
                        ["Pending", "Partial Paid", "Paid"],
                        horizontal=True
                    )
                with c4:
                    st.markdown("<div style='padding-top: 25px;'></div>", unsafe_allow_html=True)
                    if st.button(t["update_po_btn"], use_container_width=True):
                        parsed_act, act_ok = parse_cost_input(actual_cost_in)
                        if not act_ok:
                            st.error("Invalid actual cost format.")
                        else:
                            idx = df[df["PO Number"].astype(str) == selected_po].index
                            if not idx.empty:
                                df.loc[idx, "Actual Cost ($)"] = parsed_act
                                df.loc[idx, "Payment Status"] = pay_status
                                save_po_data(df)
                                st.success(f"Updated {selected_po} successfully!")
                                st.rerun()

                render_pdf_download_bar(
                    df,
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
                save_po_data(df)

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
                render_email_link_button(
                    created_rec,
                    lang,
                    t["open_email_btn"]
                )

    with tab2:
        st.subheader(t["history_tab"])
        df = load_po_data()
        if not df.empty:
            st.dataframe(df, use_container_width=True)

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
                        save_po_data(updated_df)
                        st.success(f"{t['po_erased_msg']} {po_del}")
                        st.rerun()

            render_pdf_download_bar(
                df,
                t["pdf_section"],
                t["select_po_pdf"],
                "user_po_pdf"
            )
