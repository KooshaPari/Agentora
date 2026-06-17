package audit

import (
	"encoding/json"
	"strings"
	"testing"
	"time"
)

func TestFormatJSON(t *testing.T) {
	report := &AuditReport{
		Timestamp: time.Date(2024, 1, 1, 12, 0, 0, 0, time.UTC),
		Results: []AuditResult{
			{
				PackageName: "mypackage",
				Language:    "go",
				Registry:    "go_proxy",
				Version:     "1.0.0",
				Status:      "published",
				RegistryURL: "https://proxy.golang.org",
			},
		},
		Duration: time.Second,
	}

	output, err := FormatJSON(report)
	if err != nil {
		t.Fatalf("FormatJSON failed: %v", err)
	}

	// Verify it's valid JSON
	var data map[string]interface{}
	if err := json.Unmarshal([]byte(output), &data); err != nil {
		t.Fatalf("output is not valid JSON: %v", err)
	}

	// Check keys exist
	if _, ok := data["timestamp"]; !ok {
		t.Error("timestamp key missing")
	}
	if _, ok := data["results"]; !ok {
		t.Error("results key missing")
	}
	if _, ok := data["duration"]; !ok {
		t.Error("duration key missing")
	}
}

func TestFormatCSV(t *testing.T) {
	report := &AuditReport{
		Results: []AuditResult{
			{
				PackageName: "mypackage",
				Language:    "go",
				Registry:    "go_proxy",
				Version:     "1.0.0",
				Status:      "published",
				RegistryURL: "https://proxy.golang.org",
			},
		},
	}

	output, err := FormatCSV(report)
	if err != nil {
		t.Fatalf("FormatCSV failed: %v", err)
	}

	// Check that output contains expected values
	if !strings.Contains(output, "mypackage") {
		t.Error("package name not found in CSV")
	}
	if !strings.Contains(output, "go") {
		t.Error("language not found in CSV")
	}
	if !strings.Contains(output, "PACKAGE") {
		t.Error("header not found in CSV")
	}
}
