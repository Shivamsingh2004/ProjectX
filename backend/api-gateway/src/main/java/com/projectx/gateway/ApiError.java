package com.projectx.gateway;

public record ApiError(String error, String message, int status) {}
