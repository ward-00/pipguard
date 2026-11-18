package scorer

// levenshtein computes the edit distance with two rows instead of a matrix.
func levenshtein(a, b string) int {
	ra, rb := []rune(a), []rune(b)
	prev := make([]int, len(rb)+1)
	curr := make([]int, len(rb)+1)
	for j := range prev {
		prev[j] = j
	}
	for i := 1; i <= len(ra); i++ {
		curr[0] = i
		for j := 1; j <= len(rb); j++ {
			cost := 1
			if ra[i-1] == rb[j-1] {
				cost = 0
			}
			curr[j] = min3(curr[j-1]+1, prev[j]+1, prev[j-1]+cost)
		}
		prev, curr = curr, prev
	}
	return prev[len(rb)]
}

// osa is Levenshtein that also counts swapping two adjacent characters
// ("reqeusts") as one edit (optimal string alignment).
func osa(a, b string) int {
	ra, rb := []rune(a), []rune(b)
	pprev := make([]int, len(rb)+1)
	prev := make([]int, len(rb)+1)
	curr := make([]int, len(rb)+1)
	for j := range prev {
		prev[j] = j
	}
	for i := 1; i <= len(ra); i++ {
		curr[0] = i
		for j := 1; j <= len(rb); j++ {
			cost := 1
			if ra[i-1] == rb[j-1] {
				cost = 0
			}
			curr[j] = min3(curr[j-1]+1, prev[j]+1, prev[j-1]+cost)
			if i > 1 && j > 1 && ra[i-1] == rb[j-2] && ra[i-2] == rb[j-1] && pprev[j-2]+1 < curr[j] {
				curr[j] = pprev[j-2] + 1
			}
		}
		pprev, prev, curr = prev, curr, pprev
	}
	return prev[len(rb)]
}

func min3(a, b, c int) int {
	m := a
	if b < m {
		m = b
	}
	if c < m {
		m = c
	}
	return m
}

func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}

// Similarity configures the name-similarity indicator I-05.
type Similarity struct {
	Popular        []string
	MinLen         int // short names lie close to some popular name by chance ("mcp" vs "pip")
	MaxDist        int
	Transpositions bool // use osa instead of levenshtein
	set            map[string]bool
}

func NewSimilarity(popular []string, minLen, maxDist int, transpositions bool) *Similarity {
	s := &Similarity{Popular: popular, MinLen: minLen, MaxDist: maxDist, Transpositions: transpositions,
		set: make(map[string]bool, len(popular))}
	for _, p := range popular {
		s.set[p] = true
	}
	return s
}

// Match returns the closest popular name at distance 1..MaxDist. Popular
// names themselves are exempt ("psycopg" is not a typosquat of "psycopg2").
func (s *Similarity) Match(name string) (string, int, bool) {
	if len([]rune(name)) < s.MinLen || s.set[name] {
		return "", 0, false
	}
	dist := levenshtein
	if s.Transpositions {
		dist = osa
	}
	best, bestName := -1, ""
	for _, p := range s.Popular {
		if abs(len(name)-len(p)) > s.MaxDist {
			continue
		}
		if d := dist(name, p); best == -1 || d < best {
			best, bestName = d, p
		}
	}
	if best < 1 || best > s.MaxDist {
		return "", 0, false
	}
	return bestName, best, true
}
