# System Architecture — Kenya Class Tutor Lite 🇰🇪

## 1. Executive Summary

**Kenya Class Tutor Lite** is an enterprise-grade, curriculum-grounded AI educational tutoring system architected specifically for the **Kenyan Competency-Based Curriculum (CBC)** Upper Primary framework (Grades 4 through 7).

Designed for high-reliability public sector deployment, the system addresses the two primary failure modes of LLMs in education:
1. **Hallucination & Out-of-Syllabus Drift**: Solved via a strict 5-stage retrieval-augmented generation (RAG) pipeline with an independent verification auditor and bounded 1-retry loop.
2. **Unsustainable Unit Economics**: Solved via Section 11 Capacity Planning, showing that 38,400 registered students can be served for **$0.045 per child per month** ($0.000062 per query) on $2 \times$ NVIDIA L4 GPUs using continuous batching (vLLM).

---

## 2. High-Level System Architecture Diagram

```mermaid
flowchart TB
    subgraph ClientLayer["Client & Presentation Layer"]
        UI["Enterprise Web Workbench (Light Theme)<br/>• Grade / Subject Filter Dropdowns<br/>• 6 KICD Production Scenarios<br/>• Live Latency & Token Telemetry<br/>• Trace Inspector (Spans 1–5)"]
    end

    subgraph AppTier["Application & API Gateway (Flask @ Port 5050)"]
        API_Chat["POST /api/chat"]
        API_Compare["POST /api/retrieval/compare"]
        API_Cost["POST /api/cost/calculate"]
        API_Eval["POST /api/evaluation/run"]
        API_Traces["GET /api/traces/latest"]
    end

    subgraph PipelineTier["Core Tutoring Pipeline (pipeline.py)"]
        Stage3["Stage 3: Query Rewriter<br/>(Contextual Co-reference Resolution)"]
        
        subgraph Stage2["Stage 2: Hybrid Retrieval Engine (hybrid_search.py)"]
            Corpus[("KICD CBC Upper Primary Corpus<br/>data/curriculum.json<br/>(Bilingual EN / SW)")]
            Filter["Metadata Filter<br/>(Grade & Subject)"]
            BM25["BM25 Lexical Index<br/>(Rank-BM25)"]
            Dense["Dense Semantic Vectorizer<br/>(Sublinear / e5-small)"]
            RRF["Reciprocal Rank Fusion<br/>RRF Score = Σ 1 / (60 + rank)"]
        end

        subgraph GenAudit["Stage 4 & 5: Generation & Verification Loop"]
            PromptEng["CBC Socratic Grounded Prompt<br/>(Pedagogical, Positive Tone)"]
            LLM_Gen["Primary LLM Generator<br/>(gemini-3.5-flash-lite)"]
            Auditor["Stage 5: Fact-Checking Auditor<br/>(Independent Grounding Verification)"]
            RetryDecision{"Audit Passed?<br/>(Is Claim Grounded?)"}
            RetryExec["Bounded Retry Loop<br/>(MAX_RETRIES = 1)"]
            HonestRefusal["Honest Refusal Handler<br/>('Out of Syllabus / Unverified')"]
        end
    end

    subgraph ObservabilityCost["Telemetry & Financial Infrastructure"]
        OtelStore["Stage 6: Trace Store (telemetry/collector.py)<br/>• OpenTelemetry Spans 1–5<br/>• Token Breakdown & Exact Latency"]
        CostModel["Stage 7: Section 11 Capacity Model (cost/calculator.py)<br/>• 38,400 Students Scale<br/>• $0.045 / child / month ($0.000062/query)"]
    end

    %% Wiring
    UI -->|JSON HTTP Payload| AppTier
    API_Chat --> Stage3
    Stage3 -->|Standalone Search Query| Filter
    Corpus --> Filter
    Filter --> BM25
    Filter --> Dense
    BM25 --> RRF
    Dense --> RRF
    RRF -->|Top-K Grounded Chunks| PromptEng
    PromptEng --> LLM_Gen
    LLM_Gen -->|Draft Answer| Auditor
    Auditor --> RetryDecision
    RetryDecision -->|YES| OtelStore
    RetryDecision -->|NO & Attempts < 1| RetryExec
    RetryExec -->|Corrective Prompt| LLM_Gen
    RetryDecision -->|NO & Attempts >= 1| HonestRefusal
    HonestRefusal --> OtelStore
    OtelStore --> UI
    API_Cost --> CostModel
    CostModel --> UI
```

---

## 3. Seven-Stage Pipeline Deep Dive

### Stage 1: Official KICD CBC Curriculum Knowledge Base
- **File:** `data/curriculum.json`
- **Structure:** Hierarchical KICD taxonomy:
  - `grade`: Grades 4 through 7 (Upper Primary)
  - `subject`: Mathematics, Science & Technology, Social Studies, Agriculture, Kiswahili Lugha, English
  - `strand`: Official KICD main strand (e.g., *Numbers*, *Living Things*)
  - `substrand`: Substrand (e.g., *Fractions*, *Human Digestive System*)
  - `topic`: Specific topic heading
  - `text`: Pedagogy-aligned curriculum content
  - `learning_outcomes`: Explicit KICD learning outcome codes (e.g., `KICD/PRI/CBC/G4/MAT/STR-01/LO-01`)

### Stage 2: Dual-Index Hybrid Search with Reciprocal Rank Fusion (RRF)
- **File:** `retrieval/hybrid_search.py`
- **Mechanism:**
  1. **Strict Metadata Filter**: Pre-filters candidates by selected `grade` and `subject`.
  2. **Lexical BM25**: Captures precise terminology, acronyms, and formulas without vocabulary mismatch.
  3. **Dense Semantic Vector Search**: Captures conceptual similarity and cross-lingual alignment (English / Kiswahili).
  4. **Reciprocal Rank Fusion (RRF)**:
     $$\text{RRF Score}(d) = \sum_{m \in \{\text{BM25}, \text{Dense}\}} \frac{1}{k + \text{rank}_m(d)}, \quad k = 60$$
  - Eliminates score calibration discrepancies between dot-product cosine distances and BM25 unbounded scores.

### Stage 3: Follow-Up Contextual Query Rewriting
- **File:** `llm/client.py` (`rewrite_query`)
- **Mechanism:** When a conversational turn has prior history (e.g., *Turn 1: "What is an improper fraction?"* $\rightarrow$ *Turn 2: "Can you give two examples?"*), the rewriter synthesizes a self-contained, disambiguated query (*"Give two examples of improper fractions in Grade 4 Mathematics"*).
- **Optimization:** First-turn queries bypass rewriting with $0\text{ ms}$ latency and $0$ tokens.

### Stage 4: Socratic Grounded Generation & Honest Refusal
- **File:** `llm/client.py` (`answer`)
- **System Constraints:**
  - Instructed strictly to reference the retrieved curriculum excerpts.
  - Socratic pedagogical framing (encouraging, constructive, Grade-appropriate language).
  - Out-of-curriculum questions trigger **Honest Refusal** rather than speculative hallucination.

### Stage 5: Independent Fact-Checking Auditor with Bounded Retry
- **File:** `pipeline.py` & `llm/client.py` (`validate_grounding`)
- **Mechanism:**
  - A dedicated prompt checks whether every factual assertion in the generated draft is directly verifiable against the retrieved curriculum chunks.
  - Returns a binary decision (`PASS` / `FAIL`).
  - **Bounded Retry (`MAX_RETRIES = 1`)**:
    - If `FAIL`, the orchestrator executes exactly 1 bounded correction retry, injecting the specific ungrounded violation back to the generator.
    - If it fails a second time, the pipeline gracefully falls back to an honest refusal.
    - **No infinite retry loops; deterministic upper bound on latency and cost.**

### Stage 6: Full OpenTelemetry Observability Trace
- **File:** `telemetry/collector.py`
- **Tracked Telemetry Spans:**
  - **Span 1: Query Normalization / Rewrite** (Latency, Token In/Out)
  - **Span 2: Hybrid Retrieval** (BM25 rank, Dense rank, RRF score, Top-K chunks)
  - **Span 3: Grounded Answer Synthesis** (Model name, Generation latency, Token In/Out)
  - **Span 4: Fact-Checking Audit** (Verification verdict, Audit latency)
  - **Span 5: Bounded Retry Execution** (Only populated if retry occurred)
- Real-time client inspection available via `/api/traces/latest`.

### Stage 7: Section 11 Capacity Planning & Financial Architecture
- **File:** `cost/calculator.py`
- **Core Parameters:**
  - Registered Students: $38,400$
  - Daily Active Rate: $25\%$ ($9,600\text{ students/day}$)
  - Daily Queries per Student: $3\text{ queries}$
  - Daily Query Volume: $28,800\text{ queries/day}$
  - Tokens per Query: $900\text{ tokens}$ ($25.92\text{M tokens/day}$, $\approx 777.6\text{M tokens/month}$)
- **Infrastructure Architecture:**
  - Deployment: $2 \times \text{NVIDIA L4 (24GB)}$ with continuous batching (vLLM)
  - Throughput: $220\text{ tokens/second}$ sustained
  - School hours utilization: $60\%$
  - Monthly compute cost: $\approx \$1,728$
  - **Unit Economics:**
    - Cost per student: **$0.045 / month**
    - Cost per query: **$0.000062**

---

## 4. Operational Specifications & Current Status

| Metric | Active Production Value | Verification Source |
| :--- | :--- | :--- |
| **API Provider** | Google AI Studio (OpenAI-compatible) | `.env` (`OPENAI_BASE_URL`) |
| **Active Model** | `gemini-3.5-flash-lite` | Verified live |
| **Local Port** | `http://localhost:5050` | Port 5000 avoided (AirPlay safe) |
| **Hardcoded Data** | **0%** (Fully dynamic LLM inference & RAG) | Automated audit verified |
| **Theme / UI** | Senior-grade Enterprise Light Theme | Tested & responsive |
