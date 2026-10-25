package config

import (
	"os"
	"path/filepath"
	"testing"
)

func setup(t *testing.T, system, user string) {
	t.Helper()
	dir := t.TempDir()
	SystemPath = filepath.Join(dir, "system.json")
	t.Cleanup(func() { SystemPath = "/etc/pipguard/config.json" })
	if system != "" {
		if err := os.WriteFile(SystemPath, []byte(system), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	t.Setenv("XDG_CONFIG_HOME", dir)
	if user != "" {
		if err := os.MkdirAll(filepath.Join(dir, "pipguard"), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(filepath.Join(dir, "pipguard", "config.json"), []byte(user), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	t.Setenv("PIPGUARD_ASSUME_YES", "")
	t.Setenv("PIPGUARD_DISABLE", "")
}

func TestEnvOverrideIgnoredByDefault(t *testing.T) {
	setup(t, "", "")
	t.Setenv("PIPGUARD_DISABLE", "1")
	t.Setenv("PIPGUARD_ASSUME_YES", "1")
	c := Load()
	if c.Disabled || c.AssumeYes {
		t.Fatalf("environment overrides must be ignored unless allowed: %+v", c)
	}
	if !c.EnvOverrideIgnored() {
		t.Fatal("expected EnvOverrideIgnored")
	}
}

func TestEnvOverrideAllowedByUserFile(t *testing.T) {
	setup(t, "", `{"allow_env_override": true}`)
	t.Setenv("PIPGUARD_ASSUME_YES", "1")
	if c := Load(); !c.AssumeYes {
		t.Fatalf("expected AssumeYes with allow_env_override: %+v", c)
	}
}

func TestSystemLockIgnoresUserAndEnv(t *testing.T) {
	setup(t, `{"locked": true, "allow": ["corp-internal"]}`, `{"allow_env_override": true, "disabled": true}`)
	t.Setenv("PIPGUARD_DISABLE", "1")
	c := Load()
	if c.Disabled || c.AllowEnvOverride {
		t.Fatalf("locked system config must ignore user file and environment: %+v", c)
	}
	if len(c.Allow) != 1 || c.Allow[0] != "corp-internal" {
		t.Fatalf("system allowlist lost: %v", c.Allow)
	}
}

func TestUserFileCannotLock(t *testing.T) {
	setup(t, "", `{"locked": true, "allow": ["a"]}`)
	if c := Load(); c.Locked {
		t.Fatal("only the system file may lock the configuration")
	}
}

func TestBrokenFilesIgnored(t *testing.T) {
	setup(t, `{not json`, `[]`)
	if c := Load(); c.Disabled || c.AssumeYes || len(c.Allow) != 0 {
		t.Fatalf("broken files must be ignored: %+v", c)
	}
}
