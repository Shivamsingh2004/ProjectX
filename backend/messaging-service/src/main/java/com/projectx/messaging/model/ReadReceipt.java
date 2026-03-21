package com.projectx.messaging.model;

import jakarta.validation.constraints.NotBlank;
import java.time.Instant;

/** Payload for read-receipt events. */
public record ReadReceipt(
    @NotBlank String conversationId,
    @NotBlank String messageId,
    @NotBlank String readByUserId,
    Instant readAt
) {
  public ReadReceipt(@NotBlank String conversationId,
      @NotBlank String messageId, @NotBlank String readByUserId) {
    this(conversationId, messageId, readByUserId, Instant.now());
  }
}
