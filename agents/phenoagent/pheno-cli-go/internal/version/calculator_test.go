package version

import "testing"

func TestCalculate(t *testing.T) {
	tests := []struct {
		name      string
		base      string
		channel   string
		increment int
		registry  string
		want      string
		wantErr   bool
	}{
		{"npm alpha", "0.2.0", "alpha", 1, "npm", "0.2.0-alpha.1", false},
		{"npm prod", "1.0.0", "prod", 0, "npm", "1.0.0", false},
		{"pypi alpha", "0.2.0", "alpha", 1, "pypi", "0.2.0a1", false},
		{"pypi beta", "0.2.0", "beta", 1, "pypi", "0.2.0b1", false},
		{"pypi rc", "1.0.0", "rc", 2, "pypi", "1.0.0rc2", false},
		{"pypi canary", "0.2.0", "canary", 3, "pypi", "0.2.0.dev3", false},
		{"pypi prod", "1.0.0", "prod", 0, "pypi", "1.0.0", false},
		{"crates alpha", "0.2.0", "alpha", 1, "crates.io", "0.2.0-alpha.1", false},
		{"go alpha", "0.2.0", "alpha", 1, "go_proxy", "v0.2.0-alpha.1", false},
		{"go prod", "1.0.0", "prod", 0, "go_proxy", "v1.0.0", false},
		{"zig prod", "1.0.0", "prod", 0, "zig", "v1.0.0", false},
		{"mojo alpha", "0.2.0", "alpha", 1, "mojo", "", true},
		{"unknown", "1.0.0", "alpha", 1, "nope", "", true},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := Calculate(tt.base, tt.channel, tt.increment, tt.registry)
			if (err != nil) != tt.wantErr {
				t.Fatalf("error = %v, wantErr %v", err, tt.wantErr)
			}
			if got != tt.want {
				t.Errorf("got %q, want %q", got, tt.want)
			}
		})
	}
}

func TestDistTag(t *testing.T) {
	if DistTag("prod") != "latest" {
		t.Error("prod should map to latest")
	}
	if DistTag("alpha") != "alpha" {
		t.Error("alpha should map to alpha")
	}
}
