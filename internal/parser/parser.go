// Package parser extracts package names from pip arguments and requirements
// files.
package parser

import (
	"regexp"
	"strings"
)

var normalizeRe = regexp.MustCompile(`[-_.]+`)

// Normalize applies PEP 503 project-name normalization.
func Normalize(name string) string {
	return strings.ToLower(normalizeRe.ReplaceAllString(name, "-"))
}

// generalValueOpts are pip general options whose value is a separate
// argument; they may precede the subcommand ("pip --proxy URL install x").
var generalValueOpts = map[string]bool{
	"--python": true, "--log": true, "--keyring-provider": true, "--proxy": true, "--retries": true,
	"--resume-retries": true, "--timeout": true, "--exists-action": true, "--trusted-host": true,
	"--cert": true, "--client-cert": true, "--cache-dir": true, "--use-feature": true, "--use-deprecated": true,
}

// valueOpts are the options of install, download and wheel whose value is a
// separate argument and must not be taken for a package name.
var valueOpts = map[string]bool{
	"-r": true, "--requirement": true, "-c": true, "--constraint": true, "-e": true, "--editable": true,
	"-i": true, "--index-url": true, "--extra-index-url": true, "-f": true, "--find-links": true,
	"-t": true, "--target": true, "-d": true, "--dest": true, "-w": true, "--wheel-dir": true,
	"--root": true, "--prefix": true, "--src": true, "--group": true, "--report": true,
	"--platform": true, "--python-version": true, "--implementation": true, "--abi": true,
	"--no-binary": true, "--only-binary": true, "-C": true, "--config-settings": true,
	"--global-option": true, "--build-option": true, "--upgrade-strategy": true,
	"--progress-bar": true, "--root-user-action": true,
}

var versionSeps = []string{"[", "==", ">=", "<=", "~=", "!=", ">", "<", "==="}

// ExtractPackages returns the package names among the arguments that follow
// the subcommand.
func ExtractPackages(args []string) []string {
	var pkgs []string
	for i := 0; i < len(args); i++ {
		a := args[i]
		if strings.HasPrefix(a, "-") {
			if !strings.Contains(a, "=") && (valueOpts[a] || generalValueOpts[a]) {
				i++
			}
			continue
		}
		if name, ok := nameFromSpec(a); ok {
			pkgs = append(pkgs, name)
		}
	}
	return pkgs
}

// IndexOptions describes where pip will look for packages, from the command
// line and the PIP_INDEX_URL / PIP_EXTRA_INDEX_URL / PIP_NO_INDEX variables.
type IndexOptions struct {
	IndexURL      string // "" = PyPI
	ExtraIndexURL bool
	NoIndex       bool
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

// CheckedSubcommands fetch packages from an index and may build source
// distributions, which runs package code.
var CheckedSubcommands = map[string]bool{"install": true, "download": true, "wheel": true}

// Subcommand returns the pip subcommand and the index of its first argument.
func Subcommand(args []string) (string, int) {
	for i := 0; i < len(args); i++ {
		a := args[i]
		if !strings.HasPrefix(a, "-") {
			return a, i + 1
		}
		if generalValueOpts[a] {
			i++
		}
	}
	return "", len(args)
}
