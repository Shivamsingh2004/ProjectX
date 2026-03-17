package com.projectx.messaging.controller;

/**
 * Structured response returned to the frontend after AI suggestion is generated.
 *
 * @param suggestion the AI-generated reply suggestion
 * @param score      confidence score from the AI service (0.0–1.0)
 */
public record AiReplyResponse(String suggestion, double score) {}
