package com.projectx.user;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicReference;
import org.springframework.stereotype.Service;

/**
 * User intelligence layer: stores profile, preferences, personality traits,
 * and builds AI context strings consumed by the AI service.
 */
@Service
public class UserService {

  // In-memory store keyed by userId. A real implementation would use a database.
  private final Map<String, AtomicReference<UserProfile>> profiles = new ConcurrentHashMap<>();
  private final String DEFAULT_USER_ID = "default";

  public UserService() {
    // Seed a default profile
    profiles.put(DEFAULT_USER_ID, new AtomicReference<>(new UserProfile(
        "New User",
        "Just here to meet awesome people.",
        List.of("gym", "travel", "music"),
        List.of("serious relationship"),
        List.of("outgoing", "funny", "adventurous"),
        List.of()
    )));
  }

  /**
   * Return the full {@link UserProfile} for the given user.
   * Returns a default profile when the user is not found.
   */
  public UserProfile getUserProfile(String userId) {
    AtomicReference<UserProfile> ref = profiles.get(userId);
    if (ref == null) {
      ref = profiles.get(DEFAULT_USER_ID);
    }
    return ref.get();
  }

  /**
   * Return just the preferences and personality traits for the given user.
   */
  public Map<String, List<String>> getUserPreferences(String userId) {
    UserProfile profile = getUserProfile(userId);
    return Map.of(
        "interests", profile.interests(),
        "preferences", profile.preferences(),
        "personalityTraits", profile.personalityTraits()
    );
  }

  /**
   * Build a plain-text AI context string from the user's profile data.
   *
   * <p>Example output: {@code "User likes gym, travel, and music. Personality: outgoing and funny."}
   */
  public String buildAIContext(String userId) {
    UserProfile profile = getUserProfile(userId);

    StringBuilder sb = new StringBuilder();

    List<String> interests = profile.interests();
    if (!interests.isEmpty()) {
      sb.append("User likes ").append(joinHuman(interests)).append(". ");
    }

    List<String> preferences = profile.preferences();
    if (!preferences.isEmpty()) {
      sb.append("Looking for ").append(joinHuman(preferences)).append(". ");
    }

    List<String> traits = profile.personalityTraits();
    if (!traits.isEmpty()) {
      sb.append("Personality: ").append(joinHuman(traits)).append(".");
    }

    return sb.toString().trim();
  }

  /**
   * Store or update a profile for the given user.
   */
  public UserProfile saveProfile(String userId, UserProfile profile) {
    profiles.computeIfAbsent(userId, k -> new AtomicReference<>()).set(profile);
    return profile;
  }

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------

  private static String joinHuman(List<String> items) {
    if (items.isEmpty()) return "";
    if (items.size() == 1) return items.get(0);
    if (items.size() == 2) return items.get(0) + " and " + items.get(1);
    String allButLast = String.join(", ", items.subList(0, items.size() - 1));
    return allButLast + ", and " + items.get(items.size() - 1);
  }
}
