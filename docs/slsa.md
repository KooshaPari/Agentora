# SLSA Build Attestation

This document describes the repository's configured path for generating build
provenance in accordance with [SLSA (Supply-chain Levels for Software
Artifacts)][slsa] Build specifications. No published release artifact or
attestation has been verified for this repository yet, so this document does
not claim an achieved SLSA level.

## Target Level

**Current target: SLSA Build L2 (configuration present; execution evidence pending)**

The release workflow is configured to use GitHub Actions and
[`slsa-framework/slsa-github-generator`][slsa-gh-gen]'s
`attest-build-provenance` action. A successful release run and independent
attestation verification are required before asserting provenance generation,
artifact distribution, signing, or any SLSA level.

| Requirement                                | Status           |
| ------------------------------------------ | ---------------- |
| Provenance generation configured           | Evidence pending |
| Artifact provenance distribution           | Evidence pending |
| Build-platform isolation                   | Evidence pending |
| OIDC provenance authenticity               | Evidence pending |
| Build-platform isolation from request      | Future target    |
| Hardened build platform                    | Future target    |
| Non-forgeable provenance (sigstore/cosign) | Future target    |

## Workflow

The CI workflow lives at
[`.github/workflows/release-attestation.yml`](../.github/workflows/release-attestation.yml)
and is triggered:

- Automatically on every `release: published` event.
- Manually via `workflow_dispatch` for ad-hoc provenance generation.

### Build Steps

1. **Checkout** — full history (`fetch-depth: 0`) so the git revision
   can be embedded in provenance.
2. **Toolchain** — pinned `stable` Rust via
   [`dtolnay/rust-toolchain`][rust-toolchain].
3. **Cache** — cargo registry, git index, and `target/` via
   [`Swatinem/rust-cache`][rust-cache].
4. **Build** — `cargo build --release --locked --workspace --all-targets`.
5. **Stage** — collect built executables, source tarball, and a build
   manifest into `release-artifacts/`.
6. **Upload** — publish `release-artifacts` as a GitHub Actions artifact
   (90 day retention).
7. **Attest** — generate SLSA Build L2 provenance with
   `slsa-framework/slsa-github-generator/attest-build-provenance@v1`.

## Verification

After a release attestation has been generated, consumers can verify the
artifact using the [GitHub CLI][gh-cli]:

```bash
gh attestation verify <artifact> --owner <org>
```

Or with [`cosign`][cosign]:

```bash
cosign verify-attestation \
  --certificate-identity-regexp 'https://github.com/slsa-framework/slsa-github-generator' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  <artifact>
```

When generated, the in-toto provenance attestation
(`slsa-github-generator/actions/attest-build-provenance`) is expected to
contain:

- `builder.id` — `https://github.com/actions/runner`
- `invocation.config.source.uri` — repository URL
- `invocation.config.source.entryPoint` — build workflow path
- `invocation.config.source.digest.sha1` — git commit SHA
- `invocation.config.source.ref` — git ref (tag / branch)
- `metadata.buildInvocationID` — workflow run ID
- `metadata.completeness.parameters` — whether all inputs are hashed
- `metadata.completeness.environment` — whether environment is fully captured

## Path to SLSA Build L3

The configured workflow does not establish an achieved level. After a
successful and independently verified L2 release, the following additions
would be required to pursue L3:

1. **Isolated build environment** — move from a hosted runner to
   ephemeral, single-tenant builders (e.g.
   `slsa-framework/slsa-github-generator`'s `generator_containerized_slsa3.yml`
   reusable workflow, or a self-hosted runner with a hardened image).
2. **Provenance non-forgeability** — the generator workflow re-signs
   provenance with a build-platform-held signing key (sigstore / KMS)
   rather than relying on the GitHub OIDC token alone.
3. **Provenance transparency log** — the generator publishes
   provenance to a transparency log (e.g. Rekor) so forgery is
   detectable by the wider community.

To upgrade, switch the `attest-build-provenance` step to invoke the
`slsa-framework/slsa-github-generator/.github/workflows/generator_containerized_slsa3.yml@v2`
reusable workflow with a build image pinned by digest. The reusable
workflow handles ephemeral runners, hardened isolation, and
non-forgeable provenance signing transparently.

## References

- [SLSA Framework][slsa]
- [`slsa-framework/slsa-github-generator`][slsa-gh-gen]
- [GitHub Artifact Attestations][ghaa]
- [GitHub Actions security hardening][ghas]
- [`dtolnay/rust-toolchain`][rust-toolchain]
- [`Swatinem/rust-cache`][rust-cache]
- [`cosign`][cosign]

[slsa]: https://slsa.dev
[slsa-gh-gen]: https://github.com/slsa-framework/slsa-github-generator
[ghaa]: https://docs.github.com/en/security/supply-chain-security/artifact-attestations
[ghas]: https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions
[gh-cli]: https://cli.github.com
[cosign]: https://github.com/sigstore/cosign
[rust-toolchain]: https://github.com/dtolnay/rust-toolchain
[rust-cache]: https://github.com/Swatinem/rust-cache
