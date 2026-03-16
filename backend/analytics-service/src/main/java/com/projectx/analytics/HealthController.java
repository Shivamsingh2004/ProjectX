package com.projectx.analytics;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
  @GetMapping("/api/analytics/health")
  public Map<String, String> health() {
    return Map.of("service", "analytics-service", "status", "ok");
  }
}
