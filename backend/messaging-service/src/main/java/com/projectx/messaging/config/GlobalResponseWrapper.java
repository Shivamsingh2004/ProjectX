package com.projectx.messaging.config;

import org.springframework.core.MethodParameter;
import org.springframework.http.MediaType;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.mvc.method.annotation.ResponseBodyAdvice;
import java.util.Map;
import java.util.HashMap;

@RestControllerAdvice
public class GlobalResponseWrapper implements ResponseBodyAdvice<Object> {
    @Override
    public boolean supports(MethodParameter returnType, Class<? extends HttpMessageConverter<?>> converterType) {
        String name = returnType.getDeclaringClass().getName();
        return !name.contains("springdoc") && !name.contains("swagger") && !name.contains("openapi") && !name.contains("ExceptionHandler");
    }

    @Override
    public Object beforeBodyWrite(Object body, MethodParameter returnType, MediaType selectedContentType,
                                  Class<? extends HttpMessageConverter<?>> selectedConverterType,
                                  ServerHttpRequest request, ServerHttpResponse response) {
        if (body instanceof Map && ((Map<?, ?>) body).containsKey("success")) {
            return body;
        }
        if (body instanceof String) {
            return body;
        }
        Map<String, Object> wrapper = new HashMap<>();
        wrapper.put("success", true);
        wrapper.put("data", body != null ? body : new HashMap<>());
        wrapper.put("error", null);
        wrapper.put("meta", new HashMap<>());
        return wrapper;
    }
}
