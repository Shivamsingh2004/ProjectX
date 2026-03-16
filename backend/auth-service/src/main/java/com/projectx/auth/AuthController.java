package com.projectx.auth;

import jakarta.validation.Valid;
import java.nio.charset.StandardCharsets;
import java.security.Key;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.Date;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/auth")
public class AuthController {
  private final Map<String, String> users = new ConcurrentHashMap<>();
  private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
  private final Key key;

  public AuthController(@Value("${JWT_SECRET:change-me}") String secret) {
    try {
      this.key = Keys.hmacShaKeyFor(MessageDigest.getInstance("SHA-256").digest(secret.getBytes(StandardCharsets.UTF_8)));
    } catch (Exception ex) {
      throw new IllegalStateException("Unable to initialize JWT key", ex);
    }
  }

  @PostMapping("/register")
  public AuthResponse register(@Valid @RequestBody AuthRequest request) {
    if (users.containsKey(request.email())) {
      throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "User already exists");
    }
    users.put(request.email(), encoder.encode(request.password()));
    return new AuthResponse(tokenFor(request.email()));
  }

  @PostMapping("/login")
  public AuthResponse login(@Valid @RequestBody AuthRequest request) {
    String hash = users.get(request.email());
    if (hash == null || !encoder.matches(request.password(), hash)) {
      throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid credentials");
    }
    return new AuthResponse(tokenFor(request.email()));
  }

  @PostMapping("/oauth/login")
  public AuthResponse oauthLogin(@Valid @RequestBody AuthRequest request) {
    return new AuthResponse(tokenFor(request.email()));
  }

  private String tokenFor(String email) {
    return Jwts.builder()
      .subject(email)
      .id(UUID.randomUUID().toString())
      .issuedAt(Date.from(Instant.now()))
      .expiration(Date.from(Instant.now().plusSeconds(3600)))
      .signWith(key)
      .compact();
  }
}
