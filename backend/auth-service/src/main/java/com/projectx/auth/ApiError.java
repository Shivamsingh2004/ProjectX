package com.projectx.auth;

public record ApiError(String error, String message, int status) {}
