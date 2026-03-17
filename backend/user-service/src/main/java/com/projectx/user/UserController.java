package com.projectx.user;

import jakarta.validation.Valid;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/users")
public class UserController {

  private final UserService userService;

  public UserController(UserService userService) {
    this.userService = userService;
  }

  /** Get the profile for the authenticated / default user. */
  @GetMapping("/profile")
  public UserProfile getProfile() {
    return userService.getUserProfile("default");
  }

  /** Update the profile for the authenticated / default user. */
  @PutMapping("/profile")
  public UserProfile updateProfile(@Valid @RequestBody UserProfile update) {
    return userService.saveProfile("default", update);
  }

  /** Get the full profile for a specific user (used by other services). */
  @GetMapping("/{userId}/profile")
  public UserProfile getUserProfile(@PathVariable String userId) {
    return userService.getUserProfile(userId);
  }

  /** Get preferences and personality traits for a specific user. */
  @GetMapping("/{userId}/preferences")
  public Map<String, List<String>> getUserPreferences(@PathVariable String userId) {
    return userService.getUserPreferences(userId);
  }

  /**
   * Build an AI context string for a specific user.
   * This endpoint is called by the AI service / Spring Boot gateway.
   */
  @GetMapping("/{userId}/ai-context")
  public Map<String, String> getAIContext(@PathVariable String userId) {
    return Map.of("context", userService.buildAIContext(userId));
  }
}
