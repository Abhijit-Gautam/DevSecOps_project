'use client'

import { Card } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Badge } from '@/components/ui/badge'
import { Brain, TrendingDown, TrendingUp, AlertTriangle } from 'lucide-react'

interface XAIResult {
  model_explanation: {
    predicted_label: string
    confidence: number
    plain_english_reasoning: string
    key_signals: Array<{ signal: string; impact: string; explanation: string }>
    attention_summary: string
  }
  section_explanations: Record<string, any>
  decision_factors: Array<{
    factor: string
    direction: string
    weight: number
    evidence: string
    impact_on_verdict: string
  }>
  counterfactuals: Array<{
    scenario: string
    current_state: string
    required_change: string
    difficulty: string
    would_achieve: string
  }>
  improvement_roadmap: Array<{
    priority: number
    section: string
    current_score?: string | null
    potential_gain?: number | null
    actions?: Array<string | { step?: string; explanation?: string }>
    effort?: string | null
  }>
}

interface XAIPanelProps {
  xaiResult: XAIResult
}

export default function XAIPanel({ xaiResult }: XAIPanelProps) {
  const modelExplanation = xaiResult?.model_explanation ?? {
    predicted_label: 'Unknown',
    confidence: 0,
    plain_english_reasoning: 'No model explanation available.',
    key_signals: [] as Array<{ signal: string; impact: string; explanation: string }>,
    attention_summary: 'No attention summary available.',
  }

  const decisionFactors = Array.isArray(xaiResult?.decision_factors)
    ? xaiResult.decision_factors
    : []
  const roadmapItems = Array.isArray(xaiResult?.improvement_roadmap)
    ? xaiResult.improvement_roadmap
    : []
  const counterfactuals = Array.isArray(xaiResult?.counterfactuals)
    ? xaiResult.counterfactuals
    : []

  const formatPotentialGain = (value: number | null | undefined) => {
    if (typeof value !== 'number' || Number.isNaN(value)) {
      return 'N/A'
    }
    return `+${value.toFixed(1)}`
  }

  const formatRoadmapAction = (
    action: string | { step?: string; explanation?: string } | undefined
  ) => {
    if (!action) return 'No action detail provided.'
    if (typeof action === 'string') return action

    const step = typeof action.step === 'string' ? action.step.trim() : ''
    const explanation =
      typeof action.explanation === 'string' ? action.explanation.trim() : ''

    if (step && explanation) return `${step}: ${explanation}`
    if (step) return step
    if (explanation) return explanation
    return 'No action detail provided.'
  }

  const getImpactColor = (impact: string) => {
    if (impact === 'negative') return 'text-red-400 bg-red-500/10'
    if (impact === 'positive') return 'text-emerald-400 bg-emerald-500/10'
    return 'text-yellow-400 bg-yellow-500/10'
  }

  const getEffortColor = (effort: string) => {
    if (effort === 'Low') return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
    if (effort === 'Medium') return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30'
    return 'bg-red-500/20 text-red-300 border-red-500/30'
  }

  return (
    <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-xl p-8 mb-8">
      <div className="absolute inset-0 bg-gradient-to-r from-purple-500/5 via-cyan-500/5 to-transparent pointer-events-none" />

      <div className="relative z-10">
        <h3 className="text-2xl font-bold mb-6 text-white flex items-center gap-2">
          <Brain className="w-6 h-6 text-purple-400" />
          Explainability Analysis (XAI)
        </h3>

        <Tabs defaultValue="explanation" className="w-full">
          <TabsList className="grid w-full grid-cols-4 bg-slate-700/30">
            <TabsTrigger value="explanation" className="text-slate-300 text-sm">
              Explanation
            </TabsTrigger>
            <TabsTrigger value="signals" className="text-slate-300 text-sm">
              Key Signals
            </TabsTrigger>
            <TabsTrigger value="roadmap" className="text-slate-300 text-sm">
              Roadmap
            </TabsTrigger>
            <TabsTrigger value="counterfactuals" className="text-slate-300 text-sm">
              What-If
            </TabsTrigger>
          </TabsList>

          <TabsContent value="explanation" className="mt-6 space-y-4">
            <div className="bg-slate-800/50 border border-slate-600/30 rounded-lg p-4">
              <h4 className="font-semibold text-white mb-2">Model Reasoning</h4>
              <p className="text-slate-300 text-sm leading-relaxed">
                {modelExplanation.plain_english_reasoning}
              </p>
            </div>

            <div className="bg-slate-800/50 border border-slate-600/30 rounded-lg p-4">
              <h4 className="font-semibold text-white mb-2">Attention Summary</h4>
              <p className="text-slate-300 text-sm leading-relaxed">
                {modelExplanation.attention_summary}
              </p>
            </div>

            <div>
              <h4 className="font-semibold text-white mb-3">Decision Factors</h4>
              <Accordion type="single" collapsible className="space-y-2">
                {decisionFactors.map((factor, idx) => (
                  <AccordionItem
                    key={idx}
                    value={`factor-${idx}`}
                    className="border-0 bg-slate-700/30 rounded-lg px-4 py-2 hover:bg-slate-700/50 transition"
                  >
                    <AccordionTrigger className="hover:no-underline">
                      <div className="flex items-center gap-3">
                        {factor.direction === 'negative' ? (
                          <TrendingDown className="w-4 h-4 text-red-400" />
                        ) : (
                          <TrendingUp className="w-4 h-4 text-emerald-400" />
                        )}
                        <div className="text-left">
                          <p className="font-semibold text-white">{factor.factor}</p>
                          <p className="text-xs text-slate-400">
                            Impact weight: {(factor.weight * 100).toFixed(0)}%
                          </p>
                        </div>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent className="pt-4">
                      <div className="space-y-2">
                        <p className="text-sm text-slate-300">
                          <span className="font-semibold">Evidence:</span> {factor.evidence}
                        </p>
                        <p className="text-sm text-slate-300">
                          <span className="font-semibold">Impact:</span> {factor.impact_on_verdict}
                        </p>
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </div>
          </TabsContent>

          <TabsContent value="signals" className="mt-6">
            <div className="space-y-3">
              {modelExplanation.key_signals.map((signal, idx) => (
                <div key={idx} className="border border-slate-600/30 rounded-lg p-4 bg-slate-800/30">
                  <div className="flex items-start gap-3">
                    <Badge
                      className={`mt-1 whitespace-nowrap ${
                        signal.impact === 'negative'
                          ? 'bg-red-500/20 text-red-300 border-red-500/30'
                          : signal.impact === 'positive'
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                          : 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30'
                      }`}
                    >
                      {signal.impact}
                    </Badge>
                    <div className="flex-1">
                      <p className="font-semibold text-white">{signal.signal}</p>
                      <p className="text-sm text-slate-300 mt-1">{signal.explanation}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="roadmap" className="mt-6">
            <div className="space-y-3">
              {roadmapItems.map((item, idx) => (
                <div
                  key={idx}
                  className="border border-slate-600/30 rounded-lg p-4 bg-slate-800/30"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Badge className="bg-cyan-500/20 text-cyan-300 border-cyan-500/30 border">
                          Priority {item.priority}
                        </Badge>
                        <span className="font-semibold text-white capitalize">{item.section || 'overall'}</span>
                      </div>
                      <p className="text-sm text-slate-400">
                        {item.current_score || 'Current score unavailable'} → {formatPotentialGain(item.potential_gain)}
                      </p>
                    </div>
                    <Badge className={`${getEffortColor(item.effort || 'Unknown')} border whitespace-nowrap`}>
                      {(item.effort || 'Unknown')} Effort
                    </Badge>
                  </div>

                  <ol className="space-y-2">
                    {(item.actions || []).map((action, aidx) => (
                      <li key={aidx} className="text-sm text-slate-300 flex gap-2">
                        <span className="font-semibold text-cyan-400">{aidx + 1}.</span>
                        {formatRoadmapAction(action)}
                      </li>
                    ))}
                  </ol>
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="counterfactuals" className="mt-6">
            <div className="space-y-3">
              {counterfactuals.map((cf, idx) => (
                <div key={idx} className="border border-slate-600/30 rounded-lg p-4 bg-slate-800/30">
                  <div className="mb-3">
                    <p className="font-semibold text-white mb-1">{cf.scenario}</p>
                    <Badge className={`${getEffortColor(cf.difficulty)} border`}>
                      {cf.difficulty}
                    </Badge>
                  </div>
                  <div className="space-y-2 text-sm">
                    <p className="text-slate-300">
                      <span className="font-semibold text-slate-200">Current:</span> {cf.current_state}
                    </p>
                    <p className="text-slate-300">
                      <span className="font-semibold text-slate-200">Required:</span> {cf.required_change}
                    </p>
                    <p className="text-emerald-300">
                      <span className="font-semibold">Would Achieve:</span> {cf.would_achieve}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </Card>
  )
}
