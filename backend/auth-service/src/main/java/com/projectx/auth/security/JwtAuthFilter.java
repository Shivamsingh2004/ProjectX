package com.projectx.auth.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtException;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Validates Supabase JWTs on every protected request.
 *
 * <p>The filter:
 * <ol>
 *   <li>Extracts the Bearer token from the {@code Authorization} header.</li>
 *   <li>Decodes and verifies the signature using the Supabase JWKS endpoint.</li>
 *   <li>Checks token expiration and issuer claim.</li>
 *   <li>On success, attaches the authenticated user to the {@link SecurityContextHolder}.</li>
 *   <li>On failure, returns {@code 401 Unauthorized} immediately.</li>
 * </ol>
 */
@Component
public class JwtAuthFilter extends OncePerRequestFilter {

  private static final Logger log = LoggerFactory.getLogger(JwtAuthFilter.class);
  private static final String BEARER_PREFIX = "Bearer ";

  private final JwtDecoder jwtDecoder;
  private final String expectedIssuer;

  public JwtAuthFilter(
      @Value("${supabase.jwks-uri:}") String jwksUri,
      @Value("${supabase.issuer:}") String issuer) {
    this.expectedIssuer = issuer;
    if (jwksUri != null && !jwksUri.isBlank()) {
      this.jwtDecoder = NimbusJwtDecoder.withJwkSetUri(jwksUri).build();
    } else {
      // Only warn — the filter will reject all protected requests when unconfigured.
      log.warn("supabase.jwks-uri is not configured — all protected endpoints will return 401");
      this.jwtDecoder = null;
    }
  }

  @Override
  protected boolean shouldNotFilter(HttpServletRequest request) {
    String path = request.getRequestURI();
    // Skip public endpoints
    return path.startsWith("/api/auth/") || path.startsWith("/actuator/");
  }

  @Override
  protected void doFilterInternal(HttpServletRequest request,
      HttpServletResponse response, FilterChain filterChain)
      throws ServletException, IOException {

    if (jwtDecoder == null) {
      // JWKS URI not configured — reject all protected requests (fail-closed)
      reject(response, "Authentication service not configured");
      return;
    }

    String authHeader = request.getHeader(HttpHeaders.AUTHORIZATION);
    if (authHeader == null || !authHeader.startsWith(BEARER_PREFIX)) {
      reject(response, "Missing or malformed Authorization header");
      return;
    }

    String token = authHeader.substring(BEARER_PREFIX.length()).trim();
    try {
      Jwt jwt = jwtDecoder.decode(token);

      // Validate issuer when configured
      if (expectedIssuer != null && !expectedIssuer.isBlank()) {
        String tokenIssuer = jwt.getIssuer() != null ? jwt.getIssuer().toString() : "";
        if (!expectedIssuer.equals(tokenIssuer)) {
          reject(response, "Invalid token issuer");
          return;
        }
      }

      String subject = jwt.getSubject();
      UsernamePasswordAuthenticationToken auth = new UsernamePasswordAuthenticationToken(
          subject, null, List.of(new SimpleGrantedAuthority("ROLE_USER")));
      auth.setDetails(jwt.getClaims());
      SecurityContextHolder.getContext().setAuthentication(auth);

    } catch (JwtException ex) {
      log.warn("JWT validation failed: {}", ex.getMessage());
      reject(response, "Invalid or expired token");
      return;
    }

    filterChain.doFilter(request, response);
  }

  private static void reject(HttpServletResponse response, String message) throws IOException {
    response.setStatus(HttpStatus.UNAUTHORIZED.value());
    response.setContentType("application/json");
    response.getWriter().write("{\"error\":\"" + message + "\"}");
  }
}
