// Command pipguard is a pip shim that checks requested packages on PyPI
// before forwarding the command to the real pip.
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

// findRealPip returns the first pip on PATH that is not a pipguard copy;
// forwarding to another copy would recurse forever.
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
			continue
		}
		return candidate, nil
	}
	return "", os.ErrNotExist
}

// pipCommandName returns the pip name the shim was invoked as ("pip3",
// "pip3.12"), or "pip" when it was invoked as "pipguard".
func pipCommandName(argv0 string) string {
	if base := filepath.Base(argv0); strings.HasPrefix(base, "pip") && base != "pipguard" {
		return base
	}
	return "pip"
}

func main() {
	args := os.Args[1:]
	cfg := config.Load()

	realPip, err := findRealPip(pipCommandName(os.Args[0]))
	if err != nil {
		fmt.Fprintln(os.Stderr, "pipguard: the real pip was not found on PATH")
		os.Exit(127)
	}

	sub, rest := parser.Subcommand(args)
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
	if err != nil {
		cachePath = os.DevNull
	}
	c := cache.Load(cachePath)

	pkgs := parser.ExtractPackages(args[rest:])
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
			// Fail-open: a network or registry failure must not block installation.
			fmt.Fprintf(os.Stderr, "pipguard: could not check %q (%v); installation continues\n", p, err)
			continue
		}
		res := model.Evaluate(norm, meta)
		logger.Record(norm, res)
		if res.Level != scorer.Safe && !ui.Confirm(p, res, cfg.AssumeYes, notes) {
			fmt.Fprintln(os.Stderr, "Installation cancelled.")
			_ = c.Save()
			os.Exit(ui.ExitBlocked)
		}
	}

	_ = c.Save()
	forward(realPip, args)
}

// forward replaces this process with the real pip, so that signals and the
// exit status pass through unchanged. It never returns.
func forward(realPip string, args []string) {
	err := syscall.Exec(realPip, append([]string{realPip}, args...), os.Environ())
	fmt.Fprintf(os.Stderr, "pipguard: could not run pip (%v)\n", err)
	os.Exit(126)
}
