package cache

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/editorid0001/pipguard/internal/registry"
)

func countingFetch(calls *int, m registry.Metadata, err error) FetchFunc {
	return func(string) (registry.Metadata, error) {
		*calls++
		return m, err
	}
}

func TestGetOrFetchHitAndMiss(t *testing.T) {
	c := Load(filepath.Join(t.TempDir(), "cache.json"))
	calls := 0
	f := countingFetch(&calls, registry.Metadata{Exists: true, ReleaseCount: 3}, nil)

	for i := 0; i < 3; i++ {
		m, err := c.GetOrFetch("requests", f)
		if err != nil || !m.Exists || m.ReleaseCount != 3 {
			t.Fatalf("GetOrFetch = %+v, %v", m, err)
		}
	}
	if calls != 1 {
		t.Errorf("fetch dipanggil %d kali, seharusnya 1 (sisanya dari singgahan)", calls)
	}
}

func TestFetchErrorNotCached(t *testing.T) {
	c := Load(filepath.Join(t.TempDir(), "cache.json"))
	calls := 0
	f := countingFetch(&calls, registry.Metadata{}, errors.New("jaringan putus"))

	for i := 0; i < 2; i++ {
		if _, err := c.GetOrFetch("requests", f); err == nil {
			t.Fatal("error fetch harus diteruskan ke pemanggil (fail-open di main)")
		}
	}
	if calls != 2 {
		t.Errorf("kegagalan tidak boleh disinggahkan: fetch dipanggil %d kali, seharusnya 2", calls)
	}
}

func TestExpiredEntryRefetched(t *testing.T) {
	c := Load(filepath.Join(t.TempDir(), "cache.json"))
	c.entries["requests"] = entry{Metadata: registry.Metadata{Exists: false}, FetchedAt: time.Now().Add(-TTL - time.Minute)}
	calls := 0
	m, err := c.GetOrFetch("requests", countingFetch(&calls, registry.Metadata{Exists: true}, nil))
	if err != nil || !m.Exists || calls != 1 {
		t.Fatalf("entri kedaluwarsa harus diambil ulang: m=%+v err=%v calls=%d", m, err, calls)
	}
}

func TestSaveLoadRoundTripAndPrune(t *testing.T) {
	path := filepath.Join(t.TempDir(), "sub", "cache.json")
	c := Load(path)
	calls := 0
	if _, err := c.GetOrFetch("fresh", countingFetch(&calls, registry.Metadata{Exists: true, Summary: "x"}, nil)); err != nil {
		t.Fatal(err)
	}
	c.entries["stale"] = entry{Metadata: registry.Metadata{Exists: true}, FetchedAt: time.Now().Add(-2 * TTL)}
	if err := c.Save(); err != nil {
		t.Fatal(err)
	}

	var stored map[string]entry
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(data, &stored); err != nil {
		t.Fatal(err)
	}
	if _, ok := stored["stale"]; ok {
		t.Error("entri kedaluwarsa seharusnya dibuang saat Save")
	}

	c2 := Load(path)
	m, err := c2.GetOrFetch("fresh", countingFetch(&calls, registry.Metadata{}, errors.New("tidak boleh dipanggil")))
	if err != nil || m.Summary != "x" {
		t.Fatalf("entri tidak bertahan setelah Save/Load: %+v, %v", m, err)
	}
}

func TestCorruptFileIsEmptyCache(t *testing.T) {
	path := filepath.Join(t.TempDir(), "cache.json")
	if err := os.WriteFile(path, []byte("{bukan json"), 0o644); err != nil {
		t.Fatal(err)
	}
	c := Load(path)
	if len(c.entries) != 0 {
		t.Errorf("berkas rusak harus menjadi singgahan kosong, dapat %d entri", len(c.entries))
	}
}

func TestSaveWithoutChangesDoesNotWrite(t *testing.T) {
	path := filepath.Join(t.TempDir(), "cache.json")
	if err := Load(path).Save(); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(path); !os.IsNotExist(err) {
		t.Error("Save tanpa perubahan tidak boleh membuat berkas")
	}
}
