'use client'

import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  FileText,
  Brain,
  Users,
  Zap,
  CheckCircle,
  Scale,
  Loader,
} from 'lucide-react'

interface Step {
  step: number
  title: string
  description: string
  evidence: string[]
  type: string
}

interface ThoughtTimelineProps {
  steps: Step[]
  totalSteps: number
}

const getStepIcon = (type: string) => {
  const icons: Record<string, React.ReactNode> = {
    preprocessing: FileText,
    ml_inference: Brain,
    agent_evaluation: Users,
    srlm_cross_review: Users,
    master_arbitration: Zap,
    xai: Loader,
    fol_verification: Scale,
  }
  const Icon = icons[type] || CheckCircle
  return Icon
}

const getTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    preprocessing: 'from-blue-500 to-cyan-500',
    ml_inference: 'from-purple-500 to-pink-500',
    agent_evaluation: 'from-cyan-500 to-blue-500',
    srlm_cross_review: 'from-pink-500 to-purple-500',
    master_arbitration: 'from-yellow-500 to-orange-500',
    xai: 'from-emerald-500 to-teal-500',
    fol_verification: 'from-red-500 to-pink-500',
  }
  return colors[type] || 'from-slate-500 to-slate-600'
}

export default function ThoughtTimeline({ steps, totalSteps }: ThoughtTimelineProps) {
  return (
    <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-xl p-8 mb-8">
      <div className="absolute inset-0 bg-gradient-to-r from-orange-500/5 via-yellow-500/5 to-transparent pointer-events-none" />

      <div className="relative z-10">
        <h3 className="text-2xl font-bold mb-2 text-white">Evaluation Pipeline Timeline</h3>
        <p className="text-slate-400 mb-8">
          {steps.length} / {totalSteps} steps completed
        </p>

        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gradient-to-b from-cyan-500/50 to-purple-500/50" />

          {/* Steps */}
          <div className="space-y-6">
            {steps.map((step, idx) => {
              const IconComponent = getStepIcon(step.type)
              const color = getTypeColor(step.type)

              return (
                <div key={step.step} className="relative pl-20">
                  {/* Icon circle */}
                  <div className={`absolute left-0 w-12 h-12 rounded-full bg-gradient-to-br ${color} flex items-center justify-center border-4 border-slate-900 shadow-lg`}>
                    <IconComponent className="w-6 h-6 text-white" />
                  </div>

                  {/* Content card */}
                  <div className="bg-slate-700/30 border border-slate-600/30 rounded-xl p-4 hover:bg-slate-700/50 transition">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h4 className="font-semibold text-white">{step.title}</h4>
                        <Badge className="mt-1 bg-slate-600/50 text-slate-200 border-0 text-xs">
                          Step {step.step}
                        </Badge>
                      </div>
                      <div className="text-right text-xs text-slate-400">
                        <div className="font-semibold text-slate-300">{step.type}</div>
                      </div>
                    </div>

                    <p className="text-sm text-slate-300 mb-3 leading-relaxed">
                      {step.description}
                    </p>

                    {step.evidence && step.evidence.length > 0 && (
                      <div className="bg-slate-800/50 rounded p-3 border border-slate-600/20">
                        <p className="text-xs font-semibold text-slate-400 mb-2">Evidence</p>
                        <ul className="space-y-1">
                          {step.evidence.slice(0, 3).map((ev, i) => (
                            <li key={i} className="text-xs text-slate-400 flex gap-2">
                              <span className="text-slate-500">•</span>
                              <span className="line-clamp-1">{ev}</span>
                            </li>
                          ))}
                          {step.evidence.length > 3 && (
                            <li className="text-xs text-slate-500 italic">
                              +{step.evidence.length - 3} more
                            </li>
                          )}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </Card>
  )
}
