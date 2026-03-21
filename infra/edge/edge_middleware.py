# ============================================================================
# Edge Computing Layer: Cloudflare Workers / Vercel Edge Functions
#
# Ultra-low latency request filtering, bot detection, geo-routing,
# and response caching at the CDN edge — before requests hit origin.
# ============================================================================

# ── Edge Middleware (Next.js / Vercel Edge Runtime) ─────────────────────────
# This runs at the CDN edge in ~50 regions globally.
# File: frontend/middleware.ts

"""
// middleware.ts — runs at Vercel Edge (sub-10ms cold start)
import { NextRequest, NextResponse } from 'next/server';

const BLOCKED_COUNTRIES = ['XX']; // Sanctioned regions
const BOT_PATTERNS = /bot|crawl|spider|slurp|mediapartners/i;

// Rate limit state (edge KV)
const rateLimitMap = new Map<string, { count: number; reset: number }>();

export function middleware(request: NextRequest) {
  const geo = request.geo;
  const ip = request.headers.get('x-forwarded-for') || 'unknown';
  const ua = request.headers.get('user-agent') || '';

  // 1. Geo-blocking (sanctioned countries)
  if (geo?.country && BLOCKED_COUNTRIES.includes(geo.country)) {
    return new NextResponse('Access denied', { status: 403 });
  }

  // 2. Bot detection (block scrapers, allow search engines)
  if (BOT_PATTERNS.test(ua) && !ua.includes('Googlebot')) {
    return new NextResponse('Forbidden', { status: 403 });
  }

  // 3. Edge rate limiting (per-IP, 100 req/min)
  const now = Date.now();
  const limit = rateLimitMap.get(ip);
  if (limit && limit.reset > now) {
    if (limit.count >= 100) {
      return NextResponse.json(
        { error: 'RATE_LIMITED', retry_after: Math.ceil((limit.reset - now) / 1000) },
        { status: 429, headers: { 'Retry-After': String(Math.ceil((limit.reset - now) / 1000)) } }
      );
    }
    limit.count++;
  } else {
    rateLimitMap.set(ip, { count: 1, reset: now + 60000 });
  }

  // 4. Add edge metadata headers
  const response = NextResponse.next();
  response.headers.set('X-Edge-Region', geo?.region || 'unknown');
  response.headers.set('X-Edge-Country', geo?.country || 'unknown');
  response.headers.set('X-Edge-City', geo?.city || 'unknown');
  response.headers.set('X-Edge-Latency', String(Date.now() - now));

  return response;
}

export const config = {
  matcher: ['/api/:path*', '/dashboard/:path*'],
};
"""
