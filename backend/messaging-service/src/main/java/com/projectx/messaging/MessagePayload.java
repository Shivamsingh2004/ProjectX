package com.projectx.messaging;

import jakarta.validation.constraints.NotBlank;

public record MessagePayload(@NotBlank String conversationId, @NotBlank String platform, @NotBlank String content) {}
