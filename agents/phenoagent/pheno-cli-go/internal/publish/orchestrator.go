package publish

import (
	"context"
	"fmt"

	"github.com/KooshaPari/pheno-cli/internal/adapters"
)

// PublishPackage orchestrates the publication of a package through a registry adapter.
// It performs: Build -> Publish -> Verify, and supports dry-run mode.
func PublishPackage(ctx context.Context, pkg adapters.Package, adapter adapters.RegistryAdapter, channel adapters.Channel, dryRun bool, creds map[string]string) (*adapters.PublishResult, error) {
	// Build the package artifact
	_, err := adapter.Build(pkg)
	if err != nil {
		return nil, fmt.Errorf("build failed: %w", err)
	}

	// Calculate the pre-release version string for the target channel
	version, err := adapter.Version(pkg.Version, channel, 0)
	if err != nil {
		return nil, fmt.Errorf("version calculation failed: %w", err)
	}

	if dryRun {
		// In dry-run mode, just return what would have been published
		return &adapters.PublishResult{
			RegistryURL: fmt.Sprintf("dry-run: would publish %s v%s to %s", pkg.Name, version, channel),
			Version:     version,
		}, nil
	}

	// Publish the package
	result, err := adapter.Publish(pkg, version, creds)
	if err != nil {
		return nil, fmt.Errorf("publish failed: %w", err)
	}

	// Verify the package is available on the registry
	verified, err := adapter.Verify(pkg, version)
	if err != nil {
		return nil, fmt.Errorf("verification failed: %w", err)
	}
	if !verified {
		return nil, fmt.Errorf("verification failed: package not found on registry")
	}

	return result, nil
}
