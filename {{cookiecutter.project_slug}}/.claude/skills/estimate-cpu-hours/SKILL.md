---
name: estimate-cpu-hours
description: Estimate the CPU-hours (budget) needed to run {{ cookiecutter.project_type }} on the samples of this project, from the number of reads, using a model calibrated on real runs. Use when the user asks how many CPU hours / how much budget the analysis needs, before launching it.
---

# Estimate CPU-hours ({{ cookiecutter.project_type }})

Goal: CPU-hours per process and in total, for the budget request. Cost is the
**requested** cpus x walltime (what SLURM bills), not the CPU actually used.
The model `conf/cpu_model.json` (one key per pipeline, here `{{ cookiecutter.__pipeline }}`) was fitted with
`scripts/estimate_cpu_hours.py fit` on real runs: CPU-h scale linearly with the number of reads.
{%- if cookiecutter.project_type == "nf-core/methylseq" %}
Two RRBS runs (98 samples, bismark, rat genome): ~1 CPU-h per million read pairs,
80% of it in `BISMARK_ALIGN`; per-sample error ~5%; a model fitted on one run predicted the other within 2%.
{%- else %}
Two runs (STAR + Salmon, paired-end 150, 129 samples, bos taurus and rattus norvegicus): ~0.35 CPU-h per million
read pairs (STAR_ALIGN, DUPRADAR, TRIMGALORE, PICARD_MARKDUPLICATES dominate). The total of a run is predicted
within ~10% (a model fitted on one species predicted the other within 12-24%, the pooled one within 6%),
but **per-sample cost varies a lot** (0.06-1.2 CPU-h per million reads), so trust the total, not single samples.
{%- endif %}

## 1. Reads

The predictor is the number of **read pairs** (not genome size x coverage).
Use R1 `num_seqs` from `conf/seq_stats.tsv` (see the `split-samplesheet` skill; run it
first if missing) and sum it in millions:

```bash
awk -F'\t' 'NR==1{for(i=1;i<=NF;i++)h[$i]=i} NR>1 && $h["file"] ~ /_(R)?1[._]/ {s+=$h["num_seqs"]} END{print s/1e6}' conf/seq_stats.tsv
```

(check the R1 pattern on the file names; for single-end use all files).

## 2. Estimate

```bash
python scripts/estimate_cpu_hours.py predict --pipeline {{ cookiecutter.__pipeline }} --million-reads <M>   # FASTQ read pairs
```

`--no-genome-prep` if the genome index already exists.
{%- if cookiecutter.project_type == "nf-core/methylseq" %} `--aligned` if the
number is already after trimming.
{%- endif %} Report the table and the total.

## 3. Caveats to tell the user

{% if cookiecutter.project_type == "nf-core/methylseq" -%}
- In RRBS the trimming length filter drops reads: the model applies the average
  retention of the calibration runs (0.88), but it was 0.17-0.98 per sample, so
  libraries with poor quality/adapter content cost less than predicted.
- Calibrated on **RRBS** with the `cpus` requested in those runs (bismark_align 24
  cpus); WGBS (e.g. 30X) or different resources need a new calibration, so say the
  estimate is only indicative. To recalibrate: `fit --pipeline methylseq --run
  pipeline_info/execution_report_*.html <multiqc_data>/bismark_alignment.txt
  <multiqc_data>/multiqc_fastqc.txt`
{%- else -%}
- Calibrated on mammalian PE150 samples with the `cpus` requested in those runs (STAR 12 cpus
  or similar); different read length, genome size or resources make the estimate only indicative.
  To recalibrate: `fit --pipeline rnaseq --run pipeline_info/execution_report_*.html
  <multiqc_data>/multiqc_fastqc_fastqc_raw.txt`
{%- endif %}
  (repeat `--run` to pool runs; sample names must be unique; only the `--pipeline` key is
  rewritten). The report HTML has `cpus`, the trace .txt does not. After a `-resume`, use the
  last report (cached tasks keep their realtime); failed retries are not counted.
- Check the result against the budget: round up (+20%) for reruns of failed tasks.
