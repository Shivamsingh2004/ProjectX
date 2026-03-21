package com.projectx.messaging.controller;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Incoming request body for the AI reply-suggestion endpoint.
 *
 * @param message the user's current conversation message (max 2000 chars to prevent abuse)
 */
public record AiReplyRequest(
    @NotBlank(message = "message must not be blank")
    @Size(max = 2000, message = "message must not exceed 2000 characters")
    String message) {}
