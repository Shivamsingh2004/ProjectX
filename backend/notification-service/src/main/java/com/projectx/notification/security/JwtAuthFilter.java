package com.projectx.notification.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;
import org.springframework.http.MediaType;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtException;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Supabase JWT authentication filter for the messaging-service.
 *
 * <p>Validates Bearer tokens from the Authorization header using Supabase's JWKS endpoint and
 * populates the {@link org.springframework.security.core.context.SecurityContext} with the
 * authenticated principal.
 */
public class JwtAuthFilter extends OncePerRequestFilter {

  private final JwtDecoder jwtDecoder;

  public JwtAuthFilter(JwtDecoder jwtDecoder) {
    this.jwtDecoder = jwtDecoder;
  }

  @Override
  protected void doFilterInternal(
      HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
      throws ServletException, IOException {

    String token = extractBearerToken(request);
    if (!StringUtils.hasText(token)) {
      filterChain.doFilter(request, response);
      return;
    }

    try {
      Jwt jwt = jwtDecoder.decode(token);
      JwtAuthenticationToken authentication =
          new JwtAuthenticationToken(jwt, List.of(new SimpleGrantedAuthority("ROLE_USER")));
      SecurityContextHolder.getContext().setAuthentication(authentication);
    } catch (JwtException ex) {
      SecurityContextHolder.clearContext();
      writeUnauthorized(response, resolveErrorMessage(ex));
      return;
    }

    filterChain.doFilter(request, response);
  }

  private static String extractBearerToken(HttpServletRequest request) {
    String header = request.getHeader("Authorization");
    if (StringUtils.hasText(header) && header.startsWith("Bearer ")) {
      return header.substring(7).trim();
    }
    return null;
  }

  private static String resolveErrorMessage(JwtException ex) {
    String msg = ex.getMessage();
    if (msg != null && msg.contains("expired")) {
      return "Token has expired";
    }
    if (msg != null && msg.contains("issuer")) {
      return "Invalid token issuer";
    }
    return "Invalid token";
  }

  private static void writeUnauthorized(HttpServletResponse response, String message)
      throws IOException {
    response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
    response.setContentType(MediaType.APPLICATION_JSON_VALUE);
    response.getWriter()
        .write(
            "{\"error\":\"UNAUTHORIZED\",\"message\":\""
                + escapeJson(message)
                + "\",\"status\":401}");
  }

  private static String escapeJson(String s) {
    if (s == null) {
      return "";
    }
    return s.replace("\\", "\\\\").replace("\"", "\\\"");
  }
}
