package com.projectx.activity;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
  @GetMapping("/api/activity/health")
  public Map<String, String> health() {
    return Map.of("service", "activity-service", "status", "ok");
  }
}
