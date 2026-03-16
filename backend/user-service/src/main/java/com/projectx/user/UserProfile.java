package com.projectx.user;

import jakarta.validation.constraints.NotBlank;
import java.util.List;

public record UserProfile(@NotBlank String fullName, String bio, List<String> preferences, List<String> connectedPlatforms) {}
