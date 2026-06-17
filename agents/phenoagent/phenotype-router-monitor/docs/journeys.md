# User Journeys

This document contains E2E user journey demonstrations for $(basename "$REPO_ROOT/$repo").

## Onboarding Journey

::: info Overview
Complete setup from installation to first agent execution.
:::

<div class="journey-steps">

### Step 1: Install CLI

<div class="gif-demo">
  <img src="./assets/gifs/onboarding-step1.gif" alt="CLI Installation">
  <p><strong>Command:</strong> <code>cargo install phenotype-agent-core</code></p>
  <p><strong>Expected:</strong> Binary installed, available in PATH</p>
</div>

### Step 2: Configure Provider

<div class="gif-demo">
  <img src="./assets/gifs/onboarding-step2.gif" alt="Provider Configuration">
  <p><strong>Command:</strong> <code>agent-core config set-provider openai</code></p>
  <p><strong>Expected:</strong> API key configured, connection tested</p>
</div>

</div>

---

*Generated automatically by docgen pipeline*
