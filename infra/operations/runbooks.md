# ============================================================================
# Operational Runbooks, GameDay Playbooks, MTTR Tracking
# ============================================================================

# ── AI Service Degradation Runbook ──────────────────────────────────────────
## Runbook: AI Service Degradation

### Trigger
- Alert: `AIServiceSlowResponse` or `GoldenSignal_LatencySLO{job="ai-service"}`
- Fallback rate > 20% sustained for 5 minutes

### Impact
- Users receive static fallback replies instead of AI-generated suggestions
- No data loss — fallback hierarchy guarantees continued operation

### Diagnosis Steps
1. **Check AI service health**
   ```bash
   kubectl get pods -n projectx-prod -l app=ai-service
   kubectl logs -n projectx-prod -l app=ai-service --tail=50
   ```

2. **Check NVIDIA API status**
   ```bash
   curl -s https://status.api.nvidia.com/api/v2/status.json | jq '.status'
   ```

3. **Check Redis connectivity (cache layer)**
   ```bash
   kubectl exec -n projectx-prod redis-master-0 -- redis-cli ping
   kubectl exec -n projectx-prod redis-master-0 -- redis-cli info memory
   ```

4. **Check request latency distribution**
   ```promql
   histogram_quantile(0.99, sum by (le)(rate(http_server_requests_seconds_bucket{job="ai-service"}[5m])))
   ```

### Mitigation
| Severity | Action |
|----------|--------|
| P1 (total outage) | Verify L4 generic fallback is active. Scale AI pods to 0 and rely on fallback hierarchy. Page on-call. |
| P2 (degraded, >3s latency) | Check NVIDIA rate limits. Scale AI pods up via HPA override: `kubectl scale deploy ai-service -n projectx-prod --replicas=10` |
| P3 (elevated fallback rate) | Review Redis cache hit rate. Manually warm cache if needed. |

### Resolution Checklist
- [ ] Root cause identified
- [ ] Fix deployed (canary validated)
- [ ] Fallback rate returned to <5%
- [ ] Postmortem ticket created

---

## Runbook: Kafka Consumer Lag

### Trigger
- Alert: `golden:traffic:kafka_lag > 10000` sustained for 10 minutes

### Diagnosis Steps
1. **Check consumer group status**
   ```bash
   kafka-consumer-groups --bootstrap-server kafka:9092 --describe --group analytics-group
   ```

2. **Check for poison messages**
   ```bash
   kafka-console-consumer --bootstrap-server kafka:9092 \
     --topic analytics-events-dlt --from-beginning --max-messages 5
   ```

3. **Check consumer pod health**
   ```bash
   kubectl get pods -n projectx-prod -l app=analytics-service
   kubectl top pods -n projectx-prod -l app=analytics-service
   ```

### Mitigation
- Scale consumers: `kubectl scale deploy analytics-service -n projectx-prod --replicas=10`
- If DLQ has entries: investigate and replay after fix
- If broker issue: check Strimzi operator logs

---

## Runbook: Multi-Region Failover

### Trigger
- Primary region health check fails for > 30 seconds
- Alert: `HighErrorBurnRate_Critical` in primary region

### Automatic Failover (default)
1. Istio outlier detection ejects unhealthy region endpoints
2. GSLB shifts traffic to secondary region
3. Kafka MirrorMaker ensures event continuity

### Manual Failover Steps
1. **Verify secondary region health**
   ```bash
   curl -s https://api-eu-west.projectx.internal/actuator/health
   ```

2. **Update GSLB weights**
   ```bash
   kubectl apply -f infra/multi-region/failover-weights.yaml
   ```

3. **Verify traffic shift**
   ```promql
   sum by (region)(golden:traffic:rps)
   ```

4. **Notify stakeholders** (Slack #incident channel)

### Failback (after primary recovery)
- Gradually shift traffic back: 10% → 30% → 50% → 100%
- Monitor for 30 minutes at each step
- Verify data consistency across regions

---

## GameDay Scenarios

### GameDay 1: AI Service Total Outage
**Objective**: Verify fallback hierarchy handles complete AI unavailability

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Scale AI service to 0 replicas | All pods terminate |
| 2 | Send 100 AI suggestion requests | All return 200 with L3/L4 fallbacks |
| 3 | Verify no 5xx errors in gateway | Gateway health remains green |
| 4 | Check fallback_rate metric | Should be 100% |
| 5 | Scale AI service back to 3 | Normal operation resumes |

### GameDay 2: Regional Failover
**Objective**: Validate transparent failover to secondary region

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Inject network partition to us-east | Region becomes unreachable |
| 2 | Monitor GSLB traffic shift | eu-west receives 100% traffic |
| 3 | Verify user-facing latency | P99 < 800ms (slightly elevated) |
| 4 | Verify Kafka replication | No event loss in MirrorMaker |
| 5 | Restore us-east connectivity | Traffic gradually returns |

### GameDay 3: Redis Cache Failure Under Load
**Objective**: Verify system handles cache failure gracefully

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Start load test (1000 rps) | System handles normally |
| 2 | Kill Redis master pod | Cache misses spike |
| 3 | Verify AI still responds | Uses L1 (live) or L3/L4 fallbacks |
| 4 | Check idempotency filter | Gracefully degrades (passes through) |
| 5 | Redis sentinel promotes replica | Cache operations resume |

---

## MTTR Tracking Dashboard (Prometheus)

```promql
# Mean Time To Recovery (per incident type)
# Computed from alert start → alert resolved timestamps

# Current active incidents duration
time() - alerts_active_since_seconds{alertname=~".*SLO.*|.*Critical.*"}

# Historical MTTR (requires recording rule in alertmanager)
avg_over_time(incident_resolution_duration_seconds[30d])
```

### MTTR Targets
| Severity | Target MTTR | Escalation |
|----------|------------|------------|
| P1 (critical) | < 15 minutes | Immediate page → incident commander |
| P2 (major) | < 1 hour | Slack alert → on-call investigates |
| P3 (minor) | < 4 hours | Next business day |
| P4 (cosmetic) | < 1 week | Sprint backlog |
