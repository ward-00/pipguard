// Package registry provides a client for the PyPI JSON API.
package registry

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"sort"
	"time"
)

// Metadata summarizes the package attributes used for the risk assessment.
type Metadata struct {
	Exists        bool      `json:"exists"`
	FirstRelease  time.Time `json:"first_release"`
	ReleaseCount  int       `json:"release_count"`
	HasHomepage   bool      `json:"has_homepage"`
	HasRepository bool      `json:"has_repository"`
	Summary       string    `json:"summary"`

	// Attributes of the latest release ("info" and "urls" in the PyPI JSON
	// API), used by indicators I-07..I-09.
	DescriptionLen  int  `json:"description_len"`
	ClassifierCount int  `json:"classifier_count"`
	SdistOnly       bool `json:"sdist_only"` // sdist only, no wheel: the build script runs at install time

	// Release times (first file of each version, ordered by upload time),
	// used by the release-level dormancy rule I-10. PreviousRelease is zero
	// when the project has a single release.
	LatestRelease   time.Time `json:"latest_release,omitempty"`
	PreviousRelease time.Time `json:"previous_release,omitempty"`
}

type pypiResponse struct {
	Info struct {
		Summary     string            `json:"summary"`
		Description string            `json:"description"`
		Classifiers []string          `json:"classifiers"`
		HomePage    string            `json:"home_page"`
		ProjectURLs map[string]string `json:"project_urls"`
	} `json:"info"`
	Releases map[string][]struct {
		UploadTime string `json:"upload_time_iso_8601"`
	} `json:"releases"`
	URLs []struct {
		PackageType string `json:"packagetype"`
	} `json:"urls"`
}

// runtimeTimeout is used by the shim at installation time. It is short so
// that fail-open is fast; packages with very large metadata can exceed it.
const runtimeTimeout = 3 * time.Second

var client = &http.Client{Timeout: runtimeTimeout}

// FetchWithTimeout is Fetch with a custom timeout. The evaluation tool
// (cmd/evalset) uses it so that large packages are not recorded as spurious
// network failures.
func FetchWithTimeout(name string, timeout time.Duration) (Metadata, error) {
	return fetch(name, &http.Client{Timeout: timeout})
}

// repoURLKeys are the project_urls keys taken to denote a source repository.
var repoURLKeys = []string{"Source", "Repository", "Source Code", "Homepage", "Code", "GitHub"}

// Fetch retrieves the metadata of package "name" from the PyPI JSON API.
//
// (Metadata{Exists:false}, nil) is the definitive signal that the package is
// not registered (404). An error means a network or parsing failure, and the
// caller MUST apply the fail-open policy.
func Fetch(name string) (Metadata, error) {
	return fetch(name, client)
}

// baseURL adalah akar PyPI JSON API; diganti oleh unit test (httptest).
var baseURL = "https://pypi.org"

func fetch(name string, c *http.Client) (Metadata, error) {
	u := fmt.Sprintf("%s/pypi/%s/json", baseURL, url.PathEscape(name))
	req, err := http.NewRequest("GET", u, nil)
	if err != nil {
		return Metadata{}, err
	}
	req.Header.Set("User-Agent", "pipguard/1.0 (thesis research tool)")

	resp, err := c.Do(req)
	if err != nil {
		return Metadata{}, err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return Metadata{Exists: false}, nil
	}
	if resp.StatusCode != http.StatusOK {
		return Metadata{}, fmt.Errorf("pypi: status %d for %q", resp.StatusCode, name)
	}

	var r pypiResponse
	if err := json.NewDecoder(resp.Body).Decode(&r); err != nil {
		return Metadata{}, fmt.Errorf("pypi: cannot parse the response for %q: %w", name, err)
	}

	m := Metadata{
		Exists:          true,
		Summary:         r.Info.Summary,
		ReleaseCount:    len(r.Releases),
		HasHomepage:     r.Info.HomePage != "",
		DescriptionLen:  len(r.Info.Description),
		ClassifierCount: len(r.Info.Classifiers),
	}
	// "urls" lists the files of the latest release. Sdist-only when there are
	// files and none of them is a built distribution (wheel/egg).
	m.SdistOnly = len(r.URLs) > 0
	for _, u := range r.URLs {
		if u.PackageType != "sdist" {
			m.SdistOnly = false
			break
		}
	}
	for _, k := range repoURLKeys {
		if v, ok := r.Info.ProjectURLs[k]; ok && v != "" {
			m.HasRepository = true
			break
		}
	}

	// The earliest release gives the project age. Without any parseable
	// release time the package is treated as new ("now"), which is the
	// conservative choice.
	var times []time.Time
	for _, files := range r.Releases {
		var first time.Time
		for _, f := range files {
			t, err := time.Parse(time.RFC3339, f.UploadTime)
			if err != nil {
				continue
			}
			if first.IsZero() || t.Before(first) {
				first = t
			}
		}
		if !first.IsZero() {
			times = append(times, first)
		}
	}
	m.FirstRelease, m.LatestRelease, m.PreviousRelease = releaseTimes(times, time.Now())
	return m, nil
}

// releaseTimes returns the first, latest and previous release times from
// the per-version upload times (in any order). With no times at all, the
// first and latest release are "now".
func releaseTimes(times []time.Time, now time.Time) (first, latest, previous time.Time) {
	if len(times) == 0 {
		return now, now, time.Time{}
	}
	sort.Slice(times, func(i, j int) bool { return times[i].Before(times[j]) })
	first, latest = times[0], times[len(times)-1]
	if len(times) > 1 {
		previous = times[len(times)-2]
	}
	return first, latest, previous
}
