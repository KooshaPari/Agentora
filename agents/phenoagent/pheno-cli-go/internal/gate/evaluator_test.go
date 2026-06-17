package gate

import (
	"context"
	"testing"

	"github.com/KooshaPari/pheno-cli/internal/adapters"
)

func TestValidateChannelTransition(t *testing.T) {
	tests := []struct {
		name    string
		from    adapters.Channel
		to      adapters.Channel
		risk    RiskProfile
		wantErr bool
	}{
		// Same channel should fail
		{
			name:    "same channel",
			from:    adapters.ChannelAlpha,
			to:      adapters.ChannelAlpha,
			risk:    RiskLow,
			wantErr: true,
		},

		// Backward transitions should fail
		{
			name:    "backward transition",
			from:    adapters.ChannelBeta,
			to:      adapters.ChannelAlpha,
			risk:    RiskLow,
			wantErr: true,
		},

		// Low risk: can skip any number of tiers
		{
			name:    "low risk alpha to prod",
			from:    adapters.ChannelAlpha,
			to:      adapters.ChannelProd,
			risk:    RiskLow,
			wantErr: false,
		},
		{
			name:    "low risk alpha to beta",
			from:    adapters.ChannelAlpha,
			to:      adapters.ChannelBeta,
			risk:    RiskLow,
			wantErr: false,
		},

		// Medium risk: max 2-tier skip, cannot skip Beta
		{
			name:    "medium risk alpha to beta",
			from:    adapters.ChannelAlpha,
			to:      adapters.ChannelBeta,
			risk:    RiskMedium,
			wantErr: false,
		},
		{
			name:    "medium risk beta to prod",
			from:    adapters.ChannelBeta,
			to:      adapters.ChannelProd,
			risk:    RiskMedium,
			wantErr: false,
		},
		{
			name:    "medium risk canary to beta",
			from:    adapters.ChannelCanary,
			to:      adapters.ChannelBeta,
			risk:    RiskMedium,
			wantErr: false,
		},
		{
			name:    "medium risk alpha to rc fails (skips beta)",
			from:    adapters.ChannelAlpha,
			to:      adapters.ChannelRC,
			risk:    RiskMedium,
			wantErr: true,
		},
		{
			name:    "medium risk alpha to prod fails (too many tiers)",
			from:    adapters.ChannelAlpha,
			to:      adapters.ChannelProd,
			risk:    RiskMedium,
			wantErr: true,
		},

		// High risk: must be sequential
		{
			name:    "high risk alpha to canary",
			from:    adapters.ChannelAlpha,
			to:      adapters.ChannelCanary,
			risk:    RiskHigh,
			wantErr: false,
		},
		{
			name:    "high risk alpha to beta fails (not sequential)",
			from:    adapters.ChannelAlpha,
			to:      adapters.ChannelBeta,
			risk:    RiskHigh,
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := ValidateChannelTransition(tt.from, tt.to, tt.risk)
			if (err != nil) != tt.wantErr {
				t.Errorf("ValidateChannelTransition() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestFilterGatesForChannel(t *testing.T) {
	tests := []struct {
		name        string
		channel     adapters.Channel
		expectedIDs []string
	}{
		{
			name:        "alpha channel",
			channel:     adapters.ChannelAlpha,
			expectedIDs: []string{"lint", "unit_tests"},
		},
		{
			name:        "canary channel",
			channel:     adapters.ChannelCanary,
			expectedIDs: []string{"lint", "unit_tests"},
		},
		{
			name:        "beta channel",
			channel:     adapters.ChannelBeta,
			expectedIDs: []string{"lint", "unit_tests", "integration_tests", "security_audit"},
		},
		{
			name:        "rc channel",
			channel:     adapters.ChannelRC,
			expectedIDs: []string{"lint", "unit_tests", "integration_tests", "security_audit", "rollback_plan"},
		},
		{
			name:        "prod channel",
			channel:     adapters.ChannelProd,
			expectedIDs: []string{"lint", "unit_tests", "integration_tests", "security_audit", "rollback_plan", "monitoring_dashboards"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gates := FilterGatesForChannel(tt.channel)

			if len(gates) != len(tt.expectedIDs) {
				t.Errorf("FilterGatesForChannel() returned %d gates, want %d", len(gates), len(tt.expectedIDs))
			}

			for i, expectedID := range tt.expectedIDs {
				if i >= len(gates) {
					t.Errorf("FilterGatesForChannel() missing gate %s", expectedID)
					continue
				}
				if gates[i].ID != expectedID {
					t.Errorf("FilterGatesForChannel() gate[%d].ID = %q, want %q", i, gates[i].ID, expectedID)
				}
			}
		})
	}
}

func TestEvaluateValidTransition(t *testing.T) {
	ctx := context.Background()

	// Try a valid low risk promotion
	report, err := Evaluate(ctx, "test-pkg", adapters.ChannelAlpha, adapters.ChannelBeta, RiskLow, "/tmp")

	if err != nil {
		t.Errorf("Evaluate() should not fail for valid low risk transition, got error: %v", err)
	}

	if report == nil {
		t.Errorf("Evaluate() should return report even on error")
	}

	if report != nil {
		if report.FromChannel != adapters.ChannelAlpha {
			t.Errorf("FromChannel mismatch: got %s, want %s", report.FromChannel, adapters.ChannelAlpha)
		}
		if report.ToChannel != adapters.ChannelBeta {
			t.Errorf("ToChannel mismatch: got %s, want %s", report.ToChannel, adapters.ChannelBeta)
		}
	}
}

func TestEvaluateInvalidTransition(t *testing.T) {
	ctx := context.Background()

	// Try to promote from beta backwards to alpha (should fail validation)
	report, err := Evaluate(ctx, "test-pkg", adapters.ChannelBeta, adapters.ChannelAlpha, RiskLow, "/tmp")

	if err == nil {
		t.Errorf("Evaluate() should fail for backward transition")
	}

	if report != nil {
		t.Errorf("Evaluate() should return nil report on validation error, got %+v", report)
	}
}

func TestEvaluateSameChannel(t *testing.T) {
	ctx := context.Background()

	// Try to promote to same channel (should fail)
	report, err := Evaluate(ctx, "test-pkg", adapters.ChannelAlpha, adapters.ChannelAlpha, RiskLow, "/tmp")

	if err == nil {
		t.Errorf("Evaluate() should fail for same channel")
	}

	if report != nil {
		t.Errorf("Evaluate() should return nil report on validation error, got %+v", report)
	}
}

func TestDefaultGates(t *testing.T) {
	gates := DefaultGates

	if len(gates) != 6 {
		t.Errorf("DefaultGates returned %d gates, want 6", len(gates))
	}

	expectedIDs := []string{"lint", "unit_tests", "integration_tests", "security_audit", "rollback_plan", "monitoring_dashboards"}
	for i, expectedID := range expectedIDs {
		if i >= len(gates) {
			t.Errorf("DefaultGates missing gate %s", expectedID)
			continue
		}
		if gates[i].ID != expectedID {
			t.Errorf("DefaultGates gate[%d].ID = %q, want %q", i, gates[i].ID, expectedID)
		}
	}

	// Check special gates have empty Command
	for _, gate := range gates {
		if gate.ID == "rollback_plan" || gate.ID == "monitoring_dashboards" {
			if gate.Command != "" {
				t.Errorf("Gate %s should have empty Command, got %q", gate.ID, gate.Command)
			}
		}
	}
}
