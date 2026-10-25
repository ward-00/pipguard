// Package cache provides a local cache of PyPI metadata with a TTL, so that
// repeated checks (large requirements files, frequent pip invocations) do
// not always wait for the network.
package cache

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/ward-00/pipguard/internal/registry"
)

// TTL is the lifetime of one cache entry.
const TTL = 24 * time.Hour

type entry struct {
	Metadata  registry.Metadata `json:"metadata"`
	FetchedAt time.Time         `json:"fetched_at"`
}

// FetchFunc fetches metadata from the authoritative source (e.g.
// registry.Fetch) when the cache holds no valid entry.
type FetchFunc func(name string) (registry.Metadata, error)

// Cache is loaded once at start-up and written back only when it changed.
type Cache struct {
	mu      sync.Mutex
	path    string
	entries map[string]entry
	dirty   bool
}

// DefaultPath returns the default cache file:
// $XDG_CACHE_HOME/pipguard/cache.json or ~/.cache/pipguard/cache.json.
func DefaultPath() (string, error) {
	base := os.Getenv("XDG_CACHE_HOME")
	if base == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			return "", err
		}
		base = filepath.Join(home, ".cache")
	}
	return filepath.Join(base, "pipguard", "cache.json"), nil
}

// Load reads the cache from "path". A missing, empty or corrupt file is
// treated as an empty cache, not an error: the cache must never become a
// point of failure.
func Load(path string) *Cache {
	c := &Cache{path: path, entries: make(map[string]entry)}

	data, err := os.ReadFile(path)
	if err != nil {
		return c
	}
	var stored map[string]entry
	if err := json.Unmarshal(data, &stored); err != nil {
		return c // corrupt file: start from an empty cache
	}
	c.entries = stored
	return c
}

// GetOrFetch returns the metadata of "name" from the cache while it is
// valid, or calls "fetch" and stores the result.
//
// Errors of "fetch" are returned unchanged; the caller applies the
// fail-open policy.
func (c *Cache) GetOrFetch(name string, fetch FetchFunc) (registry.Metadata, error) {
	c.mu.Lock()
	if e, ok := c.entries[name]; ok && time.Since(e.FetchedAt) < TTL {
		c.mu.Unlock()
		return e.Metadata, nil
	}
	c.mu.Unlock()

	m, err := fetch(name)
	if err != nil {
		return registry.Metadata{}, err
	}

	c.mu.Lock()
	c.entries[name] = entry{Metadata: m, FetchedAt: time.Now()}
	c.dirty = true
	c.mu.Unlock()
	return m, nil
}

// Save writes the cache to disk if it changed since the last Load/Save. It
// is safe to call repeatedly and does nothing without changes.
//
// Expired entries are dropped on write. Without this the file would grow
// without bound, and every pip invocation would pay for parsing all of it
// (see bench-results-final/).
func (c *Cache) Save() error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if !c.dirty {
		return nil
	}
	for name, e := range c.entries {
		if time.Since(e.FetchedAt) >= TTL {
			delete(c.entries, name)
		}
	}
	if err := os.MkdirAll(filepath.Dir(c.path), 0o755); err != nil {
		return err
	}
	data, err := json.Marshal(c.entries)
	if err != nil {
		return err
	}
	tmp := c.path + ".tmp"
	if err := os.WriteFile(tmp, data, 0o644); err != nil {
		return err
	}
	if err := os.Rename(tmp, c.path); err != nil {
		return err
	}
	c.dirty = false
	return nil
}
