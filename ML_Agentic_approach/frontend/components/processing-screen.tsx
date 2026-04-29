'use client'

import { Card } from '@/components/ui/card'
import { CheckCircle2, Circle, Loader2, TerminalSquare } from 'lucide-react'
import type { PipelineProgressEvent } from '@/lib/types'

interface ProcessingScreenProps {
  statusText?: string
  progress?: PipelineProgressEvent[]
}

const pipelineSteps = [
  'Pipeline Initialisation',
  'RoBERTa Inference',
  'Attention Highlights',
  'Agent Round 1',
  'Self-Reward',
  'Cross-Review',
  'Master Arbitration',
  'FOL Verification',
  'XAI Explanation',
  'Completion',
]

function formatElapsed(ms?: number) {
  if (typeof ms !== 'number') return '--'
  return `${(ms / 1000).toFixed(1)}s`
}

export default function ProcessingScreen({
  statusText = 'Evaluating your report through the full pipeline...',
  progress = [],
}: ProcessingScreenProps) {
  const latest = progress[progress.length - 1]
  const percent = latest?.percent ?? 0
  const recentEvents = progress.slice(-10).reverse()
  const completedFraction = Math.min(1, Math.max(0, percent / 100))
  const completedSteps = Math.round(completedFraction * pipelineSteps.length)

  return (
    <div className="flex items-center justify-center min-h-screen p-4">
      <Card className="w-full max-w-4xl border-0 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-xl p-8 md:p-10">
        <div className="relative z-10 text-center">
          <h2 className="text-3xl font-bold mb-2 bg-gradient-to-r from-cyan-400 to-blue-300 bg-clip-text text-transparent">
            AI Processing in Progress
          </h2>
          <p className="text-slate-300 mb-6">
            {statusText}
          </p>

          <div className="w-full bg-slate-700/50 rounded-full h-3 overflow-hidden mb-8">
            <div
              className="h-3 bg-gradient-to-r from-cyan-500 to-blue-400 transition-all duration-500"
              style={{ width: `${percent}%` }}
            />
          </div>

          <div className="text-sm text-slate-300 mb-8">
            {percent}% complete{latest?.step ? ` • ${latest.step}` : ''}
          </div>

          <div className="grid md:grid-cols-2 gap-6 text-left">
            <div className="bg-slate-900/45 border border-slate-700/50 rounded-xl p-4">
              <h3 className="text-sm uppercase tracking-wide text-slate-400 mb-3">Pipeline Stages</h3>
              <div className="space-y-2">
                {pipelineSteps.map((label, idx) => {
                  const done = idx < completedSteps
                  const current = idx === completedSteps
                  return (
                    <div key={label} className="flex items-center gap-2 text-sm">
                      {done ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      ) : current ? (
                        <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
                      ) : (
                        <Circle className="w-4 h-4 text-slate-600" />
                      )}
                      <span className={done || current ? 'text-slate-100' : 'text-slate-500'}>{label}</span>
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="bg-slate-900/45 border border-slate-700/50 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <TerminalSquare className="w-4 h-4 text-cyan-300" />
                <h3 className="text-sm uppercase tracking-wide text-slate-400">Live Event Feed</h3>
              </div>
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {recentEvents.length === 0 ? (
                  <p className="text-sm text-slate-500">Waiting for backend events...</p>
                ) : (
                  recentEvents.map((event, idx) => (
                    <div key={`${event.step}-${idx}`} className="text-xs bg-slate-800/60 border border-slate-700/60 rounded-md p-2">
                      <p className="text-slate-100">{event.message || event.step}</p>
                      <p className="text-slate-400 mt-1">
                        {event.step} • elapsed {formatElapsed(event.elapsed_ms)}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

        </div>
      </Card>
    </div>
  )
}
