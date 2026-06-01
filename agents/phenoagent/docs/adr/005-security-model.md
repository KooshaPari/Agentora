# ADR 005: Security Model

## Status

**Accepted** - 2024-02-15

**Deciders:** Security Team, CTO, Compliance Officer, Architecture Team

## Context

Security is a foundational requirement that must be designed into the system from the beginning, not bolted on later. This decision addresses authentication, authorization, data protection, and operational security.

### Threat Model

Based on STRIDE analysis, key threats include:
- **Spoofing:** Attacker impersonates legitimate user or service
- **Tampering:** Unauthorized modification of data in transit or at rest
- **Repudiation:** Actions cannot be attributed to actors
- **Information Disclosure:** Sensitive data exposed to unauthorized parties
- **Denial of Service:** System unavailable due to resource exhaustion
- **Elevation of Privilege:** User gains unauthorized access levels

### Compliance Requirements

- SOC 2 Type II
- GDPR (EU data protection)
- CCPA (California privacy)
- Industry-specific regulations (where applicable)
- Customer security questionnaires

### Security Principles

1. **Defense in Depth:** Multiple security controls at each layer
2. **Least Privilege:** Minimum access necessary for function
3. **Zero Trust:** Verify everything, trust nothing implicitly
4. **Fail Secure:** Default to deny on errors
5. **Audit Everything:** Log security-relevant events
6. **Secure by Default:** Security features enabled automatically

## Decision

### Identity and Access Management

#### Authentication

**Primary Method:** OAuth 2.0 + OpenID Connect (OIDC)

**Implementation:**
- Identity provider: Keycloak / Auth0 / Okta (configurable)
- JWT access tokens (15-minute lifetime)
- Refresh tokens (7-day lifetime, rotating)
- PKCE for public clients
- MFA enforcement for administrative roles

**Service-to-Service:** mTLS + Service Account Tokens
- Certificates issued by internal CA
- SPIFFE/SPIRE for service identity
- Short-lived service tokens (1-hour lifetime)

#### Authorization

**Model:** RBAC (Role-Based Access Control) + ABAC (Attribute-Based Access Control)

**Implementation:**
- Policy Decision Point (PDP) using OPA (Open Policy Agent)
- Policy as Code in Rego language
- Centralized policy management
- Distributed enforcement via sidecars

**Permission Structure:**
```
Permission = Resource + Action + Conditions

Examples:
- document:read:owned
- user:admin:org:{org_id}
- billing:modify:role(finance)
```

### Data Protection

#### Encryption at Rest

- **Algorithm:** AES-256-GCM
- **Key Management:** AWS KMS / HashiCorp Vault
- **Key Rotation:** 90-day automatic rotation
- **Field-Level Encryption:** PII fields encrypted separately

#### Encryption in Transit

- **Minimum TLS:** 1.3
- **Cipher Suites:** ECDHE with AES-256-GCM, ChaCha20-Poly1305
- **Certificate Management:** Let's Encrypt with cert-manager
- **HSTS:** max-age=31536000, includeSubDomains, preload

#### Secret Management

- **Vault:** HashiCorp Vault
- **Dynamic Secrets:** Database credentials, cloud provider tokens
- **Static Secrets:** API keys rotated every 30 days
- **Injection:** Sidecar pattern, never in environment variables

### Network Security

#### Service Mesh

- **Implementation:** Istio / Linkerd
- **mTLS:** Automatic sidecar-to-sidecar encryption
- **Authorization Policies:** Service-level access control
- **Traffic Policies:** Rate limiting, circuit breaking

#### Segmentation

```
┌──────────────────────────────────────────────────────────┐
│                     DMZ (Public Ingress)                  │
│                  Load Balancer, WAF                        │
└────────────────────────┬───────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────┐
│                  Application Tier                            │
│           API Gateway, Authentication                        │
└────────────────────────┬───────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────┐
│                  Service Tier                                │
│         Microservices with mTLS mesh                        │
└────────────────────────┬───────────────────────────────────┘
                         │
┌────────────────────────▼───────────────────────────────────┐
│                  Data Tier                                   │
│         Databases, Cache, Message Queue                     │
└────────────────────────────────────────────────────────────┘
```

### Application Security

#### Input Validation

- **Whitelist Approach:** Accept only known good patterns
- **Parameterized Queries:** Prevent SQL injection
- **Output Encoding:** Context-appropriate encoding (HTML, JSON, etc.)
- **File Upload:** Type verification, size limits, malware scanning

#### Session Management

- **Stateless Sessions:** JWT-based where possible
- **Secure Cookies:** HttpOnly, Secure, SameSite=Strict
- **Session Timeout:** 30-minute idle timeout
- **Concurrent Sessions:** Limited per user (5 max)

#### Vulnerability Prevention

- **Dependency Scanning:** Snyk, Dependabot in CI/CD
- **SAST:** SonarQube, Semgrep for code analysis
- **DAST:** OWASP ZAP for runtime testing
- **Container Scanning:** Trivy, Clair for image vulnerabilities

### Operational Security

#### Audit Logging

**Events Logged:**
- Authentication attempts (success and failure)
- Authorization decisions (denied access)
- Data access (read, write, delete)
- Administrative actions (configuration changes)
- System events (startup, shutdown, errors)

**Log Format:**
```json
{
  "timestamp": "2024-02-15T10:30:00Z",
  "event_type": "authentication",
  "actor": { "type": "user", "id": "user-123" },
  "action": "login",
  "resource": { "type": "system", "id": "api-gateway" },
  "result": "success",
  "context": {
    "ip": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "mfa_used": true
  }
}
```

**Retention:** 1 year hot storage, 7 years cold storage

#### Incident Response

1. **Detection:** Automated alerts on suspicious patterns
2. **Containment:** Automated isolation capabilities
3. **Investigation:** Centralized log aggregation (SIEM)
4. **Recovery:** Documented rollback and restore procedures
5. **Post-Incident:** Mandatory review and process updates

## Consequences

### Positive Consequences

- **Strong Security Posture:** Defense in depth reduces breach likelihood
- **Compliance Ready:** Meets regulatory requirements
- **Auditability:** Complete trail of security events
- **Automation:** Security controls in CI/CD prevent vulnerabilities
- **Zero Trust:** No implicit trust reduces lateral movement risk

### Negative Consequences

- **Complexity:** Multiple security layers increase system complexity
- **Performance:** Encryption and verification add overhead
- **Operational Burden:** Certificate management, key rotation
- **Cost:** Security tooling and infrastructure investment
- **Developer Friction:** Security requirements slow initial development

### Mitigations

1. **Platform Teams:** Dedicated security platform reducing burden on feature teams
2. **Automated Tooling:** CI/CD gates catch issues early
3. **Developer Education:** Security training and guidelines
4. **Performance Budgets:** Security overhead measured and optimized
5. **Gradual Rollout:** Security features enabled incrementally

## Alternatives Considered

### Basic Authentication + API Keys

**Pros:** Simple to implement, easy to understand
**Cons:** No MFA support, credential rotation challenges, limited audit
**Status:** Rejected - insufficient for security requirements

### Custom Authentication System

**Pros:** Tailored to exact needs, no vendor dependency
**Cons:** High implementation risk, ongoing maintenance burden
**Status:** Rejected - prefer battle-tested standard solutions

### RBAC Only (No ABAC)

**Pros:** Simpler to understand and implement
**Cons:** Inflexible for complex authorization scenarios
**Status:** Partial - RBAC primary with ABAC for edge cases

### Perimeter Security Only

**Pros:** Simpler network architecture
**Cons:** Insufficient for insider threats, compromised credentials
**Status:** Rejected - defense in depth required

## Implementation Checklist

### Phase 1: Authentication (Weeks 1-4)
- [ ] Identity provider selection and configuration
- [ ] JWT infrastructure (issuance, validation, rotation)
- [ ] Login and session management UI
- [ ] MFA implementation
- [ ] Password policy enforcement

### Phase 2: Authorization (Weeks 5-8)
- [ ] OPA deployment and policy structure
- [ ] Permission model implementation
- [ ] Role definitions and assignments
- [ ] Resource-level access control
- [ ] Policy testing framework

### Phase 3: Data Protection (Weeks 9-12)
- [ ] Encryption at rest implementation
- [ ] TLS 1.3 enforcement
- [ ] Secret management with Vault
- [ ] Key rotation automation
- [ ] Field-level encryption for PII

### Phase 4: Operational Security (Weeks 13-16)
- [ ] Audit logging infrastructure
- [ ] SIEM integration
- [ ] Vulnerability scanning in CI/CD
- [ ] Incident response procedures
- [ ] Security monitoring dashboards

## Security Metrics

- Mean time to detect (MTTD) security incidents
- Mean time to respond (MTTR) to incidents
- Vulnerability scan pass rate
- Penetration test findings (critical/high/medium/low)
- Security training completion rate
- MFA adoption rate
- Certificate expiration compliance

## References

- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OAuth 2.0 Specification](https://tools.ietf.org/html/rfc6749)
- [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html)
- [Open Policy Agent Documentation](https://www.openpolicyagent.org/docs/latest/)
- [SPIFFE/SPIRE](https://spiffe.io/)
- [HashiCorp Vault](https://www.vaultproject.io/docs)
- [Istio Security](https://istio.io/latest/docs/concepts/security/)
- [AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)

## Related Decisions

- ADR 002: Technology Selection
- ADR 003: Data Storage Strategy
- ADR 004: API Design Strategy
