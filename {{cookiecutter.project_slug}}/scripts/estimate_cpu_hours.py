#!/usr/bin/env python
"""Estimate the CPU-hours (requested cpus x realtime) of a nf-core/methylseq run.

fit:     calibrate CPU-h per million reads, per process, on a finished run
         (nextflow execution_report_*.html + MultiQC bismark_alignment.txt)
predict: apply conf/cpu_model.json to the number of reads of a new run
"""

import re
import csv
import json
import argparse
import collections
import pathlib

CPU_RE = re.compile(r'"name":"([^"]+)","status":"[^"]*","exit":"[^"]*","submit":"\d+",'
                    r'"start":"\d+","complete":"\d+","duration":"\d+","realtime":"(\d+)".*?"cpus":"(\d+)"')
TASK_RE = re.compile(r"^(?:\S+:)*(\w+) \((.+)\)$")


def read_tasks(report):
    """yield (process, sample or None, requested cpus x realtime in hours)"""
    for name, realtime, cpus in CPU_RE.findall(pathlib.Path(report).read_text()):
        m = TASK_RE.match(name)
        if m:
            yield m.group(1), m.group(2), int(cpus) * int(realtime) / 3.6e6
        else:
            yield name.split(":")[-1], None, int(cpus) * int(realtime) / 3.6e6


def read_millions(bismark_alignment):
    """reads given to bismark per sample, in millions (R1/R2 split names merged)"""
    reads = collections.defaultdict(float)
    with open(bismark_alignment) as f:
        for row in csv.DictReader(f, delimiter="\t"):
            sample = re.sub(r"_\d+$", "", re.sub(r"_val_\d+$", "", row["Sample"]))
            reads[sample] += sum(float(v) for k, v in row.items() if k != "Sample" and v) / 1e6
    return reads


def read_raw_millions(multiqc_fastqc):
    """raw read pairs per sample, in millions (R1 rows of multiqc_fastqc.txt)"""
    with open(multiqc_fastqc) as f:
        return {r["Sample"][:-2]: float(r["Total Sequences"]) / 1e6
                for r in csv.DictReader(f, delimiter="\t") if r["Sample"].endswith("_1")}


def fit(report, bismark_alignment, fastqc, out):
    reads = read_millions(bismark_alignment)
    per_sample = collections.defaultdict(dict)  # process -> sample -> cpu-h
    fixed = collections.defaultdict(float)
    for proc, sample, cpuh in read_tasks(report):
        if sample in reads:
            per_sample[proc][sample] = per_sample[proc].get(sample, 0) + cpuh
        else:
            fixed[proc] += cpuh

    def coef(procs, skip=None):
        num = sum(per_sample[p][s] * reads[s] for p in procs for s in per_sample[p] if s != skip)
        den = sum(reads[s] ** 2 for p in procs for s in per_sample[p] if s != skip)
        return num / den

    model = {"unit": "CPU-h (requested cpus x realtime) per million reads", "n_samples": len(reads),
             "per_million_reads": {p: coef([p]) for p in per_sample}, "fixed_cpu_h": dict(fixed)}

    # leave-one-out relative error of the per-sample total
    samples = sorted(set(s for p in per_sample.values() for s in p))
    errs = []
    for s in samples:
        pred = sum(coef([p], skip=s) * reads[s] for p in per_sample if s in per_sample[p])
        true = sum(per_sample[p][s] for p in per_sample if s in per_sample[p])
        errs.append((pred - true) / true)
    model["loo_sample_rel_err_rmse"] = (sum(e * e for e in errs) / len(errs)) ** 0.5
    total_true = sum(sum(p.values()) for p in per_sample.values())
    model["loo_total_rel_err"] = abs(sum(
        coef([p], skip=s) * reads[s] for s in samples for p in per_sample if s in per_sample[p]
    ) - total_true) / total_true
    # trimming (RRBS length filter) drops reads: fraction of FASTQ reads reaching bismark
    raw = read_raw_millions(fastqc)
    ratios = [reads[s] / raw[s] for s in samples if s in raw]
    model["retention_total"] = sum(reads[s] for s in samples) / sum(raw[s] for s in samples if s in reads)
    model["retention_range"] = [min(ratios), max(ratios)]
    pathlib.Path(out).write_text(json.dumps(model, indent=2) + "\n")
    print(f"{len(samples)} samples, {total_true + sum(fixed.values()):.0f} CPU-h in the run; "
          f"LOO error per sample {model['loo_sample_rel_err_rmse']:.1%}, total {model['loo_total_rel_err']:.1%}")


def predict(model_path, million_reads, genome_prep, raw):
    model = json.loads(pathlib.Path(model_path).read_text())
    if raw:  # FASTQ read pairs (seqkit num_seqs of R1) -> reads reaching bismark
        million_reads *= model["retention_total"]
        lo, hi = model["retention_range"]
        print(f"reads reaching bismark = FASTQ x {model['retention_total']:.2f} (per sample {lo:.2f}-{hi:.2f} in the calibration run)")
    rows = {p: c * million_reads for p, c in model["per_million_reads"].items()}
    for p, c in model["fixed_cpu_h"].items():
        # genome preparation runs once per genome, and can be skipped if the index exists
        if p != "BISMARK_GENOMEPREPARATION_BOWTIE" or genome_prep:
            rows[p] = c
    total = sum(rows.values())
    for p, v in sorted(rows.items(), key=lambda i: -i[1]):
        print(f"{p:32s}{v:10.1f}")
    err = model["loo_sample_rel_err_rmse"] / max(model["n_samples"], 1) ** 0.5
    print(f"{'TOTAL CPU-h':32s}{total:10.1f}  (+/- {total * max(err, 0.05):.0f} from the fit alone; RRBS only; add the read-retention uncertainty)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit")
    f.add_argument("--report", required=True, help="execution_report_*.html")
    f.add_argument("--bismark-alignment", required=True, help="multiqc_data/bismark_alignment.txt")
    f.add_argument("--fastqc", required=True, help="multiqc_data/multiqc_fastqc.txt")
    f.add_argument("--out", default="conf/cpu_model.json")
    p = sub.add_parser("predict")
    p.add_argument("--million-reads", type=float, required=True, help="total read pairs of all samples (R1 num_seqs), in millions")
    p.add_argument("--aligned", action="store_true", help="the number is already the reads given to bismark (after trimming)")
    p.add_argument("--model", default="conf/cpu_model.json")
    p.add_argument("--no-genome-prep", action="store_true", help="bismark index already available")
    a = ap.parse_args()
    if a.cmd == "fit":
        fit(a.report, a.bismark_alignment, a.fastqc, a.out)
    else:
        predict(a.model, a.million_reads, not a.no_genome_prep, not a.aligned)
