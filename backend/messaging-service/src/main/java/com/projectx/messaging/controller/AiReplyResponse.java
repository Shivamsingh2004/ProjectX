package com.projectx.messaging.controller;

import java.util.List;

public record AiReplyResponse(String tone, List<String> suggestions) {}
