---
name: estimate-cpu-hours
description: Estimate the CPU-hours (budget) needed to run nf-core/methylseq on the samples of this project, from the number of reads, using a model calibrated on a real run. Use when the user asks how many CPU hours / how much budget the analysis needs, before launching it.
---

# Estimate CPU-hours (nf-core/methylseq)

Goal: CPU-hours per process and in total, for the budget request. Cost is the
**requested** cpus x walltime (what SLURM bills), not the CPU actually used.
The model `conf/cpu_model.json` was fitted with `scripts/estimate_cpu_hours.py fit`
on a real RRBS run (42 samples, bismark, rat genome): CPU-h scale linearly with
the reads given to bismark (~1 CPU-h per million read pairs, 80% of it in
`BISMARK_ALIGN`; per-sample error ~5%).

## 1. Reads

The predictor is the number of **read pairs** (not genome size x coverage:
RRBS has no genome-wide coverage). Use R1 `num_seqs` from `conf/seq_stats.tsv`
(see the `split-samplesheet` skill; run it first if missing) and sum it in millions:

```bash
awk -F'\t' 'NR==1{for(i=1;i<=NF;i++)h[$i]=i} NR>1 && $h["file"] ~ /_(R)?1[._]/ {s+=$h["num_seqs"]} END{print s/1e6}' conf/seq_stats.tsv
```

(check the R1 pattern on the file names; for single-end use all files).

## 2. Estimate

```bash
python scripts/estimate_cpu_hours.py predict --million-reads <M>   # FASTQ read pairs
```

`--no-genome-prep` if the bismark index already exists; `--aligned` if the
number is already after trimming. Report the table and the total.

## 3. Caveats to tell the user

- In RRBS the trimming length filter drops reads: the model applies the average
  retention of the calibration run (0.86), but it was 0.17-0.97 per sample, so
  libraries with poor quality/adapter content cost less than predicted.
- Calibrated on **RRBS** with the `cpus` requested in that run (bismark_align 24
  cpus); WGBS (e.g. 30X) or different resources need a new calibration, so say the
  estimate is only indicative. To recalibrate on a new run: `fit --report
  pipeline_info/execution_report_*.html --bismark-alignment <multiqc_data>/bismark_alignment.txt
  --fastqc <multiqc_data>/multiqc_fastqc.txt` (the report HTML has `cpus`, the trace .txt does not).
- Check the result against the budget: round up (+20%) for reruns of failed tasks.
