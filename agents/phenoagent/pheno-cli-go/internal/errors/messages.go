// Package errors provides user-friendly error formatting for pheno-cli.
// Raw errors from adapters and internal packages are mapped to actionable
// messages before being displayed to the user.
package errors

import (
	"errors"
	"fmt"

	"github.com/KooshaPari/pheno-cli/internal/adapters"
)

// userMessage maps a sentinel error to a human-readable, actionable string.
var userMessage = map[error]string{
	adapters.ErrAuth: "Authentication failed. Check that your registry token is set " +
		"(e.g. PHENO_NPM_TOKEN) and has publish permissions.",
	adapters.ErrRateLimited: "The registry rate-limited the request. Wait a few minutes and retry.",
	adapters.ErrNetwork: "A network error occurred. Verify your internet connection and " +
		"that the registry is reachable.",
	adapters.ErrAlreadyPublished: "This version is already published on the registry. " +
		"Bump the version or use a new pre-release increment.",
	adapters.ErrPrivatePackage: "The package is marked private and cannot be published to a public registry. " +
		"Set it to public in the manifest or use a private registry.",
	adapters.ErrDirtyWorkTree: "The working tree has uncommitted changes. " +
		"Commit or stash your changes before publishing.",
	adapters.ErrNotSupported: "This operation is not yet supported for the target registry. " +
		"Check the adapter status table in README.md.",
}

// FormatError converts an internal error to a user-facing message with
// actionable guidance. The original error detail is appended for diagnostics
// when verbose mode is active, but raw stack traces are never shown.
//
// Returns a plain string suitable for printing to stderr.
func FormatError(err error) string {
	if err == nil {
		return ""
	}

	// Check sentinel errors (including wrapped ones).
	for sentinel, msg := range userMessage {
		if errors.Is(err, sentinel) {
			return fmt.Sprintf("Error: %s", msg)
		}
	}

	// Fallback: surface the error message without a stack trace.
	return fmt.Sprintf("Error: %s\n\nIf this problem persists, run with --verbose for details "+
		"or open an issue at https://github.com/KooshaPari/pheno-cli/issues.", err.Error())
}

// FormatErrorVerbose is like FormatError but also includes the underlying
// error detail for diagnostic output (used when --verbose is active).
func FormatErrorVerbose(err error) string {
	if err == nil {
		return ""
	}

	base := FormatError(err)

	// Only append detail if it adds information beyond what's in the user message.
	for sentinel := range userMessage {
		if errors.Is(err, sentinel) {
			detail := errors.Unwrap(err)
			if detail != nil {
				return fmt.Sprintf("%s\n\nDetail: %s", base, detail.Error())
			}
			return base
		}
	}

	return base
}
