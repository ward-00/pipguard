// Package popular parses the list of popular package names used by the
// name-similarity indicator I-05.
package popular

import (
	"bufio"
	"strings"

	"github.com/ward-00/pipguard/internal/parser"
)

// Parse reads one name per line, skipping empty lines and "#" comments.
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
