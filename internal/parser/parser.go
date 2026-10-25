// Package parser extracts package names from pip arguments and requirements
// files and normalizes them per PEP 503.
package parser

import (
	"regexp"
	"strings"
)

var normalizeRe = regexp.MustCompile(`[-_.]+`)

// Normalize applies PEP 503 project-name normalization: lower case, with runs
// of "-", "_" and "." collapsed into "-".
func Normalize(name string) string {
	return strings.ToLower(normalizeRe.ReplaceAllString(name, "-"))
}

// valueOpts are pip options that take their value as a separate argument
// (e.g. "-r requirements.txt"); the value must be skipped, not taken for a
// package name.
var valueOpts = map[string]bool{
	"-r": true, "--requirement": true,
	"-c": true, "--constraint": true,
	"-i": true, "--index-url": true, "--extra-index-url": true,
	"-t": true, "--target": true,
	"--find-links": true, "-f": true,
	"--trusted-host": true,
	"--cache-dir":    true,
	"--root":         true,
	"--prefix":       true,
	"--src":          true,
	"--build":        true,
	"--log":          true,
}

// versionSeps are version and extras separators that may follow a package
// name directly, e.g. "requests[security]>=2.0".
var versionSeps = []string{"[", "==", ">=", "<=", "~=", "!=", ">", "<", "==="}

// ExtractPackages separates package names from pip options in the arguments
// that follow the subcommand.
func ExtractPackages(args []string) []string {
	var pkgs []string
	skipNext := false

	for _, a := range args {
		if skipNext {
			skipNext = false
			continue
		}
		if strings.HasPrefix(a, "-") {
			// "--option=value" carries its own value
			opt := a
			if i := strings.Index(a, "="); i != -1 {
				opt = a[:i]
			}
			if valueOpts[opt] && !strings.Contains(a, "=") {
				skipNext = true
			}
			continue
		}
		// skip local paths, URLs and VCS references (git+https://, ...)
		if strings.ContainsAny(a, "/\\") || strings.Contains(a, "://") {
			continue
		}
		// skip requirements, wheel and sdist files given without a path
		if strings.HasSuffix(a, ".txt") || strings.HasSuffix(a, ".whl") ||
			strings.HasSuffix(a, ".tar.gz") || strings.HasSuffix(a, ".zip") {
			continue
		}

		name := a
		for _, sep := range versionSeps {
			if i := strings.Index(name, sep); i != -1 {
				name = name[:i]
			}
		}
		if name = strings.TrimSpace(name); name != "" {
			pkgs = append(pkgs, name)
		}
	}
	return pkgs
}

// IndexOptions describes where pip will look for packages, from the command
// line and the PIP_INDEX_URL / PIP_EXTRA_INDEX_URL / PIP_NO_INDEX variables.
// (pip configuration files are not read.)
type IndexOptions struct {
	IndexURL      string // primary index; "" = PyPI
	ExtraIndexURL bool   // at least one --extra-index-url
	NoIndex       bool   // --no-index: only local paths and --find-links
}

// CustomPrimary reports whether the primary index is not PyPI.
func (o IndexOptions) CustomPrimary() bool {
	if o.IndexURL == "" {
		return false
	}
	u := strings.ToLower(o.IndexURL)
	return !strings.HasPrefix(u, "https://pypi.org/") && !strings.HasPrefix(u, "https://pypi.python.org/")
}

// ExtractIndexOptions reads the index-selection options of a pip command.
func ExtractIndexOptions(args []string, getenv func(string) string) IndexOptions {
	o := IndexOptions{
		IndexURL:      getenv("PIP_INDEX_URL"),
		ExtraIndexURL: getenv("PIP_EXTRA_INDEX_URL") != "",
		NoIndex:       isTrue(getenv("PIP_NO_INDEX")),
	}
	for i := 0; i < len(args); i++ {
		a := args[i]
		name, value, hasValue := strings.Cut(a, "=")
		next := func() string {
			if hasValue {
				return value
			}
			if i+1 < len(args) {
				i++
				return args[i]
			}
			return ""
		}
		switch name {
		case "-i", "--index-url":
			o.IndexURL = next()
		case "--extra-index-url":
			next()
			o.ExtraIndexURL = true
		case "--no-index":
			o.NoIndex = true
		default:
			if strings.HasPrefix(a, "-i") && len(a) > 2 && !strings.HasPrefix(a, "--") {
				o.IndexURL = a[2:] // "-ihttps://..."
			}
		}
	}
	return o
}

func isTrue(s string) bool {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "1", "true", "yes", "on":
		return true
	}
	return false
}

// CheckedSubcommands are the pip subcommands that fetch packages from an
// index and may build source distributions, which runs package code.
var CheckedSubcommands = map[string]bool{"install": true, "download": true, "wheel": true}

// Subcommand returns the pip subcommand and the index of its first
// argument, skipping general options placed before it (e.g. "pip -q install").
func Subcommand(args []string) (string, int) {
	for i := 0; i < len(args); i++ {
		a := args[i]
		if !strings.HasPrefix(a, "-") {
			return a, i + 1
		}
		// General options that take a separate value.
		switch a {
		case "--log", "--cache-dir", "--proxy", "--retries", "--timeout", "--exists-action",
			"--trusted-host", "--cert", "--client-cert", "--python", "--use-feature", "--use-deprecated":
			i++
		}
	}
	return "", len(args)
}
