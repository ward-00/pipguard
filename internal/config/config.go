// Package config loads pipguard's settings from an optional system-wide
// file (/etc/pipguard/config.json), an optional per-user file
// (~/.config/pipguard/config.json) and, when permitted, environment
// variables.
//
// Every setting has a safe default; both files are optional.
package config

import (
	"encoding/json"
	"os"
	"path/filepath"
)

// SystemPath is the system-wide configuration file. When it sets "locked",
// the per-user file and environment variables are ignored, so a process that
// runs as the user (for example an AI coding agent following an injected
// instruction) cannot switch the check off.
var SystemPath = "/etc/pipguard/config.json"

// Config holds every user-adjustable setting.
type Config struct {
	// AssumeYes skips the Y/N confirmation (trusted non-interactive use).
	AssumeYes bool `json:"assume_yes"`

	// Disabled turns pipguard off: commands are forwarded unchecked.
	Disabled bool `json:"disabled"`

	// AllowEnvOverride lets PIPGUARD_ASSUME_YES=1 and PIPGUARD_DISABLE=1
	// take effect. It is off by default, because any process that can set
	// an environment variable could otherwise disable the check.
	AllowEnvOverride bool `json:"allow_env_override"`

	// Allow lists package names (PEP 503 normalized) that are never
	// prompted for, e.g. internal packages served by a private index.
	Allow []string `json:"allow"`

	// CheckCustomIndex keeps checking packages against PyPI when the
	// command selects another primary index (-i/--index-url). Off by
	// default: PyPI metadata does not describe packages served elsewhere.
	CheckCustomIndex bool `json:"check_custom_index"`

	// ReleaseDormancyDays enables the release-level rule I-10 (a release
	// younger than 30 days after at least this many days without releases).
	// 0 keeps the shipped default.
	ReleaseDormancyDays int `json:"release_dormancy_days"`

	// Locked (system file only) ignores the per-user file and environment.
	Locked bool `json:"locked"`
}

// DefaultPath returns the per-user configuration file:
// $XDG_CONFIG_HOME/pipguard/config.json or ~/.config/pipguard/config.json.
func DefaultPath() (string, error) {
	base := os.Getenv("XDG_CONFIG_HOME")
	if base == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			return "", err
		}
		base = filepath.Join(home, ".config")
	}
	return filepath.Join(base, "pipguard", "config.json"), nil
}

// Load reads the system file, then (unless it is locked) the per-user file
// and, if allowed, the environment overrides. Missing or invalid files are
// ignored silently: configuration must never become a point of failure.
func Load() Config {
	var c Config
	readInto(SystemPath, &c)
	if c.Locked {
		return c
	}
	if path, err := DefaultPath(); err == nil {
		readInto(path, &c)
	}
	c.Locked = false // only the system file may lock
	if c.AllowEnvOverride {
		if os.Getenv("PIPGUARD_ASSUME_YES") == "1" {
			c.AssumeYes = true
		}
		if os.Getenv("PIPGUARD_DISABLE") == "1" {
			c.Disabled = true
		}
	}
	return c
}

func readInto(path string, c *Config) {
	data, err := os.ReadFile(path)
	if err != nil {
		return
	}
	var fileCfg Config
	if json.Unmarshal(data, &fileCfg) != nil {
		return
	}
	c.AssumeYes = c.AssumeYes || fileCfg.AssumeYes
	c.Disabled = c.Disabled || fileCfg.Disabled
	c.AllowEnvOverride = c.AllowEnvOverride || fileCfg.AllowEnvOverride
	c.CheckCustomIndex = c.CheckCustomIndex || fileCfg.CheckCustomIndex
	c.Locked = c.Locked || fileCfg.Locked
	c.Allow = append(c.Allow, fileCfg.Allow...)
	if fileCfg.ReleaseDormancyDays > 0 {
		c.ReleaseDormancyDays = fileCfg.ReleaseDormancyDays
	}
}

// EnvOverrideIgnored reports whether an override variable is set but has no
// effect, so that the user can be told why.
func (c Config) EnvOverrideIgnored() bool {
	return !c.AllowEnvOverride &&
		(os.Getenv("PIPGUARD_ASSUME_YES") == "1" || os.Getenv("PIPGUARD_DISABLE") == "1")
}
