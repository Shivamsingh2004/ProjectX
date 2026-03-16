package com.projectx.notification;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
  @GetMapping("/api/notifications/health")
  public Map<String, String> health() {
    return Map.of("service", "notification-service", "status", "ok");
  }
}
