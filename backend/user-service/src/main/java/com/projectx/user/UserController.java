package com.projectx.user;

import jakarta.validation.Valid;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/users")
public class UserController {

  private final UserService userService;

  public UserController(UserService userService) {
    this.userService = userService;
  }

  /** Returns the authenticated user's profile. */
  @GetMapping("/profile")
  public UserProfile getProfile(@AuthenticationPrincipal Jwt jwt) {
    return userService.getUserProfile(resolveUserId(jwt));
  }

  /** Updates the authenticated user's profile. */
  @PutMapping("/profile")
  public UserProfile updateProfile(
      @AuthenticationPrincipal Jwt jwt, @Valid @RequestBody UserProfile update) {
    return userService.saveUserProfile(resolveUserId(jwt), update);
  }

  /** Returns the authenticated user's dating preferences. */
  @GetMapping("/preferences")
  public List<String> getPreferences(@AuthenticationPrincipal Jwt jwt) {
    return userService.getUserPreferences(resolveUserId(jwt));
  }

  /**
   * Returns the AI context string for the given userId.
   *
   * <p>Access is restricted: the authenticated user may only request their own context.
   */
  @GetMapping("/{userId}/ai-context")
  public AiContextResponse getAiContext(
      @AuthenticationPrincipal Jwt jwt, @PathVariable String userId) {
    String authenticatedId = resolveUserId(jwt);
    if (!authenticatedId.equals(userId)) {
      throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Access denied");
    }
    return new AiContextResponse(userId, userService.buildAIContext(userId));
  }

  /**
   * Returns a map of all personalization fields (interests, preferences, traits, behavior)
   * for the given userId.
   *
   * <p>Access is restricted: the authenticated user may only request their own preferences.
   */
  @GetMapping("/{userId}/preferences")
  public Map<String, List<String>> getUserPreferences(
      @AuthenticationPrincipal Jwt jwt, @PathVariable String userId) {
    String authenticatedId = resolveUserId(jwt);
    if (!authenticatedId.equals(userId)) {
      throw new ResponseStatusException(HttpStatus.FORBIDDEN, "Access denied");
    }
    return userService.getUserPreferencesMap(userId);
  }

  // ── helpers ─────────────────────────────────────────────────────────────────

  private static String resolveUserId(Jwt jwt) {
    if (jwt == null) {
      return "default";
    }
    String sub = jwt.getSubject();
    return (sub != null && !sub.isBlank()) ? sub : "default";
  }
}
