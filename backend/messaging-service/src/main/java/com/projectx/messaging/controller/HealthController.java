package com.projectx.messaging.controller;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
  @GetMapping("/api/messages/health")
  public Map<String, String> health() {
    return Map.of("service", "messaging-service", "status", "ok");
  }
}
