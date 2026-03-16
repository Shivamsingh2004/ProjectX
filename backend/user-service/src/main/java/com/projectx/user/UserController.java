package com.projectx.user;

import jakarta.validation.Valid;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/users")
public class UserController {
  private final AtomicReference<UserProfile> profile = new AtomicReference<>(new UserProfile("New User", "", List.of("serious relationship"), List.of()));

  @GetMapping("/profile")
  public UserProfile getProfile() {
    return profile.get();
  }

  @PutMapping("/profile")
  public UserProfile updateProfile(@Valid @RequestBody UserProfile update) {
    profile.set(update);
    return update;
  }
}
