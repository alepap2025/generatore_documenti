import streamlit as st
import pandas as pd
import json
import time
import logging
import os
import subprocess
import io
import shutil
import re
from string import Template
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm

# Configurazione del logging
logging.basicConfig(filename=r'C:\Users\Francesco\python\nis2_doc_log.txt', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# CSS per estetica test
st.markdown("""
<style>
    .main { background-color: #F5F5F5; }
    .stButton>button {
        background-color: #3498DB;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 16px;
        transition: all 0.3s;
    }
    .stButton>button:hover { background-color: #2980B9; }
    .stTextInput>div>input, .stSelectbox>div>select {
        border: 2px solid #2C3E50;
        border-radius: 8px;
        padding: 8px;
    }
    .stSidebar {
        background-color: #2C3E50;
        color: white;
        padding: 20px;
    }
    .stSidebar .stButton>button {
        background-color: #1ABC9C;
        border-radius: 8px;
        width: 100%;
        margin-bottom: 10px;
    }
    .stSidebar .stButton>button:hover { background-color: #16A085; }
    .header-logo { text-align: center; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# Inizializzazione stato sessione
if 'step' not in st.session_state:
    st.session_state.step = "Home"
    st.session_state.cliente = {
        "ragione_sociale": "",
        "contatto": "",
        "ciso_nome": "",
        "ciso_codice_fiscale": "",
        "data": time.strftime("%d/%m/%Y"),
        "sede_legale": "",
        "p_iva": ""
    }
    st.session_state.rischi = [
        {"minaccia": "Incendio", "verosimiglianza": "3", "parametri": "ID", "rischio": "24", "mitigazione": ""},
        {"minaccia": "Intercettazione", "verosimiglianza": "2", "parametri": "R", "rischio": "24", "mitigazione": ""},
        {"minaccia": "Furto di documenti", "verosimiglianza": "2", "parametri": "R", "rischio": "24", "mitigazione": ""}
    ]
    st.session_state.checklist = [
        {"controllo": "Politiche per la sicurezza delle informazioni", "valore": "1", "rischio": "9", "stato": "Non iniziato"},
        {"controllo": "Nomina CISO", "valore": "3", "rischio": "18", "stato": "Non iniziato"},
        {"controllo": "Piano di risposta agli incidenti", "valore": "1", "rischio": "36", "stato": "Non iniziato"}
    ]
    st.session_state.template_data = {}
    st.session_state.pdf_data = {}
    st.session_state.latex_content = None  # Per memorizzare il file .tex

# Funzione per caricare i clienti salvati
def load_clienti():
    try:
        if os.path.exists(r"C:\Users\Francesco\python\nis2_clienti.json"):
            with open(r"C:\Users\Francesco\python\nis2_clienti.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Errore caricamento clienti: {str(e)}")
    return []

# Funzione per salvare i clienti
def save_clienti(clienti):
    try:
        with open(r"C:\Users\Francesco\python\nis2_clienti.json", "w", encoding="utf-8") as f:
            json.dump(clienti, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Errore salvataggio clienti: {str(e)}")

# Logo nis2lab
st.markdown("<div class='header-logo'>", unsafe_allow_html=True)
if os.path.exists(r"C:\Users\Francesco\python\nis2lab_logo.png"):
    st.image(r"C:\Users\Francesco\python\nis2lab_logo.png", width=250)
else:
    st.markdown("<h1 style='color: #2C3E50;'>NIS2Lab</h1>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# Funzione per sanificare i dati LaTeX
def sanitize_latex(text):
    if not text:
        return ""
    text = str(text)
    # Escape caratteri speciali LaTeX e problematici per string.Template
    text = re.sub(r'[\\{}%&^#_$[\]]', r'\\\g<0>', text)
    text = text.replace('\n', ' ')
    # Rimuovi caratteri non ASCII problematici
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text

# Template LaTeX (definito globalmente)
LATEX_TEMPLATE = r"""
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{graphicx}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{xcolor}

\geometry{margin=2cm}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\small \detokenize{${ragione_sociale}} --- Data: \detokenize{${data}} --- Pagina \thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0.4pt}

\definecolor{bluscuro}{HTML}{2C3E50}

\begin{document}

% Logo
\begin{center}
    \IfFileExists{nis2lab_logo.png}{\includegraphics[width=6cm]{nis2lab_logo.png}}{\textbf{NIS2Lab}}
    \vspace{0.5cm}
\end{center}

% Intestazione
\begin{center}
    \textbf{\Large Atto di Nomina del Responsabile della Sicurezza Informatica (CISO)} \\
    \vspace{0.5cm}
    \textbf{\detokenize{${ragione_sociale}}} \\
    Sede Legale: \detokenize{${sede_legale}} \\
    P.IVA: \detokenize{${p_iva}} \\
    \vspace{0.3cm}
    Data: \detokenize{${data}}
\end{center}

\vspace{1cm}

% Preambolo
\section*{Preambolo}
\color{bluscuro}
\noindent
\textbf{VISTO:}
\begin{itemize}
    \item La Direttiva (UE) 2022/2555 del Parlamento europeo e del Consiglio del 14 dicembre 2022 (NIS2), che impone misure per un livello elevato di cibersicurezza nell'Unione;
    \item Il Regolamento (UE) 2016/679 (GDPR), relativo alla protezione dei dati personali;
    \item Il Decreto Legislativo 30 giugno 2003, n. 196, come modificato dal D.lgs. 101/2018, recante il Codice in materia di protezione dei dati personali;
    \item Il Decreto Legislativo 82/2005 (Codice dell’Amministrazione Digitale), articolo 51, sulla sicurezza dei dati e delle infrastrutture;
    \item La Strategia nazionale di cybersicurezza 2022-2026, adottata con DPCM del 17 maggio 2022;
    \item La norma UNI 11621-4:2024, che definisce i requisiti per il Responsabile della Sicurezza Informatica;
    \item La necessità di garantire la tutela del patrimonio informativo aziendale e la continuità dei servizi.
\end{itemize}

\noindent
\textbf{RITENUTO:}
\begin{itemize}
    \item Che la nomina di un Responsabile della Sicurezza Informatica (CISO) è necessaria per adempiere agli obblighi normativi e rafforzare la governance di sicurezza;
    \item Che il Sig./la Sig.ra \detokenize{${ciso_nome}}, codice fiscale \detokenize{${ciso_codice_fiscale}}, possiede le competenze richieste per il ruolo, in conformità alla norma UNI 11621-4:2024.
\end{itemize}

\vspace{0.5cm}

% Oggetto
\section*{Oggetto}
\color{black}
\par
\noindent
\begin{flushleft}
    Con il presente atto, \detokenize{${ragione_sociale}}, con sede legale in \detokenize{${sede_legale}}, P.IVA \detokenize{${p_iva}}, nomina formalmente il Sig./la Sig.ra \textbf{\detokenize{${ciso_nome}}}, codice fiscale \detokenize{${ciso_codice_fiscale}}, come Responsabile della Sicurezza Informatica (CISO), ai sensi dell’articolo 21 della Direttiva NIS2.
\end{flushleft}

\vspace{0.5cm}

% Responsabilità
\section*{Responsabilità del CISO}
\color{bluscuro}
\noindent
Il CISO avrà le seguenti responsabilità, in conformità alla Direttiva NIS2, al GDPR, alla norma UNI 11621-4:2024, e alle normative vigenti:

\begin{tabularx}{\textwidth}{cX}
    \toprule
    \textbf{N.} & \textbf{Responsabilità} \\
    \midrule
    1 & Definizione, redazione e aggiornamento delle politiche e procedure di sicurezza informatica, in linea con ISO/IEC 27001 e NIS2. \\
    2 & Pianificazione e implementazione di strategie per la gestione dei rischi informatici, secondo metodologie standard (es. NIST, ISO 27005). \\
    3 & Monitoraggio continuo delle minacce alla sicurezza e delle vulnerabilità dei sistemi, con redazione di rapporti periodici. \\
    4 & Supervisione delle misure tecniche e organizzative per la protezione dei dati, inclusi autenticazione, crittografia e controllo accessi. \\
    5 & Gestione della risposta agli incidenti di sicurezza, con notifiche al CSIRT entro 24 ore e coordinamento delle indagini post-incidente. \\
    6 & Progettazione e attuazione di programmi di formazione e sensibilizzazione del personale sulla sicurezza informatica. \\
    7 & Collaborazione con l’Agenzia per la Cybersicurezza Nazionale (ACN), il CSIRT Italia e altre autorità per segnalazioni e audit. \\
    8 & Garanzia della conformità a GDPR, NIS2, D.lgs. 196/2003 e altre normative applicabili, con redazione di documentazione di supporto. \\
    9 & Coordinamento con fornitori e partner per la sicurezza della supply chain, inclusa la verifica di clausole contrattuali di cybersecurity. \\
    10 & Sviluppo e monitoraggio di indicatori chiave di sicurezza (KPI) e gestione del budget per la sicurezza informatica. \\
    11 & Valutazione e implementazione di misure per la resilienza dei sistemi critici, inclusi piani di disaster recovery e continuità operativa. \\
    12 & Analisi della threat intelligence per anticipare e mitigare rischi emergenti. \\
    13 & Gestione delle certificazioni di sicurezza (es. ISO 27001, CIS) e audit interni. \\
    14 & Supervisione delle attività di penetration testing e vulnerability assessment. \\
    15 & Promozione di una cultura della sicurezza all’interno dell’organizzazione. \\
    \bottomrule
\end{tabularx}

\vspace{0.5cm}

% Competenze
\section*{Competenze del CISO}
\color{bluscuro}
\noindent
Il CISO possiede le seguenti competenze, in conformità alla norma UNI 11621-4:2024:

\begin{tabularx}{\textwidth}{lX}
    \toprule
    \textbf{Competenza} & \textbf{Livello e-CF} \\
    \midrule
    Sviluppo della Strategia della Sicurezza Informatica & 5 \\
    Gestione del Rischio & 4 \\
    Gestione della Sicurezza dell’Informazione & 4 \\
    Miglioramento del Processo & 4 \\
    Gestione del Progetto e del Portfolio & 4 \\
    \bottomrule
\end{tabularx}

\vspace{0.5cm}

% Durata e revoca
\section*{Durata e Revoca}
\color{black}
\noindent
La nomina ha durata indeterminata e può essere revocata con decisione del rappresentante legale di \detokenize{${ragione_sociale}}, previa comunicazione scritta al nominato con preavviso di 30 giorni.

\vspace{0.5cm}

% Disposizioni finali
\section*{Disposizioni Finali}
\color{black}
\noindent
Il presente atto entra in vigore in data \detokenize{${data}}. Il Sig./la Sig.ra \detokenize{${ciso_nome}} accetta formalmente la nomina apponendo la propria firma. Il presente documento sarà trasmesso per conoscenza agli organi interni competenti e pubblicato, se richiesto, secondo le normative vigenti.

\vspace{1cm}

% Firme
\section*{Firme}
\color{bluscuro}
\begin{tabularx}{\textwidth}{XX}
    \hline
    \textbf{Rappresentante Legale} & \textbf{\detokenize{${ciso_nome}} (CISO)} \\
    \vspace{2cm} \hrule & \vspace{2cm} \hrule \\
\end{tabularx}

\end{document}
"""

# Funzione per generare PDF con LaTeX
def genera_pdf_latex(template_name, data):
    # Validazione dei dati
    required_fields = ["ragione_sociale", "sede_legale", "p_iva", "data", "ciso_nome", "ciso_codice_fiscale"]
    for field in required_fields:
        if not data.get(field) or data[field].strip() == "":
            logging.error(f"Campo mancante o vuoto: {field}")
            raise ValueError(f"Il campo '{field.replace('_', ' ').title()}' è obbligatorio e non può essere vuoto.")

    # Log dei dati in ingresso
    logging.debug(f"Dati ricevuti: {data}")

    # Sanifica i dati
    sanitized_data = {k: sanitize_latex(v) for k, v in data.items()}

    try:
        template = Template(LATEX_TEMPLATE)
        latex_content = template.safe_substitute(sanitized_data)
        # Memorizza il contenuto LaTeX per il download
        st.session_state.latex_content = latex_content
    except KeyError as e:
        logging.error(f"KeyError durante la formattazione: {str(e)}")
        raise ValueError(f"Campo mancante: {str(e)}")
    except Exception as e:
        logging.error(f"Errore durante la formattazione del template: {str(e)}")
        raise ValueError(f"Errore nella formattazione del template: {str(e)}")

    temp_dir = r"C:\Users\Francesco\python\temp_latex"
    os.makedirs(temp_dir, exist_ok=True)
    tex_file = os.path.join(temp_dir, "nomina_ciso.tex")
    try:
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(latex_content)
        logging.debug(f"File LaTeX salvato: {tex_file}")
    except Exception as e:
        logging.error(f"Errore salvataggio file LaTeX: {str(e)}")
        raise Exception(f"Errore salvataggio file LaTeX: {str(e)}")

    logo_path = r"C:\Users\Francesco\python\nis2lab_logo.png"
    if os.path.exists(logo_path):
        try:
            shutil.copy(logo_path, os.path.join(temp_dir, "nis2lab_logo.png"))
            logging.debug("Logo copiato correttamente")
        except Exception as e:
            logging.warning(f"Errore copia logo: {str(e)}")
    else:
        logging.warning("Logo nis2lab_logo.png non trovato. Procedo senza logo.")

    try:
        result = subprocess.run(
            ["latexmk", "-pdf", "-interaction=nonstopmode", tex_file],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            check=True
        )
        logging.debug(f"latexmk output: {result.stdout}")
        pdf_file = os.path.join(temp_dir, "nomina_ciso.pdf")
        if not os.path.exists(pdf_file):
            logging.error(f"PDF non generato. Log: {result.stderr}")
            raise Exception(f"PDF non generato. Log: {result.stderr}")
        with open(pdf_file, "rb") as f:
            pdf_data = f.read()
        logging.debug("PDF generato correttamente")
        return pdf_data
    except subprocess.CalledProcessError as e:
        logging.error(f"Errore compilazione LaTeX: {e.stderr}")
        raise Exception(f"Errore compilazione LaTeX: {e.stderr}")
    except Exception as e:
        logging.error(f"Errore generico: {str(e)}")
        raise Exception(f"Errore generico: {str(e)}")
    finally:
        for ext in [".tex", ".pdf", ".aux", ".log", ".fls", ".fdb_latexmk"]:
            try:
                os.remove(os.path.join(temp_dir, f"nomina_ciso{ext}"))
            except:
                pass

# Funzione per generare PDF con reportlab
def genera_pdf_reportlab(template_name, data):
    output = io.BytesIO()
    pdf = SimpleDocTemplate(output, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
   
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='LegalTitle', fontName='Times-Bold', fontSize=16, alignment=1, spaceAfter=12))
    styles.add(ParagraphStyle(name='LegalHeader', fontName='Times-Bold', fontSize=14, textColor=colors.HexColor('#2C3E50'), spaceAfter=10))
    styles.add(ParagraphStyle(name='LegalBody', fontName='Helvetica', fontSize=12, spaceAfter=8))

    elements = templates[template_name]["content"](data)
    pdf.build(elements)
    return output.getvalue()

# Template documenti
templates = {
    "Politica di Sicurezza": {
        "fields": ["ragione_sociale", "ciso_nome", "data"],
        "content": lambda data: [
            Paragraph("Politica di Sicurezza delle Informazioni", styles['LegalTitle']),
            Spacer(1, 12),
            Paragraph(f"Cliente: {data['ragione_sociale']}", styles['LegalBody']),
            Paragraph(f"Responsabile: {data['ciso_nome']}", styles['LegalBody']),
            Paragraph(f"Data: {data['data']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("Questa politica definisce le misure di sicurezza per proteggere i sistemi aziendali in conformità alla Direttiva NIS2.", styles['LegalBody'])
        ]
    },
    "Valutazione dei Rischi": {
        "fields": ["ragione_sociale", "data"],
        "content": lambda data: [
            Paragraph("Valutazione dei Rischi", styles['LegalTitle']),
            Spacer(1, 12),
            Paragraph(f"Cliente: {data['ragione_sociale']}", styles['LegalBody']),
            Paragraph(f"Data: {data['data']}", styles['LegalBody']),
            Spacer(1, 12),
            Table([["Minaccia", "Verosimiglianza", "Parametri", "Rischio", "Mitigazione"]] +
                  [[r["minaccia"], r["verosimiglianza"], r["parametri"], r["rischio"], r["mitigazione"]] for r in st.session_state.rischi],
                  colWidths=[100, 80, 80, 80, 150],
                  style=TableStyle([
                      ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
                      ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                      ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                      ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                      ('FONTSIZE', (0, 0), (-1, -1), 10),
                      ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                      ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F5DC'))
                  ]))
        ]
    },
    "Piano Risposta Incidenti": {
        "fields": ["ragione_sociale", "ciso_nome", "data", "procedure"],
        "content": lambda data: [
            Paragraph("Piano di Risposta agli Incidenti", styles['LegalTitle']),
            Spacer(1, 12),
            Paragraph(f"Cliente: {data['ragione_sociale']}", styles['LegalBody']),
            Paragraph(f"Responsabile: {data['ciso_nome']}", styles['LegalBody']),
            Paragraph(f"Data: {data['data']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph(f"Procedure: {data['procedure']}", styles['LegalBody'])
        ]
    },
    "Nomina CISO": {
        "fields": ["ragione_sociale", "ciso_nome", "ciso_codice_fiscale", "data", "sede_legale", "p_iva"],
        "content": lambda data: [
            Image(r"C:\Users\Francesco\python\nis2lab_logo.png", width=150, height=50) if os.path.exists(r"C:\Users\Francesco\python\nis2lab_logo.png") else Paragraph("", styles['LegalBody']),
            Paragraph(f"{data['ragione_sociale']}", styles['LegalHeader']),
            Paragraph(f"Sede Legale: {data['sede_legale']}", styles['LegalBody']),
            Paragraph(f"P.IVA: {data['p_iva']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("Atto di Nomina del Responsabile della Sicurezza Informatica (CISO)", styles['LegalTitle']),
            Spacer(1, 12),
            Paragraph("PREMESSO CHE", styles['LegalHeader']),
            Paragraph("- La Direttiva (UE) 2022/2555 (NIS2) impone l’adozione di misure per la gestione dei rischi di sicurezza informatica;", styles['LegalBody']),
            Paragraph("- L’articolo 21 della Direttiva NIS2 richiede la designazione di un CISO;", styles['LegalBody']),
            Paragraph("- Il Regolamento (UE) 2016/679 (GDPR) sottolinea la protezione dei dati personali;", styles['LegalBody']),
            Paragraph(f"- {data['ragione_sociale']} intende rafforzare la governance di sicurezza;", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("OGGETTO", styles['LegalHeader']),
            Paragraph(f"Con il presente atto, {data['ragione_sociale']}, con sede legale in {data['sede_legale']}, P.IVA {data['p_iva']}, nomina il Sig./la Sig.ra {data['ciso_nome']}, codice fiscale {data['ciso_codice_fiscale']}, come CISO.", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("RESPONSABILITÀ DEL CISO", styles['LegalHeader']),
            Paragraph("Il CISO avrà le seguenti responsabilità:", styles['LegalBody']),
            Table([
                ["1.", "Definizione e aggiornamento delle politiche di sicurezza informatica in conformità alla Direttiva NIS2."],
                ["2.", "Gestione e coordinamento delle attività di risposta agli incidenti di sicurezza."],
                ["3.", "Supervisione della formazione del personale in materia di cybersecurity."],
                ["4.", "Monitoraggio e valutazione dei rischi di sicurezza informatica."],
                ["5.", "Coordinamento con l’ACN e altre autorità competenti."],
                ["6.", "Garanzia della conformità a GDPR e NIS2."]
            ], colWidths=[50, 400], style=TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ])),
            Spacer(1, 12),
            Paragraph("DURATA E REVOCA", styles['LegalHeader']),
            Paragraph("La nomina ha durata indeterminata e può essere revocata con comunicazione scritta.", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("DISPOSIZIONI FINALI", styles['LegalHeader']),
            Paragraph(f"Il presente atto entra in vigore in data {data['data']}.", styles['LegalBody']),
            Spacer(1, 24),
            Paragraph("FIRME", styles['LegalHeader']),
            Table([
                ["______________________________", "______________________________"],
                ["Rappresentante Legale", f"{data['ciso_nome']} (CISO)"]
            ], colWidths=[225, 225], style=TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10)
            ]))
        ]
    }
}

# Sidebar di navigazione
st.sidebar.title("Navigazione")
if st.sidebar.button("Home"):
    st.session_state.step = "Home"
if st.sidebar.button("Gestione Rischi"):
    st.session_state.step = "Rischi"
if st.sidebar.button("Checklist Requisiti"):
    st.session_state.step = "Checklist"
for template in templates:
    if st.sidebar.button(template):
        st.session_state.step = template

# Home: Inserimento dati cliente
if st.session_state.step == "Home":
    st.header("Dati Cliente")
   
    # Carica clienti salvati
    clienti = load_clienti()
    cliente_nomi = [c["ragione_sociale"] for c in clienti if c["ragione_sociale"]]
    cliente_nomi.insert(0, "Nuovo Cliente")
   
    with st.form("seleziona_cliente"):
        selected_cliente = st.selectbox("Seleziona Cliente", cliente_nomi)
        submit_select = st.form_submit_button("Carica Dati")
        if submit_select and selected_cliente != "Nuovo Cliente":
            for cliente in clienti:
                if cliente["ragione_sociale"] == selected_cliente:
                    st.session_state.cliente = cliente
                    st.success(f"Dati di {selected_cliente} caricati.")
                    break

    with st.form("dati_cliente"):
        st.session_state.cliente["ragione_sociale"] = st.text_input("Ragione Sociale", value=st.session_state.cliente["ragione_sociale"])
        st.session_state.cliente["contatto"] = st.text_input("Contatto (email)", value=st.session_state.cliente["contatto"])
        st.session_state.cliente["ciso_nome"] = st.text_input("Nome CISO", value=st.session_state.cliente["ciso_nome"])
        st.session_state.cliente["ciso_codice_fiscale"] = st.text_input("Codice Fiscale CISO", value=st.session_state.cliente["ciso_codice_fiscale"])
        st.session_state.cliente["sede_legale"] = st.text_input("Sede Legale", value=st.session_state.cliente["sede_legale"])
        st.session_state.cliente["p_iva"] = st.text_input("P.IVA", value=st.session_state.cliente["p_iva"])
        submit = st.form_submit_button("Salva Dati")
        if submit:
            # Aggiorna o aggiungi cliente alla lista
            clienti = load_clienti()
            cliente_esistente = False
            for i, cliente in enumerate(clienti):
                if cliente["ragione_sociale"] == st.session_state.cliente["ragione_sociale"]:
                    clienti[i] = st.session_state.cliente
                    cliente_esistente = True
                    break
            if not cliente_esistente:
                clienti.append(st.session_state.cliente)
            save_clienti(clienti)
            st.success("Dati cliente salvati.")

# Gestione Rischi
elif st.session_state.step == "Rischi":
    st.header("Gestione Rischi")
    st.subheader("Legenda")
    st.markdown("""
    - **Valore dei rischi**: Calcolato come **Valore delle informazioni (R, I, D) * Verosimiglianza**.
      - **Valore informazioni** (1-4):
        - **1 - Basso**: Impatto lieve (es. fastidio).
        - **2 - Medio**: Piccole difficoltà (es. costi moderati).
        - **3 - Alto**: Conseguenze significative (es. denunce).
        - **4 - Critico**: Impatti irreversibili (es. chiusura aziendale).
      - **Livelli di rischio**:
        - **Basso**: < 20
        - **Medio**: 19-40
        - **Alto**: > 40
    - **Verosimiglianza** (1-3):
      - **1 - Bassa**: Minaccia rara, scarsi incentivi.
      - **2 - Media**: Minaccia possibile, motivazione moderata.
      - **3 - Alta**: Minaccia frequente, forti incentivi.
    - **Parametri RID**:
      - **R (Riservatezza)**: Protegge dalla divulgazione non autorizzata.
      - **I (Integrità)**: Protegge da modifiche non autorizzate.
      - **D (Disponibilità)**: Garantisce accesso ai dati.
    """)
   
    df_rischi = pd.DataFrame(st.session_state.rischi)
    st.dataframe(df_rischi)
   
    with st.form("aggiungi_rischio"):
        st.subheader("Aggiungi/Modifica Rischio")
        minaccia = st.text_input("Minaccia", help="Es. Incendio, Intercettazione")
        verosimiglianza = st.selectbox("Verosimiglianza", ["1", "2", "3"], help="1: Bassa, 2: Media, 3: Alta")
        parametri = st.text_input("Parametri (es. RID)", help="R: Riservatezza, I: Integrità, D: Disponibilità")
        rischio = st.text_input("Rischio", help="Valore numerico, es. 24")
        mitigazione = st.text_input("Mitigazione", help="Es. Backup rete")
        submit = st.form_submit_button("Aggiungi")
        if submit and minaccia:
            st.session_state.rischi.append({
                "minaccia": minaccia,
                "verosimiglianza": verosimiglianza,
                "parametri": parametri,
                "rischio": rischio,
                "mitigazione": mitigazione
            })
            st.success(f"Rischio '{minaccia}' aggiunto.")

# Checklist Requisiti
elif st.session_state.step == "Checklist":
    st.header("Checklist Requisiti")
    df_checklist = pd.DataFrame(st.session_state.checklist)
    st.dataframe(df_checklist)
   
    with st.form("aggiorna_checklist"):
        st.subheader("Aggiorna Stato Controllo")
        controllo = st.selectbox("Seleziona Controllo", [c["controllo"] for c in st.session_state.checklist])
        stato = st.selectbox("Stato", ["Non iniziato", "In corso", "Completato"])
        submit = st.form_submit_button("Aggiorna")
        if submit:
            for c in st.session_state.checklist:
                if c["controllo"] == controllo:
                    c["stato"] = stato
                    break
            st.success(f"Stato di '{controllo}' aggiornato.")

# Sezioni template
for template in templates:
    if st.session_state.step == template:
        st.header(template)
        with st.form(f"form_{template}"):
            st.session_state.template_data[template] = st.session_state.template_data.get(template, {})
            for field in templates[template]["fields"]:
                if field in st.session_state.cliente:
                    st.session_state.template_data[template][field] = st.session_state.cliente.get(field, "")
                    st.write(f"{field.replace('_', ' ').title()}: {st.session_state.template_data[template][field]}")
                else:
                    st.session_state.template_data[template][field] = st.text_input(field.replace('_', ' ').title(), value=st.session_state.template_data[template].get(field, ""))
            col1, col2 = st.columns(2)
            with col1:
                generate_pdf = st.form_submit_button("Genera Documento")
            with col2:
                download_tex = st.form_submit_button("Scarica File .tex")
           
            if generate_pdf:
                try:
                    if template == "Nomina CISO":
                        st.session_state.pdf_data[template] = genera_pdf_latex(template, st.session_state.template_data[template])
                        st.session_state.pdf_generated = template
                    else:
                        st.session_state.pdf_data[template] = genera_pdf_reportlab(template, st.session_state.template_data[template])
                        st.session_state.pdf_generated = template
                except Exception as e:
                    st.error(f"Errore generazione documento: {str(e)}")
                    logging.error(f"Errore generazione {template}: {str(e)}")
           
            if download_tex and template == "Nomina CISO":
                try:
                    # Usa il contenuto LaTeX memorizzato o rigenera
                    if st.session_state.latex_content:
                        latex_content = st.session_state.latex_content
                    else:
                        # Rigenera il contenuto LaTeX
                        template_obj = Template(LATEX_TEMPLATE)
                        latex_content = template_obj.safe_substitute({k: sanitize_latex(v) for k, v in st.session_state.template_data[template].items()})
                    st.download_button(
                        label="Scarica File .tex",
                        data=latex_content,
                        file_name=f"nomina_ciso_{time.strftime('%Y%m%d_%H%M')}.tex",
                        mime="text/plain"
                    )
                except Exception as e:
                    st.error(f"Errore generazione file .tex: {str(e)}")
                    logging.error(f"Errore generazione file .tex: {str(e)}")
       
        if st.session_state.get("pdf_generated") == template:
            st.download_button(
                label=f"Scarica {template} (PDF)",
                data=st.session_state.pdf_data[template],
                file_name=f"{template.lower().replace(' ', '_')}_{time.strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf"
            )