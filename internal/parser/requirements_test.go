package parser

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

func TestExtractRequirementFiles(t *testing.T) {
	cases := []struct {
		args []string
		want []string
	}{
		{[]string{"-r", "req.txt"}, []string{"req.txt"}},
		{[]string{"--requirement", "a.txt", "flask", "-r", "b.txt"}, []string{"a.txt", "b.txt"}},
		{[]string{"--requirement=req.txt"}, []string{"req.txt"}},
		{[]string{"-rreq.txt"}, []string{"req.txt"}},
		{[]string{"-c", "constraints.txt", "requests"}, nil},
		{[]string{"requests"}, nil},
	}
	for _, c := range cases {
		if got := ExtractRequirementFiles(c.args); !reflect.DeepEqual(got, c.want) {
			t.Errorf("ExtractRequirementFiles(%v) = %v, want %v", c.args, got, c.want)
		}
	}
}

func write(t *testing.T, dir, name, content string) string {
	t.Helper()
	p := filepath.Join(dir, name)
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(p, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	return p
}

func TestReadRequirements(t *testing.T) {
	dir := t.TempDir()
	write(t, dir, "sub/base.txt", "numpy>=1.26\n-r main.txt  # siklus kembali ke induk\n")
	main := write(t, dir, "sub/main.txt", `# komentar penuh
requests[socks] >= 2.0 ; python_version < "3.8"
Flask==3.0.0 --hash=sha256:abcdef \
    --hash=sha256:012345
-r base.txt
--index-url https://example.com/simple
-c constraints.txt
-e git+https://github.com/foo/bar.git#egg=bar
./local/pkg
pkg @ https://example.com/pkg-1.0.tar.gz
https://example.com/other-1.0.whl
pandas  # komentar sebaris
`)
	got, err := ReadRequirements(main)
	if err != nil {
		t.Fatalf("ReadRequirements: %v", err)
	}
	want := []string{"requests", "Flask", "numpy", "pandas"}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("ReadRequirements = %v, want %v", got, want)
	}
}

func TestReadRequirementsMissingNested(t *testing.T) {
	dir := t.TempDir()
	main := write(t, dir, "req.txt", "requests\n-r tidak-ada.txt\nflask\n")
	got, err := ReadRequirements(main)
	if err == nil {
		t.Error("berkas bersarang yang hilang harus dilaporkan sebagai error")
	}
	if want := []string{"requests", "flask"}; !reflect.DeepEqual(got, want) {
		t.Errorf("nama yang sudah terbaca harus tetap dikembalikan: %v, want %v", got, want)
	}
}

func TestReadRequirementsMissingFile(t *testing.T) {
	if _, err := ReadRequirements(filepath.Join(t.TempDir(), "tidak-ada.txt")); err == nil {
		t.Error("berkas yang tidak ada harus menghasilkan error")
	}
}
