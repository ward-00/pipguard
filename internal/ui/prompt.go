// Package ui shows package security warnings and asks the user for
// confirmation before the installation continues.
package ui

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/ward-00/pipguard/internal/scorer"
)

// ExitBlocked is the exit status when pipguard cancels a command, distinct
// from pip's own statuses (1 = error, 2 = usage) so that scripts, CI jobs
// and AI coding agents can tell a security stop from a failed installation.
const ExitBlocked = 3

// Decision is the machine-readable record printed on stderr when no
// terminal is available, as one JSON line prefixed with "pipguard: ".
type Decision struct {
	Tool     string   `json:"tool"`
	Decision string   `json:"decision"` // "blocked"
	Package  string   `json:"package"`
	Level    string   `json:"level"`
	Score    int      `json:"score"`
	Reasons  []string `json:"reasons"`
	Advice   string   `json:"advice"`
	Exit     int      `json:"exit_status"`
}

// Confirm prints the risk summary for package "name" on stderr (so that it
// does not mix with pip's standard output) and asks for Y/N confirmation.
// Without an interactive terminal on stdin the installation is cancelled,
// unless assumeYes is set by the configuration.
func Confirm(name string, r scorer.Result, assumeYes bool, notes []string) bool {
	return confirm(os.Stderr, os.Stdin, isTerminal(os.Stdin), name, r, assumeYes, notes)
}

func confirm(w io.Writer, in io.Reader, interactive bool, name string, r scorer.Result, assumeYes bool, notes []string) bool {
	fmt.Fprintln(w, strings.Repeat("─", 60))
	fmt.Fprintln(w, "PACKAGE SECURITY WARNING")
	fmt.Fprintf(w, "Package : %s\n", name)
	fmt.Fprintf(w, "Level   : %s (score %d)\n", r.Level, r.Score)
	fmt.Fprintln(w)
	fmt.Fprintln(w, "Reasons:")
	for _, reason := range r.Reasons {
		fmt.Fprintf(w, "  - %s\n", reason)
	}
	fmt.Fprintln(w)
	advice := adviceFor(r)
	for _, line := range strings.Split(advice, "\n") {
		fmt.Fprintln(w, line)
	}
	for _, n := range notes {
		fmt.Fprintf(w, "Note: %s\n", n)
	}
	fmt.Fprintln(w, strings.Repeat("─", 60))

	if assumeYes {
		fmt.Fprintln(w, "[assume_yes] Continuing without confirmation.")
		return true
	}

	// Non-interactive context (CI, scripts, AI agents): cancel by default
	// and leave a machine-readable record of why.
	if !interactive {
		fmt.Fprintln(w, "[non-interactive] Installation cancelled.")
		d := Decision{Tool: "pipguard", Decision: "blocked", Package: name, Level: r.Level.String(),
			Score: r.Score, Reasons: r.Reasons, Exit: ExitBlocked,
			Advice: "Ask a human to verify the package name and source. To approve it permanently, " +
				"add it to the \"allow\" list in the pipguard configuration file."}
		if line, err := json.Marshal(d); err == nil {
			fmt.Fprintf(w, "pipguard: %s\n", line)
		}
		return false
	}

	fmt.Fprint(w, "Continue installation? [y/N]: ")
	line, _ := bufio.NewReader(in).ReadString('\n')
	answer := strings.ToLower(strings.TrimSpace(line))
	return answer == "y" || answer == "yes"
}

func adviceFor(r scorer.Result) string {
	for _, h := range r.Hits {
		switch h.Rule {
		case scorer.RuleNotRegistered:
			return "An unregistered package may be a hallucinated name that an attacker\n" +
				"could later register (slopsquatting)."
		case scorer.RuleReactivated:
			return "A sudden release after a long silence can indicate a compromised or\n" +
				"re-purposed project; check the release notes and the source repository."
		}
	}
	return "A newly published package has not yet been reviewed by the community;\n" +
		"verify its name and source before continuing."
}
