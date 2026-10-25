// Package popular parses a list of popular package names (e.g.
// assets/popular.txt) into normalized names for the name-similarity check
// (typosquatting) in internal/scorer.
//
// It is separate from main.go so that other tools (cmd/evalset) can reuse it
// without go:embed, which cannot cross package directories.
package popular

import (
	"bufio"
	"strings"

	"github.com/ward-00/pipguard/internal/parser"
)

// Parse reads a popular-list file: one name per line; empty lines and lines
// starting with "#" are ignored. Every name is normalized per PEP 503.
func Parse(raw string) []string {
	var list []string
	sc := bufio.NewScanner(strings.NewReader(raw))
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		list = append(list, parser.Normalize(line))
	}
	return list
}
