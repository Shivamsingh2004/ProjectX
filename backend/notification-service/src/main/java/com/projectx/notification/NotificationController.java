package com.projectx.notification;

import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/notifications")
public class NotificationController {
  @GetMapping
  public List<Map<String, Object>> list() {
    return List.of(
      Map.of("id", "1", "type", "MATCH_ALERT", "message", "You have a new match!", "read", false),
      Map.of("id", "2", "type", "MESSAGE_ALERT", "message", "You received a new message", "read", false)
    );
  }
}
