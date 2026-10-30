#! /usr/bin/env python

# Read the cost of a run on AWS Batch from AWS (Cost Explorer, CloudTrail, Batch) and
# write it as CSV files, together with the share of the vCPUs of the instances that was
# reserved by the jobs. Standard library only: AWS is queried through the aws CLI.
#
#   python3 scripts/aws_costs.py --profile <profile> --region <region> --queue <job queue> \
#       --start 2026-10-26 --end 2026-10-30
#
# AWS Batch keeps the jobs for 7 days and CloudTrail the events for 90 days: run it soon
# after the run. Cost Explorer lags up to 24 h and its end date is exclusive.

import re
import csv
import json
import shutil
import argparse
import datetime
import tempfile
import subprocess
import collections

from pathlib import Path

UTC = datetime.timezone.utc

# vCPUs per instance size (EC2 sizes of the families used by the compute environment)
SIZES = {
    "large": 2, "xlarge": 4, "2xlarge": 8, "4xlarge": 16, "8xlarge": 32, "9xlarge": 36,
    "12xlarge": 48, "16xlarge": 64, "18xlarge": 72, "24xlarge": 96,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Read the costs of a run on AWS Batch and write them as CSV files")
    parser.add_argument(
        "--start",
        required=True,
        help="First day of the period, YYYY-MM-DD (UTC)"
    )
    parser.add_argument(
        "--end",
        required=True,
        help="Day after the last one of the period, YYYY-MM-DD (UTC, exclusive)"
    )
    parser.add_argument(
        "--until",
        help="Ignore the instances launched and the job attempts started after this time, "
             "YYYY-MM-DDTHH:MM:SSZ (UTC), e.g. to leave out later tests in the same queue"
    )
    parser.add_argument(
        "--region",
        required=True,
        help="Region of Batch, EC2 and CloudTrail (the one of the awsbatch profile)"
    )
    parser.add_argument(
        "--queue",
        action="append",
        required=True,
        help="AWS Batch job queue; repeat it to read more queues (e.g. Spot and on-demand)"
    )
    parser.add_argument(
        "--aws",
        default="aws",
        help="Path of the aws CLI (default: %(default)s)"
    )
    parser.add_argument(
        "--profile",
        help="AWS CLI profile (default: the one of AWS_PROFILE or the default profile)"
    )
    parser.add_argument(
        "--classes",
        help="JSON file with a list of [label, regex] pairs to group the processes in the "
             "cost report, first match wins (default: one class per process)"
    )
    parser.add_argument(
        "--outdir",
        default="docs/aws-costs",
        help="Directory of the CSV files (default: %(default)s)"
    )
    parser.add_argument(
        "--raw-dir",
        help="Directory of the raw JSON answers of AWS (default: a temporary one)"
    )
    parser.add_argument(
        "--cache",
        action="store_true",
        help="Read the raw JSON already in --raw-dir instead of calling AWS"
    )
    parser.add_argument(
        "--exclude-types",
        nargs="*",
        default=[],
        help="Instance types not counted in the allocation, e.g. the one of a launcher "
             "VM that is not run by Batch (default: none)"
    )
    parser.add_argument(
        "--ref-vcpus",
        type=int,
        default=32,
        help="vCPUs of the reference instance of the cost model: the instance type that dominates cost_by_instance_type.csv (default: %(default)s)"
    )
    parser.add_argument(
        "--ref-memory-gib",
        type=int,
        default=256,
        help="Memory in GiB of the reference instance (default: %(default)s)"
    )
    parser.add_argument(
        "--ref-price",
        type=float,
        default=0.51,
        help="Spot price per hour of the reference instance, USD (default: %(default)s)"
    )
    parser.add_argument(
        "--window",
        type=int,
        default=30,
        help="Minutes of the windows of the allocation table (default: %(default)s)"
    )
    args = parser.parse_args()

    if args.cache and not args.raw_dir:
        parser.error("--cache needs --raw-dir")

    return args


class Aws:
    """Call the aws CLI and keep the raw answers, to read them again with --cache"""

    def __init__(self, aws, profile, raw_dir, cache):
        self.aws = aws
        self.profile = profile
        self.raw_dir = Path(raw_dir)
        self.cache = cache
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def call(self, name, *args):
        path = self.raw_dir / f"{name}.json"

        if self.cache:
            return json.loads(path.read_text())

        profile = ["--profile", self.profile] if self.profile else []
        result = subprocess.run(
            [self.aws, *profile, *args, "--output", "json"], capture_output=True, text=True)

        if result.returncode != 0:
            raise SystemExit(f"{self.aws} {' '.join(args[:3])} failed: {result.stderr.strip()}")

        path.write_text(result.stdout)
        return json.loads(result.stdout)


def vcpus_of(instance_type):
    return SIZES[instance_type.split(".")[1]]


def process_of(job_name):
    """Process part of a job name: Nextflow joins the process name (NFCORE_..._PROCESS) and
    the task tag (the sample, after a dash or an underscore followed by a number)"""

    tokens = []
    for token in job_name.split("_"):
        head, dash, _ = token.partition("-")
        if token.isdigit() or not re.fullmatch(r"[A-Za-z0-9]+", head):
            break

        if not dash and not re.fullmatch(r"[A-Z0-9]+", head):
            break

        tokens.append(head)
        if dash:
            break

    return "_".join(tokens) or job_name


def load_classes(path):
    """Classes of the jobs from a JSON list of [label, regex]: the first pattern that matches
    the process name wins"""

    if not path:
        return []

    return [(label, pattern) for label, pattern in json.loads(Path(path).read_text())]


def class_of(process, classes):
    for label, pattern in classes:
        if re.search(pattern, process):
            return label

    return "Other" if classes else process


def to_epoch(text):
    return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp()


def to_iso(epoch):
    return datetime.datetime.fromtimestamp(epoch, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_csv(path, header, rows):
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)

    print(f"wrote {path} ({len(rows)} rows)")


def read_costs(aws, args, outdir):
    period = f"Start={args.start},End={args.end}"
    ce = ["--region", "us-east-1", "ce", "get-cost-and-usage"]
    base = ["--time-period", period, "--granularity", "DAILY"]

    by_service = aws.call(
        "ce_by_service", *ce, *base, "--metrics", "UnblendedCost",
        "--group-by", "Type=DIMENSION,Key=SERVICE")

    rows = []
    for day in by_service["ResultsByTime"]:
        for group in day["Groups"]:
            cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
            rows.append((day["TimePeriod"]["Start"], group["Keys"][0], f"{cost:.4f}", day["Estimated"]))

    write_csv(outdir / "cost_by_day_service.csv", ["date", "service", "cost_usd", "estimated"], rows)

    by_type = aws.call(
        "ce_ec2_by_usage_type", *ce, *base, "--metrics", "UnblendedCost", "UsageQuantity",
        "--group-by", "Type=DIMENSION,Key=USAGE_TYPE",
        "--filter", json.dumps({"Dimensions": {
            "Key": "SERVICE", "Values": ["Amazon Elastic Compute Cloud - Compute"]}}))

    rows = []
    for day in by_type["ResultsByTime"]:
        for group in day["Groups"]:
            usage_type = group["Keys"][0]
            metrics = group["Metrics"]
            rows.append((
                day["TimePeriod"]["Start"], usage_type, usage_type.split(":")[-1],
                f"{float(metrics['UnblendedCost']['Amount']):.4f}",
                f"{float(metrics['UsageQuantity']['Amount']):.3f}"))

    write_csv(
        outdir / "cost_by_instance_type.csv",
        ["date", "usage_type", "instance_type", "cost_usd", "hours"], rows)

    return sum(float(row[3]) for row in rows)


def read_instances(aws, args, outdir):
    """Life of every instance launched by Batch, from the CloudTrail events"""

    # lookup-events needs timestamps: the period is widened by a day on both sides
    start = (datetime.date.fromisoformat(args.start) - datetime.timedelta(days=1)).isoformat()
    end = (datetime.date.fromisoformat(args.end) + datetime.timedelta(days=1)).isoformat()

    launched = {}
    terminated = {}

    for event_name in ("RunInstances", "TerminateInstances"):
        answer = aws.call(
            f"cloudtrail_{event_name}", "--region", args.region, "cloudtrail", "lookup-events",
            "--lookup-attributes", f"AttributeKey=EventName,AttributeValue={event_name}",
            "--start-time", f"{start}T00:00:00Z", "--end-time", f"{end}T00:00:00Z")

        for event in answer["Events"]:
            detail = json.loads(event["CloudTrailEvent"])

            # dry runs (Client.DryRunOperation) and capacity errors do not create instances
            if detail.get("errorCode"):
                continue

            if event_name == "RunInstances":
                if args.until and to_epoch(detail["eventTime"]) > to_epoch(args.until):
                    continue

                for item in detail["responseElements"]["instancesSet"]["items"]:
                    launched[item["instanceId"]] = (
                        to_epoch(detail["eventTime"]), detail["requestParameters"]["instanceType"])
            else:
                for item in detail["requestParameters"]["instancesSet"]["items"]:
                    terminated.setdefault(item["instanceId"], to_epoch(detail["eventTime"]))

    instances = []
    rows = []
    for instance_id, (started, instance_type) in sorted(launched.items(), key=lambda x: x[1][0]):
        stopped = terminated.get(instance_id)
        vcpus = vcpus_of(instance_type)
        hours = (stopped - started) / 3600 if stopped else None
        rows.append((
            instance_id, instance_type, vcpus, to_iso(started),
            to_iso(stopped) if stopped else "", f"{hours:.3f}" if hours is not None else "",
            instance_type in args.exclude_types))

        if stopped and instance_type not in args.exclude_types:
            instances.append((started, stopped, vcpus))

    write_csv(
        outdir / "instances.csv",
        ["instance_id", "instance_type", "vcpus", "launched", "terminated", "hours", "excluded"], rows)

    return instances


def read_jobs(aws, args, outdir):
    """Every attempt of the Batch jobs, with its vCPUs and duration"""

    ids = []
    for number, queue in enumerate(args.queue):
        for status in ("SUCCEEDED", "FAILED"):
            answer = aws.call(
                f"batch_list_{number}_{status}", "--region", args.region, "batch", "list-jobs",
                "--job-queue", queue, "--job-status", status)
            ids += [job["jobId"] for job in answer["jobSummaryList"]]

    jobs = []
    for index in range(0, len(ids), 100):
        answer = aws.call(
            f"batch_describe_{index // 100:03d}", "--region", args.region, "batch", "describe-jobs",
            "--jobs", *ids[index:index + 100])
        jobs += answer["jobs"]

    rows = []
    intervals = []
    attempts_data = []
    for job in jobs:
        container = job["container"]
        vcpus = float(container.get("vcpus") or 0)
        memory = container.get("memory") or ""

        for requirement in container.get("resourceRequirements", []):
            if requirement["type"] == "VCPU":
                vcpus = float(requirement["value"])
            elif requirement["type"] == "MEMORY":
                memory = int(requirement["value"])

        process = process_of(job["jobName"])

        attempts = job.get("attempts") or [
            {"startedAt": job.get("startedAt"), "stoppedAt": job.get("stoppedAt"),
             "statusReason": job.get("statusReason")}]

        for number, attempt in enumerate(attempts, 1):
            started, stopped = attempt.get("startedAt"), attempt.get("stoppedAt")
            if not (started and stopped):
                continue

            if args.until and started / 1000 > to_epoch(args.until):
                continue

            hours = (stopped - started) / 3600000
            intervals.append((started / 1000, stopped / 1000, vcpus))
            attempts_data.append((process, vcpus, float(memory or 0) / 1024, hours))
            rows.append((
                job["jobId"], job["jobName"], process, job["status"], number, len(attempts),
                f"{vcpus:g}", memory, to_iso(started / 1000), to_iso(stopped / 1000),
                f"{hours:.4f}", (attempt.get("statusReason") or "").replace("\n", " ")))

    write_csv(
        outdir / "jobs.csv",
        ["job_id", "job_name", "process", "status", "attempt", "attempts", "vcpus", "memory_mib",
         "started", "stopped", "hours", "status_reason"], rows)

    return intervals, attempts_data


def write_cost_report(args, outdir, attempts, ec2_cost, classes_map):
    """Cost model of the jobs: hours of every attempt times the share of the reference instance
    that its vCPUs or its memory (the scarcer one) take, times the price of that instance. It is
    an estimate of what each job costs, RAM included, not a measure: the instance of a job is unknown"""

    processes = collections.defaultdict(lambda: [0, 0.0, 0.0])
    for process, vcpus, memory_gib, hours in attempts:
        share = max(vcpus / args.ref_vcpus, memory_gib / args.ref_memory_gib)
        entry = processes[process]
        entry[0] += 1
        entry[1] += vcpus * hours
        entry[2] += hours * share * args.ref_price

    rows = [(p, class_of(p, classes_map), n, f"{v:.1f}", f"{c:.2f}") for p, (n, v, c) in sorted(
        processes.items(), key=lambda x: -x[1][2])]
    write_csv(
        outdir / "cost_by_process.csv",
        ["process", "class", "attempts", "vcpu_hours", "model_cost_usd"], rows)

    classes = collections.defaultdict(lambda: [0, 0.0, 0.0])
    for process, (n, v, c) in processes.items():
        entry = classes[class_of(process, classes_map)]
        entry[0] += n
        entry[1] += v
        entry[2] += c

    model_total = sum(c for _, _, c in classes.values())
    rows = [(label, n, f"{v:.1f}", f"{c:.2f}", f"{c / model_total:.3f}", f"{c / ec2_cost:.3f}")
            for label, (n, v, c) in sorted(classes.items(), key=lambda x: -x[1][2])]
    write_csv(
        outdir / "cost_by_class.csv",
        ["class", "attempts", "vcpu_hours", "model_cost_usd", "share_of_model", "share_of_ec2_bill"], rows)

    print(f"model of the cost of the jobs: ${model_total:.2f} of ${ec2_cost:.2f} of EC2 ({model_total / ec2_cost:.0%})")
    for label, n, v, c, share, bill in rows:
        print(f"  {label:32s} {n:5d} attempts {float(v):7.0f} vCPU-h  ${float(c):6.2f}  {float(share):4.0%} of the model  {float(bill):4.0%} of the bill")


def overlap(start, end, window_start, window_end):
    return max(0, min(end, window_end) - max(start, window_start))


def write_allocation(args, outdir, instances, jobs):
    """vCPU-hours of the instances against the ones reserved by the jobs, per time window"""

    if not instances:
        print("no terminated instance found in CloudTrail: allocation table skipped")
        return

    step = args.window * 60
    first = min(start for start, _, _ in instances)
    last = max(stop for _, stop, _ in instances)

    rows = []
    moment = first
    while moment < last:
        billed = sum(overlap(s, e, moment, moment + step) * v for s, e, v in instances) / 3600
        reserved = sum(overlap(s, e, moment, moment + step) * v for s, e, v in jobs) / 3600
        rows.append((to_iso(moment), f"{billed:.1f}", f"{reserved:.1f}",
                     f"{reserved / billed:.3f}" if billed else ""))
        moment += step

    write_csv(
        outdir / "allocation_window.csv",
        ["window_start", "instance_vcpu_hours", "job_vcpu_hours", "reserved_share"], rows)

    daily = collections.defaultdict(lambda: [0.0, 0.0])
    for window_start, billed, reserved, _ in rows:
        daily[window_start[:10]][0] += float(billed)
        daily[window_start[:10]][1] += float(reserved)

    for day, (billed, reserved) in daily.items():
        print(f"  {day}: instances {billed:7.0f} vCPU-h, jobs {reserved:7.0f}, share {reserved / billed:.0%}")


def main():
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    raw_dir = args.raw_dir
    temporary = None
    if not raw_dir:
        temporary = raw_dir = tempfile.mkdtemp(prefix="aws_costs_")

    try:
        aws = Aws(args.aws, args.profile, raw_dir, args.cache)

        ec2_cost = read_costs(aws, args, outdir)
        instances = read_instances(aws, args, outdir)
        jobs, attempts = read_jobs(aws, args, outdir)
    finally:
        if temporary:
            shutil.rmtree(temporary, ignore_errors=True)

    billed = sum((stop - start) * vcpus for start, stop, vcpus in instances) / 3600
    reserved = sum((stop - start) * vcpus for start, stop, vcpus in jobs) / 3600

    print(f"EC2 cost {args.start}..{args.end}: ${ec2_cost:.2f}")
    if not (billed and reserved and ec2_cost):
        raise SystemExit("no instances, jobs or EC2 cost found: check --start/--end, --region and --queue")

    print(f"vCPU-hours of the instances (CloudTrail): {billed:.0f}; reserved by the jobs: {reserved:.0f}"
          f" ({reserved / billed:.1%})")
    print(f"$ per instance vCPU-hour: {ec2_cost / billed:.4f}; per reserved vCPU-hour: {ec2_cost / reserved:.4f}")

    write_allocation(args, outdir, instances, jobs)
    write_cost_report(args, outdir, attempts, ec2_cost, load_classes(args.classes))


if __name__ == "__main__":
    main()
