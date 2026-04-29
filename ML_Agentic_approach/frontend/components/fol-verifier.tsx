'use client'

import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { CheckCircle, AlertTriangle, Scale } from 'lucide-react'

interface FOLVerificationDetail {
  rule_id: string
  formal: string
  natural_language: string
  satisfied: boolean
  actual_value: string
  expected: string
  explanation: string
  verdict_impact: string
}

interface FOLResult {
  verdict: string
  consistent: boolean
  consistency_score: number
  fol_statements: string[]
  satisfied_rules: string[]
  violated_rules: string[]
  verification_details: FOLVerificationDetail[]
  explanation: string
}

interface FOLVerifierProps {
  folResult: FOLResult
}

export default function FOLVerifier({ folResult }: FOLVerifierProps) {
  return (
    <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-xl p-8 mb-8">
      <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/5 via-cyan-500/5 to-transparent pointer-events-none" />

      <div className="relative z-10">
        <h3 className="text-2xl font-bold mb-6 text-white flex items-center gap-2">
          <Scale className="w-6 h-6 text-emerald-400" />
          Formal Logic Verification (FOL)
        </h3>

        <div className="grid md:grid-cols-3 gap-4 mb-8">
          <div className="bg-slate-700/30 border border-slate-600/30 rounded-lg p-4">
            <p className="text-sm text-slate-400 mb-1">Consistency</p>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-white">
                {(folResult.consistency_score * 100).toFixed(1)}%
              </span>
              {folResult.consistent ? (
                <Badge className="bg-emerald-500/20 text-emerald-300 border-emerald-500/30 border">
                  Consistent
                </Badge>
              ) : (
                <Badge className="bg-red-500/20 text-red-300 border-red-500/30 border">
                  Inconsistent
                </Badge>
              )}
            </div>
          </div>

          <div className="bg-slate-700/30 border border-slate-600/30 rounded-lg p-4">
            <p className="text-sm text-slate-400 mb-2">Satisfied Rules</p>
            <p className="text-2xl font-bold text-emerald-400">
              {folResult.satisfied_rules.length}
              <span className="text-sm text-slate-400 ml-2">axioms</span>
            </p>
          </div>

          <div className="bg-slate-700/30 border border-slate-600/30 rounded-lg p-4">
            <p className="text-sm text-slate-400 mb-2">Violated Rules</p>
            <p className={`text-2xl font-bold ${folResult.violated_rules.length === 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {folResult.violated_rules.length}
              <span className="text-sm text-slate-400 ml-2">axioms</span>
            </p>
          </div>
        </div>

        <div className="bg-slate-800/50 border border-slate-600/30 rounded-lg p-4 mb-6">
          <p className="text-slate-300 text-sm leading-relaxed">
            {folResult.explanation}
          </p>
        </div>

        <div className="mb-6">
          <h4 className="text-sm font-semibold text-slate-200 mb-3">Formal Statements</h4>
          <div className="space-y-2">
            {folResult.fol_statements.map((stmt, idx) => (
              <div key={idx} className="bg-slate-800/30 border border-slate-600/20 rounded px-4 py-2">
                <code className="text-sm text-purple-300 font-mono">{stmt}</code>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h4 className="text-sm font-semibold text-slate-200 mb-3">Axiom Verification Details</h4>
          <Accordion type="single" collapsible className="space-y-2">
            {folResult.verification_details.map((detail, idx) => (
              <AccordionItem
                key={idx}
                value={`axiom-${idx}`}
                className={`border-0 rounded-lg px-4 py-2 transition ${
                  detail.satisfied
                    ? 'bg-emerald-500/10 hover:bg-emerald-500/20'
                    : 'bg-red-500/10 hover:bg-red-500/20'
                }`}
              >
                <AccordionTrigger className="hover:no-underline">
                  <div className="flex items-center gap-3 w-full">
                    {detail.satisfied ? (
                      <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
                    )}
                    <div className="text-left">
                      <p className={`font-semibold ${detail.satisfied ? 'text-emerald-300' : 'text-red-300'}`}>
                        {detail.rule_id}: {detail.natural_language}
                      </p>
                      <code className="text-xs text-slate-400 font-mono">{detail.formal}</code>
                    </div>
                  </div>
                </AccordionTrigger>

                <AccordionContent className="pt-4">
                  <div className="space-y-3">
                    <div className="bg-slate-800/30 rounded p-3 border border-slate-600/20">
                      <p className="text-xs text-slate-400 mb-1">Explanation</p>
                      <p className="text-sm text-slate-300">{detail.explanation}</p>
                    </div>

                    <div className="grid md:grid-cols-2 gap-3">
                      <div className="bg-slate-800/30 rounded p-3 border border-slate-600/20">
                        <p className="text-xs text-slate-400 mb-1">Expected</p>
                        <p className="text-sm font-semibold text-white">{detail.expected}</p>
                      </div>
                      <div className="bg-slate-800/30 rounded p-3 border border-slate-600/20">
                        <p className="text-xs text-slate-400 mb-1">Actual Value</p>
                        <p className="text-sm font-semibold text-white">{detail.actual_value}</p>
                      </div>
                    </div>

                    <div className="bg-slate-800/30 rounded p-3 border border-slate-600/20">
                      <p className="text-xs text-slate-400 mb-1">Impact on Verdict</p>
                      <p className={`text-sm font-semibold ${
                        detail.verdict_impact === 'supports' ? 'text-emerald-300' :
                        detail.verdict_impact === 'contradicts' ? 'text-red-300' :
                        'text-yellow-300'
                      }`}>
                        {detail.verdict_impact}
                      </p>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </Card>
  )
}
