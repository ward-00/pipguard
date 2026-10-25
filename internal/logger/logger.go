// Package logger records every package assessment in a local JSON Lines
// activity log (used, among other things, as evidence by the interception
// test).
package logger

import (
	"encoding/json"
	"os"
	"path/filepath"
	"time"

	"github.com/ward-00/pipguard/internal/scorer"
)

// entryRecord is one log line.
type entryRecord struct {
	Timestamp time.Time `json:"timestamp"`
	Package   string    `json:"package"`
	Score     int       `json:"score"`
	Level     string    `json:"level"`
	Reasons   []string  `json:"reasons"`
}

// DefaultPath returns the default log file:
// $XDG_CACHE_HOME/pipguard/activity.log or ~/.cache/pipguard/activity.log.
//
// The log lives next to the cache because both are operational data that
// can be deleted at any time.
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

// Record appends one line to the activity log. Logging failures must not
// stop the main flow (fail-open), so the function returns no error.
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
