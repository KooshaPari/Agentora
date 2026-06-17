package taskrunner

import (
	"fmt"
	"os"
	"strings"

	"github.com/pelletier/go-toml/v2"
)

// RequiredTasks are the task names every mise.toml must define.
var RequiredTasks = []string{"lint", "test", "build", "format"}

// OptionalTasks are recommended but not required.
var OptionalTasks = []string{"audit", "docs:build", "release:promote", "release:status"}

// IssueSeverity indicates how serious a validation finding is.
type IssueSeverity string

const (
	SeverityError   IssueSeverity = "error"
	SeverityWarning IssueSeverity = "warning"
)

// Issue represents a single validation finding.
type Issue struct {
	Severity IssueSeverity
	Task     string
	Message  string
}

func (i Issue) String() string {
	return fmt.Sprintf("[%s] task %q: %s", i.Severity, i.Task, i.Message)
}

// rawMiseConfig is a flexible representation for parsing mise.toml task tables.
// Tasks can be either inline strings or full tables, so we decode into
// map[string]any and interpret each value manually.
type rawMiseConfig struct {
	Tasks map[string]any `toml:"tasks"`
}

// extractRun returns the "run" command from a decoded task value.
// A task value may be a plain string (shorthand) or a map with a "run" key.
func extractRun(v any) (string, bool) {
	switch val := v.(type) {
	case string:
		return val, true
	case map[string]any:
		if run, ok := val["run"].(string); ok {
			return run, true
		}
		return "", true // task table exists but no run key
	}
	return "", false
}

// ValidateMiseConfig reads the mise.toml at path, parses it, and returns any
// validation issues found. An error is returned only for I/O or parse failures;
// validation findings are returned as Issues with appropriate severities.
func ValidateMiseConfig(path string) ([]Issue, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("reading mise.toml: %w", err)
	}

	var cfg rawMiseConfig
	if err := toml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parsing mise.toml: %w", err)
	}

	var issues []Issue

	for _, required := range RequiredTasks {
		taskVal, exists := cfg.Tasks[required]
		if !exists {
			issues = append(issues, Issue{
				Severity: SeverityError,
				Task:     required,
				Message:  "required task is missing",
			})
			continue
		}
		run, ok := extractRun(taskVal)
		if !ok || strings.TrimSpace(run) == "" {
			issues = append(issues, Issue{
				Severity: SeverityError,
				Task:     required,
				Message:  "required task has no 'run' command",
			})
		}
	}

	for _, optional := range OptionalTasks {
		if _, exists := cfg.Tasks[optional]; !exists {
			issues = append(issues, Issue{
				Severity: SeverityWarning,
				Task:     optional,
				Message:  "optional task is not defined",
			})
		}
	}

	return issues, nil
}

// HasErrors reports whether any of the issues are errors (not just warnings).
func HasErrors(issues []Issue) bool {
	for _, i := range issues {
		if i.Severity == SeverityError {
			return true
		}
	}
	return false
}
