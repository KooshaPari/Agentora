package gate

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"github.com/KooshaPari/pheno-cli/internal/adapters"
)

// RiskProfile defines the risk level for a promotion.
type RiskProfile string

const (
	RiskLow    RiskProfile = "low"
	RiskMedium RiskProfile = "medium"
	RiskHigh   RiskProfile = "high"
)

// GateResult contains the result of evaluating a single gate.
type GateResult struct {
	CriterionID   string
	CriterionName string
	Passed        bool
	Output        string
	DurationMs    int64
	Error         string
}

// PromotionReport contains the results of a complete promotion evaluation.
type PromotionReport struct {
	PackageName   string
	FromChannel   adapters.Channel
	ToChannel     adapters.Channel
	Results       []GateResult
	Passed        bool
	EvaluatedAt   time.Time
	TotalDuration int64
}

// ValidateChannelTransition validates whether a promotion is allowed based on risk profile.
func ValidateChannelTransition(from, to adapters.Channel, risk RiskProfile) error {
	fromOrdinal := adapters.ChannelOrdinal(from)
	toOrdinal := adapters.ChannelOrdinal(to)

	if fromOrdinal == -1 || toOrdinal == -1 {
		return fmt.Errorf("invalid channel")
	}

	if fromOrdinal >= toOrdinal {
		return fmt.Errorf("cannot promote to same or lower channel")
	}

	distance := toOrdinal - fromOrdinal

	switch risk {
	case RiskLow:
		// Can skip any number of tiers
		return nil
	case RiskMedium:
		// Max 2-tier jump, cannot skip beta (when coming from alpha or earlier)
		if distance > 2 {
			return fmt.Errorf("medium risk: maximum 2-tier jump allowed")
		}
		// From alpha, cannot skip to RC or prod (must go through beta)
		if from == adapters.ChannelAlpha && (to == adapters.ChannelRC || to == adapters.ChannelProd) {
			return fmt.Errorf("medium risk: cannot skip beta channel when starting from alpha")
		}
		return nil
	case RiskHigh:
		// Must be sequential (distance == 1)
		if distance != 1 {
			return fmt.Errorf("high risk: must promote sequentially (distance must be 1)")
		}
		return nil
	default:
		return fmt.Errorf("unknown risk profile: %s", risk)
	}
}

// Evaluate performs gate evaluation for a promotion.
func Evaluate(ctx context.Context, pkgName string, from, to adapters.Channel, risk RiskProfile, workDir string) (*PromotionReport, error) {
	// Validate transition first
	if err := ValidateChannelTransition(from, to, risk); err != nil {
		return nil, fmt.Errorf("channel transition validation failed: %w", err)
	}

	report := &PromotionReport{
		PackageName: pkgName,
		FromChannel: from,
		ToChannel:   to,
		EvaluatedAt: time.Now(),
		Results:     make([]GateResult, 0),
		Passed:      true,
	}

	// Filter gates for target channel
	gates := FilterGatesForChannel(to)

	totalStart := time.Now()
	defer func() {
		report.TotalDuration = time.Since(totalStart).Milliseconds()
	}()

	// Execute each gate
	for _, gate := range gates {
		result := evaluateGate(ctx, gate, workDir)
		report.Results = append(report.Results, result)

		if !result.Passed {
			report.Passed = false
		}
	}

	return report, nil
}

// evaluateGate evaluates a single gate.
func evaluateGate(ctx context.Context, gate GateCriterion, workDir string) GateResult {
	result := GateResult{
		CriterionID:   gate.ID,
		CriterionName: gate.Name,
	}

	// Special handling for certain gates
	if gate.ID == "rollback_plan" {
		result = evaluateRollbackPlan(workDir)
		result.CriterionID = gate.ID
		result.CriterionName = gate.Name
		return result
	}

	if gate.ID == "monitoring_dashboards" {
		result = evaluateMonitoringDashboards(workDir)
		result.CriterionID = gate.ID
		result.CriterionName = gate.Name
		return result
	}

	// Standard gate evaluation via shell command
	return evaluateCommandGate(ctx, gate, workDir)
}

// evaluateCommandGate executes a command gate with timeout.
func evaluateCommandGate(ctx context.Context, gate GateCriterion, workDir string) GateResult {
	result := GateResult{
		CriterionID:   gate.ID,
		CriterionName: gate.Name,
	}

	// Create context with 5-minute timeout
	evalCtx, cancel := context.WithTimeout(ctx, 5*time.Minute)
	defer cancel()

	start := time.Now()
	cmd := exec.CommandContext(evalCtx, "sh", "-c", gate.Command)
	cmd.Dir = workDir

	output, err := cmd.CombinedOutput()
	result.DurationMs = time.Since(start).Milliseconds()
	result.Output = string(output)

	if err != nil {
		result.Passed = false
		result.Error = err.Error()
	} else {
		result.Passed = true
	}

	return result
}

// evaluateRollbackPlan checks for ROLLBACK.md existence and size.
func evaluateRollbackPlan(workDir string) GateResult {
	result := GateResult{}

	start := time.Now()
	rollbackPath := filepath.Join(workDir, "ROLLBACK.md")

	info, err := os.Stat(rollbackPath)
	result.DurationMs = time.Since(start).Milliseconds()

	if err != nil {
		result.Passed = false
		result.Error = fmt.Sprintf("ROLLBACK.md not found: %v", err)
		return result
	}

	if info.Size() <= 100 {
		result.Passed = false
		result.Error = fmt.Sprintf("ROLLBACK.md too small (must be >100 bytes, got %d)", info.Size())
		return result
	}

	result.Passed = true
	result.Output = fmt.Sprintf("ROLLBACK.md found (%d bytes)", info.Size())
	return result
}

// evaluateMonitoringDashboards checks for prometheus.yml or datadog.json.
func evaluateMonitoringDashboards(workDir string) GateResult {
	result := GateResult{}

	start := time.Now()

	promPath := filepath.Join(workDir, "prometheus.yml")
	datadogPath := filepath.Join(workDir, "datadog.json")

	promExists := fileExists(promPath)
	datadogExists := fileExists(datadogPath)

	result.DurationMs = time.Since(start).Milliseconds()

	if promExists || datadogExists {
		result.Passed = true
		if promExists {
			result.Output = "prometheus.yml found"
		} else {
			result.Output = "datadog.json found"
		}
	} else {
		result.Passed = false
		result.Error = "neither prometheus.yml nor datadog.json found"
	}

	return result
}

// fileExists checks if a file exists.
func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}
