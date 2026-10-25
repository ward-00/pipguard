package parser

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// maxRequirementDepth bounds chains of nested "-r" files, as a guard
// against cycles.
const maxRequirementDepth = 10

// ExtractRequirementFiles returns the files given with "-r"/"--requirement".
// Constraint files ("-c") are deliberately excluded: constraints only limit
// versions and never make pip install a new package.
func ExtractRequirementFiles(args []string) []string {
	var files []string
	for i := 0; i < len(args); i++ {
		a := args[i]
		switch {
		case a == "-r" || a == "--requirement":
			if i+1 < len(args) {
				files = append(files, args[i+1])
				i++
			}
		case strings.HasPrefix(a, "--requirement="):
			files = append(files, strings.TrimPrefix(a, "--requirement="))
		case strings.HasPrefix(a, "-r") && !strings.HasPrefix(a, "--"):
			files = append(files, strings.TrimPrefix(a, "-r")) // the "-rreq.txt" form
		}
	}
	return files
}

// ReadRequirements reads package names from a pip requirements file,
// including files included with "-r" (relative to the including file).
// Lines that do not name an index package ("-e", local paths, URLs and PEP 508
// direct references "name @ url") are skipped, as on the command line.
//
// Errors are returned together with the names read so far; the caller (main)
// applies fail-open: an unreadable file does not stop the other checks, and
// pip itself reports the error.
func ReadRequirements(path string) ([]string, error) {
	var names []string
	seen := map[string]bool{}
	err := readRequirements(path, 0, seen, &names)
	return names, err
}

func readRequirements(path string, depth int, seen map[string]bool, names *[]string) error {
	if depth > maxRequirementDepth {
		return fmt.Errorf("requirements: -r chain too deep at %q", path)
	}
	abs, err := filepath.Abs(path)
	if err != nil {
		return err
	}
	if seen[abs] {
		return nil // cycle: this file was already read
	}
	seen[abs] = true

	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()

	var firstErr error
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 0, 64*1024), 1024*1024)
	var cont strings.Builder
	for sc.Scan() {
		line := sc.Text()
		// Line continuation with a trailing "\".
		if strings.HasSuffix(line, "\\") {
			cont.WriteString(strings.TrimSuffix(line, "\\"))
			cont.WriteString(" ")
			continue
		}
		cont.WriteString(line)
		line = cont.String()
		cont.Reset()

		// Comment: "#" at the start of a line or after whitespace.
		if i := strings.Index(line, "#"); i == 0 || (i > 0 && strings.ContainsAny(line[i-1:i], " \t")) {
			line = line[:i]
		}
		fields := strings.Fields(line)
		if len(fields) == 0 {
			continue
		}

		if strings.HasPrefix(fields[0], "-") {
			if nested := ExtractRequirementFiles(fields); len(nested) > 0 {
				for _, n := range nested {
					if !filepath.IsAbs(n) {
						n = filepath.Join(filepath.Dir(path), n)
					}
					if err := readRequirements(n, depth+1, seen, names); err != nil && firstErr == nil {
						firstErr = err
					}
				}
			}
			continue // other options (-e, -c, -i, --hash, ...) are not package names
		}
		if name, ok := nameFromSpec(line); ok {
			*names = append(*names, name)
		}
	}
	if err := sc.Err(); err != nil && firstErr == nil {
		firstErr = err
	}
	return firstErr
}

// nameFromSpec extracts the project name from one PEP 508 requirement,
// e.g. `requests[socks] >= 2.0 ; python_version < "3.8" --hash=sha256:...`.
func nameFromSpec(spec string) (string, bool) {
	spec = strings.TrimSpace(spec)
	if i := strings.Index(spec, ";"); i != -1 { // environment marker
		spec = spec[:i]
	}
	if strings.Contains(spec, "@") || strings.Contains(spec, "://") ||
		strings.ContainsAny(spec, "/\\") {
		return "", false // direct reference, URL or local path
	}
	name := spec
	for _, sep := range append([]string{" ", "\t"}, versionSeps...) {
		if i := strings.Index(name, sep); i != -1 {
			name = name[:i]
		}
	}
	name = strings.TrimSpace(name)
	if name == "" || strings.HasSuffix(name, ".whl") || strings.HasSuffix(name, ".tar.gz") || strings.HasSuffix(name, ".zip") {
		return "", false
	}
	return name, true
}
