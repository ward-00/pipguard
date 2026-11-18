// Package cache keeps PyPI metadata on disk for a limited time, so that
// repeated checks do not wait for the network.
package cache

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/ward-00/pipguard/internal/registry"
)

const TTL = 24 * time.Hour

type entry struct {
	Metadata  registry.Metadata `json:"metadata"`
	FetchedAt time.Time         `json:"fetched_at"`
}

type FetchFunc func(name string) (registry.Metadata, error)

type Cache struct {
	mu      sync.Mutex
	path    string
	entries map[string]entry
	dirty   bool
}

// DefaultPath returns $XDG_CACHE_HOME/pipguard/cache.json or
// ~/.cache/pipguard/cache.json.
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

// Load reads the cache from "path". A missing or corrupt file yields an
// empty cache: the cache must never become a point of failure.
func Load(path string) *Cache {
	c := &Cache{path: path, entries: make(map[string]entry)}

	data, err := os.ReadFile(path)
	if err != nil {
		return c
	}
	var stored map[string]entry
	if json.Unmarshal(data, &stored) == nil && stored != nil {
		c.entries = stored
	}
	return c
}

// GetOrFetch returns the cached metadata of "name" while it is valid, or
// calls "fetch" and caches the result. Fetch errors are not cached.
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

// Save writes the cache if it changed. Expired entries are dropped so that
// the file, which every pip invocation parses, does not grow without bound.
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
