package errors_test

import (
	"fmt"
	"strings"
	"testing"

	"github.com/KooshaPari/pheno-cli/internal/adapters"
	phenoerrors "github.com/KooshaPari/pheno-cli/internal/errors"
)

func TestFormatError_NilReturnsEmpty(t *testing.T) {
	if got := phenoerrors.FormatError(nil); got != "" {
		t.Errorf("expected empty string for nil error, got %q", got)
	}
}

func TestFormatError_SentinelErrors(t *testing.T) {
	cases := []struct {
		err      error
		contains string
	}{
		{adapters.ErrAuth, "Authentication failed"},
		{adapters.ErrRateLimited, "rate-limited"},
		{adapters.ErrNetwork, "network error"},
		{adapters.ErrAlreadyPublished, "already published"},
		{adapters.ErrPrivatePackage, "private"},
		{adapters.ErrDirtyWorkTree, "uncommitted changes"},
		{adapters.ErrNotSupported, "not yet supported"},
	}

	for _, tc := range cases {
		t.Run(tc.err.Error(), func(t *testing.T) {
			got := phenoerrors.FormatError(tc.err)
			if !strings.Contains(got, tc.contains) {
				t.Errorf("FormatError(%v) = %q, want substring %q", tc.err, got, tc.contains)
			}
			if strings.Contains(got, "goroutine") || strings.Contains(got, ".go:") {
				t.Errorf("FormatError should not contain stack trace, got: %q", got)
			}
		})
	}
}

func TestFormatError_WrappedSentinel(t *testing.T) {
	wrapped := fmt.Errorf("npm publish failed: %w", adapters.ErrAuth)
	got := phenoerrors.FormatError(wrapped)
	if !strings.Contains(got, "Authentication failed") {
		t.Errorf("FormatError with wrapped sentinel should surface user message, got: %q", got)
	}
}

func TestFormatError_UnknownError(t *testing.T) {
	unknown := fmt.Errorf("something unexpected happened")
	got := phenoerrors.FormatError(unknown)
	if !strings.Contains(got, "something unexpected happened") {
		t.Errorf("FormatError should include original message for unknown errors, got: %q", got)
	}
	if strings.Contains(got, "goroutine") {
		t.Errorf("FormatError should not include stack trace, got: %q", got)
	}
}

func TestFormatErrorVerbose_NilReturnsEmpty(t *testing.T) {
	if got := phenoerrors.FormatErrorVerbose(nil); got != "" {
		t.Errorf("expected empty string for nil error, got %q", got)
	}
}

func TestFormatErrorVerbose_WrappedSentinelIncludesDetail(t *testing.T) {
	inner := fmt.Errorf("403 Forbidden")
	wrapped := fmt.Errorf("registry rejected request: %w: %w", adapters.ErrAuth, inner)
	got := phenoerrors.FormatErrorVerbose(wrapped)
	if !strings.Contains(got, "Authentication failed") {
		t.Errorf("verbose format should contain user message, got: %q", got)
	}
}

func TestFormatErrorVerbose_PlainSentinel(t *testing.T) {
	got := phenoerrors.FormatErrorVerbose(adapters.ErrRateLimited)
	if !strings.Contains(got, "rate-limited") {
		t.Errorf("verbose format should contain user message, got: %q", got)
	}
}
