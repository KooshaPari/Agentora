package version

import "fmt"

// Calculate returns the registry-specific versioned string for a given
// base version, target channel, pre-release increment, and registry.
//
// Examples:
//
//	Calculate("0.2.0", "alpha", 1, "npm")       → "0.2.0-alpha.1"
//	Calculate("0.2.0", "beta",  1, "pypi")      → "0.2.0b1"
//	Calculate("0.2.0", "canary", 3, "pypi")     → "0.2.0.dev3"
//	Calculate("1.0.0", "prod",  0, "crates.io") → "1.0.0"
//	Calculate("0.2.0", "alpha", 1, "go_proxy")  → "v0.2.0-alpha.1"
func Calculate(baseVersion string, channel string, increment int, registry string) (string, error) {
	if channel == "prod" {
		return prodVersion(baseVersion, registry), nil
	}

	switch registry {
	case "npm", "crates.io", "hex.pm":
		return semverPreRelease(baseVersion, channel, increment), nil
	case "pypi":
		return pypiPreRelease(baseVersion, channel, increment)
	case "go_proxy":
		return "v" + semverPreRelease(baseVersion, channel, increment), nil
	case "zig":
		return "v" + semverPreRelease(baseVersion, channel, increment), nil
	case "mojo":
		return "", fmt.Errorf("mojo: operation not supported for this registry")
	default:
		return "", fmt.Errorf("unknown registry: %s", registry)
	}
}

func prodVersion(base string, registry string) string {
	switch registry {
	case "go_proxy", "zig":
		return "v" + base
	default:
		return base
	}
}

func semverPreRelease(base string, channel string, inc int) string {
	return fmt.Sprintf("%s-%s.%d", base, channel, inc)
}

func pypiPreRelease(base string, channel string, inc int) (string, error) {
	switch channel {
	case "alpha":
		return fmt.Sprintf("%sa%d", base, inc), nil
	case "canary":
		return fmt.Sprintf("%s.dev%d", base, inc), nil
	case "beta":
		return fmt.Sprintf("%sb%d", base, inc), nil
	case "rc":
		return fmt.Sprintf("%src%d", base, inc), nil
	default:
		return "", fmt.Errorf("unknown channel: %s", channel)
	}
}

func DistTag(channel string) string {
	if channel == "prod" {
		return "latest"
	}
	return channel
}
