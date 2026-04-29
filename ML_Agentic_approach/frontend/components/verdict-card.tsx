'use client'

import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { AlertCircle, CheckCircle, Star } from 'lucide-react'

interface VerdictCardProps {
  verdict: {
    final_verdict: string
    overall_score: number
    confidence: number
    executive_summary: string
    dimension_verdicts: Record<string, string>
    key_strengths: string[]
    key_weaknesses: string[]
    priority_recommendations: string[]
  }
}

export default function VerdictCard({ verdict }: VerdictCardProps) {
  const verdictColor = {
    'Excellent': 'from-emerald-500 to-teal-500',
    'Good': 'from-cyan-500 to-blue-500',
    'Needs Improvement': 'from-amber-500 to-orange-500',
  }[verdict.final_verdict] || 'from-slate-500 to-slate-600'

  const verdictBadgeColor = {
    'Excellent': 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    'Good': 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
    'Needs Improvement': 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  }[verdict.final_verdict] || 'bg-slate-500/20 text-slate-300'

  return (
    <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-xl p-8 mb-8">
      <div className={`absolute inset-0 bg-gradient-to-r ${verdictColor} opacity-5 pointer-events-none`} />

      <div className="relative z-10">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="text-3xl font-bold text-white mb-2">Final Verdict</h2>
            <div className="flex items-center gap-3">
              <Badge className={`${verdictBadgeColor} border font-bold text-lg px-4 py-1`}>
                {verdict.final_verdict}
              </Badge>
              <div className="flex items-center gap-1">
                <span className="text-sm text-slate-400">Confidence:</span>
                <span className="font-semibold text-white">{(verdict.confidence * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>

          <div className="text-right">
            <div className="text-5xl font-bold bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">
              {verdict.overall_score.toFixed(1)}
            </div>
            <p className="text-sm text-slate-400">Overall Score</p>
          </div>
        </div>

        <p className="text-slate-300 mb-8 leading-relaxed">
          {verdict.executive_summary}
        </p>

        <div className="grid md:grid-cols-2 gap-6 mb-6">
          <div>
            <h4 className="text-sm font-semibold text-emerald-400 mb-3 flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              Key Strengths
            </h4>
            <ul className="space-y-2">
              {verdict.key_strengths.map((strength, idx) => (
                <li key={idx} className="text-sm text-slate-300 flex gap-2">
                  <span className="text-emerald-400">•</span>
                  {strength}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              Key Weaknesses
            </h4>
            <ul className="space-y-2">
              {verdict.key_weaknesses.map((weakness, idx) => (
                <li key={idx} className="text-sm text-slate-300 flex gap-2">
                  <span className="text-amber-400">•</span>
                  {weakness}
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600/30">
          <h4 className="text-sm font-semibold text-cyan-400 mb-3 flex items-center gap-2">
            <Star className="w-4 h-4" />
            Priority Recommendations
          </h4>
          <ol className="space-y-2">
            {verdict.priority_recommendations.map((rec, idx) => (
              <li key={idx} className="text-sm text-slate-300 flex gap-3">
                <span className="font-semibold text-cyan-400">{idx + 1}.</span>
                {rec}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </Card>
  )
}
