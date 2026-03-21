package com.projectx.user.controller;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
  @GetMapping("/api/users/health")
  public Map<String, String> health() {
    return Map.of("service", "user-service", "status", "ok");
  }
}
