package parser

import (
	"reflect"
	"testing"
)

func TestNormalize(t *testing.T) {
	cases := map[string]string{
		"Requests":         "requests",
		"python_dateutil":  "python-dateutil",
		"Flask.SQLAlchemy": "flask-sqlalchemy",
		"a---b__c...d":     "a-b-c-d",
	}
	for in, want := range cases {
		if got := Normalize(in); got != want {
			t.Errorf("Normalize(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestExtractPackages(t *testing.T) {
	cases := []struct {
		args []string
		want []string
	}{
		{[]string{"requests"}, []string{"requests"}},
		{[]string{"requests==2.31.0"}, []string{"requests"}},
		{[]string{"requests[security]>=2.0"}, []string{"requests"}},
		{[]string{"-r", "requirements.txt", "requests"}, []string{"requests"}},
		{[]string{"--index-url", "https://example.com/simple", "requests"}, []string{"requests"}},
		{[]string{"./local/path"}, []string{}},
		{[]string{"git+https://github.com/foo/bar.git"}, []string{}},
		{[]string{"requests", "flask"}, []string{"requests", "flask"}},
	}
	for _, c := range cases {
		got := ExtractPackages(c.args)
		if len(got) == 0 && len(c.want) == 0 {
			continue
		}
		if !reflect.DeepEqual(got, c.want) {
			t.Errorf("ExtractPackages(%v) = %v, want %v", c.args, got, c.want)
		}
	}
}

func TestExtractIndexOptions(t *testing.T) {
	env := map[string]string{}
	getenv := func(k string) string { return env[k] }
	if o := ExtractIndexOptions([]string{"requests"}, getenv); o.CustomPrimary() || o.ExtraIndexURL || o.NoIndex {
		t.Fatalf("plain install: %+v", o)
	}
	if o := ExtractIndexOptions([]string{"-i", "https://pkgs.corp.example/simple", "x"}, getenv); !o.CustomPrimary() {
		t.Fatalf("-i must select a custom index: %+v", o)
	}
	if o := ExtractIndexOptions([]string{"--index-url=https://pypi.org/simple", "x"}, getenv); o.CustomPrimary() {
		t.Fatalf("explicit PyPI is not custom: %+v", o)
	}
	if o := ExtractIndexOptions([]string{"--extra-index-url", "https://x/simple", "y"}, getenv); !o.ExtraIndexURL {
		t.Fatalf("extra index not detected: %+v", o)
	}
	if o := ExtractIndexOptions([]string{"--no-index", "--find-links", "./w", "y"}, getenv); !o.NoIndex {
		t.Fatalf("--no-index not detected: %+v", o)
	}
	env["PIP_INDEX_URL"] = "https://mirror.example/simple"
	if o := ExtractIndexOptions([]string{"y"}, getenv); !o.CustomPrimary() {
		t.Fatalf("PIP_INDEX_URL ignored: %+v", o)
	}
}

func TestSubcommand(t *testing.T) {
	cases := []struct {
		args []string
		cmd  string
		rest int
	}{
		{[]string{"install", "x"}, "install", 1},
		{[]string{"-q", "install", "x"}, "install", 2},
		{[]string{"--log", "f.txt", "download", "x"}, "download", 3},
		{[]string{"--version"}, "", 1},
	}
	for _, c := range cases {
		if cmd, rest := Subcommand(c.args); cmd != c.cmd || rest != c.rest {
			t.Errorf("Subcommand(%v) = %q,%d want %q,%d", c.args, cmd, rest, c.cmd, c.rest)
		}
	}
}
