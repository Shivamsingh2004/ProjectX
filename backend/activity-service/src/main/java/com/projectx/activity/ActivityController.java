package com.projectx.activity;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/activity")
public class ActivityController {
  @GetMapping
  public Map<String, Object> activity() {
    return Map.of("newLikes", 12, "newMatches", 5, "unreadMessages", 9);
  }
}
