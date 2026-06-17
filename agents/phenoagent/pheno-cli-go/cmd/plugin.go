package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
	"github.com/KooshaPari/pheno-cli/internal/plugin"
)

func init() {
	pluginCmd := &cobra.Command{
		Use:   "plugin",
		Short: "Manage pheno plugins",
	}
	pluginListCmd := &cobra.Command{
		Use:   "list",
		Short: "List installed plugins",
		RunE: func(cmd *cobra.Command, args []string) error {
			plugins := plugin.Global().List()
			if len(plugins) == 0 {
				fmt.Println("No plugins installed")
				return nil
			}
			fmt.Println("Installed plugins:")
			for _, p := range plugins {
				m := p.Metadata()
				fmt.Printf("  %-15s %-8s %s\n", m.Name, m.Version, m.Description)
			}
			return nil
		},
	}
	pluginRunCmd := &cobra.Command{
		Use:   "run [plugin] [args...]",
		Short: "Run a plugin",
		Args:  cobra.MinimumNArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			name := args[0]
			p, ok := plugin.Global().Get(name)
			if !ok {
				return fmt.Errorf("plugin not found: %s", name)
			}
			return p.Execute(cmd.Context(), args[1:])
		},
	}
	pluginCmd.AddCommand(pluginListCmd, pluginRunCmd)
	rootCmd.AddCommand(pluginCmd)
}
