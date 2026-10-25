package main

import (
	"math"
	"strings"
	"testing"
	"time"

	"github.com/ward-00/pipguard/internal/registry"
	"github.com/ward-00/pipguard/internal/scorer"
)

func TestWilson(t *testing.T) {
	cases := []struct {
		k, n   int
		lo, hi float64
	}{
		{54, 54, 0.9336, 1},
		{63, 1038, 0.0477, 0.0770},
		{0, 10, 0, 0.2775},
	}
	for _, c := range cases {
		lo, hi := wilson(c.k, c.n)
		if math.Abs(lo-c.lo) > 1e-3 || math.Abs(hi-c.hi) > 1e-3 {
			t.Errorf("wilson(%d,%d) = [%.4f,%.4f], want [%.4f,%.4f]", c.k, c.n, lo, hi, c.lo, c.hi)
		}
	}
}

// Ablasi dengan mengurangi poin harus identik dengan menilai ulang paket
// yang sama tetapi metadatanya diubah agar heuristik itu tidak terpicu.
// Dicek pada semua 256 kombinasi heuristik I-02..I-09, dengan bobot
// sembarang (bukan hanya bobot model yang sedang dipakai).
func TestWithoutMatchesRescoring(t *testing.T) {
	popular := []string{"requests"}
	now := time.Date(2025, 1, 1, 0, 0, 0, 0, time.UTC)
	m := scorer.Model{
		Name: "uji",
		Points: map[string]int{
			scorer.RuleNotRegistered: 100, scorer.RuleNew: 7, scorer.RuleSingleRelease: 11,
			scorer.RuleNoLinks: 13, scorer.RuleSimilarName: 17, scorer.RuleShortSummary: 5,
			scorer.RuleSdistOnly: 19, scorer.RuleShortDesc: 3, scorer.RuleNoClassifiers: 2,
		},
		Warn: 20, Danger: 40,
		Similarity: scorer.NewSimilarity(popular, 6, 2, false),
	}
	type input struct {
		name string
		meta registry.Metadata
	}
	bits := map[string]int{
		scorer.RuleNew: 1, scorer.RuleSingleRelease: 2, scorer.RuleNoLinks: 4, scorer.RuleShortSummary: 8,
		scorer.RuleSimilarName: 16, scorer.RuleSdistOnly: 32, scorer.RuleShortDesc: 64, scorer.RuleNoClassifiers: 128,
	}
	build := func(mask int) input {
		in := input{"unrelated-name", registry.Metadata{Exists: true, FirstRelease: now.AddDate(-1, 0, 0),
			ReleaseCount: 5, HasHomepage: true, Summary: "A long enough summary",
			DescriptionLen: 500, ClassifierCount: 3}}
		if mask&1 != 0 {
			in.meta.FirstRelease = now.Add(-time.Hour)
		}
		if mask&2 != 0 {
			in.meta.ReleaseCount = 1
		}
		if mask&4 != 0 {
			in.meta.HasHomepage = false
		}
		if mask&8 != 0 {
			in.meta.Summary = ""
		}
		if mask&16 != 0 {
			in.name = "reqeusts"
		}
		if mask&32 != 0 {
			in.meta.SdistOnly = true
		}
		if mask&64 != 0 {
			in.meta.DescriptionLen = 0
		}
		if mask&128 != 0 {
			in.meta.ClassifierCount = 0
		}
		return in
	}
	for mask := 0; mask < 256; mask++ {
		in := build(mask)
		sig := m.Signals(in.name, in.meta, now)
		r := labeledResult{Meta: in.meta, Signals: sig, V2: m.Score(sig)}
		for rule, bit := range bits {
			if got := len(sig.Fired) > 0 && sig.Fired[rule]; got != (mask&bit != 0) {
				t.Fatalf("mask %08b: %s fired=%v, construction wrong", mask, rule, got)
			}
			off := build(mask &^ bit)
			want := m.EvaluateAt(off.name, off.meta, now).Level != scorer.Safe
			if got := without(m, rule, scorer.Warning).flagged(r); got != want {
				t.Errorf("mask %08b without %s: got %v want %v", mask, rule, got, want)
			}
			wantB := m.EvaluateAt(off.name, off.meta, now).Level == scorer.Danger
			if got := without(m, rule, scorer.Danger).flagged(r); got != wantB {
				t.Errorf("mask %08b without %s (BAHAYA): got %v want %v", mask, rule, got, wantB)
			}
		}
	}
}

func TestRedactName(t *testing.T) {
	a, b := redactName("Some_Name"), redactName("some-name")
	if a != b || !strings.HasPrefix(a, "redacted-") || strings.Contains(a, "some") {
		t.Fatalf("redactName must be stable under normalisation and hide the name: %q %q", a, b)
	}
}
