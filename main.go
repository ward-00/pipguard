// Command pipguard is a pip shim that checks the risk of requested packages
// (new or unregistered projects, reactivated releases, typosquatting and
// slopsquatting) before forwarding the command to the real pip.
//
// See build_guide.md for the architecture.
package main

import (
	_ "embed"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"syscall"

	"github.com/ward-00/pipguard/internal/cache"
	"github.com/ward-00/pipguard/internal/config"
	"github.com/ward-00/pipguard/internal/logger"
	"github.com/ward-00/pipguard/internal/parser"
	"github.com/ward-00/pipguard/internal/popular"
	"github.com/ward-00/pipguard/internal/registry"
	"github.com/ward-00/pipguard/internal/scorer"
	"github.com/ward-00/pipguard/internal/ui"
)

//go:embed assets/popular_v2.txt
var popularRaw string

// findRealPip walks PATH and returns the first pip that is NOT this shim,
// to avoid infinite recursion.
//
// Other pipguard copies (e.g. a second installation on PATH) are skipped as
// well; otherwise two copies would forward to each other forever.
func findRealPip(cmdName string) (string, error) {
	self, err := os.Executable()
	if err == nil {
		if resolved, err := filepath.EvalSymlinks(self); err == nil {
			self = resolved
		}
	}

	for _, dir := range filepath.SplitList(os.Getenv("PATH")) {
		if dir == "" {
			continue
		}
		candidate := filepath.Join(dir, cmdName)
		info, err := os.Stat(candidate)
		if err != nil || info.IsDir() || info.Mode()&0o111 == 0 {
			continue
		}
		resolved, err := filepath.EvalSymlinks(candidate)
		if err != nil {
			resolved = candidate
		}
		if (self != "" && resolved == self) || filepath.Base(resolved) == "pipguard" {
			continue // skip ourselves and other pipguard copies
		}
		return candidate, nil
	}
	return "", os.ErrNotExist
}

// forwardToPip replaces the pipguard process with the real pip through
// syscall.Exec, so that signals and the exit status pass through unchanged.
// It does not return on success.
func forwardToPip(pipPath string, args []string) error {
	argv := append([]string{pipPath}, args...)
	return syscall.Exec(pipPath, argv, os.Environ())
}

// pipCommandName returns the name of the real pip to look for: the name the
// shim was invoked as ("pip", "pip3", "pip3.12"), or "pip" when the binary
// was invoked under another name (e.g. directly as "pipguard").
func pipCommandName(argv0 string) string {
	if base := filepath.Base(argv0); strings.HasPrefix(base, "pip") && base != "pipguard" {
		return base
	}
	return "pip"
}

func main() {
	args := os.Args[1:]
	cmdName := pipCommandName(os.Args[0])

	cfg := config.Load()

	realPip, err := findRealPip(cmdName)
	if err != nil {
		fmt.Fprintln(os.Stderr, "pipguard: the real pip was not found on PATH")
		os.Exit(127)
	}

	sub, rest := parser.Subcommand(args)
	// Disabled, or a subcommand that does not fetch packages: forward unchecked.
	if cfg.Disabled || !parser.CheckedSubcommands[sub] {
		forward(realPip, args)
	}
	if cfg.EnvOverrideIgnored() {
		fmt.Fprintln(os.Stderr, "pipguard: PIPGUARD_ASSUME_YES/PIPGUARD_DISABLE ignored "+
			"(set \"allow_env_override\": true in the configuration file to honour them)")
	}

	opts := parser.ExtractIndexOptions(args[rest:], os.Getenv)
	if opts.CustomPrimary() && !opts.ExtraIndexURL && !cfg.CheckCustomIndex {
		// PyPI metadata does not describe packages served by another index.
		// (--no-index with --find-links is still checked: the requested names
		// are usually PyPI names, and an allowlist covers private ones.)
		fmt.Fprintln(os.Stderr, "pipguard: packages come from a non-PyPI source (custom --index-url); not checked")
		forward(realPip, args)
	}
	var notes []string
	if opts.ExtraIndexURL {
		notes = append(notes, "an extra index is in use; pip may take this name from either index "+
			"(dependency confusion)")
	}

	dormancy := scorer.V3DormancyDays
	if cfg.ReleaseDormancyDays > 0 {
		dormancy = cfg.ReleaseDormancyDays
	}
	model := scorer.V3(popular.Parse(popularRaw), dormancy)

	cachePath, err := cache.DefaultPath()
	var c *cache.Cache
	if err != nil {
		// Without a valid cache location, continue without a cache
		// (fail-open): every package goes to the network.
		c = cache.Load(os.DevNull)
	} else {
		c = cache.Load(cachePath)
	}

	pkgs := parser.ExtractPackages(args[rest:])
	// Packages listed in "-r requirements.txt" files are checked too. A file
	// that cannot be read does not stop the check (fail-open); pip itself
	// will report the error.
	for _, f := range parser.ExtractRequirementFiles(args[rest:]) {
		names, err := parser.ReadRequirements(f)
		if err != nil {
			fmt.Fprintf(os.Stderr, "pipguard: could not fully read %q (%v); continuing with the rest\n", f, err)
		}
		pkgs = append(pkgs, names...)
	}

	allowed := map[string]bool{}
	for _, a := range cfg.Allow {
		allowed[parser.Normalize(a)] = true
	}
	checked := map[string]bool{}
	for _, p := range pkgs {
		norm := parser.Normalize(p)
		if checked[norm] || allowed[norm] {
			continue
		}
		checked[norm] = true

		meta, err := c.GetOrFetch(norm, registry.Fetch)
		if err != nil {
			// FAIL-OPEN: network or internal failures must not block installation.
			fmt.Fprintf(os.Stderr, "pipguard: could not check %q (%v); installation continues\n", p, err)
			continue
		}

		res := model.Evaluate(norm, meta)
		logger.Record(norm, res)

		if res.Level != scorer.Safe {
			if !ui.Confirm(p, res, cfg.AssumeYes, notes) {
				fmt.Fprintln(os.Stderr, "Installation cancelled.")
				_ = c.Save()
				os.Exit(ui.ExitBlocked)
			}
		}
	}

	_ = c.Save()
	forward(realPip, args)
}

// forward hands the command to the real pip and never returns.
func forward(realPip string, args []string) {
	if err := forwardToPip(realPip, args); err != nil {
		fmt.Fprintf(os.Stderr, "pipguard: could not run pip (%v)\n", err)
		os.Exit(126)
	}
	os.Exit(0) // not reached when Exec succeeds
}
