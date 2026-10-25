// Package scorer implements pipguard's package risk assessment.
//
// Assessment has two stages:
//
//  1. Signal extraction (Model.Signals): each indicator I-01..I-10 is
//     checked against the package name and its PyPI metadata.
//  2. Weighting (Model.Score): the points of the fired indicators are summed
//     and mapped to a risk level by two thresholds.
//
// Three models are provided. V1 is the initial design (designer-set weights)
// and V2 the calibrated two-decision model of the first journal submission;
// both are kept unchanged for comparison. V3, used by the shim, adds the
// release-level dormancy rule I-10. Weights and thresholds were calibrated
// on development/validation data and tested on temporally separated data;
// see scripts/eval/ and paper/RESULTS.md.
package scorer

import (
	"strconv"
	"time"

	"github.com/ward-00/pipguard/internal/registry"
)

// Indicator codes. I-01..I-06 come from the initial design, I-07..I-09 were
// added in iteration 2 and I-10 in iteration 3.
const (
	RuleNotRegistered = "I-01" // not registered on PyPI
	RuleNew           = "I-02" // first release less than 30 days before the check
	RuleSingleRelease = "I-03" // exactly one release
	RuleNoLinks       = "I-04" // neither homepage nor repository link
	RuleSimilarName   = "I-05" // name similar to a popular package (typosquatting)
	RuleShortSummary  = "I-06" // summary shorter than 10 characters
	RuleSdistOnly     = "I-07" // latest release is sdist only (its build script runs at install time)
	RuleShortDesc     = "I-08" // long description (README) shorter than 100 characters
	RuleNoClassifiers = "I-09" // no Trove classifiers at all
	RuleReactivated   = "I-10" // new release of an older project after a long period without releases
)

// AllRules lists every extracted indicator, in order.
var AllRules = []string{
	RuleNotRegistered, RuleNew, RuleSingleRelease, RuleNoLinks, RuleSimilarName,
	RuleShortSummary, RuleSdistOnly, RuleShortDesc, RuleNoClassifiers, RuleReactivated,
}

const (
	newPackageAge      = 30 * 24 * time.Hour
	newReleaseAge      = 30 * 24 * time.Hour
	shortSummaryLen    = 10
	shortDescriptionLn = 100
)

// Level is the final risk level of a package.
type Level int

const (
	Safe Level = iota
	Warning
	Danger
)

func (l Level) String() string {
	switch l {
	case Safe:
		return "SAFE"
	case Warning:
		return "WARNING"
	case Danger:
		return "DANGER"
	default:
		return "UNKNOWN"
	}
}

// Hit records one fired indicator and the points it contributed. Used by
// cmd/evalset for baselines and ablation.
type Hit struct {
	Rule   string // "I-01" .. "I-10"
	Points int
}

// Result is the risk assessment of one package.
type Result struct {
	Score   int
	Level   Level
	Reasons []string
	Hits    []Hit
}

// Signals is the output of the extraction stage: which indicators fired,
// with a human-readable reason for each.
type Signals struct {
	Fired     map[string]bool
	Reasons   map[string]string
	SimilarTo string // closest popular name when I-05 fired
	Distance  int
}

func (s *Signals) fire(rule, reason string) {
	s.Fired[rule] = true
	s.Reasons[rule] = reason
}

// Model combines the name-similarity configuration (I-05) and the dormancy
// period of I-10 with the indicator weights and level thresholds.
type Model struct {
	Name       string
	Points     map[string]int // indicators without points do not affect the score
	Warn       int            // minimum WARNING score
	Danger     int            // minimum DANGER score
	Similarity *Similarity
	// Dormancy enables I-10 when positive: the latest release is younger
	// than 30 days and was uploaded at least Dormancy after the previous one.
	Dormancy time.Duration
}

// V1 returns the initial design: designer-set weights, thresholds 20/60,
// I-05 at Levenshtein distance 1..2 for names of at least 6 characters.
func V1(popular []string) Model {
	return Model{
		Name: "v1",
		Points: map[string]int{
			RuleNotRegistered: 100, RuleNew: 40, RuleSingleRelease: 20,
			RuleNoLinks: 15, RuleSimilarName: 30, RuleShortSummary: 10,
		},
		Warn: 20, Danger: 60,
		Similarity: NewSimilarity(popular, 6, 2, false),
	}
}

// V2 returns the two-decision model of iteration 2.
//
//   - I-01 not registered: 100 points, always DANGER.
//   - I-02 younger than 30 days: 50 points, equal to the WARNING threshold,
//     so every new project requires confirmation (project-level cooldown).
//   - I-03..I-09 (metadata and name similarity) only raise a new package to
//     DANGER. Their points sum to at most 49, so metadata alone never flags
//     an established package.
//
// The metadata points, the DANGER threshold (50 + tau) and the I-05
// configuration (top 5,000 packages in assets/popular_v2.txt, Levenshtein
// distance 1, names of at least 5 characters) were fitted on 2025 packages
// (scripts/eval/fit_weights.py, paper/data/calibration.json). I-03 and I-06
// carry no information (0 points). scripts/eval/run_all.sh checks that the
// numbers here equal the calibration output.
func V2(popular []string) Model {
	return Model{
		Name: "v2",
		Points: map[string]int{
			RuleNotRegistered: 100, RuleNew: 50,
			RuleNoLinks: 5, RuleSimilarName: 15, RuleSdistOnly: 10, RuleShortDesc: 12, RuleNoClassifiers: 1,
		},
		Warn:       50,
		Danger:     57,
		Similarity: NewSimilarity(popular, 5, 1, false),
	}
}

// V3DormancyDays is the default dormancy period of I-10 in the shipped
// model; 0 disables the rule. It is fixed by a decision rule applied to
// development and validation data only (scripts/eval/analyze_v3.py,
// paper/data/dormancy_choice.json): the rule is enabled by default only if
// its share of affected install-client downloads does not exceed that of the
// 30-day project-level cooldown. Users can enable it with
// "release_dormancy_days" in the configuration file.
const V3DormancyDays = 0

// V3 returns the model used by the shim: V2 plus the release-level
// dormancy rule I-10 when dormancyDays > 0. A release younger than 30 days
// that follows at least dormancyDays without releases, in a project older
// than 30 days, receives 50 points and so requires confirmation like a new
// project. This covers compromised or "pre-aged" projects, which the
// project-level age of I-02 cannot see.
func V3(popular []string, dormancyDays int) Model {
	m := V2(popular)
	m.Name = "v3"
	m.Points = map[string]int{}
	for k, v := range V2(popular).Points {
		m.Points[k] = v
	}
	if dormancyDays > 0 {
		m.Points[RuleReactivated] = 50
		m.Dormancy = time.Duration(dormancyDays) * 24 * time.Hour
	}
	return m
}

// LevelFor maps a score to a risk level using the model's thresholds.
func (m Model) LevelFor(score int) Level {
	switch {
	case score >= m.Danger:
		return Danger
	case score >= m.Warn:
		return Warning
	default:
		return Safe
	}
}

// Signals extracts every indicator for package "name" (already normalized,
// see internal/parser.Normalize) at time "now".
func (m Model) Signals(name string, meta registry.Metadata, now time.Time) Signals {
	s := Signals{Fired: map[string]bool{}, Reasons: map[string]string{}}

	if match, d, ok := m.Similarity.Match(name); ok {
		s.SimilarTo, s.Distance = match, d
		s.fire(RuleSimilarName, "The name is "+strconv.Itoa(d)+
			" edit(s) away from the popular package \""+match+"\"")
	}

	// I-01: not registered is definitive; there is no metadata to check.
	if !meta.Exists {
		s.fire(RuleNotRegistered, "The package is not registered on PyPI")
		return s
	}
	if now.Sub(meta.FirstRelease) < newPackageAge {
		s.fire(RuleNew, "The project was first published less than 30 days ago")
	} else if m.Dormancy > 0 && !meta.PreviousRelease.IsZero() &&
		now.Sub(meta.LatestRelease) < newReleaseAge &&
		meta.LatestRelease.Sub(meta.PreviousRelease) >= m.Dormancy {
		days := int(meta.LatestRelease.Sub(meta.PreviousRelease).Hours() / 24)
		s.fire(RuleReactivated, "The latest release is less than 30 days old and follows "+
			strconv.Itoa(days)+" days without any release")
	}
	if meta.ReleaseCount == 1 {
		s.fire(RuleSingleRelease, "The project has only one release")
	}
	if !meta.HasHomepage && !meta.HasRepository {
		s.fire(RuleNoLinks, "No homepage or repository link")
	}
	if len(meta.Summary) < shortSummaryLen {
		s.fire(RuleShortSummary, "The package summary is empty or very short")
	}
	if meta.SdistOnly {
		s.fire(RuleSdistOnly, "The latest release is source-only (sdist): "+
			"its build script runs during installation")
	}
	if meta.DescriptionLen < shortDescriptionLn {
		s.fire(RuleShortDesc, "The package description (README) is empty or very short")
	}
	if meta.ClassifierCount == 0 {
		s.fire(RuleNoClassifiers, "No classifiers at all")
	}
	return s
}

// Score sums the points of the fired indicators and sets the risk level.
// An unregistered package is always DANGER.
func (m Model) Score(s Signals) Result {
	r := Result{}
	for _, rule := range AllRules {
		p := m.Points[rule]
		if !s.Fired[rule] || p == 0 {
			continue
		}
		r.Score += p
		r.Reasons = append(r.Reasons, s.Reasons[rule])
		r.Hits = append(r.Hits, Hit{Rule: rule, Points: p})
	}
	r.Level = m.LevelFor(r.Score)
	if s.Fired[RuleNotRegistered] {
		r.Level = Danger
	}
	return r
}

// EvaluateAt assesses a package with ages (I-02, I-10) relative to "now".
// Used by the historical evaluation: removed malicious packages are assessed
// at a time when they were still installable.
func (m Model) EvaluateAt(name string, meta registry.Metadata, now time.Time) Result {
	return m.Score(m.Signals(name, meta, now))
}

// Evaluate assesses package "name" at the current time.
func (m Model) Evaluate(name string, meta registry.Metadata) Result {
	return m.EvaluateAt(name, meta, time.Now())
}
