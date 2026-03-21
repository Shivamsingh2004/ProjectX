package com.projectx.messaging;

import jakarta.validation.constraints.NotBlank;
import java.time.Instant;

public record MessagePayload(
    @NotBlank String conversationId,
    @NotBlank String platform,
    @NotBlank String content,
    String senderId,
    String messageId,
    Instant timestamp,
    String status    // "sent" | "delivered" | "read"
) {
  /** Backwards-compatible constructor for callers that don't supply the new fields. */
  public MessagePayload(@NotBlank String conversationId,
      @NotBlank String platform, @NotBlank String content) {
    this(conversationId, platform, content, null,
        java.util.UUID.randomUUID().toString(), Instant.now(), "sent");
  }
}
