// Package config loads the optional system and per-user configuration files
// and, when permitted, environment overrides. Every setting defaults to safe.
package config

import (
	"encoding/json"
	"os"
	"path/filepath"
)

// SystemPath can set "locked", which ignores the per-user file and the
// environment, so that a process running as the user (e.g. an AI agent
// following an injected instruction) cannot switch the check off.
var SystemPath = "/etc/pipguard/config.json"

type Config struct {
	AssumeYes bool `json:"assume_yes"`
	Disabled  bool `json:"disabled"`
	// Off by default: otherwise any process that can set an environment
	// variable could disable the check.
	AllowEnvOverride    bool     `json:"allow_env_override"`
	Allow               []string `json:"allow"`
	CheckCustomIndex    bool     `json:"check_custom_index"`
	ReleaseDormancyDays int      `json:"release_dormancy_days"`
	Locked              bool     `json:"locked"` // honoured in the system file only
}

// DefaultPath returns $XDG_CONFIG_HOME/pipguard/config.json or
// ~/.config/pipguard/config.json.
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

// Load ignores missing or invalid files: configuration must never become a
// point of failure.
func Load() Config {
	var c Config
	readInto(SystemPath, &c)
	if c.Locked {
		return c
	}
	if path, err := DefaultPath(); err == nil {
		readInto(path, &c)
	}
	c.Locked = false
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

// EnvOverrideIgnored reports an override variable that is set but not allowed.
func (c Config) EnvOverrideIgnored() bool {
	return !c.AllowEnvOverride &&
		(os.Getenv("PIPGUARD_ASSUME_YES") == "1" || os.Getenv("PIPGUARD_DISABLE") == "1")
}
