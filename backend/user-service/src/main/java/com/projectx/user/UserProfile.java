package com.projectx.user;

import jakarta.validation.constraints.NotBlank;
import java.util.List;

/**
 * Extended user profile that combines identity, personalization, and AI-context data.
 *
 * @param fullName           display name (required)
 * @param bio                free-text bio
 * @param interests          list of interests/hobbies used to build AI context
 * @param preferences        dating preferences (e.g. "casual", "serious relationship")
 * @param personalityTraits  personality descriptors (e.g. "outgoing", "funny")
 * @param activityBehavior   activity patterns (e.g. "active in evenings", "gym 3x/week")
 * @param connectedPlatforms linked dating-platform identifiers
 */
public record UserProfile(
    @NotBlank String fullName,
    String bio,
    List<String> interests,
    List<String> preferences,
    List<String> personalityTraits,
    List<String> activityBehavior,
    List<String> connectedPlatforms) {}

