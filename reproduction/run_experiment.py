"""Driver reproduksi metodologi Spracklen et al. (USENIX Security 2025) untuk
Python, dalam skala kecil yang layak dijalankan di CPU.

Alur sama persis dengan run_test.py upstream:
  1. generate_code          : LLM menulis kode untuk setiap prompt
  2. aggregate_results      : kode digabung dengan prompt
  3. generate_package_names : LLM mendaftar paket dari kode (mode 1) dan
                              dari prompt (mode 2)
  4. package_detection      : paket dicocokkan dengan daftar master PyPI

Perbedaan dari upstream (lihat README.md di folder ini):
  - hanya sampel acak berbenih (seeded) N prompt per dataset
  - dijalankan di CPU, bfloat16 (device_map="cpu")
  - model tunggal: DeepSeek-Coder 1.3B instruct, dinamai DeepSeek_1B agar
    aturan pasca-proses upstream ("Deep" → DeepSeek) berlaku
"""
import argparse
import logging
import os
import random
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

DATASETS = {
    "LLM_Recent": "LLM_LY.json",
    "LLM_All_Time": "LLM_AT.json",
    "Stack_Overflow_Recent": "SO_LY.json",
    "Stack_Overflow_All_Time": "SO_AT.json",
}


def make_subset(n, seed):
    """Tulis sampel acak berbenih ke Data/Python_subset (format baris JSON sama)."""
    src_dir = os.path.join(HERE, "Data", "Python")
    dst_dir = os.path.join(HERE, "Data", "Python_subset")
    os.makedirs(dst_dir, exist_ok=True)
    for name in ("pypi_package_names.csv", "false_positive_packages.csv"):
        shutil.copy(os.path.join(src_dir, name), os.path.join(dst_dir, name))
    rng = random.Random(seed)
    for _, fname in DATASETS.items():
        with open(os.path.join(src_dir, fname), encoding="utf-8") as f:
            lines = [ln for ln in f if ln.strip()]
        picked = rng.sample(lines, min(n, len(lines)))
        with open(os.path.join(dst_dir, fname), "w", encoding="utf-8") as f:
            f.writelines(picked)
        logging.info("subset %s: %d dari %d prompt", fname, len(picked), len(lines))
    return dst_dir


def is_complete(path, expected):
    """Berkas keluaran dianggap selesai hanya bila jumlah barisnya penuh.

    Skrip upstream menulis baris demi baris, sehingga proses yang terhenti
    (mis. perangkat mati) meninggalkan berkas parsial. Berkas parsial dihapus
    agar dibangkitkan ulang, bukan dilewati diam-diam.
    """
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as f:
        n = sum(1 for ln in f if ln.strip())
    if n == expected:
        return True
    logging.warning("berkas parsial (%d/%d baris), dihapus: %s", n, expected, path)
    os.remove(path)
    return False


def count_lines(path):
    with open(path, encoding="utf-8") as f:
        return sum(1 for ln in f if ln.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default=os.path.join(HERE, "Models", "DeepSeek_1B"))
    ap.add_argument("--model-name", default="DeepSeek_1B")
    ap.add_argument("--n", type=int, default=25, help="prompt per dataset")
    ap.add_argument("--seed", type=int, default=20250101)
    ap.add_argument("--code-temp", type=float, default=0.7)
    ap.add_argument("--package-temp", type=float, default=0.01)
    ap.add_argument("--top-k", type=int, default=20)
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument("--stage", choices=["all", "generate", "detect"], default="all")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    import generate_code
    import generate_package_names
    import aggregate_results
    import package_detection

    data_path = make_subset(args.n, args.seed)
    save_path = os.path.join(HERE, "Tests", f"{args.model_name}_Python")
    os.makedirs(save_path, exist_ok=True)

    if args.stage in ("all", "generate"):
        for key, fname in DATASETS.items():
            input_path = os.path.join(data_path, fname)
            output_code = os.path.join(save_path, f"{key}_code.json")
            master_output = os.path.join(save_path, f"{key}_Master.json")
            expected = count_lines(input_path)
            if is_complete(master_output, expected):
                logging.info("sudah ada: %s, dilewati", master_output)
                continue
            if not is_complete(output_code, expected):
                logging.info("generate kode: %s", key)
                generate_code.generate_code(input_path, output_code, args.model_dir,
                                            "Python", args.code_temp, args.top_k, args.top_p)
            if "LLM" in key:
                aggregate_results.combine_code_and_prompt(input_path, output_code, master_output)
            else:
                aggregate_results.combine_SO_prompt_and_code(input_path, output_code, master_output)

        for mode in range(1, 3):
            for key in DATASETS:
                master_path = os.path.join(save_path, f"{key}_Master.json")
                output = os.path.join(save_path, f"{key}_packages_{mode}.json")
                if is_complete(output, count_lines(master_path)):
                    continue
                logging.info("query paket mode %d: %s", mode, key)
                generate_package_names.generate_packages(mode, master_path, output, args.model_dir,
                                                         "Python", args.package_temp, args.top_k, args.top_p)

    if args.stage in ("all", "detect"):
        package_detection.detect_packages(data_path, save_path, args.model_name, "verbose", "Python")
        logging.info("selesai: hasil di %s", save_path)


if __name__ == "__main__":
    main()
