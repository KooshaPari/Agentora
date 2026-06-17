package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

var rootCmd = &cobra.Command{
	Use:   "pheno",
	Short: "Phenotype release governance and DX CLI",
	Long:  "Org-wide release governance, automated publishing, and developer experience tooling for Phenotype repositories.",
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func init() {
	cobra.OnInitialize(initConfig)
	rootCmd.PersistentFlags().String("config", "", "config file (default: ~/.config/pheno/config.toml)")
	rootCmd.PersistentFlags().Bool("verbose", false, "verbose output")
}

func initConfig() {
	cfgFile, _ := rootCmd.PersistentFlags().GetString("config")
	if cfgFile != "" {
		viper.SetConfigFile(cfgFile)
	} else {
		home, _ := os.UserHomeDir()
		viper.AddConfigPath(home + "/.config/pheno")
		viper.SetConfigName("config")
		viper.SetConfigType("toml")
	}
	viper.AutomaticEnv()
	viper.SetEnvPrefix("PHENO")
	_ = viper.ReadInConfig()
}
