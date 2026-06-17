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

var promoteCmd *cobra.Command

func init() {
	promoteCmd = &cobra.Command{
		Use:   "promote [channel]",
		Short: "Promote packages to a release channel with gate checks",
		Args:  cobra.ExactArgs(1),
		RunE:  runPromote,
	}
	promoteCmd.Flags().String("risk-profile", "low", "risk profile for gate evaluation (low, medium, high)")
	promoteCmd.Flags().Bool("force", false, "skip gate checks and promote anyway")
	promoteCmd.Flags().Bool("dry-run", false, "print what would be promoted without making changes")
	rootCmd.AddCommand(promoteCmd)
}

func runPromote(cmd *cobra.Command, args []string) error {
	ctx := context.Background()

	targetChannel := args[0]
	dryRun, _ := cmd.Flags().GetBool("dry-run")
	force, _ := cmd.Flags().GetBool("force")
	riskProfile, _ := cmd.Flags().GetString("risk-profile")

	// Validate target channel
	targetCh := adapters.Channel(targetChannel)
	if adapters.ChannelOrdinal(targetCh) < 0 {
		return fmt.Errorf("invalid target channel: %s", targetChannel)
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

	// Evaluate gates if not forced
	if !force && !dryRun {
		if err := evaluateGates(ctx, riskProfile); err != nil {
			return fmt.Errorf("gate evaluation failed: %w", err)
		}
	}

	if dryRun {
		fmt.Printf("Dry-run: Would promote packages to %s (risk profile: %s)\n", targetChannel, riskProfile)
		if force {
			fmt.Println("  (gates would be skipped due to --force)")
		}
		return nil
	}

	// Load config for credentials
	cfg := config.LoadConfig(viper.GetViper())
	var promotedAny bool

	// Promote all detected packages
	for _, d := range detected {
		adapter := getAdapter(d.Registry)
		if adapter == nil {
			return fmt.Errorf("no adapter available for registry: %s", d.Registry)
		}

		packages, err := adapter.Detect(repoPath)
		if err != nil {
			return fmt.Errorf("detect failed for %s: %w", d.Registry, err)
		}

		if len(packages) == 0 {
			continue
		}

		// For now, promote the first package of each detected language
		pkg := packages[0]
		creds := cfg.GetCredentials(string(d.Registry))

		result, err := publish.PublishPackage(ctx, pkg, adapter, targetCh, dryRun, creds)
		if err != nil {
			return fmt.Errorf("promote failed for %s: %w", pkg.Name, err)
		}

		fmt.Printf("Promoted: %s\n", result.RegistryURL)
		promotedAny = true
	}

	if !promotedAny {
		return fmt.Errorf("no packages promoted")
	}

	return nil
}

// evaluateGates performs gate evaluation for promotion.
// For now, it stubs the gate evaluation with a placeholder message.
// TODO: Import and use the gate package when WP06 is available.
func evaluateGates(ctx context.Context, riskProfile string) error {
	// Placeholder: Gate evaluation not yet implemented
	// In the future, this will:
	// 1. Import the gate package (once WP06 is done)
	// 2. Evaluate release gates based on the risk profile
	// 3. Return an error if gates fail
	fmt.Printf("  Gate evaluation: %s risk profile (not yet implemented)\n", riskProfile)
	return nil
}
