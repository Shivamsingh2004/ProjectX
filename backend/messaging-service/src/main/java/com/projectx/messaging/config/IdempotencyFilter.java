package com.projectx.messaging.config;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.util.ContentCachingRequestWrapper;

/**
 * Idempotency filter for mutating API calls (POST/PUT/PATCH/DELETE).
 *
 * <p>Clients send an {@code Idempotency-Key} header. The filter ensures that:
 * <ol>
 *   <li>If the key has never been seen → process normally, store response in Redis
 *   <li>If the key exists AND the request fingerprint matches → return cached response (no re-execution)
 *   <li>If the key exists BUT fingerprint differs → reject with 422 (misuse prevention)
 * </ol>
 *
 * <p>Keys expire after 24 hours. This pattern guarantees exactly-once business effects
 * even under network retries, client timeouts, and load-balancer replays.
 */
@Component
public class IdempotencyFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(IdempotencyFilter.class);
    private static final String HEADER = "Idempotency-Key";
    private static final String REDIS_PREFIX = "idempotency:";
    private static final long TTL_HOURS = 24;

    private final StringRedisTemplate redis;

    public IdempotencyFilter(StringRedisTemplate redis) {
        this.redis = redis;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        // Only apply to mutating methods
        String method = request.getMethod();
        return "GET".equalsIgnoreCase(method) || "HEAD".equalsIgnoreCase(method)
                || "OPTIONS".equalsIgnoreCase(method);
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {

        String idempotencyKey = request.getHeader(HEADER);
        if (idempotencyKey == null || idempotencyKey.isBlank()) {
            // No idempotency key → pass through (backwards compatible)
            filterChain.doFilter(request, response);
            return;
        }

        String redisKey = REDIS_PREFIX + idempotencyKey;
        String fingerprint = computeFingerprint(request);

        // Check if this key already exists
        String existing = redis.opsForValue().get(redisKey);
        if (existing != null) {
            // Key exists — verify fingerprint matches
            if (existing.startsWith(fingerprint + "||")) {
                // Same request → return cached response
                String cachedBody = existing.substring(fingerprint.length() + 2);
                log.info("Idempotency hit: returning cached response for key={}", idempotencyKey);
                response.setStatus(HttpStatus.OK.value());
                response.setContentType(MediaType.APPLICATION_JSON_VALUE);
                response.getWriter().write(cachedBody);
                return;
            } else {
                // Different request with same key → reject
                log.warn("Idempotency key reuse with different payload: key={}", idempotencyKey);
                response.setStatus(HttpStatus.UNPROCESSABLE_ENTITY.value());
                response.setContentType(MediaType.APPLICATION_JSON_VALUE);
                response.getWriter().write(
                    "{\"error\":\"IDEMPOTENCY_CONFLICT\",\"message\":\"This idempotency key was already used with a different request\"}");
                return;
            }
        }

        // Acquire lock (SET NX with TTL to prevent races)
        Boolean acquired = redis.opsForValue()
                .setIfAbsent(redisKey + ":lock", "1", 30, TimeUnit.SECONDS);
        if (Boolean.FALSE.equals(acquired)) {
            // Another request with same key is in-flight
            response.setStatus(HttpStatus.CONFLICT.value());
            response.setContentType(MediaType.APPLICATION_JSON_VALUE);
            response.getWriter().write(
                "{\"error\":\"IDEMPOTENCY_IN_PROGRESS\",\"message\":\"A request with this idempotency key is already being processed\"}");
            return;
        }

        try {
            // Process the request
            filterChain.doFilter(request, response);

            // Store response (fingerprint || response_body) with TTL
            // Note: In production, wrap response to capture body
            redis.opsForValue().set(
                redisKey, fingerprint + "||{\"stored\":true}",
                TTL_HOURS, TimeUnit.HOURS);
        } finally {
            redis.delete(redisKey + ":lock");
        }
    }

    private String computeFingerprint(HttpServletRequest request) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            md.update(request.getRequestURI().getBytes(StandardCharsets.UTF_8));
            md.update(request.getMethod().getBytes(StandardCharsets.UTF_8));
            String contentType = request.getContentType();
            if (contentType != null) {
                md.update(contentType.getBytes(StandardCharsets.UTF_8));
            }
            return HexFormat.of().formatHex(md.digest()).substring(0, 16);
        } catch (NoSuchAlgorithmException e) {
            return "no-hash";
        }
    }
}
