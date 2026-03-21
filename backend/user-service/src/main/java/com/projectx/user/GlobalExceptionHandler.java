package com.projectx.user;

import jakarta.validation.ConstraintViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;

@RestControllerAdvice
public class GlobalExceptionHandler {
  @ExceptionHandler(MethodArgumentNotValidException.class)
  public ResponseEntity<ApiError> handleValidation(MethodArgumentNotValidException ex) {
    return ResponseEntity.badRequest().body(new ApiError("INVALID_REQUEST", "Validation failed", 400));
  }

  @ExceptionHandler(ConstraintViolationException.class)
  public ResponseEntity<ApiError> handleConstraint(ConstraintViolationException ex) {
    return ResponseEntity.badRequest().body(new ApiError("INVALID_REQUEST", ex.getMessage(), 400));
  }

  @ExceptionHandler(ResponseStatusException.class)
  public ResponseEntity<ApiError> handleStatus(ResponseStatusException ex) {
    int status = ex.getStatusCode().value();
    return ResponseEntity.status(status).body(new ApiError("REQUEST_FAILED", ex.getReason(), status));
  }

  @ExceptionHandler(AuthenticationException.class)
  public ResponseEntity<ApiError> handleAuthentication(AuthenticationException ex) {
    return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
        .body(new ApiError("UNAUTHORIZED", "Invalid or missing token", 401));
  }

  @ExceptionHandler(AccessDeniedException.class)
  public ResponseEntity<ApiError> handleAccessDenied(AccessDeniedException ex) {
    return ResponseEntity.status(HttpStatus.FORBIDDEN)
        .body(new ApiError("FORBIDDEN", "Access denied", 403));
  }

  @ExceptionHandler(Exception.class)
  public ResponseEntity<ApiError> handleGeneral(Exception ex) {
    return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
      .body(new ApiError("INTERNAL_SERVER_ERROR", "Unexpected server error", 500));
  }
}
