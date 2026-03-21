package com.projectx.analytics;

import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/analytics")
public class AnalyticsController {

  /** Legacy endpoint — kept for backwards compatibility. */
  @GetMapping
  public Map<String, Object> analytics() {
    return buildPerformance();
  }

  /**
   * GET /analytics/user
   * Returns per-user engagement metrics: message count, response rate,
   * match engagement, and active time.
   */
  @GetMapping("/user")
  public Map<String, Object> userAnalytics() {
    return Map.of(
        "messageCount", 142,
        "responseRate", 78.5,
        "matchEngagement", 84.2,
        "activeTimeMinutes", 210,
        "repliesReceived", 111,
        "conversationsStarted", 34
    );
  }

  /**
   * GET /analytics/performance
   * Returns platform-level performance breakdown.
   */
  @GetMapping("/performance")
  public Map<String, Object> performance() {
    return buildPerformance();
  }

  // -----------------------------------------------------------------------

  private Map<String, Object> buildPerformance() {
    return Map.of(
        "responseRate", 78.5,
        "engagementScore", 84.2,
        "platformPerformance", List.of(
            Map.of("platform", "Tinder",  "matches", 30, "responseRate", 80.0),
            Map.of("platform", "Bumble",  "matches", 22, "responseRate", 76.5),
            Map.of("platform", "Hinge",   "matches", 18, "responseRate", 79.0)
        )
    );
  }
}
