# =============================================================================
# Build Stage
# =============================================================================
FROM --platform=$BUILDPLATFORM docker.io/library/rust:1.77-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy manifests
COPY Cargo.toml Cargo.lock ./

# Create dummy source for dependency caching
RUN mkdir -p src && echo "fn main() {}" > src/main.rs

# Build dependencies only
RUN cargo build --release && rm -rf src

# Copy source code
COPY src/ ./src/

# Build arguments
ARG TARGETOS
ARG TARGETARCH

# Build the binary
RUN touch src/main.rs && \
    cargo build --release --target ${TARGETOS}-${TARGETARCH}

# =============================================================================
# Runtime Stage
# =============================================================================
FROM --platform=$BUILDPLATFORM docker.io/library/debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/sh -D appuser

WORKDIR /app

# Copy binary from builder
COPY --from=builder /build/target/${TARGETOS}-${TARGETARCH}/release/cmdra /app/cmdra

# Change ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Set entrypoint
ENTRYPOINT ["/app/cmdra"]
CMD ["--help"]
