import streamlit as st
import json
import os
import base64
import pandas as pd
import re
from docx import Document
import fitz  # PyMuPDF
from openai import OpenAI
from pdf_report import generate_pdf_report

# -------------------------------------------------------------------
# Configuration de la page Streamlit
# -------------------------------------------------------------------
st.set_page_config(page_title="Audit NDI - Évaluateur Multimodal", layout="wide")
st.title("🛡️ Audit de Conformité NDI - Évaluateur d'Évidences")

# -------------------------------------------------------------------
# Configuration Ollama (API OpenAI-compatible)
# -------------------------------------------------------------------
class Settings:
    OLLAMA_BASE_URL = "http://localhost:11434/v1"
    OLLAMA_API_KEY = "ollama"
    OLLAMA_TIMEOUT_SECONDS = 900
    OLLAMA_MODEL = "qwen2.5vl:7b"

settings = Settings()

client = OpenAI(
    base_url=settings.OLLAMA_BASE_URL,
    api_key=settings.OLLAMA_API_KEY,
    timeout=settings.OLLAMA_TIMEOUT_SECONDS,
)

# Dossier contenant vos fichiers JSON
JSON_DIR = "." 

# -------------------------------------------------------------------
# Fonctions de Chargement et d'Extraction
# -------------------------------------------------------------------
@st.cache_data
def load_domains(json_directory):
    domains_data = {}
    if not os.path.exists(json_directory):
        return domains_data

    for filename in os.listdir(json_directory):
        if filename.endswith(".json"):
            filepath = os.path.join(json_directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    if isinstance(data, list):
                        data = data[0]
                    domain_name = data.get("Domain", filename.replace(".json", ""))
                    domains_data[domain_name] = data
            except Exception:
                pass
    return domains_data

def process_uploaded_file(uploaded_file):
    file_ext = uploaded_file.name.split('.')[-1].lower()
    result = {"type": "text", "content": ""}
    
    try:
        if file_ext == "pdf":
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            extracted_text = [page.get_text("text") for page in doc]
            result["content"] = "\n".join(extracted_text)
            
        elif file_ext in ["txt", "csv"]:
            result["content"] = uploaded_file.read().decode("utf-8")
            
        elif file_ext in ["xlsx", "xls"]:
            df = pd.read_excel(uploaded_file)
            result["content"] = df.to_markdown(index=False) 
            
        elif file_ext == "docx":
            doc = Document(uploaded_file)
            result["content"] = "\n".join([para.text for para in doc.paragraphs])
            
        elif file_ext in ["png", "jpg", "jpeg"]:
            result["type"] = "image"
            result["content"] = base64.b64encode(uploaded_file.read()).decode('utf-8')
            result["mime_type"] = f"image/{file_ext if file_ext != 'jpg' else 'jpeg'}"
            
        else:
            result["type"] = "error"
            result["content"] = "Format de fichier non supporté."
            
    except Exception as e:
        result["type"] = "error"
        result["content"] = f"Erreur lors de la lecture du fichier : {str(e)}"
        
    return result

# -------------------------------------------------------------------
# Fonction d'Évaluation via le LLM (Ollama / Qwen2.5-VL)
# -------------------------------------------------------------------
def evaluate_evidence_with_llm(question_text, target_level, evidences_list, file_data):
    system_prompt = (
        "Vous êtes un auditeur gouvernemental expert en gouvernance des données (NDMO). "
        "Votre tâche est d'auditer avec une rigueur absolue un document d'évidence par rapport à des critères stricts. "
        "Soyez direct, factuel, et ne justifiez votre réponse qu'en vous basant sur le document fourni."
    )
    
    evidences_text = ""
    for idx, ev in enumerate(evidences_list, start=1):
        ev_title = ev.get("Acceptance_Evidence", "Non spécifié")
        ev_criteria = "\n".join(ev.get("Acceptance_Criteria", []))
        evidences_text += f"\n**Acceptance Evidence {idx} :** {ev_title}\n**Critères :**\n{ev_criteria}\n"

    base_prompt = f"""
**Contexte de l'Audit :**
* **Question d'évaluation :** {question_text}
* **Niveau de Maturité Cible :** {target_level}

**Exigences à vérifier :**
{evidences_text}

**Instructions :**
Analysez le contenu fourni ci-dessous. Répondez EXACTEMENT avec la structure suivante :

### 1. Évaluation Globale
**Résultat :** [OUI ou NON]
**Pourcentage :** [ex: 100%, 50%]
**Justification :** [Une phrase justifiant le résultat global.]

### 2. Détail par Preuve
[Pour chaque Preuve Requise :]
#### Preuve : [Copier le nom de la preuve]
**Statut :** [Satisfait / Partiellement Satisfait / Non Satisfait]

**Critères Satisfaits :**
- [Nom exact du critère] : [Information concrète réellement trouvée dans le document (citation courte, titre de section, valeur, date, version, etc.)]

**Critères Non Satisfaits (Manquants) :**
- [Nom exact du critère] : [Ce qui manque concrètement dans le document]
(Si aucun critère manquant, laissez cette liste entièrement vide — n'écrivez pas None, ni —, ni Aucun.)

Règles importantes pour les listes de critères :
- Chaque puce DOIT suivre le format : Critère : Information trouvée
- L'information trouvée doit provenir uniquement du document analysé (ne jamais inventer).
- Ne recopiez pas toute la synthèse dans chaque ligne.

### 3. Conclusion
[Conclusion finale de l'audit.]

**Contenu à analyser :**
"""

    if file_data["type"] == "text":
        content_text = file_data["content"][:20000]
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{base_prompt}\n---\n{content_text}\n---"}
        ]
    elif file_data["type"] == "image":
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": base_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{file_data['mime_type']};base64,{file_data['content']}"
                        }
                    }
                ]
            }
        ]

    try:
        response = client.chat.completions.create(
            model=settings.OLLAMA_MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=2500
        )
        return response.choices[0].message.content
    except Exception as e:
        return (
            f"❌ Erreur de l'API. Vérifiez qu'Ollama tourne sur {settings.OLLAMA_BASE_URL} "
            f"avec le modèle `{settings.OLLAMA_MODEL}`. Détails : {str(e)}"
        )

# -------------------------------------------------------------------
# Fonctions de Génération des Rapports (PDF et JSON)
# -------------------------------------------------------------------
# generate_pdf_report est fourni par pdf_report.py (présentation uniquement)

def generate_json_report(report_text, domain, question, level):
    """Extrait la structure complète du rapport pour la convertir en JSON."""
    report_data = {
        "metadata": {
            "domaine": domain,
            "question": question,
            "niveau_cible": level
        },
        "evaluation_globale": {},
        "details_preuves": [],
        "conclusion": "",
        "rapport_complet": report_text
    }

    # 1. Évaluation Globale
    s1_match = re.search(r'### 1\.\s*Évaluation Globale(.*?)### 2\.', report_text, re.DOTALL | re.IGNORECASE)
    if s1_match:
        s1_text = s1_match.group(1).strip()
        res = re.search(r'\*\*Résultat\s*:\*\*\s*(OUI|NON)', s1_text, re.IGNORECASE)
        pct = re.search(r'\*\*Pourcentage\s*:\*\*\s*(\d+\s*%)', s1_text, re.IGNORECASE)
        just = re.search(r'\*\*Justification\s*:\*\*\s*(.*)', s1_text, re.IGNORECASE | re.DOTALL)
        
        report_data["evaluation_globale"] = {
            "resultat": res.group(1).upper() if res else "Indéterminé",
            "pourcentage": pct.group(1) if pct else "N/A",
            "justification": just.group(1).strip() if just else "N/A"
        }

    # 2. Détail par Preuve (CORRECTION: Extraction fine de chaque preuve)
    s2_match = re.search(r'### 2\.\s*Détail par Preuve(.*?)### 3\.', report_text, re.DOTALL | re.IGNORECASE)
    if s2_match:
        preuves_text = s2_match.group(1).strip()
        preuves_blocs = re.split(r'####\s*Preuve\s*:', preuves_text)
        
        preuves_list = []
        for bloc in preuves_blocs:
            if not bloc.strip():
                continue
                
            lines = bloc.strip().split('\n')
            titre_preuve = lines[0].strip()
            
            # Statut
            statut_match = re.search(r'\*\*Statut\s*:\*\*\s*(.*)', bloc, re.IGNORECASE)
            statut = statut_match.group(1).strip() if statut_match else "Non défini"
            
            # Critères satisfaits
            sat_match = re.search(r'\*\*Critères Satisfaits\s*:\*\*(.*?)(?=\*\*Critères Non Satisfaits|$)', bloc, re.DOTALL | re.IGNORECASE)
            sat_list = []
            if sat_match:
                sat_list = [l.strip().replace('- ', '') for l in sat_match.group(1).split('\n') if l.strip() and l.strip() != '-']
                
            # Critères non satisfaits
            non_sat_match = re.search(r'\*\*Critères Non Satisfaits \(Manquants\)\s*:\*\*(.*?)(?=$)', bloc, re.DOTALL | re.IGNORECASE)
            non_sat_list = []
            if non_sat_match:
                non_sat_list = [l.strip().replace('- ', '') for l in non_sat_match.group(1).split('\n') if l.strip() and l.strip() != '-']
            
            preuves_list.append({
                "titre": titre_preuve.replace('**', ''),
                "statut": statut.replace('**', ''),
                "criteres_satisfaits": sat_list,
                "criteres_non_satisfaits": non_sat_list
            })
            
        report_data["details_preuves"] = preuves_list
        
    # 3. Conclusion
    s3_match = re.search(r'### 3\.\s*Conclusion(.*)', report_text, re.DOTALL | re.IGNORECASE)
    if s3_match:
        report_data["conclusion"] = s3_match.group(1).strip()

    return json.dumps(report_data, indent=4, ensure_ascii=False).encode('utf-8')

# -------------------------------------------------------------------
# Fonction de Rendu UI Amélioré
# -------------------------------------------------------------------
def render_audit_report(report_text):
    s1_pattern = r'### 1\.\s*Évaluation Globale(.*?)### 2\.'
    s2_pattern = r'### 2\.\s*Détail par Preuve(.*?)### 3\.'
    s3_pattern = r'### 3\.\s*Conclusion(.*)'
    
    try:
        s1_match = re.search(s1_pattern, report_text, re.DOTALL | re.IGNORECASE)
        s2_match = re.search(s2_pattern, report_text, re.DOTALL | re.IGNORECASE)
        s3_match = re.search(s3_pattern, report_text, re.DOTALL | re.IGNORECASE)
        
        if s1_match:
            s1_text = s1_match.group(1).strip()
            res_match = re.search(r'\*\*Résultat\s*:\*\*\s*(OUI|NON)', s1_text, re.IGNORECASE)
            pct_match = re.search(r'\*\*Pourcentage\s*:\*\*\s*(\d+\s*%)', s1_text, re.IGNORECASE)
            just_match = re.search(r'\*\*Justification\s*:\*\*\s*(.*)', s1_text, re.IGNORECASE | re.DOTALL)
            
            is_oui = res_match and res_match.group(1).upper() == "OUI"
            is_non = res_match and res_match.group(1).upper() == "NON"
            
            st.markdown("### 1. Évaluation Globale")
            
            col1, col2 = st.columns(2)
            with col1:
                if is_oui: st.success("## Résultat : OUI ✅")
                elif is_non: st.error("## Résultat : NON ❌")
                else: st.warning("## Résultat : INDÉTERMINÉ")
            
            with col2:
                if pct_match:
                    score_color = "success" if is_oui else ("warning" if "50" in pct_match.group(1) else "error")
                    if score_color == "success": st.success(f"### Satisfaction : {pct_match.group(1)}")
                    elif score_color == "warning": st.warning(f"### Satisfaction : {pct_match.group(1)}")
                    else: st.error(f"### Satisfaction : {pct_match.group(1)}")
            
            if just_match:
                st.write(f"**Justification :** {just_match.group(1).strip()}")
            else:
                st.write(s1_text)
            
            st.markdown("---")
            
        if s2_match:
            st.markdown("### 2. Détail par Preuve et Critères")
            preuves_text = s2_match.group(1).strip()
            preuves_blocs = re.split(r'####\s*Preuve\s*:', preuves_text)
            
            for bloc in preuves_blocs:
                if not bloc.strip(): continue
                with st.container():
                    lines = bloc.strip().split('\n')
                    title = lines[0].strip()
                    content = '\n'.join(lines[1:]).strip()
                    
                    if "Satisfait" in content and "Non Satisfait" not in content and "Partiellement" not in content:
                        st.success(f"**Preuve :** {title}")
                    elif "Partiellement Satisfait" in content:
                        st.warning(f"**Preuve :** {title}")
                    else:
                        st.error(f"**Preuve :** {title}")
                    
                    st.markdown(content)
                    st.markdown("<br>", unsafe_allow_html=True)
            
            st.markdown("---")
            
        if s3_match:
            st.markdown("### 3. Conclusion")
            st.info(f"💡 {s3_match.group(1).strip()}")
            
        if not s1_match and not s2_match:
            st.markdown(report_text)
            
    except Exception:
        st.markdown(report_text)

# -------------------------------------------------------------------
# Interface Utilisateur Principale
# -------------------------------------------------------------------
if "audit_report" not in st.session_state:
    st.session_state.audit_report = None
if "current_config" not in st.session_state:
    st.session_state.current_config = None

domains_data = load_domains(JSON_DIR)

if not domains_data:
    st.warning("⚠️ Aucun fichier JSON n'a été trouvé. Veuillez placer vos fichiers dans le même dossier que app.py.")
else:
    logo_path = next((p for p in ("Dev_logo.png", "dev_logo.png") if os.path.exists(p)), None)
    if logo_path:
        st.sidebar.image(logo_path, use_container_width=True)
    
    st.sidebar.header("⚙️ Configuration de l'Audit")
    
    selected_domain = st.sidebar.selectbox("1️⃣ Domaine", list(domains_data.keys()))
    domain_json = domains_data[selected_domain]
    questions_list = domain_json.get("Questions", [])
    
    if questions_list:
        q_options = [f"{q.get('Question_ID', 'ID Inconnu')} - {q.get('Question', '')}" for q in questions_list]
        selected_q_display = st.sidebar.selectbox("2️⃣ Question", q_options)
        selected_question = next(q for q in questions_list if f"{q.get('Question_ID', 'ID Inconnu')} - {q.get('Question', '')}" == selected_q_display)
        selected_q_text = selected_question.get("Question", "")
        
        levels = selected_question.get("Levels", [])
        if levels:
            selected_level_name = st.sidebar.selectbox("3️⃣ Niveau ciblé", [lvl["Level_Name"] for lvl in levels])
            selected_level_data = next(lvl for lvl in levels if lvl["Level_Name"] == selected_level_name)
            evidences_list = selected_level_data.get("Evidences", [])
            
            current_config = f"{selected_domain}_{selected_q_display}_{selected_level_name}"
            if st.session_state.current_config != current_config:
                st.session_state.audit_report = None
                st.session_state.current_config = current_config
            
            st.markdown("### 📋 Exigences du Niveau")
            
            if not evidences_list:
                st.info("Aucune évidence spécifiée pour ce niveau.")
            else:
                for idx, ev in enumerate(evidences_list, start=1):
                    with st.expander(f"📌 Acceptance Evidence {idx} : {ev.get('Acceptance_Evidence', 'Non spécifiée')}", expanded=True):
                        criteria = ev.get("Acceptance_Criteria", [])
                        if criteria:
                            st.write("**Acceptance Criteria :**")
                            for c in criteria:
                                st.write(f"- {c}")
                        else:
                            st.write("*Aucun critère spécifique listé.*")

            st.markdown("---")
            st.markdown("### 📎 Upload du Document")
            uploaded_file = st.file_uploader(
                "Fichiers supportés : PDF, Excel (XLSX), Word (DOCX), TXT, Images (PNG, JPG)", 
                type=["pdf", "txt", "xlsx", "xls", "docx", "png", "jpg", "jpeg"]
            )

            if uploaded_file is not None:
                if st.button("🚀 Lancer l'Audit par l'IA", use_container_width=True):
                    with st.spinner("Traitement du fichier et analyse en cours..."):
                        file_data = process_uploaded_file(uploaded_file)
                        
                        if file_data["type"] == "error":
                            st.error(file_data['content'])
                        else:
                            st.session_state.audit_report = evaluate_evidence_with_llm(
                                question_text=selected_q_text,
                                target_level=selected_level_name,
                                evidences_list=evidences_list,
                                file_data=file_data
                            )

            if st.session_state.audit_report:
                st.markdown("---")
                st.markdown("## 📊 Rapport d'Audit")
                
                render_audit_report(st.session_state.audit_report)
                
                st.markdown("---")
                st.markdown("### 💾 Exporter le Rapport")
                
                pdf_bytes = generate_pdf_report(
                    st.session_state.audit_report, 
                    selected_domain, 
                    selected_q_text, 
                    selected_level_name
                )
                
                json_bytes = generate_json_report(
                    st.session_state.audit_report, 
                    selected_domain, 
                    selected_q_text, 
                    selected_level_name
                )
                
                col_dl1, col_dl2 = st.columns(2)
                
                with col_dl1:
                    st.download_button(
                        label="📄 Télécharger en PDF",
                        data=pdf_bytes,
                        file_name="rapport_audit_ndi.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                with col_dl2:
                    st.download_button(
                        label="🗂️ Télécharger en JSON",
                        data=json_bytes,
                        file_name="rapport_audit_ndi.json",
                        mime="application/json",
                        use_container_width=True
                    )