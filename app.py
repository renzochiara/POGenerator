import os
import random
from datetime import datetime
import pandas as pd
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# PAGE CONFIG & TRANSLATIONS
# ==========================================
st.set_page_config(
    page_title="Indigo PO Generator",
    page_icon="🎫",
    layout="wide"
)

# Text Dictionary for EN / FR
TEXTS = {
    "EN": {
        "title": "Indigo Parking - Service Call PO Generator",
        "subtitle": "Create, track, and email Purchase Orders for service calls (Logic Control, HVAC, Gates, etc.)",
        "new_po_tab": "➕ Create New PO",
        "history_tab": "📋 PO History & Excel Log",
        "settings_tab": "⚙️ Email & System Settings",
        "po_details": "PO General Details",
        "cmo_code": "CMO / Parking Lot Code",
        "service_provider": "Service Provider / Vendor",
        "work_reason": "Reason for Service Call / Work Details",
        "category": "Maintenance Category",
        "priority": "Priority Level",
        "est_cost": "Estimated Cost ($ CAD)",
        "requested_by": "Requested By (Your Name)",
        "approver_email": "Send Auto Email To (Comma separated)",
        "generate_btn": "Generate PO & Send Notifications",
        "success_msg": "PO Generated and Logged Successfully!",
        "email_success": "Notification email sent successfully!",
        "email_error": "Failed to send background email: ",
        "search_label": "Filter by CMO Code or Vendor:",
        "download_excel": "📥 Download Full PO Log (Excel)",
        "po_number": "PO Number",
        "date": "Date",
        "status": "Status",
        "actions": "Actions"
    },
    "FR": {
        "title": "Indigo Parking - Générateur de Bons de Commande (PO)",
        "subtitle": "Créer, suivre et envoyer des bons de commande pour appels de service (Logic Control, HVAC, Barrières, etc.)",
        "new_po_tab": "➕ Créer un PO",
        "history_tab": "📋 Historique & Registre Excel",
        "settings_tab": "⚙️ Configuration Courriel",
        "po_details": "Détails du Bon de Commande",
        "cmo_code": "Code CMO / Code du Stationnement",
        "service_provider": "Fournisseur de Service / Vendeur",
        "work_reason": "Raison de l'appel de service / Détails du travail",
        "category": "Catégorie d'entretien",
        "priority": "Niveau de Priorité",
        "est_cost": "Coût Estimé ($ CAD)",
        "requested_by": "Demandé par (Votre nom)",
        "approver_email": "Envoyer courriel auto à (Séparés par virgule)",
        "generate_btn": "Générer le PO et envoyer les notifications",
        "success_msg": "PO généré et enregistré avec succès!",
        "email_success": "Courriel de notification envoyé avec succès!",
        "email_error": "Échec de l'envoi du courriel: ",
        "search_label": "Filtrer par code CMO ou fournisseur:",
        "download_excel": "📥 Télécharger le registre complet (Excel)",
        "po_number": "Numéro de PO",
        "date": "Date",
        "status": "Statut",
        "actions": "Actions"
    }
}

EXCEL_FILE = "po_log.xlsx"

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def load_po_data():
    """Loads existing PO data from Excel or creates a new DataFrame."""
    if os.path.exists(EXCEL_FILE):
        return pd.read_excel(EXCEL_FILE)
    else:
        columns = ["PO Number", "Date", "CMO Code", "Vendor", "Category", "Priority", "Estimated Cost", "Reason", "Requested By", "Status"]
        df = pd.DataFrame(columns=columns)
        df.to_excel(EXCEL_FILE, index=False)
        return df

def save_po_data(df):
    """Saves DataFrame to Excel."""
    df.to_excel(EXCEL_FILE, index=False)

def generate_po_number():
    """Generates a standard PO-YYYYMMDD-XXXX number."""
    today = datetime.now().strftime("%Y%m%d")
    rand_id = random.randint(1000, 9999)
    return f"PO-{today}-{rand_id}"

def send_background_email(recipient_list, po_data):
    """Sends background notification email via SMTP using Secrets."""
    # Read email credentials from Streamlit Secrets or Environment
    smtp_server = st.secrets.get("SMTP_SERVER", "smtp.office365.com")
    smtp_port = int(st.secrets.get("SMTP_PORT", 587))
    sender_email = st.secrets.get("SENDER_EMAIL", "")
    sender_password = st.secrets.get("SENDER_PASSWORD", "")

    if not sender_email or not sender_password:
        return False, "Email credentials not configured in secrets.toml"

    subject = f"[Indigo PO] {po_data['PO Number']} - {po_data['CMO Code']} - {po_data['Vendor']}"
    
    body = f"""
    PURCHASE ORDER NOTIFICATION - INDIGO PARKING
    --------------------------------------------------
    PO Number:        {po_data['PO Number']}
    Date:             {po_data['Date']}
    CMO / Lot Code:   {po_data['CMO Code']}
    Service Vendor:   {po_data['Vendor']}
    Category:         {po_data['Category']}
    Priority:         {po_data['Priority']}
    Est. Cost:        ${po_data['Estimated Cost']:.2f} CAD
    Requested By:     {po_data['Requested By']}
    
    Work Description / Reason:
    {po_data['Reason']}
    --------------------------------------------------
    This is an automated operational notification.
    """

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = ", ".join([e.strip() for e in recipient_list])
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True, None
    except Exception as e:
        return False, str(e)

# ==========================================
# APP LAYOUT & LOGIC
# ==========================================

# Sidebar Controls
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Indigo_Group_logo.svg/320px-Indigo_Group_logo.svg.png", width=160)
lang = st.sidebar.radio("Language / Langue", ["EN", "FR"], horizontal=True)
t = TEXTS[lang]

st.title(t["title"])
st.caption(t["subtitle"])

tab1, tab2, tab3 = st.tabs([t["new_po_tab"], t["history_tab"], t["settings_tab"]])

# --- TAB 1: NEW PO FORM ---
with tab1:
    st.subheader(t["po_details"])
    
    with st.form("po_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            cmo_code = st.text_input(t["cmo_code"], placeholder="e.g. CMO-1851, Forum, Medifice").upper()
            vendor = st.selectbox(t["service_provider"], ["Logic Control", "Amano", "Stanley / Door Automation", "HVAC / Climate Controls", "Elevator Service", "Electrical / Lighting", "Plumbing", "Other"])
            if vendor == "Other":
                vendor = st.text_input("Specify Vendor Name")
            
            category = st.selectbox(t["category"], ["Gate & Equipment Repair", "Software / Network Call", "HVAC Maintenance", "General Repairs", "Emergency Security Fix"])
        
        with col2:
            priority = st.select_slider(t["priority"], options=["Normal", "Urgent", "Emergency"])
            est_cost = st.number_input(t["est_cost"], min_value=0.0, step=50.0, value=0.0)
            requested_by = st.text_input(t["requested_by"], value="")
            recipients = st.text_input(t["approver_email"], help="Enter emails separated by commas to notify automatically")
        
        work_reason = st.text_area(t["work_reason"], placeholder="Detail why logic control or vendor was called out...")
        
        submit_btn = st.form_submit_button(t["generate_btn"], use_container_width=True)

    if submit_btn:
        if not cmo_code or not work_reason or not requested_by:
            st.error("Please fill in CMO Code, Reason for Work, and Requested By.")
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
                "Estimated Cost": est_cost,
                "Reason": work_reason,
                "Requested By": requested_by,
                "Status": "Pending Follow-up"
            }
            
            # Save to Excel File
            df = load_po_data()
            df = pd.concat([pd.DataFrame([new_record]), df], ignore_index=False)
            save_po_data(df)
            
            st.success(f"{t['success_msg']} **PO #: {po_num}**")
            
            # Trigger email if recipients added
            if recipients:
                email_list = recipients.split(",")
                success, err = send_background_email(email_list, new_record)
                if success:
                    st.info(t["email_success"])
                else:
                    st.warning(f"{t['email_error']} {err}")

# --- TAB 2: PO HISTORY & LOG ---
with tab2:
    st.subheader(t["history_tab"])
    
    df = load_po_data()
    
    if df.empty:
        st.info("No PO records found yet.")
    else:
        # Search filter
        search_query = st.text_input(t["search_label"], "").upper()
        if search_query:
            filtered_df = df[df["CMO Code"].str.contains(search_query, na=False) | df["Vendor"].str.contains(search_query, case=False, na=False)]
        else:
            filtered_df = df
            
        st.dataframe(filtered_df, use_container_width=True)
        
        # Excel Export Button
        excel_data = pd.ExcelWriter(EXCEL_FILE, engine='openpyxl')
        
        with open(EXCEL_FILE, "rb") as file:
            st.download_button(
                label=t["download_excel"],
                data=file,
                file_name=f"Indigo_PO_Log_{datetime.now().strftime('%Y%m%m')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# --- TAB 3: SETTINGS INSTRUCTIONS ---
with tab3:
    st.subheader(t["settings_tab"])
    st.markdown("""
    ### How to configure automatic emails on Streamlit Cloud:
    To enable background emails when a PO is created, set your SMTP credentials in your Streamlit App **Secrets Manager**:
    
    ```toml
    SMTP_SERVER = "smtp.office365.com"
    SMTP_PORT = 587
    SENDER_EMAIL = "your-email@indigo.com"
    SENDER_PASSWORD = "your-app-password"
    ```
    """)
