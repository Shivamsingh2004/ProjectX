package com.projectx.messaging.model;

public record ApiError(String error, String message, int status) {}
