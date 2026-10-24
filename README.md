# Kenya CBC AI Learning Assistant 🇰🇪

[![Curriculum](https://img.shields.io/badge/Curriculum-KICD%20CBC%20Upper%20Primary-blue.svg)](https://kicd.ac.ke/)
[![Grades](https://img.shields.io/badge/Grades-4%2C%205%2C%206-green.svg)](#)
[![Model](https://img.shields.io/badge/Engine-Gemini%203.5%20%7C%20vLLM%20Qwen-purple.svg)](#)
[![Cost](https://img.shields.io/badge/Cost-%240.045%2Fchild%2Fmonth-teal.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-orange.svg)](#)

A production-grade, culturally attuned conversational AI learning companion engineered for the **Kenya Competency Based Curriculum (CBC)** Upper Primary cohort (Grades 4–6). 

Designed to overcome severe pupil-to-teacher disparities (exceeding 1:45 in public primary schools), the system combines **Hybrid RAG (BM25 + Dense Semantic Vector + Reciprocal Rank Fusion)**, a **10-Tier Governed Orchestration Harness**, **Multi-Layer Validation Guardrails**, and **Real-Time OpenTelemetry Observability** at an ultra-low fiscal run-rate of **$0.045 per child per month**.

---

## 🌟 Key Capabilities & Architectural Innovations

1. **Strict KICD Curriculum Grounding (0.00% Hallucination Tolerance):**  
   Answers strictly derived from approved KICD syllabus documents (Science & Tech, Mathematics, English, and Agriculture).
2. **Hybrid RAG with Reciprocal Rank Fusion ($k=60$):**  
   Fuses sparse lexical BM25 matching (for Kenyan domain terms like *shamba*, *stomata*, *kwashiorkor*) with dense multilingual semantic vector search.
3. **10-Tier Governed Orchestration Harness:**  
   Includes contextual coreference query rewriting, system prompt assembling, foundation inference, and multi-tier post-generation validation.
4. **Bounded Self-Correction Feedback Loop:**  
   Automated readability (Flesch-Kincaid Grade 4.0–6.5) and factual grounding checks with a strict limit of $\le 3$ retries.
5. **Decoupled Multimodal Vision OCR:**  
   Pre-processes student textbook snapshots at the edge, reducing multimodal token costs by 78.4%.
6. **Ultra-Low Sizing & Financial Model:**  
   Serves 38,400 active learners on 2&times; NVIDIA L4 instances at **$0.045/child/month** and **$0.000062/query**.
7. **Bilingual Resilience:**  
   Full support for standard Kenyan English and Kiswahili code-switching.

---

## 📸 System Screenshots

<div align="center">
  <table>
    <tr>
      <td align="center"><b>Clean Welcome Screen (Minimal Cognitive Load)</b></td>
      <td align="center"><b>Live Pedagogical Dialogue (Grade 6 Photosynthesis)</b></td>
    </tr>
    <tr>
      <td><img src="report_assets/ui_welcome_chatgpt_style.png" width="440" alt="Welcome UI"></td>
      <td><img src="report_assets/ui_active_pedagogical_conversation.png" width="440" alt="Chat UI"></td>
    </tr>
    <tr>
      <td align="center"><b>Capacity Model & Telemetry Drawer</b></td>
      <td align="center"><b>OpenTelemetry Distributed Spans 1–5</b></td>
    </tr>
    <tr>
      <td><img src="report_assets/telemetry_capacity_drawer.png" width="440" alt="Telemetry Drawer"></td>
      <td><img src="report_assets/opentelemetry_spans_trace.png" width="440" alt="OpenTelemetry Spans"></td>
    </tr>
  </table>
</div>

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.9+
- A Google AI Studio Gemini API Key (or self-hosted vLLM endpoint)

### 2. Clone and Setup
```bash
git clone https://github.com/Shubhamver45/Kenya-AI-Tutor.git
cd Kenya-AI-Tutor

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the template and add your API key:
```bash
cp .env.example .env
```
Edit `.env`:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-3.5-flash-lite
PORT=5050
```

### 4. Launch the Web Application
```bash
python3 app.py
```
Open **http://localhost:5050** in your browser to experience the tutor!

---

## 🔬 Testing & Verification Tools

Run individual pipeline stages directly from the command line:

- **Test Hybrid Search (BM25 vs Vector vs RRF):**
  ```bash
  python3 retrieval/hybrid_search.py
  ```
- **Run Capacity & Financial Model Calculation:**
  ```bash
  python3 cost/calculator.py
  ```
- **Execute 16-Test Bilingual Evaluation Benchmark:**
  ```bash
  python3 evaluation/eval_suite.py
  ```
- **Compile the Official PDF Architecture Report:**
  ```bash
  python3 build_professional_report.py
  ```

---

## 🏛️ Project Structure

```
├── app.py                     # Flask web server and conversational API endpoints
├── pipeline.py                # 10-tier governed orchestration and RAG harness
├── requirements.txt           # Python application dependencies
├── .env.example               # Environment template for API keys
├── ARCHITECTURE.md            # Detailed systems architecture specification
│
├── data/
│   ├── curriculum.json        # KICD Upper Primary curriculum knowledge base
│   └── eval_dataset.json      # Bilingual evaluation test cases
│
├── retrieval/
│   └── hybrid_search.py       # BM25, Dense Vector, and RRF rank fusion logic
├── llm/
│   └── client.py              # LLM client supporting Gemini 3.5 & vLLM
├── cost/
│   └── calculator.py          # Section 11 financial capacity and compute calculator
├── telemetry/
│   └── collector.py           # OpenTelemetry 5-span execution tracing
├── evaluation/
│   └── eval_suite.py          # Automated pedagogical benchmark runner
│
├── templates/
│   └── index.html             # ChatGPT-style clean web interface
├── static/
│   ├── css/styles.css         # Modern, responsive design system
│   └── js/app.js              # Client state, session history, and streaming
│
├── report_assets/             # High-res UI screenshots and architecture visuals
└── Kenya_AI_Tutor_Professional_Engineering_Report.pdf  # 12-page official delivery report
```

---

## 📜 License & Compliance

Distributed under the MIT License. Designed in compliance with the **Kenya Data Protection Act 2019** and the **KICD Competency Based Curriculum Guidelines**.
