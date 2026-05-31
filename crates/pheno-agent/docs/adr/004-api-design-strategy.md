# ADR 004: API Design Strategy

## Status

**Accepted** - 2024-02-10

**Deciders:** API Design Committee, Backend Team Leads, Frontend Representatives

## Context

APIs are the primary interface between system components and external consumers. Well-designed APIs enable rapid development, system integration, and future evolution.

### Problem Statement

We need to establish:
- API architectural style and conventions
- Versioning strategy for evolution
- Authentication and authorization patterns
- Documentation and discovery mechanisms
- Rate limiting and throttling approaches

### Stakeholder Requirements

| Stakeholder | Need | Constraint |
|-------------|------|------------|
| Frontend Teams | Type-safe, predictable APIs | Low latency for user experience |
| Mobile Teams | Efficient payloads, offline support | Bandwidth optimization |
| Integration Partners | Stable contracts, clear documentation | Backward compatibility |
| Internal Services | High-performance inter-service calls | Service mesh integration |
| Third-party Developers | Self-service onboarding | Sandboxed access |

### Current Challenges

- Inconsistent endpoint naming across services
- Lack of standard error response format
- Documentation drift from implementation
- Breaking changes without proper versioning
- Insufficient rate limiting causing incidents

## Decision

### Multi-Protocol API Strategy

We will support different API protocols optimized for different use cases.

#### 1. External Public APIs: GraphQL

**Rationale:**
- Clients request exactly what they need
- Single endpoint reduces complexity
- Strong typing with schema
- Excellent developer experience
- Built-in introspection and documentation

**Implementation:**
- Schema-first development with code generation
- Query complexity analysis and depth limiting
- persisted queries for production
- Subscriptions for real-time updates
- Apollo Federation for microservices composition

**Example:**
```graphql
type Query {
  user(id: ID!): User
  searchUsers(filters: UserFilters!, pagination: PaginationInput): UserConnection
}

type User {
  id: ID!
  email: String!
  profile: UserProfile
  organizations: [Organization!]!
}
```

#### 2. Internal Service APIs: gRPC

**Rationale:**
- Binary protocol efficiency
- Strongly typed contracts via Protocol Buffers
- Bi-directional streaming support
- Code generation for multiple languages
- Native HTTP/2 support

**Implementation:**
- Proto files as source of truth
- Buf for linting and breaking change detection
- Interceptors for auth, logging, metrics
- Health checking standardization
- Reflection for development tools

**Example:**
```protobuf
service UserService {
  rpc GetUser(GetUserRequest) returns (User);
  rpc ListUsers(ListUsersRequest) returns (stream User);
  rpc StreamUpdates(StreamUpdatesRequest) returns (stream UserUpdate);
}

message User {
  string id = 1;
  string email = 2;
  UserProfile profile = 3;
}
```

#### 3. Webhook and Event APIs: CloudEvents

**Rationale:**
- Industry standard for event description
- Vendor-neutral specification
- Clear metadata and payload separation
- Excellent tooling support

**Implementation:**
- CloudEvents 1.0 specification compliance
- HTTP binding for webhooks
- Idempotency keys for at-least-once delivery
- Signature verification for security
- Retry with exponential backoff

#### 4. Legacy/Integration: REST (OpenAPI)

**Rationale:**
- Universal compatibility
- Excellent tooling ecosystem
- Human-readable for debugging
- Industry standard for integrations

**Implementation:**
- OpenAPI 3.1 specification
- Resource-oriented URL design
- HTTP method semantics (GET, POST, PUT, PATCH, DELETE)
- Consistent error format (RFC 7807 Problem Details)
- JSON:API or simple JSON conventions

### API Design Principles

1. **Contract First:** Design APIs before implementation
2. **Version Explicitly:** URLs (/v1/, /v2/) or headers for versioning
3. **Fail Clearly:** Standard error format with actionable messages
4. **Document Completely:** OpenAPI/GraphQL schemas always current
5. **Secure by Default:** Authentication required unless explicitly public
6. **Monitor Religiously:** Latency, errors, rate limits, usage patterns

### API Governance

#### Schema Registry

- Central repository for all API schemas
- Breaking change detection in CI/CD
- Version history and diff visualization
- Usage analytics per endpoint

#### Linting Standards

- Spectral rules for OpenAPI
- GraphQL schema linting
- Protobuf linting with buf
- Naming conventions enforcement

#### Documentation Standards

- Interactive documentation (Swagger UI, GraphiQL)
- Code examples in multiple languages
- Changelog per API version
- Deprecation notices with timelines

## Consequences

### Positive Consequences

- **Developer Experience:** Typed APIs with excellent documentation
- **Performance:** Efficient protocols matched to use cases
- **Flexibility:** GraphQL reduces over/under-fetching
- **Integration:** Standard protocols ease third-party integration
- **Evolution:** Clear versioning and deprecation strategies

### Negative Consequences

- **Complexity:** Multiple protocols to maintain and understand
- **Tooling:** Different tools needed for each protocol
- **Debugging:** Binary protocols harder to debug than HTTP/JSON
- **Caching:** GraphQL requires different caching strategies
- **Learning Curve:** Team must understand multiple API paradigms

### Mitigation Strategies

1. **Gateway Pattern:** Unified entry point handling cross-cutting concerns
2. **Client Generation:** Automated SDK generation from schemas
3. **Developer Portal:** Centralized documentation and exploration
4. **Playground Environments:** Safe testing spaces for each protocol
5. **Training:** Regular workshops on API design and usage

## Alternatives Considered

### REST Only (OpenAPI)

**Pros:** Simplicity, universal understanding, excellent caching
**Cons:** Over/under-fetching, multiple round-trips, versioning challenges
**Status:** Used for public REST endpoints but not exclusive strategy

### GraphQL for Everything

**Pros:** Unified API, flexible queries, strong typing
**Cons:** Complexity for simple use cases, caching challenges, N+1 query risks
**Status:** Adopted for external APIs but not internal services

### tRPC or Similar

**Pros:** End-to-end type safety, excellent DX, no schema maintenance
**Cons:** TypeScript-only ecosystem, less language diversity
**Status:** Evaluated for internal TypeScript services, not primary choice

### SOAP/XML

**Pros:** Enterprise standard, formal contracts, WS-* standards
**Cons:** Verbose, complex, poor developer experience
**Status:** Explicitly rejected - legacy technology

## Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)
- [ ] Schema registry setup
- [ ] API gateway deployment
- [ ] Authentication middleware
- [ ] Basic monitoring and rate limiting

### Phase 2: Public APIs (Weeks 5-8)
- [ ] GraphQL schema design
- [ ] Code generation pipeline
- [ ] Developer portal launch
- [ ] Beta with internal consumers

### Phase 3: Internal Services (Weeks 9-12)
- [ ] gRPC adoption for new services
- [ ] Proto repository and CI integration
- [ ] Service mesh integration
- [ ] Migration of existing REST internal APIs

### Phase 4: Events and Webhooks (Weeks 13-16)
- [ ] CloudEvents adoption
- [ ] Webhook infrastructure
- [ ] Event catalog publication
- [ ] Partner integration support

## References

- [GraphQL Specification](https://spec.graphql.org/)
- [gRPC Documentation](https://grpc.io/docs/)
- [CloudEvents Specification](https://cloudevents.io/)
- [OpenAPI Specification](https://spec.openapis.org/oas/v3.1.0)
- [JSON:API Specification](https://jsonapi.org/)
- [RFC 7807: Problem Details](https://tools.ietf.org/html/rfc7807)
- [API Design Patterns by JJ Geewax](https://www.oreilly.com/library/view/api-design-patterns/9781617295850/)
- [The Design of Web APIs by Arnaud Lauret](https://www.manning.com/books/the-design-of-web-apis)

## Monitoring Checklist

- [ ] Request rate per endpoint
- [ ] Latency percentiles (p50, p95, p99)
- [ ] Error rate and error budget tracking
- [ ] Payload size distribution
- [ ] Authentication failure rates
- [ ] Rate limit hit rates
- [ ] Schema usage analytics
- [ ] Client version distribution

## Security Considerations

- [ ] OAuth 2.0 / OIDC for authentication
- [ ] Scope-based authorization
- [ ] Input validation and sanitization
- [ ] Rate limiting per client
- [ ] API key rotation policies
- [ ] Audit logging for sensitive operations
- [ ] CORS policy enforcement
- [ ] TLS 1.3 minimum
