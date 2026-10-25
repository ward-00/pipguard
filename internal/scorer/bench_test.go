package scorer

import (
	"encoding/json"
	"fmt"
	"os"
	"testing"
)

// BenchmarkSimilarityMatch mengukur biaya I-05 per paket untuk beberapa
// ukuran daftar rujukan (daftar teratas beku di testdata/frozen/raw).
func BenchmarkSimilarityMatch(b *testing.B) {
	raw, err := os.ReadFile("../../testdata/frozen/raw/top_pypi_packages.json")
	if err != nil {
		b.Skip("daftar teratas beku tidak ada")
	}
	var top struct {
		Rows []struct {
			Project string `json:"project"`
		} `json:"rows"`
	}
	if err := json.Unmarshal(raw, &top); err != nil {
		b.Fatal(err)
	}
	var names []string
	for _, r := range top.Rows {
		names = append(names, r.Project)
	}
	for _, n := range []int{331, 1000, 2000, 5000} {
		s := NewSimilarity(names[:n], 6, 2, true)
		b.Run(fmt.Sprintf("list=%d", n), func(b *testing.B) {
			for i := 0; i < b.N; i++ {
				s.Match("python-dateutl")
			}
		})
	}
}
