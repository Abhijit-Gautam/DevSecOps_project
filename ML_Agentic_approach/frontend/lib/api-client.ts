import { API_ENDPOINTS } from './config'
import type { ReportResponse, ApiError } from './types'

export class ApiError extends Error {
  constructor(
    public statusCode: number,
    public detail: string,
    message: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    try {
      const error: ApiError = await response.json()
      throw new ApiError(
        response.status,
        error.detail || 'Unknown error',
        error.error || 'Request failed'
      )
    } catch (e) {
      if (e instanceof ApiError) throw e
      throw new ApiError(
        response.status,
        'Unknown error',
        `HTTP ${response.status}: ${response.statusText}`
      )
    }
  }

  return response.json()
}

export const apiClient = {
  /**
   * Evaluate a report by uploading a file
   */
  evaluateFile: async (
    file: File,
    options: {
      run_srlm?: boolean
      run_highlights?: boolean
      run_fol?: boolean
      run_xai?: boolean
    } = {}
  ): Promise<ReportResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('run_srlm', String(options.run_srlm ?? true))
    formData.append('run_highlights', String(options.run_highlights ?? true))
    formData.append('run_fol', String(options.run_fol ?? true))
    formData.append('run_xai', String(options.run_xai ?? true))

    const response = await fetch(API_ENDPOINTS.EVALUATE_UPLOAD, {
      method: 'POST',
      body: formData,
    })

    return handleResponse<ReportResponse>(response)
  },

  /**
   * Evaluate a report by submitting text directly
   */
  evaluateText: async (
    text: string,
    filename: string,
    options: {
      run_srlm?: boolean
      run_highlights?: boolean
      run_fol?: boolean
      run_xai?: boolean
    } = {}
  ): Promise<ReportResponse> => {
    const response = await fetch(API_ENDPOINTS.EVALUATE_TEXT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text,
        filename,
        run_srlm: options.run_srlm ?? true,
        run_highlights: options.run_highlights ?? true,
        run_fol: options.run_fol ?? true,
        run_xai: options.run_xai ?? true,
      }),
    })

    return handleResponse<ReportResponse>(response)
  },

  /**
   * Get all reports with optional filtering
   */
  getReports: async (
    domain?: string,
    label?: string,
    limit: number = 50,
    offset: number = 0
  ) => {
    const params = new URLSearchParams()
    if (domain) params.append('domain', domain)
    if (label) params.append('label', label)
    params.append('limit', String(limit))
    params.append('offset', String(offset))

    const response = await fetch(
      `${API_ENDPOINTS.REPORTS}?${params.toString()}`
    )

    return handleResponse(response)
  },

  /**
   * Get a specific report by ID
   */
  getReport: async (reportId: string, includeText: boolean = false) => {
    const url = new URL(`${API_ENDPOINTS.REPORTS}/${reportId}`)
    if (includeText) url.searchParams.append('include_text', 'true')

    const response = await fetch(url.toString())
    return handleResponse(response)
  },

  /**
   * Delete a report
   */
  deleteReport: async (reportId: string) => {
    const response = await fetch(`${API_ENDPOINTS.REPORTS}/${reportId}`, {
      method: 'DELETE',
    })

    return handleResponse(response)
  },

  /**
   * Get report highlights
   */
  getReportHighlights: async (reportId: string) => {
    const response = await fetch(`${API_ENDPOINTS.REPORTS}/${reportId}/highlights`)
    return handleResponse(response)
  },

  /**
   * Get thought process steps
   */
  getThoughtProcess: async (reportId: string) => {
    const response = await fetch(`${API_ENDPOINTS.REPORTS}/${reportId}/thought-process`)
    return handleResponse(response)
  },

  /**
   * Get FOL verification result
   */
  getFOLResult: async (reportId: string) => {
    const response = await fetch(`${API_ENDPOINTS.REPORTS}/${reportId}/fol`)
    return handleResponse(response)
  },

  /**
   * Get agent evaluations
   */
  getAgentEvaluations: async (reportId: string) => {
    const response = await fetch(`${API_ENDPOINTS.REPORTS}/${reportId}/agents`)
    return handleResponse(response)
  },

  /**
   * Get XAI explanation
   */
  getXAIExplanation: async (reportId: string) => {
    const response = await fetch(`${API_ENDPOINTS.REPORTS}/${reportId}/xai`)
    return handleResponse(response)
  },

  /**
   * Get full report text
   */
  getReportText: async (reportId: string) => {
    const response = await fetch(`${API_ENDPOINTS.REPORTS}/${reportId}/full-text`)
    return handleResponse(response)
  },

  /**
   * Get analytics overview
   */
  getAnalyticsOverview: async () => {
    const response = await fetch(API_ENDPOINTS.ANALYTICS_OVERVIEW)
    return handleResponse(response)
  },

  /**
   * Health check
   */
  healthCheck: async () => {
    const response = await fetch(API_ENDPOINTS.HEALTH)
    return handleResponse(response)
  },
}
