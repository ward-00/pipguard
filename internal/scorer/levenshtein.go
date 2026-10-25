package scorer

// levenshtein computes the edit distance between two strings with two rows
// of memory instead of a full matrix.
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

// osa computes the optimal string alignment distance (restricted
// Damerau-Levenshtein): Levenshtein plus the swap of two adjacent characters
// ("reqeusts" vs "requests") as a single operation.
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

// Similarity configures the name-similarity indicator (I-05).
type Similarity struct {
	Popular        []string // normalized popular names
	MinLen         int      // shorter names are not assessed
	MaxDist        int      // maximum distance considered similar
	Transpositions bool     // use OSA instead of Levenshtein
	set            map[string]bool
}

// NewSimilarity prepares an I-05 configuration.
//
// minLen exists because short names are within a distance of two of one of
// hundreds of popular names by chance (e.g. "mcp" vs "pip", "jedi" vs
// "redis"); see testdata/ACCURACY_NOTES.md, finding 2.
func NewSimilarity(popular []string, minLen, maxDist int, transpositions bool) *Similarity {
	s := &Similarity{Popular: popular, MinLen: minLen, MaxDist: maxDist, Transpositions: transpositions,
		set: make(map[string]bool, len(popular))}
	for _, p := range popular {
		s.set[p] = true
	}
	return s
}

// Match returns the closest popular name when "name" is long enough, is not
// itself popular, and lies at distance 1..MaxDist from it.
//
// Names on the popular list are exempt: a popular package is not a typosquat
// of another popular package, even if the names are similar
// (e.g. "psycopg" vs "psycopg2").
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
		// A length difference above MaxDist implies a distance above
		// MaxDist; skip without computing it.
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
