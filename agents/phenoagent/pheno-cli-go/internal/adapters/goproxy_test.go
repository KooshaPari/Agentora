package adapters

import (
	"os"
	"path/filepath"
	"testing"
)

func TestGoProxyDetect(t *testing.T) {
	d := t.TempDir()
	os.WriteFile(filepath.Join(d, "go.mod"), []byte("module github.com/example/mymod\n\ngo 1.21\n"), 0644)

	adapter := &GoProxyAdapter{}
	got, err := adapter.Detect(d)
	if err != nil {
		t.Fatalf("error = %v", err)
	}
	if len(got) != 1 {
		t.Fatalf("got %d, want 1", len(got))
	}
	if got[0].Name != "github.com/example/mymod" {
		t.Errorf("name = %s", got[0].Name)
	}
	if got[0].Registry != RegistryGo {
		t.Errorf("registry = %s", got[0].Registry)
	}
}

func TestGoProxyDetectNoMod(t *testing.T) {
	d := t.TempDir()
	adapter := &GoProxyAdapter{}
	got, _ := adapter.Detect(d)
	if len(got) != 0 {
		t.Error("expected empty for no go.mod")
	}
}

func TestGoProxyVersion(t *testing.T) {
	adapter := &GoProxyAdapter{}
	got, err := adapter.Version("1.0.0", ChannelAlpha, 1)
	if err != nil {
		t.Fatal(err)
	}
	if got != "v1.0.0-alpha.1" {
		t.Errorf("got %q", got)
	}

	got, _ = adapter.Version("1.0.0", ChannelProd, 0)
	if got != "v1.0.0" {
		t.Errorf("prod got %q", got)
	}
}

func TestStubAdapters(t *testing.T) {
	stubs := []RegistryAdapter{&HexAdapter{}, &ZigAdapter{}, &MojoAdapter{}}
	for _, s := range stubs {
		_, err := s.Build(Package{})
		if err == nil {
			t.Errorf("%s Build should return error", s.Name())
		}
		_, err = s.Publish(Package{}, "1.0.0", nil)
		if err == nil {
			t.Errorf("%s Publish should return error", s.Name())
		}
		_, err = s.Verify(Package{}, "1.0.0")
		if err == nil {
			t.Errorf("%s Verify should return error", s.Name())
		}
	}
}

func TestGetAdapter(t *testing.T) {
	for _, reg := range []Registry{RegistryNPM, RegistryPyPI, RegistryCrates, RegistryGo, RegistryHex, RegistryZig, RegistryMojo} {
		a, err := GetAdapter(reg)
		if err != nil {
			t.Errorf("GetAdapter(%s) error = %v", reg, err)
		}
		if a.Name() != reg {
			t.Errorf("adapter.Name() = %s, want %s", a.Name(), reg)
		}
	}

	_, err := GetAdapter(Registry("fake"))
	if err == nil {
		t.Error("expected error for unknown registry")
	}
}

func TestHexDetect(t *testing.T) {
	d := t.TempDir()
	os.WriteFile(filepath.Join(d, "mix.exs"), []byte("defmodule MyApp.MixProject do\nend\n"), 0644)
	adapter := &HexAdapter{}
	got, _ := adapter.Detect(d)
	if len(got) != 1 {
		t.Errorf("got %d, want 1", len(got))
	}
}

func TestMojoDetect(t *testing.T) {
	d := t.TempDir()
	os.WriteFile(filepath.Join(d, "mojoproject.toml"), []byte(`[project]
name = "my-mojo"
version = "0.1.0"
`), 0644)
	adapter := &MojoAdapter{}
	got, _ := adapter.Detect(d)
	if len(got) != 1 || got[0].Name != "my-mojo" {
		t.Errorf("got %v", got)
	}
}
