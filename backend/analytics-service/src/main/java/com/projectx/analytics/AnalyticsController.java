package com.projectx.analytics;

import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/analytics")
public class AnalyticsController {
  @GetMapping
  public Map<String, Object> analytics() {
    return Map.of(
      "responseRate", 78.5,
      "engagementScore", 84.2,
      "platformPerformance", List.of(
        Map.of("platform", "Tinder", "matches", 30),
        Map.of("platform", "Bumble", "matches", 22),
        Map.of("platform", "Hinge", "matches", 18)
      )
    );
  }
}
