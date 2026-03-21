package com.projectx.messaging.model;

import jakarta.validation.constraints.NotBlank;
import java.time.Instant;

/** Payload for typing-indicator events. */
public record TypingEvent(
    @NotBlank String conversationId,
    @NotBlank String userId,
    boolean typing,
    Instant timestamp
) {
  public TypingEvent(@NotBlank String conversationId,
      @NotBlank String userId, boolean typing) {
    this(conversationId, userId, typing, Instant.now());
  }
}
