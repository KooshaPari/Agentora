package cmd

import (
	"context"
	"fmt"
	"os"

	"github.com/KooshaPari/pheno-cli/internal/adapters"
	"github.com/KooshaPari/pheno-cli/internal/config"
	"github.com/KooshaPari/pheno-cli/internal/detect"
	"github.com/KooshaPari/pheno-cli/internal/publish"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var publishCmd *cobra.Command

func init() {
	publishCmd = &cobra.Command{
		Use:   "publish",
		Short: "Publish packages to their registries",
		RunE:  runPublish,
	}
	publishCmd.Flags().String("registry", "", "registry to publish to (npm, pypi, crates.io)")
	publishCmd.Flags().String("version", "", "version to publish (overrides auto-detection)")
	publishCmd.Flags().String("channel", "alpha", "release channel (alpha, canary, beta, rc, prod)")
	publishCmd.Flags().Bool("dry-run", false, "print what would be published without making changes")
	rootCmd.AddCommand(publishCmd)
}

func runPublish(cmd *cobra.Command, args []string) error {
	ctx := context.Background()

	dryRun, _ := cmd.Flags().GetBool("dry-run")
	registryFlag, _ := cmd.Flags().GetString("registry")
	channel, _ := cmd.Flags().GetString("channel")

	// Validate channel
	ch := adapters.Channel(channel)
	if adapters.ChannelOrdinal(ch) < 0 {
		return fmt.Errorf("invalid channel: %s", channel)
	}

	// Get the current working directory as the repo path
	repoPath, err := os.Getwd()
	if err != nil {
		return err
	}

	// Detect languages
	detected := detect.DetectLanguages(repoPath)
	if len(detected) == 0 {
		return fmt.Errorf("no publishable packages detected in %s", repoPath)
	}

	// Load config for credentials
	cfg := config.LoadConfig(viper.GetViper())
	var publishedAny bool

	// If registry flag is set, publish only that registry; otherwise publish all detected
	for _, d := range detected {
		if registryFlag != "" && registryFlag != string(d.Registry) {
			continue
		}

		adapter := getAdapter(d.Registry)
		if adapter == nil {
			if dryRun {
				fmt.Printf("Warning: No adapter available for %s\n", d.Registry)
				continue
			}
			return fmt.Errorf("no adapter available for registry: %s", d.Registry)
		}

		packages, err := adapter.Detect(repoPath)
		if err != nil {
			return fmt.Errorf("detect failed for %s: %w", d.Registry, err)
		}

		if len(packages) == 0 {
			continue
		}

		// For now, publish the first package of each detected language
		pkg := packages[0]
		creds := cfg.GetCredentials(string(d.Registry))

		result, err := publish.PublishPackage(ctx, pkg, adapter, ch, dryRun, creds)
		if err != nil {
			return fmt.Errorf("publish failed for %s: %w", pkg.Name, err)
		}

		fmt.Printf("Published: %s\n", result.RegistryURL)
		publishedAny = true
	}

	if !publishedAny {
		return fmt.Errorf("no packages published")
	}

	return nil
}

// getAdapter returns a RegistryAdapter for the given registry.
func getAdapter(reg adapters.Registry) adapters.RegistryAdapter {
	switch reg {
	case adapters.RegistryNPM:
		return &adapters.NpmAdapter{}
	default:
		return nil
	}
}
