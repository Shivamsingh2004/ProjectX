package com.projectx.user;

import jakarta.validation.constraints.NotBlank;
import java.util.List;

public record UserProfile(
    @NotBlank String fullName,
    String bio,
    List<String> interests,
    List<String> preferences,
    List<String> personalityTraits,
    List<String> connectedPlatforms
) {
  /** Backwards-compatible constructor that omits the new optional fields. */
  public UserProfile(@NotBlank String fullName, String bio,
      List<String> preferences, List<String> connectedPlatforms) {
    // interests and personalityTraits default to empty lists when not supplied
    this(fullName, bio, List.of(), preferences, List.of(), connectedPlatforms);
  }
}
