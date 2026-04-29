'use client'

import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { CheckCircle, AlertCircle, TrendingUp } from 'lucide-react'

interface AgentEval {
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

interface AgentPanelProps {
  evaluations: AgentEval[]
  selfRewardScores: Record<string, number>
}

export default function AgentPanel({ evaluations, selfRewardScores }: AgentPanelProps) {
  const getVerdictColor = (verdict: string) => {
    switch (verdict) {
      case 'Excellent':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
      case 'Good':
        return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30'
      case 'Needs Improvement':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/30'
      default:
        return 'bg-slate-500/20 text-slate-300'
    }
  }

  const agentDisplayNames: Record<string, string> = {
    'AbstractAgent': '📋 Abstract Evaluator',
    'MethodologyAgent': '🔬 Methodology Specialist',
    'ResultsAgent': '📊 Results Analyst',
    'CitationAgent': '📚 Citation Expert',
    'DocumentStructure': '🏗️ Structure Auditor',
    'ContentDepth': '🧠 Content Depth Reviewer',
  }

  return (
    <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-xl p-8 mb-8">
      <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/5 via-purple-500/5 to-transparent pointer-events-none" />

      <div className="relative z-10">
        <h3 className="text-2xl font-bold mb-6 text-white">Multi-Agent Evaluation Panel</h3>

        <Accordion type="single" collapsible className="space-y-3">
          {evaluations.map((agent, idx) => (
            <AccordionItem
              key={idx}
              value={`agent-${idx}`}
              className="border-0 bg-slate-700/30 rounded-xl px-6 py-2 hover:bg-slate-700/50 transition data-[state=open]:bg-slate-700/50"
            >
              <AccordionTrigger className="py-4 hover:no-underline">
                <div className="flex items-center justify-between w-full gap-4">
                  <div className="flex items-center gap-4">
                    <div className="text-left">
                      <p className="font-semibold text-white">
                        {agentDisplayNames[agent.agent] || agent.agent}
                      </p>
                      <p className="text-xs text-slate-400">Round {agent.round}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge className={`${getVerdictColor(agent.verdict)} border font-semibold`}>
                      {agent.verdict}
                    </Badge>
                    <div className="text-right">
                      <div className="font-bold text-white">
                        {agent.score}/{agent.max_score}
                      </div>
                      <div className="text-xs text-slate-400 flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" />
                        Quality: {agent.self_reward.score.toFixed(1)}/10
                      </div>
                    </div>
                  </div>
                </div>
              </AccordionTrigger>

              <AccordionContent className="pt-0">
                <div className="space-y-4 mt-4">
                  <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-600/30">
                    <p className="text-slate-300 text-sm leading-relaxed">
                      <span className="font-semibold text-slate-200">Reasoning: </span>
                      {agent.reasoning}
                    </p>
                  </div>

                  {agent.evidence.length > 0 && (
                    <div>
                      <h5 className="text-xs font-semibold text-cyan-400 mb-2">Evidence</h5>
                      <div className="space-y-2">
                        {agent.evidence.map((ev, i) => (
                          <p key={i} className="text-sm text-slate-400 italic border-l-2 border-cyan-500/30 pl-3">
                            "{ev}"
                          </p>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="grid md:grid-cols-2 gap-4">
                    <div>
                      <h5 className="text-xs font-semibold text-emerald-400 mb-2 flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" />
                        Strengths
                      </h5>
                      <ul className="space-y-1">
                        {agent.strengths.map((s, i) => (
                          <li key={i} className="text-xs text-slate-300 flex gap-2">
                            <span className="text-emerald-400">•</span>{s}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h5 className="text-xs font-semibold text-amber-400 mb-2 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" />
                        Weaknesses
                      </h5>
                      <ul className="space-y-1">
                        {agent.weaknesses.map((w, i) => (
                          <li key={i} className="text-xs text-slate-300 flex gap-2">
                            <span className="text-amber-400">•</span>{w}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {agent.recommendations.length > 0 && (
                    <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3">
                      <h5 className="text-xs font-semibold text-purple-300 mb-2">Recommendations</h5>
                      <ol className="space-y-1">
                        {agent.recommendations.map((rec, i) => (
                          <li key={i} className="text-xs text-slate-300 flex gap-2">
                            <span className="text-purple-400">{i + 1}.</span>{rec}
                          </li>
                        ))}
                      </ol>
                    </div>
                  )}

                  <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-600/30">
                    <h5 className="text-xs font-semibold text-slate-300 mb-2">Self-Reward Quality Score</h5>
                    <p className="text-sm text-slate-300 mb-2">{agent.self_reward.justification}</p>
                    {agent.self_reward.weaknesses.length > 0 && (
                      <p className="text-xs text-amber-300">
                        <span className="font-semibold">Noted weaknesses:</span> {agent.self_reward.weaknesses.join(', ')}
                      </p>
                    )}
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </Card>
  )
}
