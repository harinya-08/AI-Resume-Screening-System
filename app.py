import streamlit as st
import openai
import PyPDF2
import docx
import io
import json
import os
from dotenv import load_dotenv
load_dotenv()
st.set_page_config(
    page_title="AI Resume Advisor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #1a1a1a; }
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }
    
    .score-card {
        background: white;
        border-radius: 14px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid #f0f0f0;
    }
    
    .score-number {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    /* Force Black text in result sections */
    .section-card {
        background: white;
        border-radius: 14px;
        padding: 1.5rem 1.8rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 16px rgba(0,0,0,0.06);
        border-left: 4px solid #667eea;
    }
    
    .section-card h3 { color: #2d3748; margin-top: 0; font-weight: 700; }
    .section-card p, .section-card li { color: #000000 !important; font-size: 1rem; line-height: 1.6; }

    .tag {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
        margin: 0.2rem;
    }
    .tag-green { background: #d4edda; color: #155724; }
    .tag-red { background: #f8d7da; color: #721c24; }

    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        font-weight: 600;
        border: none;
        padding: 0.6rem;
    }
</style>
""", unsafe_allow_html=True)
def extract_text(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif name.endswith(".docx"):
        doc = docx.Document(io.BytesIO(uploaded_file.read()))
        return "\n".join(para.text for para in doc.paragraphs)
    else:
        return uploaded_file.read().decode("utf-8", errors="ignore")
def analyze_resume(api_key: str, resume_text: str, job_description: str, model: str) -> dict:
    client = openai.OpenAI(api_key=api_key)
    
    system_prompt = """You are an expert career coach and document validator.
    FIRST: Check if the provided 'RESUME' text is actually a professional resume, CV, or LinkedIn profile.
    If it is NOT a resume (e.g., a book, random article, news, menu, or generic text), return ONLY this JSON: {"is_valid": false}.
    If it IS a resume, return a JSON with: 
    {"is_valid": true, "match_score": int, "summary": str, "strengths": list, "gaps": list, 
    "missing_keywords": list, "matched_keywords": list, "experience_feedback": str, 
    "skills_feedback": str, "education_feedback": str, "ats_tips": list, 
    "rewrite_suggestions": [{"original": str, "improved": str}], "action_plan": list}"""
    user_prompt = f"RESUME TEXT:\n{resume_text[:4000]}\n\nJOB DESCRIPTION:\n{job_description[:2000]}"
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        response_format={ "type": "json_object" }
    )

    return json.loads(response.choices[0].message.content)

def score_color(score: int) -> str:
    if score >= 75: return "#28a745"
    if score >= 50: return "#ffc107"
    return "#dc3545"
with st.sidebar:
    st.markdown("## ⚙️ Configuration")
    user_api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    model_choice = st.selectbox("Model", ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"])
    st.markdown("---")
    st.info("1. Enter API Key\n2. Upload Resume\n3. Paste JD\n4. Analyze")
st.markdown("""<div class='main-header'><h1>📄 AI Resume Advisor</h1><p>Instant, AI-powered resume optimization</p></div>""", unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")
with col1:
    st.markdown("### 📤 Upload Resume")
    resume_file = st.file_uploader("PDF, DOCX, TXT", type=["pdf", "docx", "txt"], label_visibility="collapsed")

with col2:
    st.markdown("### 📝 Job Description")
    job_desc = st.text_area("Paste JD here...", height=180, label_visibility="collapsed")

analyze_btn = st.button("🔍 Analyze My Resume", use_container_width=True)

if analyze_btn:
    if not user_api_key:
        st.error("⛔ Please enter your OpenAI API key.")
    elif not resume_file:
        st.error("⛔ Please upload your resume.")
    elif not job_desc.strip():
        st.error("⛔ Please paste a job description.")
    else:
        with st.spinner("🤖 Validating and Analyzing..."):
            try:
                resume_content = extract_text(resume_file)
                result = analyze_resume(user_api_key, resume_content, job_desc, model_choice)
                if result.get("is_valid") is False:
                    st.error("🚫 **Invalid Document Detected.** The uploaded file does not appear to be a professional resume. Please upload a valid resume or CV.")
                else:
                    st.markdown("---")
                    st.header("📊 Analysis Results")
                    
                    score = result.get("match_score", 0)
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"<div class='score-card'><div class='score-number' style='color:{score_color(score)}'>{score}%</div><div>Match Score</div></div>", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"<div class='score-card'><div class='score-number'>{len(result.get('matched_keywords', []))}</div><div>Keywords Matched</div></div>", unsafe_allow_html=True)
                    with c3:
                        st.markdown(f"<div class='score-card'><div class='score-number'>{len(result.get('gaps', []))}</div><div>Gaps Found</div></div>", unsafe_allow_html=True)

                    st.markdown(f"<div class='section-card'><h3>💬 Overall Assessment</h3><p>{result.get('summary', '')}</p></div>", unsafe_allow_html=True)
                    
                    # Keywords
                    matched = "".join(f"<span class='tag tag-green'>✓ {k}</span>" for k in result.get("matched_keywords", []))
                    missing = "".join(f"<span class='tag tag-red'>✗ {k}</span>" for k in result.get("missing_keywords", []))
                    st.markdown(f"<div class='section-card'><h3>🔑 Keywords Analysis</h3><p><b>Matched:</b></p><div>{matched}</div><br><p><b>Missing:</b></p><div>{missing}</div></div>", unsafe_allow_html=True)
                    plan = result.get("action_plan", [])
                    if plan:
                        steps = "".join(f"<li>{s}</li>" for s in plan)
                        st.markdown(f"<div class='section-card'><h3>🚀 Your Action Plan</h3><ul>{steps}</ul></div>", unsafe_allow_html=True)
                    
                    st.success("✅ Analysis complete!")

            except json.JSONDecodeError:
                st.error("⚠️ AI returned invalid data. Please try again.")
            except Exception as e:
                st.error(f"❌ Error: {e}")

st.markdown("<p style='text-align:center; color:#aaa; margin-top:50px;'>Built with Streamlit & OpenAI</p>", unsafe_allow_html=True)
