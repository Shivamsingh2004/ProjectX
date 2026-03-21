package com.projectx.messaging.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.Instant;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Audit logging filter that captures every authenticated request as a structured
 * audit event. Placed after the JwtAuthFilter in the filter chain.
 *
 * <p>Populates MDC fields for downstream log correlation:
 * <ul>
 *   <li>{@code audit.user_id} — Supabase user UUID
 *   <li>{@code audit.method} — HTTP method
 *   <li>{@code audit.path} — Request URI
 *   <li>{@code audit.ip} — Client IP (X-Forwarded-For aware)
 *   <li>{@code audit.status} — HTTP response status
 *   <li>{@code audit.duration_ms} — Request processing time
 * </ul>
 */
@Component
public class AuditLoggingFilter extends OncePerRequestFilter {

    private static final Logger auditLog = LoggerFactory.getLogger("AUDIT");

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {

        long start = System.nanoTime();
        String userId = "anonymous";

        try {
            Authentication auth = SecurityContextHolder.getContext().getAuthentication();
            if (auth != null && auth.getPrincipal() instanceof Jwt jwt) {
                userId = jwt.getSubject() != null ? jwt.getSubject() : "anonymous";
            }

            // Populate MDC for structured logging
            MDC.put("audit.user_id", userId);
            MDC.put("audit.method", request.getMethod());
            MDC.put("audit.path", request.getRequestURI());
            MDC.put("audit.ip", resolveClientIp(request));
            MDC.put("audit.timestamp", Instant.now().toString());

            filterChain.doFilter(request, response);

        } finally {
            long durationMs = (System.nanoTime() - start) / 1_000_000;
            MDC.put("audit.status", String.valueOf(response.getStatus()));
            MDC.put("audit.duration_ms", String.valueOf(durationMs));

            // Emit structured audit log entry
            auditLog.info(
                "AUDIT user={} method={} path={} status={} ip={} duration_ms={}",
                userId,
                request.getMethod(),
                request.getRequestURI(),
                response.getStatus(),
                resolveClientIp(request),
                durationMs
            );

            MDC.clear();
        }
    }

    private static String resolveClientIp(HttpServletRequest request) {
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) {
            return xff.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
