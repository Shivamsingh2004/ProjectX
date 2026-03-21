package com.projectx.user;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

/**
 * Personalization engine for managing per-user profiles and building structured AI context.
 *
 * <p>Data is currently held in-memory (ConcurrentHashMap keyed by userId). A production deployment
 * should swap this for a database-backed repository.
 */
@Service
public class UserService {

  private final Map<String, UserProfile> store = new ConcurrentHashMap<>();

  // ── Seeded demo profile ─────────────────────────────────────────────────────

  {
    store.put(
        "default",
        new UserProfile(
            "New User",
            "",
            List.of("travel", "gym", "music"),
            List.of("serious relationship"),
            List.of("outgoing", "funny"),
            List.of("active in evenings", "gym 3x/week"),
            List.of()));
  }

  // ── Public API ──────────────────────────────────────────────────────────────

  /**
   * Returns the full profile for the given user.
   *
   * @throws ResponseStatusException 404 when the user is not found
   */
  public UserProfile getUserProfile(String userId) {
    UserProfile profile = store.get(userId);
    if (profile == null) {
      throw new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found: " + userId);
    }
    return profile;
  }

  /**
   * Returns only the dating preferences for the given user.
   *
   * @throws ResponseStatusException 404 when the user is not found
   */
  public List<String> getUserPreferences(String userId) {
    return getUserProfile(userId).preferences();
  }

  /**
   * Returns a map of all personalization fields for the given user.
   *
   * @throws ResponseStatusException 404 when the user is not found
   */
  public Map<String, List<String>> getUserPreferencesMap(String userId) {
    UserProfile profile = getUserProfile(userId);
    return Map.of(
        "interests", profile.interests(),
        "preferences", profile.preferences(),
        "personalityTraits", profile.personalityTraits(),
        "activityBehavior", profile.activityBehavior()
    );
  }

  /**
   * Persists (or replaces) the profile for the given user and returns it.
   */
  public UserProfile saveUserProfile(String userId, UserProfile profile) {
    store.put(userId, profile);
    return profile;
  }

  /**
   * Builds a structured natural-language AI context string from the user's profile data.
   *
   * <p>Example output:
   * "User likes travel, gym, and music. Personality: outgoing and funny. Prefers serious relationship."
   *
   * @throws ResponseStatusException 404 when the user is not found
   */
  public String buildAIContext(String userId) {
    UserProfile profile = getUserProfile(userId);

    StringBuilder ctx = new StringBuilder();

    if (profile.interests() != null && !profile.interests().isEmpty()) {
      ctx.append("User likes ").append(joinNatural(profile.interests())).append(". ");
    }

    if (profile.personalityTraits() != null && !profile.personalityTraits().isEmpty()) {
      ctx.append("Personality: ").append(joinNatural(profile.personalityTraits())).append(". ");
    }

    if (profile.preferences() != null && !profile.preferences().isEmpty()) {
      ctx.append("Prefers ").append(joinNatural(profile.preferences())).append(". ");
    }

    if (profile.activityBehavior() != null && !profile.activityBehavior().isEmpty()) {
      ctx.append("Activity: ").append(joinNatural(profile.activityBehavior())).append(".");
    }

    String result = ctx.toString().trim();
    return result.isEmpty() ? "No personalization data available." : result;
  }

  // ── Helpers ─────────────────────────────────────────────────────────────────

  private static String joinNatural(List<String> items) {
    if (items.size() == 1) {
      return items.get(0);
    }
    if (items.size() == 2) {
      return items.get(0) + " and " + items.get(1);
    }
    return String.join(", ", items.subList(0, items.size() - 1))
        + ", and "
        + items.get(items.size() - 1);
  }
}
