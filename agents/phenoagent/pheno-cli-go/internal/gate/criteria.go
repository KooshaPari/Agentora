package gate

import (
	"github.com/KooshaPari/pheno-cli/internal/adapters"
)

// GateCriterion defines a single gate that must be passed for promotion.
type GateCriterion struct {
	ID           string
	Name         string
	Command      string
	RequiredFrom adapters.Channel
}

// GateSet is a collection of gates.
type GateSet []GateCriterion

// DefaultGates contains the 6 default promotion gates.
var DefaultGates = GateSet{
	{
		ID:           "lint",
		Name:         "Linting",
		Command:      "go vet ./...",
		RequiredFrom: adapters.ChannelAlpha,
	},
	{
		ID:           "unit_tests",
		Name:         "Unit Tests",
		Command:      "go test -v ./...",
		RequiredFrom: adapters.ChannelAlpha,
	},
	{
		ID:           "integration_tests",
		Name:         "Integration Tests",
		Command:      "go test -v -tags=integration ./...",
		RequiredFrom: adapters.ChannelBeta,
	},
	{
		ID:           "security_audit",
		Name:         "Security Audit",
		Command:      "go list -json -m all | nancy sleuth",
		RequiredFrom: adapters.ChannelBeta,
	},
	{
		ID:           "rollback_plan",
		Name:         "Rollback Plan",
		Command:      "",
		RequiredFrom: adapters.ChannelRC,
	},
	{
		ID:           "monitoring_dashboards",
		Name:         "Monitoring Dashboards",
		Command:      "",
		RequiredFrom: adapters.ChannelProd,
	},
}

// FilterGatesForChannel returns gates required for promotion to the specified channel.
func FilterGatesForChannel(target adapters.Channel) GateSet {
	targetOrdinal := adapters.ChannelOrdinal(target)
	result := make(GateSet, 0)

	for _, gate := range DefaultGates {
		gateOrdinal := adapters.ChannelOrdinal(gate.RequiredFrom)
		if gateOrdinal >= 0 && gateOrdinal <= targetOrdinal {
			result = append(result, gate)
		}
	}

	return result
}
