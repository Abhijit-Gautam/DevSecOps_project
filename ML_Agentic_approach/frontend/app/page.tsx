'use client'

import { useState } from 'react'
import { useToast } from '@/hooks/use-toast'
import { API_BASE_URL, API_ENDPOINTS } from '@/lib/config'
import type { PipelineProgressEvent, ReportResponse } from '@/lib/types'
import UploadSection, { type UploadOptions } from '@/components/upload-section'
import ProcessingScreen from '@/components/processing-screen'
import VerdictCard from '@/components/verdict-card'
import AgentPanel from '@/components/agent-panel'
import HighlightsViewer from '@/components/highlights-viewer'
import XAIPanel from '@/components/xai-panel'
import FOLVerifier from '@/components/fol-verifier'
import ThoughtTimeline from '@/components/thought-timeline'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'


interface ParsedSSEEvent {
  event: string
  data: unknown
}

function parseSSEEvent(rawBlock: string): ParsedSSEEvent | null {
  if (!rawBlock || rawBlock.startsWith(':')) {
    return null
  }

  let event = 'message'
  const dataLines: string[] = []

  for (const line of rawBlock.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim())
    }
  }

  const payload = dataLines.join('\n').trim()
  if (!payload) {
    return { event, data: {} }
  }

  try {
    return { event, data: JSON.parse(payload) }
  } catch {
    return { event, data: { message: payload } }
  }
}

function formatElapsed(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  if (minutes === 0) {
    return `${seconds}s`
  }
  return `${minutes}m ${seconds}s`
}

function toReportResponseFromStored(report: any, fallbackReportId?: string): ReportResponse {
  const parsedData = (report?.parsed_data ?? {}) as ReportResponse['parsed_data']
  const srlmResults = report?.srlm_results ?? {}
  const highlights = report?.highlights ?? report?.highlight_data ?? {}
  const tokens = Array.isArray(highlights?.tokens) ? highlights.tokens : []

  const finalVerdict = report?.unified_verdict?.final_verdict
  const safeVerdict: 'Excellent' | 'Good' | 'Needs Improvement' =
    finalVerdict === 'Excellent' || finalVerdict === 'Good' || finalVerdict === 'Needs Improvement'
      ? finalVerdict
      : 'Needs Improvement'

  const unifiedVerdict = {
    final_verdict: safeVerdict,
    overall_score:
      typeof report?.unified_verdict?.overall_score === 'number'
        ? report.unified_verdict.overall_score
        : parsedData?.total_score ?? 0,
    confidence:
      typeof report?.unified_verdict?.confidence === 'number'
        ? report.unified_verdict.confidence
        : typeof report?.confidence === 'number'
        ? report.confidence
        : 0,
    executive_summary:
      report?.unified_verdict?.executive_summary ?? 'Recovered result from persisted backend record.',
    dimension_verdicts: report?.unified_verdict?.dimension_verdicts ?? {},
    key_strengths: report?.unified_verdict?.key_strengths ?? [],
    key_weaknesses: report?.unified_verdict?.key_weaknesses ?? [],
    priority_recommendations: report?.unified_verdict?.priority_recommendations ?? [],
    agent_agreement_level: report?.unified_verdict?.agent_agreement_level ?? 'Unknown',
    ml_model_alignment: report?.unified_verdict?.ml_model_alignment ?? 'Unknown',
    reasoning_chain: report?.unified_verdict?.reasoning_chain ?? '',
  }

  const status: 'pending' | 'complete' | 'error' =
    report?.status === 'pending' || report?.status === 'error' ? report.status : 'complete'

  return {
    report_id: report?.report_id ?? fallbackReportId ?? 'unknown',
    filename: report?.filename ?? 'unknown',
    elapsed_ms: typeof report?.elapsed_ms === 'number' ? report.elapsed_ms : 0,
    status,
    parsed_data: parsedData,
    roberta_result: {
      predicted_label_id:
        typeof report?.predicted_label_id === 'number' ? report.predicted_label_id : 0,
      predicted_label: report?.predicted_label ?? safeVerdict,
      confidence: typeof report?.confidence === 'number' ? report.confidence : 0,
      probabilities: report?.probabilities ?? {},
    },
    unified_verdict: unifiedVerdict,
    agent_evaluations: srlmResults?.agent_evaluations ?? [],
    self_reward_scores: srlmResults?.self_reward_scores ?? {},
    cross_reviews: srlmResults?.cross_reviews ?? [],
    highlight_data: {
      highlighted_spans: highlights?.highlighted_spans ?? [],
      pdf_annotations: highlights?.pdf_annotations ?? [],
      threshold: typeof highlights?.threshold === 'number' ? highlights.threshold : 0.5,
      total_tokens: tokens.length,
    },
    xai_result: report?.explanations ?? {},
    fol_result: report?.fol_verification ?? {},
    thought_process: report?.thought_process ?? [],
    pipeline_timeline: report?.pipeline_timeline ?? [],
    pdf_url:
      typeof report?.pdf_url === 'string'
        ? report.pdf_url
        : report?.filename?.toLowerCase?.().endsWith('.pdf')
        ? `/api/reports/${report?.report_id ?? fallbackReportId}/pdf`
        : null,
  }
}



export default function Home() {
  const [isLoading, setIsLoading] = useState(false)
  const [reportData, setReportData] = useState<ReportResponse | null>(null)
  const [progressEvents, setProgressEvents] = useState<PipelineProgressEvent[]>([])
  const [statusText, setStatusText] = useState('Preparing evaluation...')
  const [activeReportId, setActiveReportId] = useState<string | null>(null)
  const { toast } = useToast()

  const handleUpload = async (file: File, options: UploadOptions) => {
    setIsLoading(true)
    setStatusText('Uploading file and starting pipeline...')
    setProgressEvents([])
    setActiveReportId(null)

    let heartbeatTimer: ReturnType<typeof setInterval> | null = null

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('run_srlm', String(options.run_srlm))
      formData.append('run_highlights', String(options.run_highlights))
      formData.append('run_fol', String(options.run_fol))
      formData.append('run_xai', String(options.run_xai))

      const response = await fetch(API_ENDPOINTS.EVALUATE_STREAM, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(
          `API error ${response.status}: ${errorText || response.statusText}`
        )
      }

      if (!response.body) {
        throw new Error('Streaming response not available in this browser/session.')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let streamedResult: ReportResponse | null = null
      const startedAt = Date.now()
      let lastProgressAt = startedAt
      let currentReportId: string | null = null

      heartbeatTimer = setInterval(async () => {
        const now = Date.now()
        if (now - lastProgressAt < 30000) {
          return
        }

        const elapsedSeconds = Math.floor((now - startedAt) / 1000)
        const elapsedLabel = formatElapsed(elapsedSeconds)

        setStatusText(`Still processing... ${elapsedLabel} elapsed.`)
        setProgressEvents((prev) =>
          [
            ...prev,
            {
              step: 'heartbeat',
              message: `Still processing... ${elapsedLabel} elapsed.`,
              elapsed_ms: elapsedSeconds * 1000,
            },
          ].slice(-200)
        )

        try {
          if (currentReportId) {
            const statusRes = await fetch(`${API_ENDPOINTS.REPORTS}/${currentReportId}`)
            if (statusRes.ok) {
              const statusPayload = (await statusRes.json()) as { status?: string }
              if (statusPayload.status === 'complete') {
                setStatusText(
                  `Backend marked report ${currentReportId} complete. Waiting for final stream payload...`
                )
              } else if (statusPayload.status === 'error') {
                setStatusText(`Backend marked report ${currentReportId} as error.`)
              }
            }
          } else {
            await fetch(API_ENDPOINTS.HEALTH)
          }
        } catch {
          setStatusText(`Still processing... ${elapsedLabel} elapsed (status probe retrying).`)
        }
      }, 30000)

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          break
        }

        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')

        let splitAt = buffer.indexOf('\n\n')
        while (splitAt !== -1) {
          const rawBlock = buffer.slice(0, splitAt).trim()
          buffer = buffer.slice(splitAt + 2)

          const parsed = parseSSEEvent(rawBlock)
          if (parsed) {
            if (parsed.event === 'connected') {
              const data = parsed.data as { message?: string }
              setStatusText(data.message || 'Connected to backend stream.')
            } else if (parsed.event === 'report_id') {
              const data = parsed.data as { report_id?: string }
              if (data.report_id) {
                currentReportId = data.report_id
                setActiveReportId(data.report_id)
              }
            } else if (parsed.event === 'progress') {
              const event = parsed.data as PipelineProgressEvent
              lastProgressAt = Date.now()
              setProgressEvents((prev) => [...prev, event].slice(-200))
              setStatusText(event.message || event.step || 'Processing...')
            } else if (parsed.event === 'result') {
              lastProgressAt = Date.now()
              streamedResult = parsed.data as ReportResponse
            } else if (parsed.event === 'error') {
              const data = parsed.data as { message?: string }
              throw new Error(data.message || 'Evaluation stream returned an error.')
            }
          }

          splitAt = buffer.indexOf('\n\n')
        }
      }

      const trailing = buffer.trim()
      if (trailing) {
        const parsed = parseSSEEvent(trailing)
        if (parsed?.event === 'result') {
          streamedResult = parsed.data as ReportResponse
        }
      }

      if (!streamedResult && currentReportId) {
        try {
          const fallbackUrl = new URL(`${API_ENDPOINTS.REPORTS}/${currentReportId}`)
          fallbackUrl.searchParams.set('include_text', 'true')
          const fallbackRes = await fetch(fallbackUrl.toString())
          if (fallbackRes.ok) {
            const storedReport = await fallbackRes.json()
            if (storedReport?.status === 'complete') {
              streamedResult = toReportResponseFromStored(storedReport, currentReportId)
              setStatusText(`Recovered final result from backend storage (${currentReportId}).`)
            }
          }
        } catch {
          // Best-effort fallback only.
        }
      }

      if (!streamedResult) {
        throw new Error(
          currentReportId
            ? `Stream ended before final result. Report ID: ${currentReportId}.`
            : 'Stream ended before final result was received.'
        )
      }

      setReportData(streamedResult)
      toast({
        title: 'Success',
        description: `Report evaluated successfully (ID: ${streamedResult.report_id})`,
      })
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to upload report'
      toast({
        title: 'Error',
        description: message,
        variant: 'destructive',
      })
    } finally {
      if (heartbeatTimer) {
        clearInterval(heartbeatTimer)
      }
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <ProcessingScreen
        statusText={activeReportId ? `${statusText} (Report ID: ${activeReportId})` : statusText}
        progress={progressEvents}
      />
    )
  }

  return (
    <main className="min-h-screen py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent mb-3">
            DevSecOps Report Evaluator
          </h1>
          <p className="text-lg text-slate-400">
            Advanced AI-powered academic report evaluation with multi-layer analysis
          </p>
        </div>

        {/* Results View */}
        {reportData ? (
          <div className="space-y-8">
            <Button
              onClick={() => setReportData(null)}
              variant="ghost"
              className="text-slate-400 hover:text-white hover:bg-slate-800/50"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Upload
            </Button>

            {/* Report Summary */}
            <div className="bg-slate-700/20 border border-slate-600/30 rounded-lg p-6 mb-8">
              <div className="grid md:grid-cols-3 gap-4">
                <div>
                  <p className="text-sm text-slate-400">Filename</p>
                  <p className="font-semibold text-white">{reportData.filename}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400">Report ID</p>
                  <p className="font-semibold text-slate-300 font-mono text-sm">{reportData.report_id}</p>
                </div>
                <div>
                  <p className="text-sm text-slate-400">Processing Time</p>
                  <p className="font-semibold text-white">{(reportData.elapsed_ms / 1000).toFixed(2)}s</p>
                </div>
              </div>
            </div>

            {/* Main Results */}
            <VerdictCard verdict={reportData.unified_verdict} />

            {reportData.agent_evaluations.length > 0 && (
              <AgentPanel
                evaluations={reportData.agent_evaluations}
                selfRewardScores={reportData.self_reward_scores}
              />
            )}

            {reportData.highlight_data && (
              <HighlightsViewer
                text={reportData.parsed_data.report_text || 'Report text not available'}
                highlightedSpans={reportData.highlight_data.highlighted_spans || []}
                pdfAnnotations={reportData.highlight_data.pdf_annotations || []}
                pdfUrl={
                  reportData.pdf_url
                    ? reportData.pdf_url.startsWith('http')
                      ? reportData.pdf_url
                      : `${API_BASE_URL}${reportData.pdf_url}`
                    : null
                }
                threshold={reportData.highlight_data.threshold || 0.5}
              />
            )}

            {reportData.xai_result && (
              <XAIPanel xaiResult={reportData.xai_result} />
            )}

            {reportData.fol_result && (
              <FOLVerifier folResult={reportData.fol_result} />
            )}

            {reportData.thought_process.length > 0 && (
              <ThoughtTimeline
                steps={reportData.thought_process}
                totalSteps={11}
              />
            )}
          </div>
        ) : (
          /* Upload View */
          <div>
            <UploadSection onUpload={handleUpload} isLoading={isLoading} />

            {/* Feature Overview */}
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[
                {
                  icon: '🤖',
                  title: 'Multi-Agent Evaluation',
                  description: 'Six specialized AI agents evaluate different aspects of your report',
                },
                {
                  icon: '🧠',
                  title: 'Deep Learning Analysis',
                  description: 'RoBERTa model with attention-based text highlighting',
                },
                {
                  icon: '🔬',
                  title: 'Explainable AI',
                  description: 'Understand decision factors and improvement recommendations',
                },
                {
                  icon: '⚖️',
                  title: 'Formal Verification',
                  description: 'Logic-based consistency checking against rubric axioms',
                },
                {
                  icon: '📊',
                  title: 'Comprehensive Scoring',
                  description: 'Detailed breakdown across abstract, methodology, results, and more',
                },
                {
                  icon: '🎯',
                  title: 'Actionable Insights',
                  description: 'Priority-ranked recommendations for improvement',
                },
              ].map((feature, idx) => (
                <div
                  key={idx}
                  className="group relative bg-gradient-to-br from-slate-800/40 to-slate-900/40 border border-slate-700/50 rounded-2xl p-6 hover:border-cyan-500/50 hover:bg-slate-800/60 transition-all hover:shadow-lg hover:shadow-cyan-500/10"
                >
                  <div className="text-3xl mb-3">{feature.icon}</div>
                  <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                  <p className="text-sm text-slate-400 leading-relaxed">{feature.description}</p>
                  <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/0 to-purple-500/0 group-hover:from-cyan-500/5 group-hover:to-purple-500/5 rounded-2xl transition-all pointer-events-none" />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  )
}
