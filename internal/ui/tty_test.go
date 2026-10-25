package ui

import (
	"encoding/json"
	"os"
	"strings"
	"testing"

	"github.com/ward-00/pipguard/internal/scorer"
)

func TestDevNullIsNotTerminal(t *testing.T) {
	f, err := os.Open(os.DevNull)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	if isTerminal(f) {
		t.Fatal("/dev/null must not be treated as an interactive terminal")
	}
}

func TestPipeIsNotTerminal(t *testing.T) {
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatal(err)
	}
	defer r.Close()
	defer w.Close()
	if isTerminal(r) {
		t.Fatal("a pipe must not be treated as an interactive terminal")
	}
}

func TestNonInteractiveBlocksWithJSON(t *testing.T) {
	var out strings.Builder
	r := scorer.Result{Score: 100, Level: scorer.Danger, Reasons: []string{"The package is not registered on PyPI"},
		Hits: []scorer.Hit{{Rule: scorer.RuleNotRegistered, Points: 100}}}
	if confirm(&out, strings.NewReader("y\n"), false, "zzz-x", r, false, nil) {
		t.Fatal("non-interactive confirmation must cancel")
	}
	var d Decision
	for _, line := range strings.Split(out.String(), "\n") {
		if strings.HasPrefix(line, "pipguard: {") {
			if err := json.Unmarshal([]byte(strings.TrimPrefix(line, "pipguard: ")), &d); err != nil {
				t.Fatal(err)
			}
		}
	}
	if d.Decision != "blocked" || d.Package != "zzz-x" || d.Level != "DANGER" || d.Exit != ExitBlocked {
		t.Fatalf("bad decision record: %+v\n%s", d, out.String())
	}
}

func TestInteractiveDefaultIsNo(t *testing.T) {
	r := scorer.Result{Score: 50, Level: scorer.Warning}
	var out strings.Builder
	if confirm(&out, strings.NewReader("\n"), true, "x", r, false, nil) {
		t.Fatal("pressing Enter must cancel")
	}
	if !confirm(&out, strings.NewReader("y\n"), true, "x", r, false, nil) {
		t.Fatal("answering y must continue")
	}
}
