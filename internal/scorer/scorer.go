// Package scorer assesses package risk in two stages: Signals checks the
// indicators I-01..I-10, and Score sums the points of the fired indicators
// and maps the sum to a risk level. V1 (initial design) and V2 (calibrated)
// are kept for comparison; the shim uses V3.
package scorer

import (
	"strconv"
	"time"

	"github.com/ward-00/pipguard/internal/registry"
)

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

type Hit struct {
	Rule   string // "I-01" .. "I-10"
	Points int
}

type Result struct {
	Score   int
	Level   Level
	Reasons []string
	Hits    []Hit
}

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

type Model struct {
	Name       string
	Points     map[string]int
	Warn       int // minimum WARNING score
	Danger     int // minimum DANGER score
	Similarity *Similarity
	Dormancy   time.Duration // enables I-10 when positive
}

// V1 is the initial design with designer-set weights.
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

// V2 is the calibrated two-decision model. I-02 alone reaches the WARNING
// threshold, so every new project requires confirmation; the metadata and
// name points sum to less than 50, so they never flag an established
// project and only raise a new one to DANGER.
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

// V3DormancyDays is the default I-10 dormancy period; 0 disables the rule.
// Users can enable it with "release_dormancy_days" in the configuration.
const V3DormancyDays = 0

// V3 is V2 plus I-10: a release younger than 30 days that follows at least
// dormancyDays without releases requires confirmation like a new project,
// which covers compromised or pre-aged projects that I-02 cannot see.
func V3(popular []string, dormancyDays int) Model {
	m := V2(popular)
	m.Name = "v3"
	if dormancyDays > 0 {
		m.Points[RuleReactivated] = 50
		m.Dormancy = time.Duration(dormancyDays) * 24 * time.Hour
	}
	return m
}

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

// Signals checks every indicator for the normalized name "name" at "now".
func (m Model) Signals(name string, meta registry.Metadata, now time.Time) Signals {
	s := Signals{Fired: map[string]bool{}, Reasons: map[string]string{}}

	if match, d, ok := m.Similarity.Match(name); ok {
		s.SimilarTo, s.Distance = match, d
		s.fire(RuleSimilarName, "The name is "+strconv.Itoa(d)+
			" edit(s) away from the popular package \""+match+"\"")
	}

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

// Score sums the points of the fired indicators. An unregistered package is
// always DANGER.
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

// EvaluateAt assesses a package as of "now" (used by the historical
// evaluation).
func (m Model) EvaluateAt(name string, meta registry.Metadata, now time.Time) Result {
	return m.Score(m.Signals(name, meta, now))
}

func (m Model) Evaluate(name string, meta registry.Metadata) Result {
	return m.EvaluateAt(name, meta, time.Now())
}
