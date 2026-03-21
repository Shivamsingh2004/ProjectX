# ============================================================================
# OPA (Open Policy Agent) Policies for Zero-Trust Authorization
#
# These Rego policies are deployed as an Istio External Authorizer.
# Every request hitting the mesh is evaluated against these rules BEFORE
# reaching any service.
# ============================================================================
package projectx.authz

import future.keywords.if
import future.keywords.in

default allow := false

# ── Public endpoints (no auth required) ─────────────────────────────────────
allow if {
    input.parsed_path[0] == "api"
    input.parsed_path[1] == "auth"
}

allow if {
    input.parsed_path[0] == "actuator"
    input.parsed_path[1] == "health"
}

# ── Authenticated endpoints ─────────────────────────────────────────────────
allow if {
    valid_token
    is_active_user
}

# ── Admin-only endpoints ────────────────────────────────────────────────────
allow if {
    valid_token
    is_admin
    admin_paths
}

# ── Token Validation ────────────────────────────────────────────────────────
valid_token if {
    input.parsed_headers.authorization
    startswith(input.parsed_headers.authorization, "Bearer ")
    token := trim_prefix(input.parsed_headers.authorization, "Bearer ")
    # In production, decode JWT and validate claims here
    token != ""
}

is_active_user if {
    # Verify the user's account status claim
    claims := input.parsed_token
    claims.sub != ""
    claims.aud == "authenticated"
}

is_admin if {
    claims := input.parsed_token
    claims.role == "admin"
}

admin_paths if {
    input.parsed_path[0] == "api"
    input.parsed_path[1] in {"admin", "internal"}
}

# ── Rate Limit Enforcement by Role ──────────────────────────────────────────
rate_limit_tier := "premium" if {
    claims := input.parsed_token
    claims.subscription == "premium"
} else := "free"

max_requests_per_minute := 100 if {
    rate_limit_tier == "premium"
} else := 10

# ── Data Access Policies (Row-Level Security) ──────────────────────────────
allow_data_access if {
    # Users can only access their own data
    input.parsed_path[0] == "api"
    input.parsed_path[1] == "users"
    input.parsed_path[2] == input.parsed_token.sub
}

allow_data_access if {
    # Admins can access any user's data
    is_admin
}

# ── Audit Decision ──────────────────────────────────────────────────────────
decision := {
    "allow": allow,
    "rate_limit_tier": rate_limit_tier,
    "user_id": input.parsed_token.sub,
    "path": input.parsed_path,
    "method": input.method,
    "timestamp": time.now_ns(),
}
