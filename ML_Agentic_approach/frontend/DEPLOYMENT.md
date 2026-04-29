# Deployment Guide

Complete guide for deploying the DevSecOps Report Evaluator frontend to production.

## Prerequisites

- Backend API deployed and running
- GitHub repository (for Vercel)
- Node.js 18+ installed locally

## 🚀 Deployment Options

### Option 1: Vercel (Recommended)

Vercel is the optimal choice since Next.js is built by Vercel.

#### Step 1: Prepare for Deployment

1. **Create `.env.local` with your backend URL:**
```env
NEXT_PUBLIC_API_URL=https://your-backend-domain.com
```

2. **Test locally:**
```bash
pnpm build
pnpm start
# Visit http://localhost:3000 and verify everything works
```

#### Step 2: Deploy to Vercel

**Option A: Using Vercel CLI**
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
# Follow prompts to connect GitHub and deploy
```

**Option B: Using GitHub Integration**
1. Push code to GitHub:
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

2. Go to https://vercel.com/new
3. Select your GitHub repository
4. Click "Import"
5. Configure project settings:
   - Framework: Next.js
   - Build command: `pnpm build` (default)
   - Output directory: `.next` (default)

#### Step 3: Set Environment Variables

1. Go to **Settings** → **Environment Variables**
2. Add `NEXT_PUBLIC_API_URL`:
   - **Key**: `NEXT_PUBLIC_API_URL`
   - **Value**: `https://your-backend-api.com`
   - **Environment**: Production (and Preview if needed)
3. Click "Save"
4. Trigger a redeploy

**Example Backend URLs:**
- Vercel: `https://backend-api.vercel.app`
- Railway: `https://yourapp-production.up.railway.app`
- Render: `https://yourapp.onrender.com`
- AWS: `https://api.yourdomain.com`
- Azure: `https://yourapp.azurewebsites.net`

#### Step 4: Verify Deployment

1. Visit your Vercel URL (e.g., `https://yourapp.vercel.app`)
2. Try uploading a test report
3. Verify all sections load correctly
4. Check browser DevTools console for errors

### Option 2: Netlify

Alternative to Vercel with similar ease of deployment.

#### Step 1: Build Locally

```bash
pnpm build
```

#### Step 2: Deploy via Netlify UI

1. Go to https://app.netlify.com
2. Click "Add new site" → "Import an existing project"
3. Select your GitHub repository
4. Configure build settings:
   - **Build command**: `pnpm build`
   - **Publish directory**: `.next`
5. Click "Deploy site"

#### Step 3: Add Environment Variables

1. Go to **Site settings** → **Build & deploy** → **Environment**
2. Add `NEXT_PUBLIC_API_URL` variable
3. Trigger a new build

**Note:** Netlify requires a Netlify plugin for Next.js. Use `@netlify/plugin-nextjs`.

### Option 3: Docker Deployment

Deploy to any Docker-supporting platform (AWS, GCP, Azure, etc.).

#### Create Dockerfile

```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN npm install -g pnpm && pnpm install --frozen-lockfile

# Copy source
COPY . .

# Build
RUN pnpm build

# Expose port
EXPOSE 3000

# Start
CMD ["pnpm", "start"]
```

#### Build and Push

```bash
# Build image
docker build -t report-evaluator:latest .

# Tag for registry (e.g., Docker Hub)
docker tag report-evaluator:latest your-registry/report-evaluator:latest

# Push
docker push your-registry/report-evaluator:latest
```

#### Deploy to Cloud Platforms

**AWS (using ECR + ECS):**
```bash
# Push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

docker tag report-evaluator:latest <account>.dkr.ecr.us-east-1.amazonaws.com/report-evaluator:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/report-evaluator:latest
```

**Google Cloud Run:**
```bash
gcloud run deploy report-evaluator \
  --image gcr.io/your-project/report-evaluator:latest \
  --platform managed \
  --region us-central1 \
  --set-env-vars NEXT_PUBLIC_API_URL=https://your-backend-api.com
```

**Azure Container Instances:**
```bash
az container create \
  --resource-group myResourceGroup \
  --name report-evaluator \
  --image <registry>.azurecr.io/report-evaluator:latest \
  --environment-variables NEXT_PUBLIC_API_URL=https://your-backend-api.com \
  --ports 3000 \
  --cpu 1 --memory 1
```

### Option 4: Self-Hosted (VPS/Dedicated Server)

Suitable for on-premises or dedicated infrastructure.

#### Step 1: Setup Server

1. SSH into your server
2. Install Node.js 18+:
```bash
curl https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
```

3. Install pnpm:
```bash
npm install -g pnpm
```

#### Step 2: Deploy Application

```bash
# Clone repository
git clone https://github.com/your-org/report-evaluator.git
cd report-evaluator

# Install dependencies
pnpm install

# Create .env.production.local
echo "NEXT_PUBLIC_API_URL=https://your-backend-api.com" > .env.production.local

# Build
pnpm build

# Start with PM2 (process manager)
npm install -g pm2
pm2 start "pnpm start" --name "report-evaluator"
pm2 startup
pm2 save
```

#### Step 3: Setup Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Setup SSL with Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --nginx -d yourdomain.com
```

## 🔒 Security Considerations

### Environment Variables

- **NEVER** commit `.env.local` or `.env.production.local`
- Use your platform's secure environment variable management
- Rotate secrets regularly
- Use different values for production vs. staging

### CORS Configuration

If your backend is on a different domain, ensure CORS is properly configured:

```python
# Flask backend example
from flask_cors import CORS
CORS(app, resources={r"/api/*": {"origins": ["https://yourfrontend.com"]}})
```

### API Security

- Use HTTPS only (enforce in browser via CSP headers)
- Implement rate limiting on backend
- Validate all inputs on both frontend and backend
- Use authentication tokens if needed

### Content Security Policy

Add to your `next.config.mjs`:
```javascript
const securityHeaders = [
  {
    key: 'Content-Security-Policy',
    value: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
  },
  {
    key: 'X-Frame-Options',
    value: 'SAMEORIGIN'
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff'
  },
]

export default {
  async headers() {
    return [{ source: '/:path*', headers: securityHeaders }]
  },
}
```

## 🔄 CI/CD Pipeline

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Vercel

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Vercel CLI
        run: npm install -g vercel
      
      - name: Deploy
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
          VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
          VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
        run: vercel --prod
```

## 📊 Monitoring & Analytics

### Enable Vercel Analytics
1. Go to project settings
2. Enable "Web Analytics"
3. View metrics at https://vercel.com/analytics

### Application Performance Monitoring

**Sentry (Error Tracking)**
```bash
pnpm add @sentry/nextjs
```

## 🆘 Troubleshooting Deployment

### "Cannot find module" errors

**Solution:**
```bash
# Clear caches
rm -rf node_modules pnpm-lock.yaml .next
pnpm install
pnpm build
```

### "NEXT_PUBLIC_API_URL is undefined"

**Solution:**
- Environment variables starting with `NEXT_PUBLIC_` are embedded at build time
- Ensure variable is set BEFORE building
- Rebuild after changing environment variables

### "API calls failing with 503"

**Solution:**
- Backend might be sleeping (on free tiers)
- Check backend logs
- Verify CORS is enabled on backend
- Test backend directly: `curl https://your-backend-api.com/api/health`

### "Uploads failing with CORS error"

**Solution:**
1. Check browser console for exact error
2. Backend CORS configuration:
```python
CORS(app, 
  origins=["https://yourfrontend.com"],
  allow_headers=["Content-Type"],
  expose_headers=["Content-Type"]
)
```

## 📈 Scaling Considerations

- Frontend is static after build (scales horizontally easily)
- Use CDN for static assets (Vercel does this automatically)
- Backend needs proper scaling for concurrent uploads
- Consider database for analytics if needed

## 🎉 Deployment Checklist

- [ ] Backend API is deployed and working
- [ ] Environment variables are set correctly
- [ ] Local build completes without errors
- [ ] Local testing passes
- [ ] Repository is clean (no .env files)
- [ ] Build succeeds on deployment platform
- [ ] Environment variables are set on platform
- [ ] Deployment completes successfully
- [ ] Can access application in browser
- [ ] Can upload a test file and see results
- [ ] All sections load correctly
- [ ] API calls work (check network tab)
- [ ] No console errors in DevTools
- [ ] Mobile/responsive design works
- [ ] Forms are functional

---

**Deployment successful! 🚀**
