# Third-party code and data

The package-hallucination probe in this directory reuses code and prompt datasets from
Spracklen et al., *We have a package for you! A comprehensive analysis of package hallucinations by code
generating LLMs* (USENIX Security 2025), https://github.com/Spracks/PackageHallucination, which its
README (`UPSTREAM_README.md`) releases under the MIT License. Files taken from that repository
(`generate_code.py` and `generate_package_names.py` adapted to local models):
`package_detection.py`, `custom_parse_python.py`, `custom_parse_javascript.py`, `generate_code.py`,
`generate_package_names.py`, `aggregate_results.py`, `run_test.py` and `Data/Python/`.

Model weights (`Models/`) and the raw model outputs (`Tests/`) are not distributed; the outputs contain
package names that are not registered on PyPI.
