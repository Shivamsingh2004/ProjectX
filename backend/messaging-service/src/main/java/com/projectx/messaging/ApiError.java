package com.projectx.messaging;

public record ApiError(String error, String message, int status) {}
