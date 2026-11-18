// Package logger appends every assessment to a JSON Lines activity log.
package logger

import (
	"encoding/json"
	"os"
	"path/filepath"
	"time"

	"github.com/ward-00/pipguard/internal/scorer"
)

type entryRecord struct {
	Timestamp time.Time `json:"timestamp"`
	Package   string    `json:"package"`
	Score     int       `json:"score"`
	Level     string    `json:"level"`
	Reasons   []string  `json:"reasons"`
}

// DefaultPath returns $XDG_CACHE_HOME/pipguard/activity.log or
// ~/.cache/pipguard/activity.log.
func DefaultPath() (string, error) {
	base := os.Getenv("XDG_CACHE_HOME")
	if base == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			return "", err
		}
		base = filepath.Join(home, ".cache")
	}
	return filepath.Join(base, "pipguard", "activity.log"), nil
}

// Record never fails: logging must not stop the installation.
func Record(name string, r scorer.Result) {
	path, err := DefaultPath()
	if err != nil {
		return
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return
	}

	f, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o644)
	if err != nil {
		return
	}
	defer f.Close()

	rec := entryRecord{
		Timestamp: time.Now(),
		Package:   name,
		Score:     r.Score,
		Level:     r.Level.String(),
		Reasons:   r.Reasons,
	}
	line, err := json.Marshal(rec)
	if err != nil {
		return
	}
	line = append(line, '\n')
	_, _ = f.Write(line)
}
