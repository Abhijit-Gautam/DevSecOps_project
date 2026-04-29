# API Integration Guide

Comprehensive guide for integrating the frontend with the Flask backend API.

## 📋 Quick Start

### 1. Backend Requirements

Ensure your Flask backend is running:
```bash
cd backend
pip install -r requirements.txt
python app.py
# Should be accessible at http://localhost:5000
```

### 2. Frontend Configuration

Edit `lib/config.ts`:
```typescript
export const API_BASE_URL = 'http://localhost:5000' // or your backend URL
```

Or set environment variable:
```bash
NEXT_PUBLIC_API_URL=http://localhost:5000
```

### 3. Start Frontend Dev Server

```bash
pnpm dev
# Visit http://localhost:3000
```

### 4. Test Integration

1. Open DevTools → Network tab
2. Upload a test file
3. Watch the API calls in Network tab
4. Check response data

## 🔌 API Endpoints Reference

All endpoints are defined in `lib/config.ts`:

```typescript
export const API_ENDPOINTS = {
  EVALUATE_UPLOAD: '/api/evaluate/upload',      // POST - upload file
  EVALUATE_TEXT: '/api/evaluate/text',          // POST - evaluate text
  REPORTS: '/api/reports',                      // GET - list reports
  HEALTH: '/api/health',                        // GET - health check
  ANALYTICS_OVERVIEW: '/api/analytics/overview' // GET - analytics
}
```

## 📡 Using the API Client

The `lib/api-client.ts` provides a clean interface for API calls:

```typescript
import { apiClient } from '@/lib/api-client'

// Upload a file
try {
  const response = await apiClient.evaluateFile(file, {
    run_srlm: true,
    run_highlights: true,
    run_fol: true,
    run_xai: true,
  })
  console.log(response)
} catch (error) {
  console.error('Upload failed:', error)
}

// Evaluate text
const textResponse = await apiClient.evaluateText(
  'Report text here...',
  'my_report.txt'
)

// Get reports
const reports = await apiClient.getReports()

// Health check
const health = await apiClient.healthCheck()
```

## 🔄 Request/Response Flow

### File Upload Flow

```
User selects file
    ↓
[upload-section.tsx] calls apiClient.evaluateFile()
    ↓
FormData created with file + options
    ↓
POST /api/evaluate/upload
    ↓
Backend processes (30-60 seconds)
    ↓
JSON response with ReportResponse type
    ↓
[page.tsx] receives data
    ↓
Render results dashboard with all panels
```

### Request Example

```bash
curl -X POST http://localhost:5000/api/evaluate/upload \
  -F "file=@report.pdf" \
  -F "run_srlm=true" \
  -F "run_highlights=true" \
  -F "run_fol=true" \
  -F "run_xai=true"
```

### Response Structure

```json
{
  "report_id": "a1b2c3d4",
  "filename": "report.pdf",
  "elapsed_ms": 45000,
  "status": "complete",
  "parsed_data": { ... },
  "roberta_result": { ... },
  "unified_verdict": { ... },
  "agent_evaluations": [ ... ],
  "self_reward_scores": { ... },
  "highlight_data": { ... },
  "xai_result": { ... },
  "fol_result": { ... },
  "thought_process": [ ... ]
}
```

## 🛠️ TypeScript Integration

All response types are defined in `lib/types.ts`:

```typescript
import type { ReportResponse, AgentEvaluation, XAIResult } from '@/lib/types'

const handleResponse = (data: ReportResponse) => {
  // Full type safety
  console.log(data.unified_verdict.final_verdict) // ✓ TypeScript knows type
  console.log(data.agent_evaluations[0].score)     // ✓ Full autocomplete
}
```

## 🐛 Debugging API Issues

### 1. Network Tab Inspection

In Chrome DevTools:
1. Open DevTools → Network tab
2. Try to upload a file
3. Look for the POST request
4. Click the request to see:
   - Request headers
   - Request body
   - Response headers
   - Response preview

### 2. Console Logging

Frontend logs:
```typescript
// In app/page.tsx
console.log('[API] Response:', data)
console.log('[API] Error:', error)
```

Backend logs:
```bash
# Watch Flask logs in terminal
# Should show:
# - POST /api/evaluate/upload
# - Status codes
# - Error messages
```

### 3. Check Backend Health

```bash
# Test backend is running
curl http://localhost:5000/api/health

# Expected response:
# {
#   "status": "healthy",
#   "components": {
#     "model": { "status": "ok" },
#     "ollama": { "status": "ok" },
#     "db": { "status": "ok" }
#   }
# }
```

## ❌ Common Issues & Solutions

### Issue: "Failed to fetch" or Network Error

**Cause:** Backend not running or unreachable

**Solution:**
```bash
# 1. Check if backend is running
curl http://localhost:5000/api/health

# 2. If not running, start it
cd backend
python app.py

# 3. Verify backend URL in config
# lib/config.ts should point to correct URL

# 4. Check CORS headers in browser
# Network tab → Response Headers should have:
# Access-Control-Allow-Origin: *
```

### Issue: "CORS error" (cross-origin request blocked)

**Cause:** Backend doesn't allow requests from frontend domain

**Solution (Backend):**
```python
from flask_cors import CORS

# Enable CORS for all origins (dev) or specific origins (prod)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# For production, be more specific:
CORS(app, resources={
    r"/api/*": {
        "origins": ["https://yourfrontend.com"],
        "methods": ["GET", "POST", "DELETE"],
        "allow_headers": ["Content-Type"]
    }
})
```

### Issue: 503 Error - "Model Still Loading"

**Cause:** Models are loading on first request

**Solution:**
- Backend loads RoBERTa and Ollama on startup
- First request may take 30-60 seconds
- Wait for `/api/health` to return `"status": "healthy"`
- Then try upload again

### Issue: File Upload Stuck / Timeout

**Cause:** Large file or slow network

**Solution:**
```typescript
// Increase fetch timeout in lib/api-client.ts
const controller = new AbortController()
const timeoutId = setTimeout(() => controller.abort(), 300000) // 5 minutes

const response = await fetch(API_ENDPOINTS.EVALUATE_UPLOAD, {
  method: 'POST',
  body: formData,
  signal: controller.signal, // Add timeout
})

clearTimeout(timeoutId)
```

### Issue: "Cannot read properties of undefined"

**Cause:** API response missing expected fields

**Solution:**
1. Check backend response structure
2. Verify all fields in `lib/types.ts`
3. Add null checks in components:
```typescript
{data?.unified_verdict && (
  <VerdictCard verdict={data.unified_verdict} />
)}
```

### Issue: Environment Variables Not Loading

**Cause:** Variable not prefixed with `NEXT_PUBLIC_`

**Solution:**
```bash
# ✓ CORRECT - accessible in browser
NEXT_PUBLIC_API_URL=http://localhost:5000

# ✗ WRONG - only available on server
API_URL=http://localhost:5000

# For Vercel, set in project settings:
# Settings → Environment Variables → Add
```

## 📝 Adding New API Endpoints

1. **Add to Backend** (Flask):
```python
@app.route('/api/new-endpoint', methods=['POST'])
def new_endpoint():
    return jsonify({"result": "data"})
```

2. **Update Config** (`lib/config.ts`):
```typescript
export const API_ENDPOINTS = {
  // ... existing
  NEW_ENDPOINT: `${API_BASE_URL}/api/new-endpoint`,
}
```

3. **Add Type** (`lib/types.ts`):
```typescript
export interface NewResponse {
  result: string
}
```

4. **Add to Client** (`lib/api-client.ts`):
```typescript
newEndpoint: async (): Promise<NewResponse> => {
  const response = await fetch(API_ENDPOINTS.NEW_ENDPOINT, {
    method: 'POST',
  })
  return handleResponse<NewResponse>(response)
}
```

5. **Use in Components**:
```typescript
const data = await apiClient.newEndpoint()
```

## 🔐 Production API Security

### 1. HTTPS Only

```typescript
// lib/config.ts
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.yourdomain.com'
```

### 2. API Key / Auth Token

```typescript
// lib/api-client.ts
const response = await fetch(endpoint, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${process.env.NEXT_PUBLIC_API_KEY}`,
  },
  body: formData,
})
```

### 3. Rate Limiting

Implement on backend:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(app, key_func=get_remote_address)

@app.route('/api/evaluate/upload', methods=['POST'])
@limiter.limit("5 per minute")
def evaluate_upload():
    # ...
```

### 4. Input Validation

Frontend:
```typescript
// Check file size
if (file.size > 16 * 1024 * 1024) { // 16 MB
  throw new Error('File too large')
}

// Check file type
const validTypes = ['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
if (!validTypes.includes(file.type)) {
  throw new Error('Invalid file type')
}
```

## 📊 API Performance Tips

### 1. Request Caching
```typescript
// Cache recent reports
const cache = new Map<string, ReportResponse>()
```

### 2. Progressive Loading
```typescript
// Show results as they arrive
setVerdictData(response.unified_verdict) // Show first
setAgentData(response.agent_evaluations) // Then agents
setXAIData(response.xai_result)           // Then XAI
```

### 3. Compression
```typescript
// Backend should return gzip compressed
// Nginx/Apache handles automatically
```

## 🧪 Testing API Integration

```typescript
// __tests__/api.test.ts
import { apiClient } from '@/lib/api-client'

describe('API Client', () => {
  it('should fetch health status', async () => {
    const health = await apiClient.healthCheck()
    expect(health.status).toBe('healthy')
  })

  it('should handle errors', async () => {
    try {
      await apiClient.getReport('invalid-id')
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
    }
  })
})
```

## 📚 Additional Resources

- [BACKEND.md](./user_read_only_context/text_attachments/BACKEND-0auf9.md) - Full backend API documentation
- [lib/types.ts](./lib/types.ts) - Complete TypeScript definitions
- [lib/api-client.ts](./lib/api-client.ts) - API client implementation
- [app/page.tsx](./app/page.tsx) - Usage examples

---

**Ready to integrate! 🔌**
