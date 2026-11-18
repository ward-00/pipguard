package parser

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// maxRequirementDepth bounds chains of nested "-r" files.
const maxRequirementDepth = 10

// ExtractRequirementFiles returns the files given with "-r"/"--requirement".
// Constraint files ("-c") are excluded: they never make pip install a new
// package.
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
			files = append(files, strings.TrimPrefix(a, "-r")) // "-rreq.txt"
		}
	}
	return files
}

// ReadRequirements reads package names from a requirements file and the
// files it includes with "-r". On error it also returns the names read so
// far, so that the caller can stay fail-open.
func ReadRequirements(path string) ([]string, error) {
	var names []string
	err := readRequirements(path, 0, map[string]bool{}, &names)
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
		return nil // cycle
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
		if strings.HasSuffix(line, "\\") {
			cont.WriteString(strings.TrimSuffix(line, "\\"))
			cont.WriteString(" ")
			continue
		}
		cont.WriteString(line)
		line = cont.String()
		cont.Reset()

		// "#" starts a comment only at the start of a line or after whitespace.
		if i := strings.Index(line, "#"); i == 0 || (i > 0 && strings.ContainsAny(line[i-1:i], " \t")) {
			line = line[:i]
		}
		fields := strings.Fields(line)
		if len(fields) == 0 {
			continue
		}
		if strings.HasPrefix(fields[0], "-") {
			for _, n := range ExtractRequirementFiles(fields) {
				if !filepath.IsAbs(n) {
					n = filepath.Join(filepath.Dir(path), n)
				}
				if err := readRequirements(n, depth+1, seen, names); err != nil && firstErr == nil {
					firstErr = err
				}
			}
			continue
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

// nameFromSpec extracts the project name from one requirement, e.g.
// `requests[socks] >= 2.0 ; python_version < "3.8"`. Local paths, URLs,
// direct references ("name @ url") and archive files are not index packages.
func nameFromSpec(spec string) (string, bool) {
	spec = strings.TrimSpace(spec)
	if i := strings.Index(spec, ";"); i != -1 {
		spec = spec[:i]
	}
	if spec == "." || spec == ".." || strings.Contains(spec, "@") || strings.ContainsAny(spec, "/\\") {
		return "", false
	}
	name := spec
	for _, sep := range append([]string{" ", "\t"}, versionSeps...) {
		if i := strings.Index(name, sep); i != -1 {
			name = name[:i]
		}
	}
	name = strings.TrimSpace(name)
	for _, ext := range []string{".whl", ".tar.gz", ".zip", ".txt"} {
		if strings.HasSuffix(name, ext) {
			return "", false
		}
	}
	return name, name != ""
}
