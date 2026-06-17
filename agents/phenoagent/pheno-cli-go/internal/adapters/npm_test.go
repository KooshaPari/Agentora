package adapters

import (
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestNpmDetect(t *testing.T) {
	tests := []struct {
		name    string
		setup   func(tmpdir string) error
		want    int
		wantErr bool
	}{
		{
			name: "single package",
			setup: func(d string) error {
				return os.WriteFile(filepath.Join(d, "package.json"),
					[]byte(`{"name":"test-pkg","version":"1.0.0"}`), 0644)
			},
			want: 1,
		},
		{
			name: "scoped package",
			setup: func(d string) error {
				return os.WriteFile(filepath.Join(d, "package.json"),
					[]byte(`{"name":"@myorg/test-pkg","version":"1.0.0"}`), 0644)
			},
			want: 1,
		},
		{
			name: "private package",
			setup: func(d string) error {
				return os.WriteFile(filepath.Join(d, "package.json"),
					[]byte(`{"name":"priv","version":"1.0.0","private":true}`), 0644)
			},
			want: 1,
		},
		{
			name: "skip node_modules",
			setup: func(d string) error {
				nm := filepath.Join(d, "node_modules", "dep")
				os.MkdirAll(nm, 0755)
				return os.WriteFile(filepath.Join(nm, "package.json"),
					[]byte(`{"name":"dep","version":"1.0.0"}`), 0644)
			},
			want: 0,
		},
		{
			name: "skip invalid json",
			setup: func(d string) error {
				return os.WriteFile(filepath.Join(d, "package.json"), []byte("{bad}"), 0644)
			},
			want: 0,
		},
		{
			name: "skip missing name",
			setup: func(d string) error {
				return os.WriteFile(filepath.Join(d, "package.json"),
					[]byte(`{"version":"1.0.0"}`), 0644)
			},
			want: 0,
		},
		{
			name: "monorepo with nested packages",
			setup: func(d string) error {
				root := `{"name":"root","version":"1.0.0"}`
				os.WriteFile(filepath.Join(d, "package.json"), []byte(root), 0644)
				sub := filepath.Join(d, "packages", "sub")
				os.MkdirAll(sub, 0755)
				return os.WriteFile(filepath.Join(sub, "package.json"),
					[]byte(`{"name":"@myorg/sub","version":"1.0.0"}`), 0644)
			},
			want: 2,
		},
	}

	adapter := &NpmAdapter{}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			d := t.TempDir()
			if err := tt.setup(d); err != nil {
				t.Fatalf("setup: %v", err)
			}
			got, err := adapter.Detect(d)
			if (err != nil) != tt.wantErr {
				t.Fatalf("Detect() error = %v, wantErr %v", err, tt.wantErr)
			}
			if len(got) != tt.want {
				t.Errorf("Detect() = %d packages, want %d", len(got), tt.want)
			}
			for _, p := range got {
				if p.Registry != RegistryNPM {
					t.Errorf("package %s has registry %s, want npm", p.Name, p.Registry)
				}
				if p.Language != LangTypeScript {
					t.Errorf("package %s has language %s, want typescript", p.Name, p.Language)
				}
			}
		})
	}
}

func TestNpmDetectPrivateFlag(t *testing.T) {
	d := t.TempDir()
	os.WriteFile(filepath.Join(d, "package.json"),
		[]byte(`{"name":"priv","version":"1.0.0","private":true}`), 0644)

	adapter := &NpmAdapter{}
	got, _ := adapter.Detect(d)
	if len(got) != 1 || !got[0].Private {
		t.Error("expected private flag to be true")
	}
}

func TestNpmVersion(t *testing.T) {
	adapter := &NpmAdapter{}
	tests := []struct {
		base    string
		channel Channel
		inc     int
		want    string
	}{
		{"1.2.3", ChannelProd, 0, "1.2.3"},
		{"1.2.3", ChannelAlpha, 1, "1.2.3-alpha.1"},
		{"1.2.3", ChannelCanary, 5, "1.2.3-canary.5"},
		{"1.2.3", ChannelBeta, 1, "1.2.3-beta.1"},
		{"1.2.3", ChannelRC, 2, "1.2.3-rc.2"},
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

func TestNpmName(t *testing.T) {
	adapter := &NpmAdapter{}
	if adapter.Name() != RegistryNPM {
		t.Errorf("Name() = %s, want npm", adapter.Name())
	}
}

func TestIsExcludedDir(t *testing.T) {
	excluded := []string{"node_modules", ".git", "dist", "build", ".next", ".nuxt", ".hidden"}
	for _, name := range excluded {
		if !isExcludedDir(name) {
			t.Errorf("isExcludedDir(%q) = false, want true", name)
		}
	}
	allowed := []string{"src", "lib", "packages", "apps"}
	for _, name := range allowed {
		if isExcludedDir(name) {
			t.Errorf("isExcludedDir(%q) = true, want false", name)
		}
	}
}

func TestParseRetryAfter(t *testing.T) {
	tests := []struct {
		msg  string
		want time.Duration
	}{
		{"npm ERR! code E429\nnpm ERR! retry after 30 seconds", 30 * time.Second},
		{"npm ERR! retry after 60 seconds", 60 * time.Second},
		{"no retry info", 45 * time.Second}, // returns default
	}
	for _, tt := range tests {
		got := parseRetryAfter(tt.msg, 45*time.Second)
		if got != tt.want {
			t.Errorf("parseRetryAfter(%q) = %v, want %v", tt.msg, got, tt.want)
		}
	}
}
