package config

import (
	"os"

	"github.com/spf13/viper"
)

// Config holds the loaded CLI configuration.
type Config struct {
	v *viper.Viper
}

// LoadConfig loads the global Viper configuration into a Config instance.
func LoadConfig(v *viper.Viper) *Config {
	return &Config{v: v}
}

// GetCredentials returns credentials for a given registry from environment variables.
// It checks PHENO_NPM_TOKEN, PHENO_PYPI_TOKEN, and PHENO_CRATES_TOKEN.
func (c *Config) GetCredentials(registry string) map[string]string {
	creds := make(map[string]string)

	// Map registry names to environment variable suffixes
	switch registry {
	case "npm":
		if token := os.Getenv("PHENO_NPM_TOKEN"); token != "" {
			creds["npm_token"] = token
		}
	case "pypi":
		if token := os.Getenv("PHENO_PYPI_TOKEN"); token != "" {
			creds["pypi_token"] = token
		}
	case "crates.io":
		if token := os.Getenv("PHENO_CRATES_TOKEN"); token != "" {
			creds["crates_token"] = token
		}
	}

	return creds
}
