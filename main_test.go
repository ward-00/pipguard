package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestPipCommandName(t *testing.T) {
	cases := map[string]string{
		"/home/u/.local/bin/pip":      "pip",
		"pip3":                        "pip3",
		"/usr/local/bin/pip3.12":      "pip3.12",
		"/home/u/.local/bin/pipguard": "pip", // dipanggil langsung (fungsi shell versi lama)
		"notpip":                      "pip",
	}
	for in, want := range cases {
		if got := pipCommandName(in); got != want {
			t.Errorf("pipCommandName(%q) = %q, want %q", in, got, want)
		}
	}
}

func exe(t *testing.T, path string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte("#!/bin/sh\n"), 0o755); err != nil {
		t.Fatal(err)
	}
}

// Shim lain di PATH (instalasi kedua pipguard) harus dilewati; tanpa ini
// dua salinan saling exec tanpa henti (ditemukan 2026-10-19).
func TestFindRealPipSkipsOtherPipguardCopies(t *testing.T) {
	root := t.TempDir()
	other := filepath.Join(root, "other", "pipguard")
	exe(t, other)
	shimDir := filepath.Join(root, "shim")
	if err := os.MkdirAll(shimDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(other, filepath.Join(shimDir, "pip")); err != nil {
		t.Fatal(err)
	}
	real := filepath.Join(root, "real", "pip")
	exe(t, real)
	exe(t, filepath.Join(root, "notexec", "pip"))
	if err := os.Chmod(filepath.Join(root, "notexec", "pip"), 0o644); err != nil {
		t.Fatal(err)
	}

	t.Setenv("PATH", shimDir+string(os.PathListSeparator)+filepath.Join(root, "notexec")+
		string(os.PathListSeparator)+filepath.Join(root, "real"))
	got, err := findRealPip("pip")
	if err != nil || got != real {
		t.Fatalf("findRealPip = %q, %v; want %q", got, err, real)
	}
}

func TestFindRealPipNotFound(t *testing.T) {
	t.Setenv("PATH", t.TempDir())
	if _, err := findRealPip("pip"); err == nil {
		t.Fatal("expected an error when no pip exists on PATH")
	}
}
