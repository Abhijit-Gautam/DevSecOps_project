# Architecture & Data Flow

Visual guide to the application structure and data flow.

## 📊 Application Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    User Interface Layer                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  app/page.tsx (Main Dashboard)                         │    │
│  │  - Orchestrates all components                         │    │
│  │  - Manages report state                                │    │
│  │  - Handles upload/results flow                         │    │
│  └────────────────────────────────────────────────────────┘    │
│           │                          │                           │
│           ▼                          ▼                           │
│  ┌─────────────────────┐  ┌──────────────────────────┐        │
│  │   Upload View       │  │    Results Dashboard     │        │
│  ├─────────────────────┤  ├──────────────────────────┤        │
│  │ - Upload Section    │  │ - Verdict Card           │        │
│  │ - Feature Cards     │  │ - Agent Panel            │        │
│  └─────────────────────┘  │ - Highlights Viewer      │        │
│                           │ - XAI Panel              │        │
│                           │ - FOL Verifier           │        │
│                           │ - Thought Timeline       │        │
│                           │ - Processing Screen      │        │
│                           └──────────────────────────┘        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
          │
          │  API Calls
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API Integration Layer                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  lib/api-client.ts (Type-Safe API Client)          │        │
│  │  - evaluateFile()                                   │        │
│  │  - evaluateText()                                   │        │
│  │  - getReports()                                     │        │
│  │  - healthCheck()                                    │        │
│  │  - Error handling & response mapping               │        │
│  └─────────────────────────────────────────────────────┘        │
│           │                                                       │
│           ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐        │
│  │  lib/types.ts (TypeScript Interfaces)              │        │
│  │  - ReportResponse                                   │        │
│  │  - UnifiedVerdict                                   │        │
│  │  - AgentEvaluation                                  │        │
│  │  - XAIResult, FOLResult, etc.                      │        │
│  └─────────────────────────────────────────────────────┘        │
│           │                                                       │
│           │  HTTPS/CORS
│           ▼
└─────────────────────────────────────────────────────────────────┘
          │
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│              Flask Backend API (Python)                          │
├─────────────────────────────────────────────────────────────────┤
│  - POST /api/evaluate/upload                                     │
│  - POST /api/evaluate/text                                       │
│  - GET /api/reports                                              │
│  - GET /api/health                                               │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 User Journey & Data Flow

### Step 1: Upload Section
```
User selects file
    │
    ▼
[upload-section.tsx]
    │
    ├─ Validates file (size, type)
    ├─ Displays file preview
    ├─ User toggles options (SRLM, XAI, FOL, Highlights)
    │
    ▼
[User clicks "Evaluate Report"]
    │
    ├─ Creates FormData with file + options
    ├─ Calls: apiClient.evaluateFile(file, options)
    │
    ▼
[Processing Screen Displayed]
    │
    └─ Shows 5-step animation
```

### Step 2: Backend Processing
```
Backend receives POST /api/evaluate/upload
    │
    ├─ Parse report structure
    ├─ Run RoBERTa ML model
    ├─ Run 6 specialized AI agents
    ├─ Master Arbiter synthesis
    ├─ XAI explanation generation
    ├─ FOL logic verification
    │
    ▼
Returns ReportResponse (JSON)
```

### Step 3: Results Dashboard
```
Frontend receives ReportResponse
    │
    ├─ Extract unified_verdict
    │  └─ [Verdict Card]
    │
    ├─ Extract agent_evaluations
    │  └─ [Agent Panel] (expandable cards)
    │
    ├─ Extract highlight_data
    │  └─ [Highlights Viewer] (colored tokens)
    │
    ├─ Extract xai_result
    │  └─ [XAI Panel] (explanations, roadmap)
    │
    ├─ Extract fol_result
    │  └─ [FOL Verifier] (axiom checks)
    │
    └─ Extract thought_process
       └─ [Thought Timeline] (execution steps)
```

## 📱 Component Hierarchy

```
RootLayout
└── Main Page (app/page.tsx)
    │
    ├── Upload View
    │   ├── UploadSection
    │   │   ├── FileInput
    │   │   ├── DragDropArea
    │   │   └── OptionToggles
    │   │
    │   └── FeatureOverviewCards (6)
    │
    └── Results View
        ├── ProcessingScreen (loading)
        │   └── StepIndicators (5 steps)
        │
        └── Dashboard
            ├── ReportSummary
            ├── VerdictCard
            │   ├── FinalVerdict Badge
            │   ├── OverallScore
            │   ├── KeyStrengths
            │   ├── KeyWeaknesses
            │   └── PriorityRecommendations
            │
            ├── AgentPanel
            │   └── AgentEvaluationCards (6)
            │       ├── Accordion
            │       ├── VerdictBadge
            │       ├── ScoreDisplay
            │       ├── Reasoning
            │       ├── Evidence
            │       ├── Strengths/Weaknesses
            │       └── SelfRewardScore
            │
            ├── HighlightsViewer
            │   ├── TabsContainer
            │   │   ├── HighlightedTextTab
            │   │   └── LegendTab
            │   └── ColorIntensityScales
            │
            ├── XAIPanel
            │   ├── Tabs
            │   │   ├── Explanation
            │   │   │   ├── ModelReasoning
            │   │   │   ├── AttentionSummary
            │   │   │   └── DecisionFactors
            │   │   ├── KeySignals
            │   │   ├── ImprovementRoadmap
            │   │   └── Counterfactuals
            │
            ├── FOLVerifier
            │   ├── ConsistencyScore
            │   ├── SatisfiedRulesCount
            │   ├── ViolatedRulesCount
            │   ├── FormalStatements
            │   └── AxiomDetails (expandable)
            │
            └── ThoughtTimeline
                └── StepCards (11 total)
                    ├── Icon
                    ├── Title
                    ├── Description
                    └── Evidence
```

## 🔌 API Request/Response Pattern

### Upload File Flow
```
┌─ Frontend ─────────────────────────────────────────────────┐
│                                                              │
│  User uploads file                                          │
│      │                                                       │
│      ▼                                                       │
│  [upload-section.tsx]                                       │
│      │                                                       │
│      ├─ Create FormData                                    │
│      │  ├─ file                                            │
│      │  ├─ run_srlm: boolean                               │
│      │  ├─ run_highlights: boolean                         │
│      │  ├─ run_fol: boolean                                │
│      │  └─ run_xai: boolean                                │
│      │                                                       │
│      ▼                                                       │
│  [api-client.evaluateFile()]                               │
│      │                                                       │
│      ├─ fetch(POST /api/evaluate/upload, FormData)         │
│      ├─ handleResponse<ReportResponse>()                   │
│      ├─ Error handling                                     │
│      │                                                       │
│      ▼                                                       │
│  [page.tsx state update]                                   │
│      │                                                       │
│      └─ setReportData(response)                            │
│         └─ Triggers re-render with results                │
│                                                              │
└──────────────────────────────────────────────────────────────┘
           │
           │ HTTPS POST
           │ FormData
           │
           ▼
┌─ Backend ──────────────────────────────────────────────────┐
│                                                              │
│  POST /api/evaluate/upload                                 │
│      │                                                       │
│      ├─ Validate file                                      │
│      ├─ Parse report structure                             │
│      ├─ Run RoBERTa model                                  │
│      ├─ Run 6 SRLM agents                                  │
│      ├─ Master Arbiter synthesis                           │
│      ├─ XAI explanations                                   │
│      ├─ FOL verification                                   │
│      │                                                       │
│      ▼                                                       │
│  ReportResponse (JSON)                                     │
│      {                                                      │
│        report_id: "...",                                   │
│        unified_verdict: {...},                             │
│        agent_evaluations: [...],                           │
│        highlight_data: {...},                              │
│        xai_result: {...},                                  │
│        fol_result: {...},                                  │
│        thought_process: [...]                              │
│      }                                                      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
           │
           │ HTTPS Response
           │ JSON
           │
           ▼
┌─ Frontend ─────────────────────────────────────────────────┐
│                                                              │
│  Receive ReportResponse                                    │
│      │                                                       │
│      ├─ Parse JSON                                         │
│      ├─ Validate types                                     │
│      │                                                       │
│      ▼                                                       │
│  Render Components with Data                               │
│      │                                                       │
│      ├─ VerdictCard(verdict)                               │
│      ├─ AgentPanel(agents)                                 │
│      ├─ HighlightsViewer(highlights)                       │
│      ├─ XAIPanel(xai)                                      │
│      ├─ FOLVerifier(fol)                                   │
│      └─ ThoughtTimeline(timeline)                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## 🎨 Design System Structure

```
app/globals.css
├── Design Tokens (CSS Variables)
│   ├── Colors
│   │   ├── --background
│   │   ├── --foreground
│   │   ├── --primary
│   │   ├── --accent
│   │   └── [20+ more]
│   │
│   └── Spacing, Typography, Borders
│
tailwind.config.ts
├── Theme Configuration
│   ├── Colors
│   ├── Spacing
│   ├── Typography
│   ├── Border Radius
│   └── Shadows
│
Components/
├── UI Components (shadcn/ui)
│   ├── Card
│   ├── Button
│   ├── Badge
│   ├── Tabs
│   ├── Accordion
│   └── [30+ more]
│
└── Custom Components
    ├── Upload Section
    ├── Verdict Card
    ├── Agent Panel
    ├── Highlights Viewer
    ├── XAI Panel
    ├── FOL Verifier
    └── Thought Timeline
```

## 📊 Data Type Hierarchy

```
ReportResponse (Main)
├── parsed_data: ParsedData
│   ├── domain: string
│   ├── total_score: number
│   ├── sections: Section[]
│   └── document_quality: Record<string, number>
│
├── roberta_result: RoberTaResult
│   ├── predicted_label: string
│   ├── confidence: number
│   └── probabilities: Record<string, number>
│
├── unified_verdict: UnifiedVerdict
│   ├── final_verdict: string
│   ├── overall_score: number
│   ├── confidence: number
│   ├── executive_summary: string
│   ├── dimension_verdicts: Record<string, string>
│   ├── key_strengths: string[]
│   ├── key_weaknesses: string[]
│   └── priority_recommendations: string[]
│
├── agent_evaluations: AgentEvaluation[]
│   └── AgentEvaluation
│       ├── agent: string
│       ├── verdict: string
│       ├── score: number
│       ├── reasoning: string
│       ├── evidence: string[]
│       ├── strengths: string[]
│       ├── weaknesses: string[]
│       └── self_reward: {score, justification}
│
├── highlight_data: HighlightData
│   ├── highlighted_spans: HighlightSpan[]
│   │   ├── token: string
│   │   ├── start: number
│   │   ├── end: number
│   │   └── score: number
│   └── threshold: number
│
├── xai_result: XAIResult
│   ├── model_explanation: {reasoning, key_signals}
│   ├── section_explanations: Record<string, SectionExplanation>
│   ├── decision_factors: DecisionFactor[]
│   ├── counterfactuals: Counterfactual[]
│   └── improvement_roadmap: ImprovementRoadmapItem[]
│
├── fol_result: FOLResult
│   ├── verdict: string
│   ├── consistent: boolean
│   ├── consistency_score: number
│   ├── fol_statements: string[]
│   ├── satisfied_rules: string[]
│   ├── violated_rules: string[]
│   └── verification_details: VerificationDetail[]
│
└── thought_process: ThoughtStep[]
    └── ThoughtStep
        ├── step: number
        ├── title: string
        ├── description: string
        ├── evidence: string[]
        └── type: string
```

## 🚀 Deployment Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         CDN                                   │
│               (Static assets & caching)                      │
└────────────────────────────┬─────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────┐
│                    Vercel / Netlify                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Next.js Frontend (Production Build)                │   │
│  │  - Static analysis & bundle optimization            │   │
│  │  - Automatic code splitting                         │   │
│  │  - Image optimization                               │   │
│  │  - Environment variables injected at build time     │   │
│  └──────────────────────────────────────────────────────┘   │
│         │                                                     │
│         │ HTTPS                                              │
│         │                                                     │
│         ▼                                                     │
├──────────────────────────────────────────────────────────┤
│  API Gateway / Proxy (Optional)                          │
│  - CORS configuration                                   │
│  - Rate limiting                                        │
│  - Request logging                                      │
└────────────────────────────┬─────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────┐
│          Flask Backend (Docker / VPS / Cloud)                │
│  ├─ RoBERTa Model Server                                    │
│  ├─ Ollama (LLM Server)                                     │
│  ├─ SQLite Database                                         │
│  └─ API Routes & Orchestration                             │
└──────────────────────────────────────────────────────────────┘
```

## 🔐 Security Layers

```
User's Browser
    │
    ▼ Input Validation
[File size check, File type check]
    │
    ▼ HTTPS Encryption
[TLS/SSL Protocol]
    │
    ▼ CORS Validation
[Backend checks origin]
    │
    ▼ Request Validation
[Backend validates input]
    │
    ▼ Response Encryption
[HTTPS Response]
    │
    ▼ TypeScript Type Safety
[Frontend validates response shape]
    │
    ▼ Secure Display
[Sanitized rendering]
```

## 📈 Performance Optimization

```
Build Time Optimization:
├── Code Splitting (automatic)
├── Tree Shaking
├── CSS Purging
└── Asset Optimization

Runtime Optimization:
├── Component Memoization
├── State Management
├── Smooth Animations (60 FPS)
└── Responsive Images

Network Optimization:
├── Gzip Compression
├── CDN Caching
├── Lazy Loading (ready)
└── Image Optimization
```

---

**Architecture documentation complete! 🏗️**
