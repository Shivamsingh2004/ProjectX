package com.projectx.messaging.controller;

import jakarta.validation.Valid;
import java.time.Duration;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import org.springframework.web.server.ResponseStatusException;

/**
 * AI integration controller that generates reply suggestions for the authenticated user.
 *
 * <p>Flow:
 * <ol>
 *   <li>Validate the incoming request body
 *   <li>Extract the authenticated user (sub) from the Supabase JWT
 *   <li>Fetch the user's AI context from the user-service
 *   <li>Forward message + context to the external FastAPI AI service
 *   <li>Return the structured suggestion to the frontend
 * </ol>
 *
 * <p>Timeouts and fallback: if the AI service fails or times out, a safe fallback suggestion is
 * returned so the UI remains functional.
 */
@RestController
@RequestMapping("/api")
public class AIController {

  private static final Logger log = LoggerFactory.getLogger(AIController.class);

  private static final Duration AI_TIMEOUT = Duration.ofSeconds(10);
  private static final AiReplyResponse FALLBACK =
      new AiReplyResponse("casual", List.of("Ask an open-ended, friendly follow-up question."));

  private final WebClient aiServiceClient;
  private final WebClient userServiceClient;

  public AIController(
      @Value("${ai-service.base-url}") String aiServiceBaseUrl,
      @Value("${user-service.base-url}") String userServiceBaseUrl) {
    this.aiServiceClient =
        WebClient.builder()
            .baseUrl(aiServiceBaseUrl)
            .defaultHeader("Content-Type", MediaType.APPLICATION_JSON_VALUE)
            .build();
    this.userServiceClient =
        WebClient.builder()
            .baseUrl(userServiceBaseUrl)
            .defaultHeader("Content-Type", MediaType.APPLICATION_JSON_VALUE)
            .build();
  }

  /**
   * Generates an AI reply suggestion for a given message.
   *
   * @param jwt     the authenticated Supabase user (injected by Spring Security)
   * @param request the request body containing the user's message
   * @return an {@link AiReplyResponse} with the suggestion and confidence score
   */
  @CircuitBreaker(name = "aiService", fallbackMethod = "suggestReplyFallback")
  @PostMapping("/ai/reply")
  public AiReplyResponse suggestReply(
      @AuthenticationPrincipal Jwt jwt, @Valid @RequestBody AiReplyRequest request) {

    String userId = resolveUserId(jwt);
    String sanitizedMessage = sanitize(request.message());
    String aiContext = fetchAiContext(userId, jwt);

    return callAiService(sanitizedMessage, aiContext);
  }

  // ── private helpers ──────────────────────────────────────────────────────────

  public AiReplyResponse suggestReplyFallback(Jwt jwt, AiReplyRequest request, Throwable t) {
      log.warn("AI service call failed, returning fallback. Error: {}", t.getMessage());
      return FALLBACK;
  }

  private String fetchAiContext(String userId, Jwt jwt) {
    try {
      String authHeader = jwt != null ? "Bearer " + jwt.getTokenValue() : "";
      AiContextResponse ctx =
          userServiceClient
              .get()
              .uri("/api/users/{userId}/ai-context", userId)
              .header("Authorization", authHeader)
              .retrieve()
              .bodyToMono(AiContextResponse.class)
              .timeout(Duration.ofSeconds(5))
              .block();
      return (ctx != null && ctx.context() != null) ? ctx.context() : "";
    } catch (Exception ex) {
      log.warn("Could not fetch AI context for user {}: {}", userId, ex.getMessage());
      return "";
    }
  }

  private AiReplyResponse callAiService(String message, String context) {
    try {
      Map<?, ?> aiResponse =
          aiServiceClient
              .post()
              .uri("/ai/reply-suggestion")
              .bodyValue(Map.of("message", message, "context", context))
              .retrieve()
              .bodyToMono(Map.class)
              .timeout(AI_TIMEOUT)
              .block();

      if (aiResponse == null) {
        return FALLBACK;
      }

      Object rawSuggestions = aiResponse.get("suggestions");
      Object rawTone = aiResponse.get("tone");
      
      List<String> suggestions = (rawSuggestions instanceof List) ? 
          ((List<?>) rawSuggestions).stream().map(String::valueOf).toList() : FALLBACK.suggestions();
      String tone = (rawTone != null) ? String.valueOf(rawTone) : FALLBACK.tone();
      
      return new AiReplyResponse(tone, suggestions);

    } catch (WebClientResponseException ex) {
      log.error("AI service returned error {}: {}", ex.getStatusCode(), ex.getMessage());
      if (ex.getStatusCode().value() >= 500) {
        return FALLBACK;
      }
      throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "AI service error");
    } catch (Exception ex) {
      log.error("AI service call failed: {}", ex.getMessage());
      return FALLBACK;
    }
  }

  private static String resolveUserId(Jwt jwt) {
    if (jwt == null) {
      return "default";
    }
    String sub = jwt.getSubject();
    return (sub != null && !sub.isBlank()) ? sub : "default";
  }

  /**
   * Basic sanitization: strips leading/trailing whitespace and removes non-printable control
   * characters while preserving newlines ({@code \n}), carriage returns ({@code \r}), and
   * horizontal tabs ({@code \t}).
   *
   * <p>Newlines and tabs are intentionally preserved because they appear in legitimate multi-line
   * conversation messages. All other C0/C1 control characters (e.g. NUL, BEL, ESC, DEL) are
   * stripped to prevent prompt-injection via invisible characters and to ensure the content is safe
   * to embed in JSON or forward to the AI service.
   */
  private static String sanitize(String input) {
    if (input == null) {
      return "";
    }
    // Remove non-printable control characters (keep newlines for multi-line messages)
    return input.strip().replaceAll("[\\p{Cntrl}&&[^\n\r\t]]", "");
  }

  /** Minimal DTO for deserialising the user-service AI context response. */
  private record AiContextResponse(String userId, String context) {}
}
