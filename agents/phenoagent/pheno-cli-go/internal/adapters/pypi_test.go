package adapters

import (
	"os"
	"path/filepath"
	"testing"
)

func TestPyPIDetect(t *testing.T) {
	tests := []struct {
		name    string
		setup   func(d string) error
		want    int
		private bool
	}{
		{
			name: "modern project format",
			setup: func(d string) error {
				return os.WriteFile(filepath.Join(d, "pyproject.toml"), []byte(`[project]
name = "my-pkg"
version = "1.0.0"
`), 0644)
			},
			want: 1,
		},
		{
			name: "poetry format",
			setup: func(d string) error {
				return os.WriteFile(filepath.Join(d, "pyproject.toml"), []byte(`[tool.poetry]
name = "poetry-pkg"
version = "2.0.0"
`), 0644)
			},
			want: 1,
		},
		{
			name: "private package",
			setup: func(d string) error {
				return os.WriteFile(filepath.Join(d, "pyproject.toml"), []byte(`[project]
name = "secret"
version = "1.0.0"
classifiers = ["Private :: Do Not Upload"]
`), 0644)
			},
			want:    1,
			private: true,
		},
		{
			name: "skip venv",
			setup: func(d string) error {
				venv := filepath.Join(d, ".venv", "lib")
				os.MkdirAll(venv, 0755)
				return os.WriteFile(filepath.Join(venv, "pyproject.toml"), []byte(`[project]
name = "venv-pkg"
version = "1.0.0"
`), 0644)
			},
			want: 0,
		},
		{
			name: "skip invalid toml",
			setup: func(d string) error {
				return os.WriteFile(filepath.Join(d, "pyproject.toml"), []byte(`{not toml}`), 0644)
			},
			want: 0,
		},
		{
			name: "skip missing name",
			setup: func(d string) error {
				return os.WriteFile(filepath.Join(d, "pyproject.toml"), []byte(`[project]
version = "1.0.0"
`), 0644)
			},
			want: 0,
		},
	}

	adapter := &PyPIAdapter{}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			d := t.TempDir()
			if err := tt.setup(d); err != nil {
				t.Fatalf("setup: %v", err)
			}
			got, err := adapter.Detect(d)
			if err != nil {
				t.Fatalf("Detect() error = %v", err)
			}
			if len(got) != tt.want {
				t.Errorf("Detect() = %d packages, want %d", len(got), tt.want)
			}
			if tt.private && len(got) > 0 && !got[0].Private {
				t.Error("expected private flag")
			}
			for _, p := range got {
				if p.Registry != RegistryPyPI {
					t.Errorf("registry = %s, want pypi", p.Registry)
				}
			}
		})
	}
}

func TestPyPIVersion(t *testing.T) {
	adapter := &PyPIAdapter{}
	tests := []struct {
		base    string
		channel Channel
		inc     int
		want    string
	}{
		{"1.0.0", ChannelProd, 0, "1.0.0"},
		{"1.0.0", ChannelAlpha, 1, "1.0.0a1"},
		{"1.0.0", ChannelCanary, 3, "1.0.0.dev3"},
		{"1.0.0", ChannelBeta, 1, "1.0.0b1"},
		{"1.0.0", ChannelRC, 2, "1.0.0rc2"},
	}
	for _, tt := range tests {
		t.Run(tt.want, func(t *testing.T) {
			got, err := adapter.Version(tt.base, tt.channel, tt.inc)
			if err != nil {
				t.Fatalf("Version() error = %v", err)
			}
			if got != tt.want {
				t.Errorf("Version() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestPyPIName(t *testing.T) {
	adapter := &PyPIAdapter{}
	if adapter.Name() != RegistryPyPI {
		t.Errorf("Name() = %s, want pypi", adapter.Name())
	}
}

func TestIsExcludedPythonDir(t *testing.T) {
	excluded := []string{"venv", ".venv", "__pycache__", ".tox", "build", "dist"}
	for _, name := range excluded {
		if !isExcludedPythonDir(name) {
			t.Errorf("isExcludedPythonDir(%q) = false, want true", name)
		}
	}
	allowed := []string{"src", "lib", "tests"}
	for _, name := range allowed {
		if isExcludedPythonDir(name) {
			t.Errorf("isExcludedPythonDir(%q) = true, want false", name)
		}
	}
}
