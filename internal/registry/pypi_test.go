package registry

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

// serve menjalankan PyPI JSON API tiruan selama satu test.
func serve(t *testing.T, h http.HandlerFunc) {
	t.Helper()
	srv := httptest.NewServer(h)
	old := baseURL
	baseURL = srv.URL
	t.Cleanup(func() { srv.Close(); baseURL = old })
}

const sampleJSON = `{
  "info": {
    "summary": "HTTP for Humans.",
    "description": "` + "Long README text that is clearly longer than one hundred characters, as real packages usually have one." + `",
    "classifiers": ["License :: OSI Approved", "Programming Language :: Python :: 3"],
    "home_page": "",
    "project_urls": {"Source": "https://github.com/psf/requests", "Documentation": "https://requests.readthedocs.io"}
  },
  "releases": {
    "2.0.0": [{"upload_time_iso_8601": "2013-09-24T19:00:00.000000Z"}],
    "0.2.0": [{"upload_time_iso_8601": "2011-02-14T00:00:00.000000Z"}, {"upload_time_iso_8601": "2011-02-15T00:00:00.000000Z"}],
    "2.31.0": [{"upload_time_iso_8601": "2023-05-22T15:00:00.000000Z"}]
  },
  "urls": [{"packagetype": "bdist_wheel"}, {"packagetype": "sdist"}]
}`

func TestFetchParsesMetadata(t *testing.T) {
	serve(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/pypi/requests/json" {
			t.Errorf("path = %q", r.URL.Path)
		}
		if !strings.HasPrefix(r.Header.Get("User-Agent"), "pipguard/") {
			t.Errorf("User-Agent = %q", r.Header.Get("User-Agent"))
		}
		w.Write([]byte(sampleJSON))
	})
	m, err := Fetch("requests")
	if err != nil {
		t.Fatal(err)
	}
	want := time.Date(2011, 2, 14, 0, 0, 0, 0, time.UTC)
	if !m.Exists || m.ReleaseCount != 3 || !m.FirstRelease.Equal(want) {
		t.Errorf("exists/releases/first = %v/%d/%v", m.Exists, m.ReleaseCount, m.FirstRelease)
	}
	if m.HasHomepage || !m.HasRepository || m.Summary != "HTTP for Humans." {
		t.Errorf("homepage/repo/summary = %v/%v/%q", m.HasHomepage, m.HasRepository, m.Summary)
	}
	if m.DescriptionLen < 100 || m.ClassifierCount != 2 || m.SdistOnly {
		t.Errorf("desc/classifiers/sdistOnly = %d/%d/%v", m.DescriptionLen, m.ClassifierCount, m.SdistOnly)
	}
}

func TestFetchSdistOnly(t *testing.T) {
	serve(t, func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte(`{"info":{"summary":"x"},"releases":{"0.1":[{"upload_time_iso_8601":"2026-01-01T00:00:00Z"}]},
			"urls":[{"packagetype":"sdist"}]}`))
	})
	m, err := Fetch("x")
	if err != nil || !m.SdistOnly || m.HasRepository || m.ClassifierCount != 0 {
		t.Fatalf("m = %+v, err = %v", m, err)
	}
}

func TestFetchNotFound(t *testing.T) {
	serve(t, func(w http.ResponseWriter, r *http.Request) { http.NotFound(w, r) })
	m, err := Fetch("zzz-not-registered")
	if err != nil || m.Exists {
		t.Fatalf("404 must be a definitive 'not registered' without error: m=%+v err=%v", m, err)
	}
}

// Kegagalan server dan respons rusak harus menjadi error (bukan "tidak
// terdaftar"), agar main menerapkan fail-open dan tidak memblokir.
func TestFetchErrorsAreNotNotFound(t *testing.T) {
	for name, h := range map[string]http.HandlerFunc{
		"500":        func(w http.ResponseWriter, r *http.Request) { http.Error(w, "boom", 500) },
		"rusak":      func(w http.ResponseWriter, r *http.Request) { w.Write([]byte("{not json")) },
		"rate-limit": func(w http.ResponseWriter, r *http.Request) { http.Error(w, "slow down", 429) },
	} {
		serve(t, h)
		if _, err := Fetch("requests"); err == nil {
			t.Errorf("%s: expected an error", name)
		}
	}
}

func TestFetchTimeoutIsError(t *testing.T) {
	serve(t, func(w http.ResponseWriter, r *http.Request) { time.Sleep(300 * time.Millisecond) })
	if _, err := FetchWithTimeout("requests", 50*time.Millisecond); err == nil {
		t.Fatal("a timeout must surface as an error so that main fails open")
	}
}

func TestFetchEscapesName(t *testing.T) {
	serve(t, func(w http.ResponseWriter, r *http.Request) {
		if r.URL.RawPath != "" && strings.Contains(r.URL.RawPath, "/../") {
			t.Errorf("unescaped path %q", r.URL.RawPath)
		}
		http.NotFound(w, r)
	})
	if _, err := Fetch("../admin"); err != nil {
		t.Fatal(err)
	}
}
