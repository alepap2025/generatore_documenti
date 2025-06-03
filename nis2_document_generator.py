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

# CSS per estetica
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
    .stTextInput>div>input, .stSelectbox {
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
    st.session_state.latex_content = None
    st.session_state.download = False
    st.session_state.pdf_generated = None

# Funzione per caricare i clienti salvati
def load_clienti():
    try:
        if os.path.exists(r"C:\Users\Francesco\python\nis2_clienti.json"):
            with open(r"C:\Users\Francesco\python\nis2_clienti.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Errore caricamento dei clienti: {str(e)}")
    return []

# Funzione per salvare i clienti
def save_clienti(clienti):
    try:
        with open(r"C:\Users\Francesco\python\nis2_clienti.json", "w", encoding="utf-8") as f:
            json.dump(clienti, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Errore salvataggio dei clienti: {str(e)}")

# Logo
st.markdown("<div class='header-logo'>", unsafe_allow_html=True)
logo_path = r"C:\Users\Francesco\python\nis2lab_logo.png"
if os.path.exists(logo_path):
    st.image(logo_path, width=250)
else:
    st.markdown("<h1 style='color: #2C3E50;'>NIS2Lab</h1>", unsafe_allow_html=True)
    logging.warning("Logo nis2lab_logo.png non trovato nel percorso specificato")
st.markdown("</div>", unsafe_allow_html=True)

# Funzione per sanificare i dati LaTeX
def sanitize_latex(text):
    if not text:
        return "N/A"
    text = str(text).strip()

    # Gestisci input specifici
    if text.lower() in ["sì", "si"]:
        return r"S\`i"
    if text.lower() == "no":
        return "No"

    # Caratteri accentati
    accent_map = {
        "à": r"\`a", "è": r"\`e", "ì": r"\`i", "ò": r"\`o", "ù": r"\`u",
        "á": r"\'a", "é": r"\'e", "í": r"\'i", "ó": r"\'o", "ú": r"\'u",
        "À": r"\`A", "È": r"\`E", "Ì": r"\`I", "Ò": r"\`O", "Ù": r"\`U",
        "ç": r"\c{c}", "ñ": r"\~n", "Ñ": r"\~N", "€": r"\euro{}", "°": r"\textdegree{}",
        "’": r"\textquotesingle{}", "“": r"``", "”": r"''", "–": r"--", "—": r"---"
    }

    # Caratteri speciali LaTeX
    special_chars = {
        "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
        "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
        "\\": r"\textbackslash{}", "[": r"\lbrack{}", "]": r"\rbrack{}",
        "<": r"\textless{}", ">": r"\textgreater{}", "|": r"\textbar{}",
        "\"": r"\textquotedbl{}", "'": r"\textquotesingle{}", ",": r"\,",
        "(": r"\(", ")": r"\)", ";": r"\;", ":": r"\:", "/": r"/"
    }

    # Sostituisci caratteri
    for char, repl in accent_map.items():
        text = text.replace(char, repl)
    for char, repl in special_chars.items():
        text = text.replace(char, repl)

    # Rimuovi caratteri di controllo e non stampabili
    text = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    # Limita lunghezza
    if len(text) > 200:
        text = text[:200] + "..."

    # Escapa le graffe per Python
    text = text.replace("{", "{{").replace("}", "}}")

    return text

# Elenco predefinito di rischi
RISCHI = {
    "Danni fisici": [
        "Incendio",
        "Allagazione",
        "Polvere, corrosione, congelamento",
        "Distruzione di strumentazione da parte di malintenzionati o per errore",
        "Attacchi (bombe, terroristi)"
    ],
    "Eventi naturali": [
        "Fenomeni climatici (uragani, nevicate)",
        "Terremoti, eruzioni vulcaniche",
        "Fulmini e scariche atmosferiche"
    ],
    "Perdita di servizi essenziali": [
        "Guasto aria condizionata o sistemi di raffreddamento",
        "Perdita di energia (o sbalzi di tensione)",
        "Malfunzionamento nei componenti di rete",
        "Errori di trasmissione (incluso il misrouting)",
        "Interruzione nei collegamenti di rete (inclusi danni alle linee di TLC)",
        "Eccesso di traffico sulla rete",
        "Interruzione di servizi erogati riconducibili ai fornitori esterni",
        "Indisponibilità di personale (malattie, sciopero, eccetera)"
    ],
    "Disturbi": [
        "Disturbi elettromagnetici"
    ],
    "Compromissione di informazioni": [
        "Intercettazione (inclusa analisi del traffico)",
        "Furto di documenti o supporti di memorizzazione",
        "Furto di apparati o componenti",
        "Recupero di informazioni da media dismessi",
        "Rivelazione di informazioni (da parte del personale o fornitori)",
        "Ricezione dati da origini non affidabili",
        "Infiltrazione nelle comunicazioni",
        "Ripudio dei messaggi",
        "Accesso non autorizzato alle informazioni"
    ],
    "Problemi tecnici": [
        "Fault o malfunzionamento della strumentazione IT",
        "Saturazione dei sistemi IT",
        "Malfunzionamenti software applicativi sviluppati per i clienti",
        "Malfunzionamenti pacchetti software usati internamente",
        "Malfunzionamenti software applicativi sviluppati per uso interno",
        "Errori di manutenzione hardware e software di base"
    ],
    "Azioni non autorizzate": [
        "Uso non autorizzato o negligente della strumentazione",
        "Importazione o esportazione illegale di software",
        "Alterazione volontaria e non autorizzata di dati di business",
        "Virus (malware, anche per mobile)",
        "Accesso non autorizzato alla rete",
        "Uso non autorizzato della rete da parte degli utenti",
        "Trattamento non consentito di dati (personali)"
    ],
    "Compromissione di funzioni": [
        "Errori degli utenti di business",
        "Uso dei servizi da parte di persone non autorizzate",
        "Degrado dei media (memorie di massa)",
        "Uso di servizi in modo non autorizzato",
        "Furto identità"
    ],
    "Trattamento dati personali": [
        "Eccessiva raccolta di dati personali",
        "Collegamenti o raffronti inappropriati di dati personali",
        "Divulgazione o riuso per finalità diverse dei dati personali",
        "Conservazione immotivamente prolungata dei dati personali",
        "Inesattezza o mancato aggiornamento dei dati personali",
        "Violazione delle istruzioni ricevute in materia di dati personali",
        "Trasferimento dati personali extra UE senza garanzie"
    ],
    "Direzione": [
        "Mancanza di impegno della direzione",
        "Mancanza di investimenti e di risorse nel SG",
        "Inserimento di nuovi soci o partner"
    ],
    "Sistema di gestione": [
        "Aggiornamento non corretto della documentazione",
        "Adozione di nuovi strumenti e software",
        "Nuovi obblighi di origine normativa o legislativa"
    ],
    "Rapporto con i clienti": [
        "Inadeguato recepimento delle esigenze dei clienti",
        "Inadeguatezza delle offerte rispetto alle esigenze dei clienti"
    ],
    "Monitoraggio": [
        "Monitoraggi inadeguati"
    ],
    "Esercizio": [
        "Errori a causa della mancata pianificazione",
        "Errori a causa di carenza nella formazione",
        "Errori a causa di documentazione carente",
        "Picco di lavoro"
    ],
    "Reato": [
        "Uso malware"
    ]
}

# Opzioni predefinite per i form
SETTORI = ["Manifatturiero", "Sanità", "Energia", "Trasporti", "Finanza", "Telecomunicazioni", "Altro"]
RUOLI_SUPPLY_CHAIN = ["Produttore", "Fornitore", "Distributore", "Cliente finale", "Altro"]
SOGGETTO_ESSENZIALE = ["Sì", "No"]
RESPONSABILITA_CISO = [
    "Definizione politiche di sicurezza",
    "Gestione rischi informatici",
    "Monitoraggio minacce",
    "Protezione dati",
    "Risposta agli incidenti",
    "Formazione personale",
    "Collaborazione con autorità",
    "Conformità normativa",
    "Sicurezza supply chain",
    "Gestione budget sicurezza",
    "Resilienza sistemi critici",
    "Threat intelligence",
    "Certificazioni sicurezza",
    "Penetration testing",
    "Cultura della sicurezza"
]
PRINCIPI_SICUREZZA = ["Riservatezza", "Integrità", "Disponibilità", "Autenticità", "Non ripudio"]
AMBITI_APPLICAZIONE = ["Sistemi IT", "Personale", "Fornitori", "Infrastrutture fisiche", "Dati sensibili"]
FUNZIONI_CRITICHE = ["Produzione", "Servizi clienti", "Gestione dati", "Comunicazioni", "Logistica"]
STRATEGIE_CONTINUITA = ["Backup", "Ridondanza sistemi", "Siti alternativi", "Piani di emergenza"]
PROCEDURE_RECOVERY = ["Ripristino dati", "Ricostituzione servizi", "Comunicazione crisi", "Test di ripristino"]

# Funzione per calcolare il livello di rischio
def calcola_livello_rischio(impatto, probabilita):
    matrice_rischio = {
        ("Basso", "Bassa"): "Basso",
        ("Basso", "Media"): "Basso",
        ("Basso", "Alta"): "Medio",
        ("Medio", "Bassa"): "Basso",
        ("Medio", "Media"): "Medio",
        ("Medio", "Alta"): "Alto",
        ("Alto", "Bassa"): "Medio",
        ("Alto", "Media"): "Alto",
        ("Alto", "Alta"): "Alto",
        ("Critico", "Bassa"): "Alto",
        ("Critico", "Media"): "Alto",
        ("Critico", "Alta"): "Alto"
    }
    return matrice_rischio.get((impatto, probabilita), "N/A")

# Template LaTeX per Nomina CISO
NOMINA_CISO_TEMPLATE = r"""
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{graphicx}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{xcolor}
\usepackage{colortbl}

\geometry{margin=2cm}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\small \detokenize{${ragione_sociale}} --- Data: \detokenize{${data}} --- Pagina \thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0.4pt}

\definecolor{bluscuro}{HTML}{2C3E50}
\rowcolors{2}{gray!10}{white}

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
    \item La Direttiva (UE) 2022/2555 del Parlamento europeo e del Consiglio del 14 dicembre 2022 (NIS2), che impone misure per un livello elevato di cibersicurezza nell’Unione;
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
\noindent
\begin{flushleft}
    Con il presente atto, \detokenize{${ragione_sociale}}, con sede legale in \detokenize{${sede_legale}}, P.IVA \detokenize{${p_iva}}, nomina formalmente il Sig./la Sig.ra \textbf{\detokenize{${ciso_nome}}}, codice fiscale \detokenize{${ciso_codice_fiscale}}, come Responsabile della Sicurezza Informatica (CISO), ai sensi dell’articolo 21 della Direttiva NIS2.
\end{flushleft}

\vspace{0.5cm}

% Responsabilità
\section*{Responsabilità del CISO}
\color{bluscuro}
\noindent
Il CISO avrà le seguenti responsabilità, selezionate per l’organizzazione:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{1.5cm}>{\raggedright\arraybackslash}X}
    \toprule
    \textbf{N.} & \textbf{Responsabilità} \\
    \midrule
    \detokenize{${responsabilita_tabella}} \\
    \bottomrule
\end{tabularx}

\vspace{0.5cm}

% Competenze
\section*{Competenze del CISO}
\color{bluscuro}
\noindent
Il CISO possiede le seguenti competenze, in conformità alla norma UNI 11621-4:2024:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{6.5cm}>{\raggedright\arraybackslash}X}
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

# Template LaTeX per Documento di analisi e classificazione
ANALISI_CLASSIFICAZIONE_TEMPLATE = r"""
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{graphicx}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{xcolor}
\usepackage{colortbl}

\geometry{margin=2cm}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\small \detokenize{${ragione_sociale}} --- Data: \detokenize{${data}} --- Pagina \thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0.4pt}

\definecolor{bluscuro}{HTML}{2C3E50}
\rowcolors{2}{gray!10}{white}

\begin{document}

% Logo
\begin{center}
    \IfFileExists{nis2lab_logo.png}{\includegraphics[width=6cm]{nis2lab_logo.png}}{\textbf{NIS2Lab}}
    \vspace{0.5cm}
\end{center}

% Intestazione
\begin{center}
    \textbf{\Large Documento di Analisi e Classificazione dell’Organizzazione} \\
    \vspace{0.5cm}
    \textbf{\detokenize{${ragione_sociale}}} \\
    Sede Legale: \detokenize{${sede_legale}} \\
    P.IVA: \detokenize{${p_iva}} \\
    \vspace{0.3cm}
    Data: \detokenize{${data}}
\end{center}

\vspace{1cm}

% Mappatura aziendale
\section*{Mappatura Aziendale}
\color{bluscuro}
\noindent
Il presente documento descrive l’analisi e la classificazione dell’organizzazione ai fini della conformità alla Direttiva (UE) 2022/2555 (NIS2).

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{5.5cm}>{\raggedright\arraybackslash}X}
    \toprule
    \textbf{Campo} & \textbf{Descrizione} \\
    \midrule
    Entità Giuridica & \detokenize{${ragione_sociale}} \\
    P.IVA & \detokenize{${p_iva}} \\
    Settore & \detokenize{${settore}} \\
    Ruolo nella Catena di Fornitura & \detokenize{${ruolo_supply_chain}} \\
    Attività Essenziali o Importanti & \detokenize{${attivita_essenziali}} \\
    \bottomrule
\end{tabularx}

\vspace{0.5cm}

% Valutazione NIS2
\section*{Valutazione di Appartenenza NIS2}
\color{black}
\noindent
Sulla base dell’analisi condotta, l’organizzazione è classificata come segue:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{5.5cm}>{\raggedright\arraybackslash}X}
    \toprule
    \textbf{Criterio} & \textbf{Esito} \\
    \midrule
    Soggetto Essenziale & \detokenize{${soggetto_essenziale}} \\
    Motivazione & \detokenize{${motivazione_nis2}} \\
    \bottomrule
\end{tabularx}

\vspace{0.5cm}

% Registro filiali
\section*{Registro delle Filiali e Sedi Operative}
\color{bluscuro}
\noindent
Elenco delle filiali e sedi operative dell’organizzazione:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{5.5cm}>{\raggedright\arraybackslash}X}
    \toprule
    \textbf{Sede} & \textbf{Indirizzo} \\
    \midrule
    \detokenize{${filiali}} \\
    \bottomrule
\end{tabularx}

\end{document}
"""

# Template LaTeX per Politica di Sicurezza
POLITICA_SICUREZZA_TEMPLATE = r"""
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{graphicx}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{xcolor}
\usepackage{colortbl}

\geometry{margin=2cm}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\small \detokenize{${ragione_sociale}} --- Data: \detokenize{${data}} --- Pagina \thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0.4pt}

\definecolor{bluscuro}{HTML}{2C3E50}
\rowcolors{2}{gray!10}{white}

\begin{document}

% Logo
\begin{center}
    \IfFileExists{nis2lab_logo.png}{\includegraphics[width=6cm]{nis2lab_logo.png}}{\textbf{NIS2Lab}}
    \vspace{0.5cm}
\end{center}

% Intestazione
\begin{center}
    \textbf{\Large Politica di Sicurezza delle Informazioni} \\
    \vspace{0.5cm}
    \textbf{\detokenize{${ragione_sociale}}} \\
    Sede Legale: \detokenize{${sede_legale}} \\
    P.IVA: \detokenize{${p_iva}} \\
    \vspace{0.3cm}
    Data: \detokenize{${data}}
\end{center}

\vspace{1cm}

% Introduzione
\section*{Introduzione}
\color{black}
\noindent
La presente politica definisce le misure di sicurezza delle informazioni adottate da \detokenize{${ragione_sociale}} per garantire la conformità alla Direttiva (UE) 2022/2555 (NIS2).

\vspace{0.5cm}

% Principi di sicurezza
\section*{Principi di Sicurezza}
\color{bluscuro}
\noindent
La politica si basa sui seguenti principi:

\begin{itemize}
    \item \detokenize{${principi_sicurezza}}
\end{itemize}

\vspace{0.5cm}

% Misure di sicurezza
\section*{Misure di Sicurezza}
\color{black}
\noindent
Le seguenti misure sono implementate per proteggere le informazioni:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{4.5cm}>{\raggedright\arraybackslash}X}
    \toprule
    \textbf{Misura} & \textbf{Descrizione} \\
    \midrule
    \detokenize{${misure_sicurezza}} \\
    \bottomrule
\end{tabularx}

\vspace{0.5cm}

% Responsabilità
\section*{Responsabilità}
\color{bluscuro}
\noindent
Le responsabilità per l’implementazione della politica sono assegnate come segue:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{4.5cm}>{\raggedright\arraybackslash}X}
    \toprule
    \textbf{Ruolo} & \textbf{Responsabilità} \\
    \midrule
    \detokenize{${responsabilita_sicurezza}} \\
    \bottomrule
\end{tabularx}

\end{document}
"""

# Template LaTeX per Verifica di Sicurezza
VERIFICA_SICUREZZA_TEMPLATE = r"""
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{graphicx}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{xcolor}
\usepackage{colortbl}

\geometry{margin=2cm}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\small \detokenize{${ragione_sociale}} --- Data: \detokenize{${data}} --- Pagina \thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0.4pt}

\definecolor{bluscuro}{HTML}{2C3E50}
\rowcolors{2}{gray!10}{white}

\begin{document}

% Logo
\begin{center}
    \IfFileExists{nis2lab_logo.png}{\includegraphics[width=6cm]{nis2lab_logo.png}}{\textbf{NIS2Lab}}
    \vspace{0.5cm}
\end{center}

% Intestazione
\begin{center}
    \textbf{\Large Verifica di Sicurezza} \\
    \vspace{0.5cm}
    \textbf{\detokenize{${ragione_sociale}}} \\
    Sede Legale: \detokenize{${sede_legale}} \\
    P.IVA: \detokenize{${p_iva}} \\
    \vspace{0.3cm}
    Data: \detokenize{${data}}
\end{center}

\vspace{1cm}

% Introduzione
\section*{Introduzione}
\color{black}
\noindent
La presente verifica descrive i risultati delle attività di controllo della sicurezza presso \detokenize{${ragione_sociale}} in conformità alla Direttiva (UE) 2022/2555 (NIS2).

\vspace{0.5cm}

% Risultati della verifica
\section*{Risultati della Verifica}
\color{bluscuro}
\noindent
I seguenti risultati sono stati ottenuti:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{4.5cm}>{\raggedright\arraybackslash}X}
    \toprule
    \textbf{Area} & \textbf{Risultato} \\
    \midrule
    \detokenize{${risultati_verifica}} \\
    \bottomrule
\end{tabularx}

\vspace{0.5cm}

% Azioni correttive
\section*{Azioni Correttive}
\color{black}
\noindent
Le seguenti azioni correttive sono state definite:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{4.5cm}>{\raggedright\arraybackslash}X}
    \toprule
    \textbf{Azione} & \textbf{Descrizione} \\
    \midrule
    \detokenize{${azioni_correttive}} \\
    \bottomrule
\end{tabularx}

\end{document}
"""

# Template LaTeX per Piano Risposta Incidenti
PIANO_RISPOSTA_INCIDENTI_TEMPLATE = r"""
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{graphicx}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{xcolor}
\usepackage{colortbl}

\geometry{margin=2cm}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\small \detokenize{${ragione_sociale}} --- Data: \detokenize{${data}} --- Pagina \thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0.4pt}

\definecolor{bluscuro}{HTML}{2C3E50}
\rowcolors{2}{gray!10}{white}

\begin{document}

% Logo
\begin{center}
    \IfFileExists{nis2lab_logo.png}{\includegraphics[width=6cm]{nis2lab_logo.png}}{\textbf{NIS2Lab}}
    \vspace{0.5cm}
\end{center}

% Intestazione
\begin{center}
    \textbf{\Large Piano di Risposta agli Incidenti} \\
    \vspace{0.5cm}
    \textbf{\detokenize{${ragione_sociale}}} \\
    Sede Legale: \detokenize{${sede_legale}} \\
    P.IVA: \detokenize{${p_iva}} \\
    \vspace{0.3cm}
    Data: \detokenize{${data}}
\end{center}

\vspace{1cm}

% Introduzione
\section*{Introduzione}
\color{black}
\noindent
Il presente piano definisce le procedure per la gestione degli incidenti di sicurezza presso \detokenize{${ragione_sociale}} in conformità alla Direttiva (UE) 2022/2555 (NIS2).

\vspace{0.5cm}

% Procedure di risposta
\section*{Procedure di Risposta}
\color{bluscuro}
\noindent
Le seguenti procedure sono definite per la gestione degli incidenti:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{4.5cm}>{\raggedright\arraybackslash}X}
    \toprule
    \textbf{Fase} & \textbf{Descrizione} \\
    \midrule
    \detokenize{${procedure_risposta}} \\
    \bottomrule
\end{tabularx}

\vspace{0.5cm}

% Responsabilità
\section*{Responsabilità}
\color{black}
\noindent
Le responsabilità per la gestione degli incidenti sono assegnate come segue:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{4.5cm}>{\raggedright\arraybackslash}X}
    \toprule
    \textbf{Ruolo} & \textbf{Responsabilità} \\
    \midrule
    \detokenize{${responsabilita_risposta}} \\
    \bottomrule
\end{tabularx}

\end{document}
"""

# Template LaTeX per Valutazione dei Rischi
VALUTAZIONE_RISCHI_TEMPLATE = r"""
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{graphicx}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{xcolor}
\usepackage{colortbl}

\geometry{margin=2cm}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\small \detokenize{${ragione_sociale}} --- Data: \detokenize{${data}} --- Pagina \thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0.4pt}

\definecolor{bluscuro}{HTML}{2C3E50}
\rowcolors{2}{gray!10}{white}

\begin{document}

% Logo
\begin{center}
    \IfFileExists{nis2lab_logo.png}{\includegraphics[width=6cm]{nis2lab_logo.png}}{\textbf{NIS2Lab}}
    \vspace{0.5cm}
\end{center}

% Intestazione
\begin{center}
    \textbf{\Large Valutazione dei Rischi} \\
    \vspace{0.5cm}
    \textbf{\detokenize{${ragione_sociale}}} \\
    Sede Legale: \detokenize{${sede_legale}} \\
    P.IVA: \detokenize{${p_iva}} \\
    \vspace{0.3cm}
    Data: \detokenize{${data}}
\end{center}

\vspace{1cm}

% Introduzione
\section*{Introduzione}
\color{black}
\noindent
La presente valutazione descrive i rischi identificati presso \detokenize{${ragione_sociale}} in conformità alla Direttiva (UE) 2022/2555 (NIS2).

\vspace{0.5cm}

% Rischi valutati
\section*{Rischi Valutati}
\color{bluscuro}
\noindent
I seguenti rischi sono stati valutati:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{4.5cm}>{\raggedright\arraybackslash}X}
    \toprule
    \textbf{Rischio} & \textbf{Valutazione} \\
    \midrule
    \detokenize{${rischi_valutati}} \\
    \bottomrule
\end{tabularx}

\vspace{0.5cm}

% Azioni di mitigazione
\section*{Azioni di Mitigazione}
\color{black}
\noindent
Le seguenti azioni sono state definite per mitigare i rischi:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{4.5cm}>{\raggedright\arraybackslash}X}
    \toprule
    \textbf{Azione} & \textbf{Descrizione} \\
    \midrule
    \detokenize{${azioni_mitigazione}} \\
    \bottomrule
\end{tabularx}

\end{document}
"""

# Template LaTeX per Documento di analisi e gestione del rischio
RISK_ASSESSMENT_TEMPLATE = r"""
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{graphicx}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{xcolor}
\usepackage{colortbl}

\geometry{margin=2cm}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\small \detokenize{${ragione_sociale}} --- Data: \detokenize{${data}} --- Pagina \thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0.4pt}

\definecolor{bluscuro}{HTML}{2C3E50}
\rowcolors{2}{gray!10}{white}

\begin{document}

% Logo
\begin{center}
    \IfFileExists{nis2lab_logo.png}{\includegraphics[width=6cm]{nis2lab_logo.png}}{\textbf{NIS2Lab}}
    \vspace{0.5cm}
\end{center}

% Intestazione
\begin{center}
    \textbf{\Large Documento di Analisi e Gestione del Rischio} \\
    \vspace{0.5cm}
    \textbf{\detokenize{${ragione_sociale}}} \\
    Sede Legale: \detokenize{${sede_legale}} \\
    P.IVA: \detokenize{${p_iva}} \\
    \vspace{0.3cm}
    Data: \detokenize{${data}}
\end{center}

\vspace{1cm}

% Introduzione
\section*{Introduzione}
\color{black}
\noindent
Il presente documento descrive l’analisi e la gestione dei rischi relativi alla sicurezza delle informazioni presso \detokenize{${ragione_sociale}}, in conformità alla Direttiva (UE) 2022/2555 (NIS2).

\vspace{0.5cm}

% Metodologia di analisi
\section*{Metodologia di Analisi}
\color{bluscuro}
\noindent
La valutazione dei rischi è stata condotta utilizzando la seguente metodologia:

\begin{itemize}
    \item \detokenize{${metodologia_analisi}}
\end{itemize}

\vspace{0.5cm}

% Identificazione e valutazione dei rischi
\section*{Identificazione e Valutazione dei Rischi}
\color{black}
\noindent
I seguenti rischi sono stati identificati e valutati in termini di riservatezza, integrità e disponibilità:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{4.5cm}>{\raggedright\arraybackslash}p{2.5cm}>{\raggedright\arraybackslash}p{2.5cm}>{\raggedright\arraybackslash}p{2.5cm}>{\raggedright\arraybackslash}X}
    \toprule
    \textbf{Minaccia} & \textbf{Impatto} & \textbf{Probabilità} & \textbf{Livello di Rischio} & \textbf{Note} \\
    \midrule
    \detokenize{${rischi_tabella}} \\
    \bottomrule
\end{tabularx}

\vspace{0.5cm}

% Piano di trattamento del rischio
\section*{Piano di Trattamento del Rischio}
\color{bluscuro}
\noindent
Il piano di trattamento del rischio include le seguenti misure:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{3.5cm}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{2.5cm}>{\raggedright\arraybackslash}p{2.5cm}}
    \toprule
    \textbf{Misura} & \textbf{Descrizione} & \textbf{Priorità} & \textbf{Responsabile} \\
    \midrule
    \detokenize{${piano_trattamento}} \\
    \bottomrule
\end{tabularx}

\end{document}
"""

# Template LaTeX per Continuità Operativa
CONTINUITA_OPERATIVA_TEMPLATE = r"""
\documentclass[a4paper,12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{geometry}
\usepackage{fancyhdr}
\usepackage{graphicx}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage{xcolor}
\usepackage{colortbl}

\geometry{margin=2cm}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\small \detokenize{${ragione_sociale}} --- Data: \detokenize{${data}} --- Pagina \thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0.4pt}

\definecolor{bluscuro}{HTML}{2C3E50}
\rowcolors{2}{gray!10}{white}

\begin{document}

% Logo
\begin{center}
    \IfFileExists{nis2lab_logo.png}{\includegraphics[width=6cm]{nis2lab_logo.png}}{\textbf{NIS2Lab}}
    \vspace{0.5cm}
\end{center}

% Intestazione
\begin{center}
    \textbf{\Large Piano di Continuità Operativa} \\
    \vspace{0.5cm}
    \textbf{\detokenize{${ragione_sociale}}} \\
    Sede Legale: \detokenize{${sede_legale}} \\
    P.IVA: \detokenize{${p_iva}} \\
    \vspace{0.3cm}
    Data: \detokenize{${data}}
\end{center}

\vspace{1cm}

% Introduzione
\section*{Introduzione}
\color{black}
\noindent
Il presente piano descrive le procedure per garantire la continuità operativa di \detokenize{${ragione_sociale}} in conformità alla Direttiva (UE) 2022/2555 (NIS2).

\vspace{0.5cm}

% Obiettivi
\section*{Obiettivi del Piano}
\color{bluscuro}
\noindent
Gli obiettivi del piano sono:

\begin{itemize}
    \item \detokenize{${obiettivi_piano}}
\end{itemize}

\vspace{0.5cm}

% Procedure di ripristino
\section*{Procedure di Ripristino}
\color{black}
\noindent
Le seguenti procedure sono definite per il ripristino dei servizi critici:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{4.5cm}>{\raggedright\arraybackslash}X>{\raggedright\arraybackslash}p{2.5cm}}
    \toprule
    \textbf{Servizio} & \textbf{Procedura} & \textbf{Tempo di Ripristino (RTO)} \\
    \midrule
    \detokenize{${procedure_ripristino}} \\
    \bottomrule
\end{tabularx}

\vspace{0.5cm}

% Responsabilità
\section*{Responsabilità}
\color{bluscuro}
\noindent
Le responsabilità per l’esecuzione del piano sono assegnate come segue:

\begin{tabularx}{\textwidth}{>{\raggedright\arraybackslash}p{4.5cm}>{\raggedright\arraybackslash}X}
    \toprule
    \textbf{Ruolo} & \textbf{Responsabilità} \\
    \midrule
    \detokenize{${responsabilita_continuita}} \\
    \bottomrule
\end{tabularx}

\end{document}
"""

def genera_pdf_latex(data, template_name, template_str=None, logo_path=None):
    import os
    import shutil
    import subprocess
    import logging
    import time
    from string import Template
    import streamlit as st

    # Definisci i template di default
    templates = {
        "Analisi e Gestione del Rischio": RISK_ASSESSMENT_TEMPLATE,
        "Analisi e Classificazione": ANALISI_CLASSIFICAZIONE_TEMPLATE,
        "Nomina CISO": NOMINA_CISO_TEMPLATE,
        "Politica di Sicurezza": POLITICA_SICUREZZA_TEMPLATE,
        "Continuità Operativa": CONTINUITA_OPERATIVA_TEMPLATE,
        "Verifica di Sicurezza": VERIFICA_SICUREZZA_TEMPLATE,
        "Piano Risposta Incidenti": PIANO_RISPOSTA_INCIDENTI_TEMPLATE,
        "Valutazione dei Rischi": VALUTAZIONE_RISCHI_TEMPLATE
    }

    # Usa il template specificato o quello di default
    if template_str is None:
        template_str = templates.get(template_name, "")
        if not template_str:
            raise ValueError(f"Template non trovato per {template_name}")

    # Definisci il percorso del logo di default
    if logo_path is None:
        logo_path = r"C:\Users\Francesco\python\nis2lab_logo.png"

    # Inizializza i dati sanificati
    sanitized_data = {}
    for key, value in data.items():
        if isinstance(value, list):
            sanitized_data[key] = value  # Mantieni liste (es. rischi)
        else:
            sanitized_data[key] = sanitize_latex(value) if value else "N/A"
        logging.debug(f"Sanitizzato {key}: {sanitized_data[key]}")

    # Gestione rischi per Analisi e Gestione del Rischio
    if template_name == "Analisi e Gestione del Rischio":
        rischi = data.get("rischi", [])
        if not rischi:
            logging.error("Nessun rischio selezionato")
            raise ValueError("È necessario selezionare almeno un rischio")
       
        rischi_tabella = []
        for rischio in rischi:
            livello_rischio = calcola_livello_rischio(rischio.get("impatto", "Basso"), rischio.get("probabilita", "Bassa"))
            minaccia = sanitize_latex(rischio.get("minaccia", "N/A"))
            impatto = sanitize_latex(rischio.get("impatto", "N/A"))
            probabilita = sanitize_latex(rischio.get("probabilita", "N/A"))
            note = sanitize_latex(rischio.get("note", ""))
            if all([minaccia, impatto, probabilita, livello_rischio]):
                riga = f"{minaccia} & {impatto} & {probabilita} & {livello_rischio} & {note} \\\\"
                rischi_tabella.append(riga)
        sanitized_data["rischi_tabella"] = "\n".join(rischi_tabella) if rischi_tabella else "Nessun rischio valido \\\\"
       
        piano_trattamento = sanitize_latex(data.get("piano_trattamento", ""))
        if not piano_trattamento or piano_trattamento == "N/A":
            sanitized_data["piano_trattamento"] = "Firewall & Configurazione aggiornata & Alta & IT Manager \\\\"
        else:
            sanitized_data["piano_trattamento"] = f"{piano_trattamento} & {piano_trattamento} & Media & CISO \\\\"

    # Gestione Nomina CISO
    if template_name == "Nomina CISO":
        responsabilita = data.get("responsabilita", [])
        responsabilita_tabella = "\n".join([f"{i+1} & {sanitize_latex(resp)} \\\\" for i, resp in enumerate(responsabilita)])
        sanitized_data["responsabilita_tabella"] = responsabilita_tabella if responsabilita else "Nessuna responsabilità selezionata \\\\"

    # Gestione Politica di Sicurezza
    if template_name == "Politica di Sicurezza":
        principi_sicurezza = sanitize_latex(data.get("principi_sicurezza", "Riservatezza; Integrità; Non ripudio"))
        sanitized_data["principi_sicurezza"] = principi_sicurezza if principi_sicurezza else "Riservatezza; Integrità; Non ripudio"
        sanitized_data["misure_sicurezza"] = sanitize_latex(data.get("misure_sicurezza", "Firewall & Protezione rete")) or "Firewall & Protezione rete \\\\"
        sanitized_data["responsabilita_sicurezza"] = sanitize_latex(data.get("responsabilita_sicurezza", "CISO & Implementazione misure")) or "CISO & Implementazione misure \\\\"

    # Gestione Continuità Operativa
    if template_name == "Continuità Operativa":
        obiettivi_piano = sanitize_latex(data.get("obiettivi_piano", "Minimizzare tempi di inattività"))
        sanitized_data["obiettivi_piano"] = obiettivi_piano if obiettivi_piano else "Minimizzare tempi di inattività"
        sanitized_data["procedure_ripristino"] = sanitize_latex(data.get("procedure_ripristino", "Server & Backup giornaliero & 4 ore")) or "Server & Backup giornaliero & 4 ore \\\\"
        sanitized_data["responsabilita_continuita"] = sanitize_latex(data.get("responsabilita_continuita", "CISO & Coordinamento ripristino")) or "CISO & Coordinamento ripristino \\\\"

    # Gestione Verifica di Sicurezza
    if template_name == "Verifica di Sicurezza":
        sanitized_data["risultati_verifica"] = sanitize_latex(data.get("risultati_verifica", "Nessuna vulnerabilità & Conformità verificata")) or "Nessuna vulnerabilità & Conformità verificata \\\\"
        sanitized_data["azioni_correttive"] = sanitize_latex(data.get("azioni_correttive", "Nessuna azione richiesta & N/A")) or "Nessuna azione richiesta & N/A \\\\"

    # Gestione Piano Risposta Incidenti
    if template_name == "Piano Risposta Incidenti":
        sanitized_data["procedure_risposta"] = sanitize_latex(data.get("procedure_risposta", "Notifica & Contenimento")) or "Notifica & Contenimento \\\\"
        sanitized_data["responsabilita_risposta"] = sanitize_latex(data.get("responsabilita_risposta", "CISO & Gestione incidente")) or "CISO & Gestione incidente \\\\"

    # Gestione Valutazione dei Rischi
    if template_name == "Valutazione dei Rischi":
        sanitized_data["rischi_valutati"] = sanitize_latex(data.get("rischi_valutati", "Phishing & Valutazione completata")) or "Phishing & Valutazione completata \\\\"
        sanitized_data["azioni_mitigazione"] = sanitize_latex(data.get("azioni_mitigazione", "Formazione & Prevenzione")) or "Formazione & Prevenzione \\\\"

    # Validazione campo Sede Legale
    sede_legale = data.get("sede_legale", "").strip()
    if not sede_legale:
        logging.error(f"Campo obbligatorio mancante: sede_legale, valore ricevuto: '{sede_legale}'")
        raise ValueError("Il campo 'Sede Legale' è obbligatorio e non può essere vuoto")
    sanitized_data["sede_legale"] = sanitize_latex(sede_legale)

    # Generazione file LaTeX
    temp_dir = r"C:\Users\Francesco\python\temp_latex"
    os.makedirs(temp_dir, exist_ok=True)
   
    # Pulizia directory temporanea
    for file in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            logging.warning(f"Errore pulizia file temporaneo {file_path}: {str(e)}")

    tex_file = os.path.join(temp_dir, f"{template_name.lower().replace(' ', '_')}.tex")
    debug_tex = os.path.join(temp_dir, f"debug_{template_name.lower().replace(' ', '_')}_{time.strftime('%Y%m%d_%H%M%S')}.tex")
    debug_output = os.path.join(temp_dir, "debug_output.tex")
    try:
        template = Template(template_str)
        latex_content = template.safe_substitute(sanitized_data)
        # Salva il contenuto .tex per debug
        with open(debug_output, "w", encoding="utf-8") as f:
            f.write(latex_content)
        logging.debug(f"Contenuto LaTeX salvato in: {debug_output}")
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(latex_content)
        logging.debug(f"File LaTeX salvato: {tex_file}")
        shutil.copy(tex_file, debug_tex)
        logging.debug(f"Copia di debug salvata: {debug_tex}")
        st.session_state.latex_content = latex_content
    except Exception as e:
        logging.error(f"Errore generazione file LaTeX: {str(e)}")
        raise Exception(f"Errore generazione file LaTeX: {str(e)}")

    if os.path.exists(logo_path):
        try:
            shutil.copy(logo_path, os.path.join(temp_dir, "nis2lab_logo.png"))
            logging.debug("Logo copiato correttamente")
        except Exception as e:
            logging.error(f"Errore copia logo: {str(e)}")
            raise Exception(f"Errore copia logo: {str(e)}")
    else:
        logging.warning("Logo nis2lab_logo.png non trovato nel percorso specificato")

    try:
        result = subprocess.run(
            ["latexmk", "-pdf", "-interaction=nonstopmode", "-f", "-verbose", "-diagnostics", tex_file],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            check=True
        )
        logging.debug(f"latexmk output: {result.stdout}")
        pdf_file = os.path.join(temp_dir, f"{template_name.lower().replace(' ', '_')}.pdf")
        if not os.path.exists(pdf_file):
            logging.error(f"PDF non generato. Log: {result.stderr}")
            debug_log = os.path.join(temp_dir, f"latexmk_log_{template_name.lower().replace(' ', '_')}_{time.strftime('%Y%m%d_%H%M%S')}.txt")
            with open(debug_log, "w", encoding="utf-8") as f:
                f.write(f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}")
            raise Exception(f"PDF non generato. Log salvato in: {debug_log}")
        with open(pdf_file, "rb") as f:
            pdf_data = f.read()
        logging.debug("PDF generato correttamente")
        return pdf_data
    except subprocess.CalledProcessError as e:
        logging.error(f"Errore compilazione LaTeX: {e.stderr}")
        debug_log = os.path.join(temp_dir, f"latexmk_log_{template_name.lower().replace(' ', '_')}_{time.strftime('%Y%m%d_%H%M%S')}.txt")
        with open(debug_log, "w", encoding="utf-8") as f:
            f.write(f"STDOUT:\n{e.stdout}\n\nSTDERR:\n{e.stderr}")
        raise Exception(f"Errore compilazione LaTeX. Log salvato in: {debug_log}")
    except Exception as e:
        logging.error(f"Errore generico: {str(e)}")
        raise Exception(f"Errore generico: {str(e)}")

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
        "fields": ["ragione_sociale", "sede_legale", "p_iva", "data", "direttore_nome", "principi_sicurezza", "obiettivi_sicurezza", "ambiti_applicazione", "struttura_organizzativa", "misure_sicurezza", "responsabilita_sicurezza"],
        "content": lambda data: [
            Image(logo_path, width=150, height=50) if os.path.exists(logo_path) else Paragraph("", styles['LegalBody']),
            Paragraph(f"{data['ragione_sociale']}", styles['LegalHeader']),
            Paragraph(f"Sede Legale: {data['sede_legale']}", styles['LegalBody']),
            Paragraph(f"P.IVA: {data['p_iva']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("Politica di Sicurezza delle Informazioni", styles['LegalTitle']),
            Spacer(1, 12),
            Paragraph("APPROVAZIONE", styles['LegalHeader']),
            Paragraph(f"Approvata da {data['direttore_nome']} in data {data['data']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("PRINCIPI DI SICUREZZA", styles['LegalHeader']),
            Paragraph(f"{data['principi_sicurezza']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("OBIETTIVI DI SICUREZZA", styles['LegalHeader']),
            Paragraph(f"{data['obiettivi_sicurezza']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("AMBITI DI APPLICAZIONE", styles['LegalHeader']),
            Paragraph(f"{data['ambiti_applicazione']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("STRUTTURA ORGANIZZATIVA", styles['LegalHeader']),
            Paragraph(f"{data['struttura_organizzativa']}", styles['LegalBody'])
        ]
    },
    "Valutazione dei Rischi": {
        "fields": ["ragione_sociale", "data", "rischi_valutati", "azioni_mitigazione"],
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
        "fields": ["ragione_sociale", "ciso_nome", "data", "procedure_risposta", "responsabilita_risposta"],
        "content": lambda data: [
            Paragraph("Piano di Risposta agli Incidenti", styles['LegalTitle']),
            Spacer(1, 12),
            Paragraph(f"Cliente: {data['ragione_sociale']}", styles['LegalBody']),
            Paragraph(f"Responsabile: {data['ciso_nome']}", styles['LegalBody']),
            Paragraph(f"Data: {data['data']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph(f"Procedure: {data['procedure_risposta']}", styles['LegalBody'])
        ]
    },
    "Nomina CISO": {
        "fields": ["ragione_sociale", "ciso_nome", "ciso_codice_fiscale", "data", "sede_legale", "p_iva", "responsabilita"],
        "content": lambda data: [
            Image(logo_path, width=150, height=50) if os.path.exists(logo_path) else Paragraph("", styles['LegalBody']),
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
            Table(
                [["N.", "Responsabilità"]] + [[str(i+1), resp] for i, resp in enumerate(data.get("responsabilita", []))],
                colWidths=[50, 400],
                style=TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white)
                ])
            ),
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
    },
    "Analisi e Classificazione": {
        "fields": ["ragione_sociale", "sede_legale", "p_iva", "data", "settore", "ruolo_supply_chain", "attivita_essenziali", "soggetto_essenziale", "motivazione_nis2", "filiali"],
        "content": lambda data: [
            Image(logo_path, width=150, height=50) if os.path.exists(logo_path) else Paragraph("", styles['LegalBody']),
            Paragraph(f"{data['ragione_sociale']}", styles['LegalHeader']),
            Paragraph(f"Sede Legale: {data['sede_legale']}", styles['LegalBody']),
            Paragraph(f"P.IVA: {data['p_iva']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("Documento di Analisi e Classificazione dell’Organizzazione", styles['LegalTitle']),
            Spacer(1, 12),
            Paragraph("MAPPATURA AZIENDALE", styles['LegalHeader']),
            Table([
                ["Entità Giuridica", f"{data['ragione_sociale']}"],
                ["P.IVA", f"{data['p_iva']}"],
                ["Settore", f"{data['settore']}"],
                ["Ruolo nella Catena di Fornitura", f"{data['ruolo_supply_chain']}"],
                ["Attività Essenziali o Importanti", f"{data['attivita_essenziali']}"]
            ], colWidths=[150, 350], style=TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
            ])),
            Spacer(1, 12),
            Paragraph("VALUTAZIONE DI APPARTENENZA NIS2", styles['LegalHeader']),
            Table([
                ["Soggetto Essenziale", f"{data['soggetto_essenziale']}"],
                ["Motivazione", f"{data['motivazione_nis2']}"]
            ], colWidths=[150, 350], style=TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
            ])),
            Spacer(1, 12),
            Paragraph("REGISTRO DELLE FILIALI", styles['LegalHeader']),
            Paragraph(f"{data['filiali']}", styles['LegalBody'])
        ]
    },
    "Analisi e Gestione del Rischio": {
        "fields": ["ragione_sociale", "sede_legale", "p_iva", "data", "metodologia_analisi", "rischi", "piano_trattamento"],
        "content": lambda data: [
            Image(logo_path, width=150, height=50) if os.path.exists(logo_path) else Paragraph("", styles['LegalBody']),
            Paragraph(f"{data['ragione_sociale']}", styles['LegalHeader']),
            Paragraph(f"Sede Legale: {data['sede_legale']}", styles['LegalBody']),
            Paragraph(f"P.IVA: {data['p_iva']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("Documento di Analisi e Gestione del Rischio", styles['LegalTitle']),
            Spacer(1, 12),
            Paragraph("METODOLOGIA DI ANALISI", styles['LegalHeader']),
            Paragraph(f"{data['metodologia_analisi']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("IDENTIFICAZIONE E VALUTAZIONE DEI RISCHI", styles['LegalHeader']),
            Table([
                ["Minaccia", "Impatto", "Probabilità", "Livello di Rischio", "Note"]
            ] + [[r["minaccia"], r["impatto"], r["probabilita"], calcola_livello_rischio(r["impatto"], r["probabilita"]), r.get("note", "")] for r in data.get("rischi", [])],
                colWidths=[100, 80, 80, 80, 150],
                style=TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F5DC'))
                ])),
            Spacer(1, 12),
            Paragraph("PIANO DI TRATTAMENTO DEL RISCHIO", styles['LegalHeader']),
            Paragraph(f"{data['piano_trattamento']}", styles['LegalBody'])
        ]
    },
    "Continuità Operativa": {
        "fields": ["ragione_sociale", "sede_legale", "p_iva", "data", "obiettivi_piano", "funzioni_critiche", "strategie_continuita", "procedure_recovery", "test_manutenzione", "procedure_ripristino", "responsabilita_continuita"],
        "content": lambda data: [
            Image(logo_path, width=150, height=50) if os.path.exists(logo_path) else Paragraph("", styles['LegalBody']),
            Paragraph(f"{data['ragione_sociale']}", styles['LegalHeader']),
            Paragraph(f"Sede Legale: {data['sede_legale']}", styles['LegalBody']),
            Paragraph(f"P.IVA: {data['p_iva']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("Piano di Continuità Operativa e Disaster Recovery", styles['LegalTitle']),
            Spacer(1, 12),
            Paragraph("OBIETTIVI DEL PIANO", styles['LegalHeader']),
            Paragraph(f"{data['obiettivi_piano']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("FUNZIONI CRITICHE", styles['LegalHeader']),
            Paragraph(f"{data['funzioni_critiche']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("STRATEGIE DI CONTINUITÀ", styles['LegalHeader']),
            Paragraph(f"{data['strategie_continuita']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("PROCEDURE DI RECOVERY", styles['LegalHeader']),
            Paragraph(f"{data['procedure_recovery']}", styles['LegalBody']),
            Spacer(1, 12),
            Paragraph("TEST E MANUTENZIONE", styles['LegalHeader']),
            Paragraph(f"{data['test_manutenzione']}", styles['LegalBody'])
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
# Sezioni template
for template in templates:
    if st.session_state.step == template:
        st.header(template)
        with st.form(f"form_{template}"):
            st.session_state.template_data[template] = st.session_state.template_data.get(template, {})
            for field in templates[template]["fields"]:
                if field == "rischi" and template == "Analisi e Gestione del Rischio":
                    st.subheader("Selezione Rischi")
                    rischi_selezionati = []
                    for categoria, minacce in RISCHI.items():
                        st.subheader(categoria)
                        for rischio in minacce:
                            if st.checkbox(rischio, key=f"rischio_{rischio}_{template}"):
                                impatto = st.selectbox(f"Impatto per {rischio}", ["Basso", "Medio", "Alto", "Critico"], key=f"impatto_{rischio}_{template}")
                                probabilita = st.selectbox(f"Probabilità per {rischio}", ["Bassa", "Media", "Alta"], key=f"probabilita_{rischio}_{template}")
                                note = st.text_input(f"Note per {rischio}", key=f"note_{rischio}_{template}")
                                rischi_selezionati.append({
                                    "minaccia": rischio,
                                    "impatto": impatto,
                                    "probabilita": probabilita,
                                    "note": note
                                })
                    st.session_state.template_data[template]["rischi"] = rischi_selezionati
                elif field == "responsabilita" and template == "Nomina CISO":
                    st.subheader("Selezione Responsabilità CISO")
                    responsabilita_selezionate = []
                    for resp in RESPONSABILITA_CISO:
                        if st.checkbox(resp, key=f"resp_{resp}_{template}"):
                            responsabilita_selezionate.append(resp)
                    st.session_state.template_data[template]["responsabilita"] = responsabilita_selezionate
                elif field == "settore" and template == "Analisi e Classificazione":
                    st.session_state.template_data[template][field] = st.selectbox(field.replace('_', ' ').title(), SETTORI, key=f"{field}_{template}")
                elif field == "ruolo_supply_chain" and template == "Analisi e Classificazione":
                    st.session_state.template_data[template][field] = st.selectbox(field.replace('_', ' ').title(), RUOLI_SUPPLY_CHAIN, key=f"{field}_{template}")
                elif field == "soggetto_essenziale" and template == "Analisi e Classificazione":
                    st.session_state.template_data[template][field] = st.selectbox(field.replace('_', ' ').title(), SOGGETTO_ESSENZIALE, key=f"{field}_{template}")
                elif field == "principi_sicurezza" and template == "Politica di Sicurezza":
                    st.subheader("Selezione Principi di Sicurezza")
                    principi_selezionati = []
                    for principio in PRINCIPI_SICUREZZA:
                        if st.checkbox(principio, key=f"principio_{principio}_{template}"):
                            principi_selezionati.append(principio)
                    st.session_state.template_data[template][field] = "; ".join(principi_selezionati)
                elif field == "ambiti_applicazione" and template == "Politica di Sicurezza":
                    st.subheader("Selezione Ambiti di Applicazione")
                    ambiti_selezionati = []
                    for ambito in AMBITI_APPLICAZIONE:
                        if st.checkbox(ambito, key=f"ambito_{ambito}_{template}"):
                            ambiti_selezionati.append(ambito)
                    st.session_state.template_data[template][field] = "; ".join(ambiti_selezionati)
                elif field == "funzioni_critiche" and template == "Continuità Operativa":
                    st.subheader("Selezione Funzioni Critiche")
                    funzioni_selezionate = []
                    for funzione in FUNZIONI_CRITICHE:
                        if st.checkbox(funzione, key=f"funzione_{funzione}_{template}"):
                            descrizione = st.text_input(f"Descrizione per {funzione}", key=f"desc_{funzione}_{template}")
                            funzioni_selezionate.append(f"{funzione}: {descrizione}")
                    st.session_state.template_data[template][field] = "; ".join(funzioni_selezionate)
                elif field == "strategie_continuita" and template == "Continuità Operativa":
                    st.subheader("Selezione Strategie di Continuità")
                    strategie_selezionate = []
                    for strategia in STRATEGIE_CONTINUITA:
                        if st.checkbox(strategia, key=f"strategia_{strategia}_{template}"):
                            strategie_selezionate.append(strategia)
                    st.session_state.template_data[template][field] = "; ".join(strategie_selezionate)
                elif field == "procedure_recovery" and template == "Continuità Operativa":
                    st.subheader("Selezione Procedure di Recovery")
                    procedure_selezionate = []
                    for procedura in PROCEDURE_RECOVERY:
                        if st.checkbox(procedura, key=f"procedura_{procedura}_{template}"):
                            procedure_selezionate.append(procedura)
                    st.session_state.template_data[template][field] = "; ".join(procedure_selezionate)
                elif field in st.session_state.cliente:
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
                    data = st.session_state.template_data[template].copy()
                    data.update({
                        "ragione_sociale": st.session_state.cliente.get("ragione_sociale", ""),
                        "sede_legale": st.session_state.cliente.get("sede_legale", ""),
                        "p_iva": st.session_state.cliente.get("p_iva", ""),
                        "data": st.session_state.cliente.get("data", time.strftime("%d/%m/%Y")),
                        "ciso_nome": st.session_state.cliente.get("ciso_nome", ""),
                        "ciso_codice_fiscale": st.session_state.cliente.get("ciso_codice_fiscale", "")
                    })
                    # Genera la tabella delle responsabilità per Nomina CISO
                    if template == "Nomina CISO":
                        responsabilita = data.get("responsabilita", [])
                        responsabilita_tabella = "\n".join([f"{i+1} & {sanitize_latex(resp)} \\\\" for i, resp in enumerate(responsabilita) if isinstance(resp, str)])
                        data["responsabilita_tabella"] = responsabilita_tabella if responsabilita else "Nessuna responsabilità selezionata \\\\"
                    st.session_state.pdf_data[template] = genera_pdf_latex(data, template)
                    st.session_state.pdf_generated = template
                except Exception as e:
                    st.error(f"Errore generazione documento: {str(e)}")
                    logging.error(f"Errore generazione {template}: {str(e)}")
           
            if download_tex:
                st.session_state.download = True

        if st.session_state.download and template in templates:
            try:
                if st.session_state.latex_content:
                    latex_content = st.session_state.latex_content
                else:
                    template_obj = Template({
                        "Nomina CISO": NOMINA_CISO_TEMPLATE,
                        "Analisi e Classificazione": ANALISI_CLASSIFICAZIONE_TEMPLATE,
                        "Politica di Sicurezza": POLITICA_SICUREZZA_TEMPLATE,
                        "Analisi e Gestione del Rischio": RISK_ASSESSMENT_TEMPLATE,
                        "Continuità Operativa": CONTINUITA_OPERATIVA_TEMPLATE,
                        "Verifica di Sicurezza": VERIFICA_SICUREZZA_TEMPLATE,
                        "Piano Risposta Incidenti": PIANO_RISPOSTA_INCIDENTI_TEMPLATE,
                        "Valutazione dei Rischi": VALUTAZIONE_RISCHI_TEMPLATE
                    }[template])
                    data = st.session_state.template_data[template].copy()
                    data.update({
                        "ragione_sociale": st.session_state.cliente.get("ragione_sociale", ""),
                        "sede_legale": st.session_state.cliente.get("sede_legale", ""),
                        "p_iva": st.session_state.cliente.get("p_iva", ""),
                        "data": st.session_state.cliente.get("data", time.strftime("%d/%m/%Y")),
                        "ciso_nome": st.session_state.cliente.get("ciso_nome", ""),
                        "ciso_codice_fiscale": st.session_state.cliente.get("ciso_codice_fiscale", "")
                    })
                    if template == "Nomina CISO":
                        responsabilita = data.get("responsabilita", [])
                        responsabilita_tabella = "\n".join([f"{i+1} & {sanitize_latex(resp)} \\\\" for i, resp in enumerate(responsabilita) if isinstance(resp, str)])
                        data["responsabilita_tabella"] = responsabilita_tabella if responsabilita else "Nessuna responsabilità selezionata \\\\"
                    latex_content = template_obj.safe_substitute({k: sanitize_latex(v) if isinstance(v, str) else v for k, v in data.items()})
                st.download_button(
                    label="Scarica File .tex",
                    data=latex_content,
                    file_name=f"{template.lower().replace(' ', '_')}_{time.strftime('%Y%m%d_%H%M')}.tex",
                    mime="text/plain",
                    key=f"download_tex_{template}"
                )
                st.session_state.download = False
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