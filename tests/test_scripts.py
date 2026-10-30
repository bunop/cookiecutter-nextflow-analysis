import csv
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent.parent / "{{cookiecutter.project_slug}}" / "scripts"


def run(script, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *map(str, args)],
        capture_output=True, text=True)


def test_batches_are_balanced(tmp_path):
    sizes = {"s1": 100, "s2": 90, "s3": 10, "s4": 10}

    sheet = tmp_path / "sheet.csv"
    sheet.write_text("sample,fastq_1\n" + "".join(f"{s},{s}.fq.gz\n" for s in sizes))

    stats = tmp_path / "stats.tsv"
    stats.write_text("file\tsum_len\n" + "".join(f"{s}.fq.gz\t{n}\n" for s, n in sizes.items()))

    result = run("divide_samples_in_batches.py", "--samplesheet", sheet, "--stats", stats,
                 "--num_batches", 2, "-o", tmp_path / "batch")
    assert result.returncode == 0, result.stderr

    totals = []
    for batch in sorted(tmp_path.glob("batch_*.csv")):
        rows = list(csv.DictReader(batch.open()))
        totals.append(sum(sizes[r["sample"]] for r in rows))

    assert sorted(totals) == [100, 110]


def test_more_batches_than_samples_has_no_empty_batch(tmp_path):
    sheet = tmp_path / "sheet.csv"
    sheet.write_text("sample,fastq_1\ns1,s1.fq.gz\n")
    stats = tmp_path / "stats.tsv"
    stats.write_text("file\tsum_len\ns1.fq.gz\t5\n")

    run("divide_samples_in_batches.py", "--samplesheet", sheet, "--stats", stats,
        "--num_batches", 4, "-o", tmp_path / "batch")

    assert len(list(tmp_path.glob("batch_*.csv"))) == 1


def test_bad_samples_file_writes_no_header(tmp_path):
    (tmp_path / "s1").mkdir()
    (tmp_path / "s1" / "a_R1.fastq.gz").touch()
    (tmp_path / "s1" / "a_R2.fastq.gz").touch()
    samples = tmp_path / "samples.csv"
    samples.write_text("name,group\ns1,x\n")  # no 'sample' column

    result = run("make_samplesheet.py", "--path", tmp_path, "--samples", samples)

    assert result.returncode == 1
    assert result.stdout == ""


def test_samples_file_filters_by_name_or_list(tmp_path):
    for name in ("s1", "s2"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "a_R1.fastq.gz").touch()
        (tmp_path / name / "a_R2.fastq.gz").touch()

    csv_file = tmp_path / "samples.csv"
    csv_file.write_text("sample,group\ns1,x\n")
    plain = tmp_path / "list.txt"
    plain.write_text("s1\n")

    for samples in (csv_file, plain):
        result = run("make_samplesheet.py", "--path", tmp_path, "--samples", samples,
                     "--format", "rnaseq")
        rows = list(csv.DictReader(result.stdout.splitlines()))
        assert [r["sample"] for r in rows] == ["s1"], samples
