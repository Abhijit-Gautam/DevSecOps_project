/**
 * API Response Types based on BACKEND.md schema
 */

export interface UnifiedVerdict {
  final_verdict: 'Excellent' | 'Good' | 'Needs Improvement'
  overall_score: number
  confidence: number
  executive_summary: string
  dimension_verdicts: Record<string, string>
  key_strengths: string[]
  key_weaknesses: string[]
  priority_recommendations: string[]
  agent_agreement_level: string
  ml_model_alignment: string
  reasoning_chain: string
}

export interface AgentEvaluation {
  agent: string
  round: number
  verdict: string
  score: number
  max_score: number
  reasoning: string
  evidence: string[]
  strengths: string[]
  weaknesses: string[]
  recommendations: string[]
  self_reward: {
    score: number
    justification: string
    weaknesses: string[]
  }
}

export interface CrossReview {
  reviewer: string
  reviewee: string
  agree_with_peer: boolean
  revised_verdict: string
  confidence_change: number
  reasoning: string
}

export interface HighlightSpan {
  token: string
  start: number
  end: number
  score: number
}

export interface HighlightData {
  highlighted_spans: HighlightSpan[]
  threshold: number
  total_tokens: number
  mapped_evidence?: Array<{
    token: string
    importance_score: number
    context: string
    assigned_section: string
  }>
}

export interface KeySignal {
  signal: string
  impact: 'positive' | 'negative' | 'neutral'
  explanation: string
}

export interface SectionExplanation {
  section: string
  score: number
  max_score: number
  verdict: string
  reasoning: string
  met_criteria: string[]
  unmet_criteria: string[]
  key_text_evidence: Array<{
    text: string
    interpretation: string
  }>
  specific_improvements: string[]
}

export interface DecisionFactor {
  factor: string
  direction: 'positive' | 'negative'
  weight: number
  evidence: string
  impact_on_verdict: string
}

export interface Counterfactual {
  scenario: string
  current_state: string
  required_change: string
  difficulty: 'Low' | 'Medium' | 'High'
  would_achieve: string
}

export interface ImprovementRoadmapItem {
  priority: number
  section: string
  current_score: string
  potential_gain: number
  actions: string[]
  effort: 'Low' | 'Medium' | 'High'
}

export interface XAIResult {
  model_explanation: {
    predicted_label: string
    confidence: number
    plain_english_reasoning: string
    key_signals: KeySignal[]
    attention_summary: string
  }
  section_explanations: Record<string, SectionExplanation>
  highlighted_evidence: any[]
  decision_factors: DecisionFactor[]
  counterfactuals: Counterfactual[]
  improvement_roadmap: ImprovementRoadmapItem[]
}

export interface VerificationDetail {
  rule_id: string
  formal: string
  natural_language: string
  satisfied: boolean
  actual_value: string
  expected: string
  explanation: string
  verdict_impact: string
}

export interface FOLResult {
  verdict: string
  consistent: boolean
  consistency_score: number
  fol_statements: string[]
  satisfied_rules: string[]
  violated_rules: string[]
  verification_details: VerificationDetail[]
  explanation: string
}

export interface ThoughtStep {
  step: number
  title: string
  description: string
  evidence: string[]
  type: string
}

export interface PipelineTimeline {
  name: string
  elapsed_ms: number
  data?: any
}

export interface PipelineProgressEvent {
  step: string
  message: string
  icon?: string
  step_index?: number
  total_steps?: number
  percent?: number
  elapsed_ms?: number
}

export interface RoberTaResult {
  predicted_label_id: number
  predicted_label: string
  confidence: number
  probabilities: Record<string, number>
}

export interface ParsedData {
  domain: string
  total_score: number
  max_score: number
  word_count: number
  sections: Array<{
    name: string
    score: number
    max_score: number
    feedback: string
  }>
  document_quality: Record<string, number>
  has_abstract: boolean
  has_methodology: boolean
  has_results: boolean
  has_conclusion: boolean
  reference_count: number
  report_text?: string
}

export interface ReportResponse {
  report_id: string
  filename: string
  elapsed_ms: number
  status: 'pending' | 'complete' | 'error'
  parsed_data: ParsedData
  roberta_result: RoberTaResult
  unified_verdict: UnifiedVerdict
  agent_evaluations: AgentEvaluation[]
  self_reward_scores: Record<string, number>
  cross_reviews: CrossReview[]
  highlight_data: HighlightData
  xai_result: XAIResult
  fol_result: FOLResult
  thought_process: ThoughtStep[]
  pipeline_timeline: PipelineTimeline[]
}

export interface ApiError {
  error: string
  detail?: string
}
