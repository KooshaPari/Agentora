package adapters

import (
	"os"
	"path/filepath"
	"testing"
)

func TestCratesDetectSingle(t *testing.T) {
	d := t.TempDir()
	os.WriteFile(filepath.Join(d, "Cargo.toml"), []byte(`[package]
name = "my-crate"
version = "0.1.0"
`), 0644)

	adapter := &CratesAdapter{}
	got, err := adapter.Detect(d)
	if err != nil {
		t.Fatalf("Detect() error = %v", err)
	}
	if len(got) != 1 {
		t.Fatalf("got %d packages, want 1", len(got))
	}
	if got[0].Name != "my-crate" || got[0].Registry != RegistryCrates {
		t.Errorf("unexpected package: %+v", got[0])
	}
}

func TestCratesDetectPublishFalse(t *testing.T) {
	d := t.TempDir()
	os.WriteFile(filepath.Join(d, "Cargo.toml"), []byte(`[package]
name = "private-crate"
version = "0.1.0"
publish = false
`), 0644)

	adapter := &CratesAdapter{}
	got, _ := adapter.Detect(d)
	if len(got) != 0 {
		t.Error("expected no packages for publish=false")
	}
}

func TestCratesDetectWorkspace(t *testing.T) {
	d := t.TempDir()
	os.WriteFile(filepath.Join(d, "Cargo.toml"), []byte(`[workspace]
members = ["crates/*"]
`), 0644)

	for _, name := range []string{"core", "cli"} {
		dir := filepath.Join(d, "crates", name)
		os.MkdirAll(dir, 0755)
		os.WriteFile(filepath.Join(dir, "Cargo.toml"), []byte(`[package]
name = "`+name+`"
version = "0.1.0"
`), 0644)
	}

	adapter := &CratesAdapter{}
	got, err := adapter.Detect(d)
	if err != nil {
		t.Fatalf("Detect() error = %v", err)
	}
	if len(got) != 2 {
		t.Fatalf("got %d packages, want 2", len(got))
	}
}

func TestCratesDetectNoCargo(t *testing.T) {
	d := t.TempDir()
	adapter := &CratesAdapter{}
	got, err := adapter.Detect(d)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(got) != 0 {
		t.Error("expected empty for no Cargo.toml")
	}
}

func TestCratesVersion(t *testing.T) {
	adapter := &CratesAdapter{}
	tests := []struct {
		base    string
		channel Channel
		inc     int
		want    string
	}{
		{"1.0.0", ChannelProd, 0, "1.0.0"},
		{"1.0.0", ChannelAlpha, 1, "1.0.0-alpha.1"},
		{"1.0.0", ChannelBeta, 2, "1.0.0-beta.2"},
		{"1.0.0", ChannelRC, 1, "1.0.0-rc.1"},
	}
	for _, tt := range tests {
		t.Run(tt.want, func(t *testing.T) {
			got, err := adapter.Version(tt.base, tt.channel, tt.inc)
			if err != nil {
				t.Fatalf("error = %v", err)
			}
			if got != tt.want {
				t.Errorf("got %q, want %q", got, tt.want)
			}
		})
	}
}

func TestTopoSort(t *testing.T) {
	packages := []Package{
		{Name: "app", WorkspaceDeps: []string{"core", "utils"}},
		{Name: "core", WorkspaceDeps: []string{"utils"}},
		{Name: "utils"},
	}

	sorted, err := TopoSort(packages)
	if err != nil {
		t.Fatalf("TopoSort error: %v", err)
	}
	if len(sorted) != 3 {
		t.Fatalf("got %d, want 3", len(sorted))
	}

	// utils must come before core, core before app
	idx := map[string]int{}
	for i, p := range sorted {
		idx[p.Name] = i
	}
	if idx["utils"] >= idx["core"] {
		t.Error("utils should come before core")
	}
	if idx["core"] >= idx["app"] {
		t.Error("core should come before app")
	}
}

func TestTopoSortCycle(t *testing.T) {
	packages := []Package{
		{Name: "a", WorkspaceDeps: []string{"b"}},
		{Name: "b", WorkspaceDeps: []string{"a"}},
	}

	_, err := TopoSort(packages)
	if err == nil {
		t.Error("expected cycle error")
	}
}

func TestCratesName(t *testing.T) {
	if (&CratesAdapter{}).Name() != RegistryCrates {
		t.Error("wrong name")
	}
}
