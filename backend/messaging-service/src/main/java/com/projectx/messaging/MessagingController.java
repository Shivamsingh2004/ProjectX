package com.projectx.messaging;

import jakarta.validation.Valid;
import java.util.List;
import java.util.Map;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/messages")
public class MessagingController {
  private final SimpMessagingTemplate template;

  public MessagingController(SimpMessagingTemplate template) {
    this.template = template;
  }

  @GetMapping("/conversations")
  public List<Map<String, String>> conversations() {
    return List.of(Map.of("id", "conv-1", "name", "Alex", "platform", "Tinder"));
  }

  @PostMapping("/send")
  public Map<String, String> send(@Valid @RequestBody MessagePayload payload) {
    template.convertAndSend("/topic/messages/" + payload.conversationId(), payload);
    return Map.of("status", "sent");
  }
}
