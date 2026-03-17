package com.projectx.messaging;

import jakarta.validation.Valid;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/messages")
public class MessagingController {

  private final SimpMessagingTemplate template;

  /** In-memory message store. A real service would use a database. */
  private final List<MessagePayload> messageStore = new CopyOnWriteArrayList<>();

  public MessagingController(SimpMessagingTemplate template) {
    this.template = template;
  }

  @GetMapping("/conversations")
  public List<Map<String, String>> conversations() {
    return List.of(
        Map.of("id", "conv-1", "name", "Alex",   "platform", "Tinder"),
        Map.of("id", "conv-2", "name", "Riley",  "platform", "Bumble"),
        Map.of("id", "conv-3", "name", "Jordan", "platform", "Hinge")
    );
  }

  /** REST endpoint: send a message and broadcast via WebSocket. */
  @PostMapping("/send")
  public MessagePayload send(@Valid @RequestBody MessagePayload payload) {
    MessagePayload stored = new MessagePayload(
        payload.conversationId(),
        payload.platform(),
        payload.content(),
        payload.senderId(),
        payload.messageId() != null ? payload.messageId() : UUID.randomUUID().toString(),
        payload.timestamp() != null ? payload.timestamp() : Instant.now(),
        "sent"
    );
    messageStore.add(stored);
    template.convertAndSend("/topic/messages/" + stored.conversationId(), stored);
    return stored;
  }

  /** REST endpoint: retrieve stored messages for a conversation. */
  @GetMapping("/history")
  public List<MessagePayload> history(@RequestParam String conversationId) {
    return messageStore.stream()
        .filter(m -> m.conversationId().equals(conversationId))
        .toList();
  }

  // ------------------------------------------------------------------
  // WebSocket message handlers (STOMP)
  // ------------------------------------------------------------------

  /** STOMP handler: client sends to /app/chat.message */
  @MessageMapping("/chat.message")
  public void handleMessage(@Payload MessagePayload payload) {
    MessagePayload stored = new MessagePayload(
        payload.conversationId(),
        payload.platform(),
        payload.content(),
        payload.senderId(),
        payload.messageId() != null ? payload.messageId() : UUID.randomUUID().toString(),
        Instant.now(),
        "delivered"
    );
    messageStore.add(stored);
    template.convertAndSend("/topic/messages/" + stored.conversationId(), stored);
  }

  /** STOMP handler: client sends to /app/chat.typing */
  @MessageMapping("/chat.typing")
  public void handleTyping(@Payload TypingEvent event) {
    TypingEvent stamped = new TypingEvent(
        event.conversationId(), event.userId(), event.typing());
    template.convertAndSend("/topic/typing/" + stamped.conversationId(), stamped);
  }

  /** STOMP handler: client sends to /app/chat.read */
  @MessageMapping("/chat.read")
  public void handleReadReceipt(@Payload ReadReceipt receipt) {
    ReadReceipt stamped = new ReadReceipt(
        receipt.conversationId(), receipt.messageId(), receipt.readByUserId());
    template.convertAndSend("/topic/read/" + stamped.conversationId(), stamped);
  }
}
