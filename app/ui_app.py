import requests, streamlit as st, json
import json

raw = draft.get("raw")
if raw and not draft.get("cover_letter_markdown"):
    try:
        draft = json.loads(raw)
    except Exception:
        pass

st.set_page_config(page_title="qPro", layout="wide")
st.title("qPro — Tailored Job Application")

job = st.text_area("Paste job post", height=260)
if st.button("Generate"):
    with st.spinner("Generating..."):
        r = requests.post("http://127.0.0.1:8000/apply", json={"job_post": job}, timeout=180)
        r.raise_for_status()
        draft = r.json().get("draft", {})
    st.subheader("Cover Letter (Markdown)")
    st.code(draft.get("cover_letter_markdown", draft.get("raw","")), language="markdown")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("CV Bullets")
        st.code("\n".join("• "+b for b in draft.get("cv_bullets", [])))
    with col2:
        st.subheader("ATS Report")
        st.json(draft.get("ats_report", {}))
