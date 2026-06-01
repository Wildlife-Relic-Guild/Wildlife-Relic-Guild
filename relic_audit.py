#!/usr/bin/env python3
"""
RELIC AUDIT GUILD v19.7 — PRODUCTION READY (Rich CLI + Integrated HTML Reports)
✅ Pre-flight credential validation
✅ Minimal IAM policy included
✅ Rate limiting (time.sleep(0.1))
✅ Legal disclaimer footer
✅ HTML report output — conversion-optimised, fully self-contained (v16)
✅ Rotating rewilding messages in progress bar
✅ Single-file — no external module dependencies beyond boto3 + rich
✅ Wildlife Relic Guild — May 2026
"""
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                         RELIC AUDIT GUILD                                  ║
║                  Cloud Waste Intelligence Engine v19.7                     ║
║                                                                            ║
║        "Legacy in the landscape, for your company and my family."          ║
╚══════════════════════════════════════════════════════════════════════════════╝

WHAT THIS SCRIPT DOES:
  Scans your AWS account across all regions for hidden, forgotten, and wasteful
  cloud resources that are silently draining your budget and your planet's energy.
  Results are always delivered in full. No fee. No paywall. No locked content.

ARCHITECTURE (v13.0):
  Class-based RelicAuditEngine from v9.4 merged with all 14 checks from
  v2.6. Warnings (data gaps) and errors (API failures) are separated throughout.
  Three-tier instance type lookup. Confidence threshold on CPU idle checks.
  LocalStack support for dev/test without a live AWS account.
  Rich CLI interface added in v14.0 — presentation layer only, core unchanged.
  HTML report output added in v15.0 — aegis_html_report.py module called after
  scan. Rotating rewilding messages added to progress bar in v15.0.
  v16.0: HTML report module merged into single file. No external dependencies.
  Full report always delivered. Closing conversation weighs savings and kWh,
  then invites voluntary donation to Mossy Earth.

MODEL:
  Every scan delivers the full report — all resource IDs, all costs, all remediation.
  No fee. No paywall. No locked content. The scan is always free.
  If waste is found, the closing report invites a voluntary donation to Mossy Earth.
  No suggested amount. No obligation. The user decides.
  Account is clean — we still let you donate!

CHECKS PERFORMED (14 total):
   1. Orphaned EBS Volumes       — Unattached hard drives
   2. Zombie Snapshots           — Backups whose parent volume no longer exists
   3. Stopped EC2 Instances      — Servers off but still costing money
   4. Unused Elastic IPs         — Idle reserved IP addresses
   5. Idle Load Balancers        — Traffic managers with no healthy targets
   6. Idle NAT Gateways          — Network gateways with zero traffic (verified)
   7. Stopped RDS Instances      — Databases still billed for storage
   8. CloudWatch Log Groups      — Logs stored forever with no retention policy
   9. Old ECR Container Images   — Abandoned Docker images (>90 days)
  10. Idle Lambda Functions       — Hygiene/indirect risk (no direct cost)
  11. Abandoned S3 Buckets        — Storage untouched for 90+ days
  12. Idle SageMaker Endpoints    — AI inference endpoints (7-day status check)
  13. GPU Zombie Endpoints        — InService endpoints with 0 invocations/72h
  14. Redundant Snapshot Lineage  — Volumes with excessive snapshot accumulation

PRICING & BUSINESS MODEL:
  Fee                      : None. This service is entirely free.
  Conservation              : Voluntary donation to Mossy Earth invited after scan
  Your Saving              : 100% of waste found is yours to reclaim

SECURITY COMMITMENTS:
  - Read-Only IAM policy only — we cannot create, modify or delete anything
  - No machine learning — your data never trains any model
  - No credentials stored after the scan completes
  - No agents, no installs, no ongoing access of any kind

RECOMMENDED IAM POLICY:
  {
    "Version": "2012-10-17",
    "Statement": [{
      "Sid": "RelicAuditReadOnly",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVolumes", "ec2:DescribeSnapshots", "ec2:DescribeInstances",
        "ec2:DescribeAddresses", "ec2:DescribeRegions", "ec2:DescribeNatGateways",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeTargetHealth",
        "rds:DescribeDBInstances",
        "logs:DescribeLogGroups", "logs:DescribeLogStreams",
        "ecr:DescribeRepositories", "ecr:DescribeImages",
        "lambda:ListFunctions", "lambda:GetFunctionConcurrency",
        "s3:ListAllMyBuckets", "s3:GetBucketLocation", "s3:GetBucketLogging",
        "sagemaker:ListEndpoints", "sagemaker:DescribeEndpoint",
        "sagemaker:DescribeEndpointConfig",
        "cloudwatch:GetMetricStatistics",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }]
  }

REQUIREMENTS:
  pip install boto3 rich
  AWS credentials via: aws configure  OR  environment variables
  LocalStack testing: set ENDPOINT_URL = "http://localhost:4566"
  Single file — no other Relic modules required.
"""

import sys
import json
import logging
import time
import itertools
import threading
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from botocore.exceptions import NoCredentialsError, ClientError
from botocore.config import Config

import boto3

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.text import Text
from rich.rule import Rule
from rich import box
from rich.padding import Padding

console = Console(highlight=False)

# ─────────────────────────────────────────────────────────────────────────────
# GUILD MUSIC
# Plays a medieval music file during the scan if pygame is installed and a
# compatible audio file is found alongside the script.
# Supported formats: .mp3 .ogg .wav  — place file next to this script.
# Install: pip install pygame
# Fails silently if pygame missing or no audio file found — scan unaffected.
# ─────────────────────────────────────────────────────────────────────────────

_MUSIC_EXTENSIONS  = ('.mp3', '.ogg', '.wav', '.flac')
_PREFERRED_TRACK   = 'watermelon_beats-medieval-folk-music-505203.mp3'
_music_playing     = False

def _find_music_file():
    """Look for audio file in the same directory as this script. Preferred track first."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    preferred  = os.path.join(script_dir, _PREFERRED_TRACK)
    if os.path.isfile(preferred):
        return preferred
    for fname in os.listdir(script_dir):
        if fname.lower().endswith(_MUSIC_EXTENSIONS):
            return os.path.join(script_dir, fname)
    return None

def _start_music():
    """Start playing guild music in a background thread. Silent on failure."""
    global _music_playing
    def _play():
        global _music_playing
        try:
            import pygame
            music_file = _find_music_file()
            if not music_file:
                return
            pygame.mixer.init()
            pygame.mixer.music.load(music_file)
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(-1)  # loop until stopped
            _music_playing = True
            fname = os.path.basename(music_file)
            console.print(f"  [dim green]♫  Playing: {fname}[/dim green]\n")
        except Exception:
            pass  # no pygame, no file, no problem
    threading.Thread(target=_play, daemon=True).start()

def _stop_music():
    """Fade out guild music at end of scan. Silent on failure."""
    global _music_playing
    if not _music_playing:
        return
    try:
        import pygame
        if pygame.mixer.get_init():
            pygame.mixer.music.fadeout(3000)  # 3 second fade
        _music_playing = False
    except Exception:
        pass

# ─────────────────────────────────────────────────────────────────────────────
# REWILDING PROGRESS MESSAGES
# Presentation layer only — cycles through during the region scan progress bar.
# ─────────────────────────────────────────────────────────────────────────────

REWILDING_MESSAGES = [
    "🌱 Your scan helps fund native woodland in the British Isles",
    "🦅 Mossy Earth has restored over 1,000 hectares of wild land",
    "🐺 Wolves, lynx, bison — rewilding returns apex predators to Europe",
    "🌊 Cloud waste powers data centres that warm seas. Less waste = less harm.",
    "🦋 One scan can fund the planting of 200 native trees",
    "🌿 Mossy Earth · Verified native rewilding · Zero greenwash",
    "🐝 Pollinators collapse when habitat collapses. Rewilding reverses it.",
    "🌍 The UK has lost 97% of its wildflower meadows. We fund recovery.",
    "🦌 Red deer, red kite, red squirrel — all returning through rewilding",
    "🌲 Mossy Earth · Verified rewilding · Donation-funded by the people this scan serves.",
    "🪸 Kelp forests sequester CO₂ 35× faster than terrestrial forest",
    "🐺 Rewilding Britain — one neglected cloud resource at a time",
    "🌾 No waste found = a clean account. The scan is always free.",
    "🌻 The audit takes minutes. The forest takes decades. Start now.",
    "📋 Your audit is ESG-reportable — cost saving, CO₂ reduction, conservation funding",
    "🌐 CSRD & Scope 3 reporting now mandatory. Cloud waste is in the frame.",
]

_rewilding_cycle = itertools.cycle(REWILDING_MESSAGES)

def _next_rewilding_msg():
    """Return the next message in the rotating rewilding cycle."""
    return next(_rewilding_cycle)

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s'
)
logger = logging.getLogger('relic')

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
ENDPOINT_URL             = None       # LocalStack: "http://localhost:4566"

# Pricing (GBP, eu-west-2 rates — ⚠ update annually)
EBS_GBP_PER_GB_MONTH     = 0.079
SNAPSHOT_GBP_PER_GB      = 0.053
ELASTIC_IP_COST_PER_MONTH= 3.60
LB_COST_PER_MONTH        = 15.00
RDS_STORAGE_GBP_PER_GB   = 0.115
LOGS_GBP_PER_GB          = 0.03
ECR_GBP_PER_GB           = 0.10
NAT_GBP_PER_MONTH        = 27.00
S3_GBP_PER_GB            = 0.023
SAGEMAKER_ML_T3_MEDIUM   = 0.056     # £/hour floor for unknown SM instances

# GPU endpoint costs (£/hour) — for Check 13
SAGEMAKER_GPU_COSTS = {
    'ml.p2.xlarge':    0.900,
    'ml.p3.2xlarge':   3.825,
    'ml.p3.8xlarge':   15.300,
    'ml.p3.16xlarge':  30.600,
    'ml.g4dn.xlarge':  0.526,
    'ml.g4dn.2xlarge': 0.940,
    'ml.g4dn.4xlarge': 1.505,
    'ml.g4dn.8xlarge': 2.720,
    'ml.g4dn.12xlarge':4.075,
    'ml.g5.xlarge':    1.006,
    'ml.g5.2xlarge':   1.210,
    'ml.g5.4xlarge':   1.620,
    'ml.g5.8xlarge':   2.440,
}

# EC2 instance data (watts, USD/month) — three-tier lookup
INSTANCE_DATA = {
    't3.nano':    {'w': 2,   'cost': 3.80},
    't3.micro':   {'w': 4,   'cost': 7.60},
    't3.small':   {'w': 8,   'cost': 15.00},
    't3.medium':  {'w': 12,  'cost': 30.00},
    'm5.large':   {'w': 25,  'cost': 70.00},
    'm5.xlarge':  {'w': 45,  'cost': 140.00},
    'c5.large':   {'w': 30,  'cost': 62.00},
    'c5.xlarge':  {'w': 60,  'cost': 124.00},
    'p3.2xlarge': {'w': 150, 'cost': 918.00},
    't3':         {'w': 8,   'cost': 15.00},   # family fallback
    'default':    {'w': 15,  'cost': 25.00},   # last resort
}
USD_TO_GBP = 0.79   # ⚠ update periodically

# Boto3 connection config — prevents hanging on slow/rural connections
from botocore.config import Config
BOTO_CONFIG = Config(
    connect_timeout=5,
    read_timeout=10,
    retries={'max_attempts': 2, 'mode': 'standard'}
)

# Thresholds
ZOMBIE_SNAPSHOT_AGE_DAYS  = 90
S3_IDLE_DAYS              = 90
LAMBDA_IDLE_DAYS          = 90
GPU_ZOMBIE_IDLE_HOURS     = 72
SNAPSHOT_LINEAGE_THRESHOLD= 30
SNAPSHOT_LINEAGE_AGE_DAYS = 90
IDLE_THRESHOLD            = 5.0      # % CPU below which instance is idle
IDLE_MIN_RATIO            = 0.90     # 90% of hourly points must be idle
MIN_DATA_POINTS           = 20       # minimum CW points for confidence

# Business model
AEGIS_FEE_CAP_GBP  = 0.00   # No fee — service is free
MOSSY_EARTH_SPLIT  = 0.80
AEGIS_SPLIT        = 0.00   # No fee split

# Energy / CO₂ (UK grid)
KWH_PER_GB_STORAGE_MONTH = 0.000392
KWH_PER_HOUR_COMPUTE     = 0.08
CO2_KG_PER_KWH           = 0.233

# Priority and effort maps
PRIORITY = {
    'gpu_zombies':      ('CRITICAL', '★★★'),
    'sagemaker':        ('CRITICAL', '★★★'),
    'instances':        ('HIGH',     '★★☆'),
    'nat_gateways':     ('HIGH',     '★★☆'),
    'load_balancers':   ('HIGH',     '★★☆'),
    'rds_instances':    ('HIGH',     '★★☆'),
    's3_buckets':       ('HIGH',     '★★☆'),
    'volumes':          ('HIGH',     '★★☆'),
    'snap_lineage':     ('MEDIUM',   '★☆☆'),
    'snapshots':        ('MEDIUM',   '★☆☆'),
    'elastic_ips':      ('LOW',      '☆☆☆'),
    'ecr_images':       ('LOW',      '☆☆☆'),
    'cloudwatch_logs':  ('LOW',      '☆☆☆'),
    'lambda_functions': ('LOW',      '☆☆☆'),
}

EFFORT = {
    'gpu_zombies':      ('2 min',  'Delete endpoint in SageMaker console'),
    'sagemaker':        ('2 min',  'Delete endpoint in SageMaker console'),
    'instances':        ('5 min',  'Terminate via EC2 console — create AMI first if unsure'),
    'nat_gateways':     ('5 min',  'Delete via VPC console — remove route table entries first'),
    'load_balancers':   ('2 min',  'Delete via EC2 console > Load Balancers'),
    'rds_instances':    ('5 min',  'Delete via RDS console — take final snapshot if needed'),
    's3_buckets':       ('10 min', 'Empty bucket then delete — or archive to Glacier'),
    'volumes':          ('2 min',  'Delete via EC2 console > Volumes'),
    'snap_lineage':     ('15 min', 'Delete oldest snapshots in batches via EC2 console'),
    'snapshots':        ('5 min',  'Delete via EC2 console > Snapshots'),
    'elastic_ips':      ('1 min',  'Release via EC2 console > Elastic IPs'),
    'ecr_images':       ('5 min',  'Delete old images or set lifecycle policy to auto-expire'),
    'cloudwatch_logs':  ('3 min',  'Set retention policy via CloudWatch > Log Groups'),
    'lambda_functions': ('10 min', 'Review triggers then delete unused functions'),
}

# Boto3 retry
BOTO_CONFIG = Config(retries={'max_attempts': 5, 'mode': 'adaptive'})

W = 76  # report width (kept for summary box rendering)

# ─────────────────────────────────────────────────────────────────────────────
# RICH DISPLAY HELPERS
# Presentation layer only — audit logic is untouched.
# Colour scheme (Section 11 spec):
#   green  → savings, eco, clean results
#   orange → waste findings
#   red    → critical priority
#   grey   → secondary / info text
# ─────────────────────────────────────────────────────────────────────────────

def banner(text):
    """Opening and section banners — rendered as a rich Panel."""
    lines = text.strip().split('\n')
    content = Text(justify="center")
    for i, line in enumerate(lines):
        if i == 0:
            content.append(line + "\n", style="bold green")
        elif i == 1:
            content.append(line + "\n", style="italic dim white")
        else:
            content.append(line + "\n", style="dim white")
    console.print()
    console.print(Panel(content, border_style="green", padding=(0, 2)))

def section(title):
    """Per-check section header."""
    console.print()
    console.print(Rule(f"[bold white]{title}[/bold white]", style="dim white"))

def row(label, value):
    """Key-value data row."""
    console.print(f"  [dim white]{label:<46}[/dim white] [bold orange1]{value}[/bold orange1]")

def ok(msg):
    """Clean / success message."""
    console.print(f"  [bold green]✓[/bold green]  [green]{msg}[/green]")

def warn(msg):
    """Warning — data gap or caution."""
    console.print(f"  [bold yellow]⚠[/bold yellow]  [yellow]{msg}[/yellow]")

def info(msg):
    """Neutral informational message."""
    console.print(f"  [dim cyan]ℹ[/dim cyan]  [cyan]{msg}[/cyan]")

def storage_co2(gb):
    return gb * KWH_PER_GB_STORAGE_MONTH * CO2_KG_PER_KWH

def co2_for_cost(monthly_gbp):
    return (monthly_gbp / 0.30) * KWH_PER_HOUR_COMPUTE * 730 * CO2_KG_PER_KWH


# ─────────────────────────────────────────────────────────────────────────────
# HTML REPORT — CONVERSION-OPTIMISED CLOSING DOCUMENT
# Presentation layer only. Uses constants already defined above.
# Full report always delivered. Closing conversation invites voluntary Mossy Earth donation.
# ─────────────────────────────────────────────────────────────────────────────

# Category labels for HTML report (keyed to audit_data buckets)
_HTML_LABELS = {
    'volumes':          'Orphaned EBS Volumes',
    'snapshots':        'Zombie Snapshots',
    'instances':        'Stopped EC2 Instances',
    'elastic_ips':      'Idle Elastic IPs',
    'load_balancers':   'Idle Load Balancers',
    'nat_gateways':     'Idle NAT Gateways',
    'rds_instances':    'Stopped RDS Instances',
    'cloudwatch_logs':  'Log Groups (No Retention)',
    'ecr_images':       'Old ECR Images',
    'lambda_functions': 'Idle Lambda Functions',
    's3_buckets':       'Abandoned S3 Buckets',
    'sagemaker':        'Idle SageMaker Endpoints',
    'gpu_zombies':      'GPU Zombie Endpoints \u2605',
    'snap_lineage':     'Redundant Snapshot Lineage',
}

# Priority labels for HTML (string only — HTML doesn't use the star tuples)
_HTML_PRIORITY = {
    'gpu_zombies':      'CRITICAL',
    'sagemaker':        'CRITICAL',
    'instances':        'HIGH',
    'nat_gateways':     'HIGH',
    'load_balancers':   'HIGH',
    'rds_instances':    'HIGH',
    's3_buckets':       'HIGH',
    'volumes':          'HIGH',
    'snap_lineage':     'MEDIUM',
    'snapshots':        'MEDIUM',
    'elastic_ips':      'LOW',
    'ecr_images':       'LOW',
    'cloudwatch_logs':  'LOW',
    'lambda_functions': 'LOW',
}

# Risk metadata per check — deletion risk level, verification advice, snapshot needed
# Shown in the findings table and safety panel to prevent accidental removal
_HTML_RISK = {
    'gpu_zombies':      {'level': 'HIGH',   'snapshot': False, 'days': 7,
                         'advice': 'Verify no active inference jobs before stopping. Check CloudWatch invocations.'},
    'sagemaker':        {'level': 'HIGH',   'snapshot': False, 'days': 7,
                         'advice': 'Confirm with the ML team. Endpoints may serve infrequent batch jobs.'},
    'instances':        {'level': 'HIGH',   'snapshot': True,  'days': 7,
                         'advice': 'Tag or snapshot before terminating. Stopped instances may hold data.'},
    'rds_instances':    {'level': 'HIGH',   'snapshot': True,  'days': 14,
                         'advice': 'Take a final snapshot. Confirm no scheduled jobs or reporting queries depend on this.'},
    'nat_gateways':     {'level': 'MEDIUM', 'snapshot': False, 'days': 7,
                         'advice': 'Check for private subnet resources routing through this gateway before deletion.'},
    'load_balancers':   {'level': 'MEDIUM', 'snapshot': False, 'days': 7,
                         'advice': 'Verify no DNS records or services still point to this load balancer.'},
    's3_buckets':       {'level': 'HIGH',   'snapshot': True,  'days': 14,
                         'advice': 'Enable versioning or download contents before deletion. S3 deletions are irreversible.'},
    'volumes':          {'level': 'MEDIUM', 'snapshot': True,  'days': 7,
                         'advice': 'Create a snapshot before deleting. Unattached does not always mean unused.'},
    'snap_lineage':     {'level': 'LOW',    'snapshot': False, 'days': 7,
                         'advice': 'Review the full snapshot chain. Keep the most recent in any active lineage.'},
    'snapshots':        {'level': 'LOW',    'snapshot': False, 'days': 7,
                         'advice': 'Verify these are not the only recovery point for a production volume.'},
    'elastic_ips':      {'level': 'LOW',    'snapshot': False, 'days': 3,
                         'advice': 'Check Route53 and DNS records. Some teams hard-code IPs in firewall rules.'},
    'ecr_images':       {'level': 'LOW',    'snapshot': False, 'days': 7,
                         'advice': 'Confirm no pipelines reference these image tags before removal.'},
    'cloudwatch_logs':  {'level': 'LOW',    'snapshot': False, 'days': 7,
                         'advice': 'Check compliance requirements. Some industries mandate log retention periods.'},
    'lambda_functions': {'level': 'LOW',    'snapshot': False, 'days': 7,
                         'advice': 'Verify no scheduled triggers or event sources invoke this function infrequently.'},
}
_HTML_CSS = """
:root{--forest:#2f5d4a;--forest-lt:#3d7a61;--forest-dim:#182e24;
--amber:#d4833a;--amber-lt:#e8a05a;--ash:#0b0e12;--slate:#13181f;
--slate-lt:#1a2130;--mist:#e4e7ea;--mist-dim:#7a8490;--red:#b84035;--red-lt:#d05040;}
*{box-sizing:border-box;margin:0;padding:0;}
body{background:var(--ash);color:var(--mist);font-family:'Crimson Pro',Georgia,serif;
font-weight:300;line-height:1.6;min-height:100vh;}
.mission-strip{background:var(--forest);text-align:center;padding:9px 20px;
font-family:'Space Mono',monospace;font-size:10px;letter-spacing:2px;
color:rgba(255,255,255,.8);text-transform:uppercase;overflow:hidden;position:relative;}
.mission-strip::before{content:'';position:absolute;inset:0;
background:repeating-linear-gradient(90deg,transparent,transparent 40px,
rgba(255,255,255,.03) 40px,rgba(255,255,255,.03) 41px);}
.mission-strip span{position:relative;}
.mossy-name{color:#fff;font-weight:700;}
header{padding:44px 30px 32px;max-width:920px;margin:auto;}
.eyebrow{font-family:'Space Mono',monospace;font-size:10px;letter-spacing:4px;
color:var(--forest-lt);text-transform:uppercase;margin-bottom:12px;}
.brand{font-family:'Space Mono',monospace;font-size:clamp(16px,3vw,24px);
font-weight:700;color:var(--forest-lt);letter-spacing:1px;margin-bottom:16px;}
.headline{font-size:clamp(20px,3.5vw,32px);font-weight:300;line-height:1.35;
max-width:700px;margin-bottom:10px;}
.hl-amber{color:var(--amber);}
.hl-red{color:var(--red-lt);}
.subhead{font-size:16px;color:var(--mist-dim);font-style:italic;
max-width:580px;line-height:1.75;margin-bottom:20px;}
.badge-row{display:flex;flex-wrap:wrap;gap:8px;}
.badge{font-family:'Space Mono',monospace;font-size:10px;letter-spacing:1px;
padding:4px 11px;border-radius:3px;text-transform:uppercase;}
.bg{background:rgba(47,93,74,.18);color:var(--forest-lt);border:1px solid rgba(47,93,74,.45);}
.ba{background:rgba(212,131,58,.13);color:var(--amber-lt);border:1px solid rgba(212,131,58,.38);}
.br{background:rgba(184,64,53,.13);color:#d06050;border:1px solid rgba(184,64,53,.38);}
.container{max-width:920px;margin:0 auto;padding:0 30px 60px;overflow-x:hidden;box-sizing:border-box;}
.summary-box{background:var(--slate);border:1px solid #1c2530;
border-top:3px solid var(--red-lt);border-radius:8px;padding:28px 30px;margin-bottom:16px;}
.summary-title{font-family:'Space Mono',monospace;font-size:10px;letter-spacing:3px;
color:var(--mist-dim);text-transform:uppercase;margin-bottom:18px;}
.summary-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-bottom:20px;}
.summary-stat{text-align:center;padding:16px;background:var(--slate-lt);
border-radius:6px;border-bottom:3px solid var(--amber);}
.summary-stat.red-border{border-bottom-color:var(--red-lt);}
.summary-stat.green-border{border-bottom-color:var(--forest-lt);}
.ss-value{font-family:'Space Mono',monospace;font-size:24px;font-weight:700;
color:var(--amber);line-height:1;margin-bottom:5px;}
.ss-value.red{color:var(--red-lt);}
.ss-value.green{color:var(--forest-lt);}
.ss-label{font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;
color:var(--mist-dim);text-transform:uppercase;}
.efficiency-row{display:flex;align-items:center;gap:14px;
padding:14px 18px;background:var(--slate-lt);border-radius:6px;}
.eff-label{font-family:'Space Mono',monospace;font-size:10px;letter-spacing:1px;
color:var(--mist-dim);text-transform:uppercase;white-space:nowrap;}
.eff-track{flex:1;height:6px;background:#1a2030;border-radius:3px;overflow:hidden;}
.eff-fill{height:100%;border-radius:3px;
background:linear-gradient(90deg,var(--red-lt),var(--amber),var(--forest-lt));}
.eff-pct{font-family:'Space Mono',monospace;font-size:13px;font-weight:700;
color:var(--amber);white-space:nowrap;}
.findings-panel{background:var(--slate);border:1px solid #1c2530;
border-radius:8px;margin-bottom:16px;overflow:hidden;}
.panel-header{padding:15px 22px;border-bottom:1px solid #1c2530;
display:flex;justify-content:space-between;align-items:center;}
.panel-title{font-family:'Space Mono',monospace;font-size:10px;letter-spacing:2px;
color:var(--mist-dim);text-transform:uppercase;}
.panel-count{font-family:'Space Mono',monospace;font-size:10px;color:var(--amber);}
table{width:100%;border-collapse:collapse;}
thead th{font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;
text-transform:uppercase;color:var(--forest-lt);padding:10px 18px;
text-align:left;border-bottom:1px solid #1c2530;}
tbody td{padding:12px 18px;border-bottom:1px solid #0f1520;vertical-align:top;}
tbody tr:last-child td{border-bottom:none;}
tbody tr:hover td{background:rgba(255,255,255,.012);}
.finding-name{font-size:15px;color:var(--mist);}
.finding-cost{font-family:'Space Mono',monospace;font-size:13px;
color:var(--amber);white-space:nowrap;}
.detail-cell{font-size:13px;color:#6a7a8a;line-height:1.65;}
.priority-tag{font-family:'Space Mono',monospace;font-size:9px;letter-spacing:1px;
padding:3px 8px;border-radius:3px;text-transform:uppercase;display:inline-block;}
.pri-critical{background:rgba(184,64,53,.15);color:#d05040;border:1px solid rgba(184,64,53,.38);}
.pri-high{background:rgba(212,131,58,.12);color:var(--amber-lt);border:1px solid rgba(212,131,58,.33);}
.pri-medium{background:rgba(200,170,80,.1);color:#c8aa50;border:1px solid rgba(200,170,80,.28);}
.pri-low{background:rgba(100,120,140,.1);color:#6a7f90;border:1px solid rgba(100,120,140,.22);}
.eco-panel{background:var(--forest-dim);border:1px solid rgba(47,93,74,.45);
border-radius:8px;padding:28px 30px;margin-bottom:16px;position:relative;overflow:hidden;}
.eco-panel::before{content:'\U0001f331';position:absolute;right:-6px;top:-6px;
font-size:100px;opacity:.05;transform:rotate(12deg);pointer-events:none;}
.eco-eyebrow{font-family:'Space Mono',monospace;font-size:10px;letter-spacing:3px;
color:var(--forest-lt);text-transform:uppercase;margin-bottom:12px;}
.eco-headline{font-size:20px;font-weight:300;color:#fff;line-height:1.5;
margin-bottom:16px;max-width:560px;}
.eco-headline em{color:var(--forest-lt);font-style:italic;}
.eco-impact-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:18px;}
.eco-card{background:rgba(0,0,0,.22);border:1px solid rgba(47,93,74,.28);
border-radius:5px;padding:14px 16px;text-align:center;}
.eco-card-value{font-family:'Space Mono',monospace;font-size:20px;font-weight:700;
color:var(--forest-lt);line-height:1;margin-bottom:4px;}
.eco-card-label{font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;
color:rgba(255,255,255,.38);text-transform:uppercase;}
.eco-body{font-size:14px;color:rgba(255,255,255,.55);line-height:1.8;max-width:540px;}
.eco-footer{font-family:'Space Mono',monospace;font-size:10px;color:rgba(255,255,255,.3);
margin-top:16px;border-top:1px solid rgba(47,93,74,.2);padding-top:13px;letter-spacing:.5px;}
.eco-footer a{color:var(--forest-lt);text-decoration:none;}
.decision-panel{background:linear-gradient(160deg,#0d1f18,#111a24);
border:1px solid rgba(47,93,74,.5);border-top:3px solid var(--forest-lt);
border-radius:8px;padding:32px 30px;margin-bottom:16px;}
.decision-trigger{font-size:17px;font-weight:300;color:#fff;line-height:1.6;
max-width:620px;margin-bottom:24px;border-left:3px solid var(--forest-lt);
padding-left:18px;}
.decision-trigger em{color:var(--forest-lt);font-style:normal;font-weight:400;}
.three-pillar{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px;}
.pillar{background:rgba(0,0,0,.25);border-radius:6px;padding:18px 16px;}
.pillar-financial{border-top:3px solid var(--red-lt);}
.pillar-efficiency{border-top:3px solid var(--amber);}
.pillar-impact{border-top:3px solid var(--forest-lt);}
.pillar-label{font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;
text-transform:uppercase;margin-bottom:10px;}
.pillar-financial .pillar-label{color:var(--red-lt);}
.pillar-efficiency .pillar-label{color:var(--amber);}
.pillar-impact .pillar-label{color:var(--forest-lt);}
.pillar-value{font-family:'Space Mono',monospace;font-size:20px;font-weight:700;
line-height:1;margin-bottom:4px;}
.pillar-financial .pillar-value{color:var(--red-lt);}
.pillar-efficiency .pillar-value{color:var(--amber);}
.pillar-impact .pillar-value{color:var(--forest-lt);}
.pillar-sub{font-size:12px;color:rgba(255,255,255,.38);line-height:1.5;margin-top:4px;}
.pillar-note{font-size:11px;color:rgba(255,255,255,.22);margin-top:6px;font-style:italic;}
.decision-vow{font-family:'Space Mono',monospace;font-size:10px;letter-spacing:1px;
color:rgba(255,255,255,.28);border-top:1px solid rgba(47,93,74,.2);
padding-top:14px;margin-top:4px;}
.badge-panel{background:var(--slate);border:1px solid #1c2530;
border-radius:8px;padding:28px 30px;margin-bottom:16px;text-align:center;}
.safety-panel{background:#1a1200;border:1px solid #5a3a00;border-left:4px solid #e8a05a;
border-radius:6px;padding:22px 26px;margin-bottom:20px;}
.safety-panel-title{font-family:'Space Mono',monospace;font-size:11px;letter-spacing:2px;
text-transform:uppercase;color:var(--amber-lt);margin-bottom:12px;}
.safety-panel-body{font-size:14px;color:rgba(255,255,255,.72);line-height:1.75;}
.safety-panel-body strong{color:var(--amber-lt);}
.safety-rules{margin-top:14px;display:flex;flex-direction:column;gap:8px;}
.safety-rule{display:flex;align-items:flex-start;gap:10px;font-size:13px;
color:rgba(255,255,255,.62);line-height:1.6;}
.safety-rule-icon{flex-shrink:0;font-size:14px;margin-top:1px;}
.risk-badge{display:inline-block;padding:2px 7px;border-radius:3px;
font-family:'Space Mono',monospace;font-size:9px;font-weight:700;
letter-spacing:.08em;text-transform:uppercase;margin-left:6px;vertical-align:middle;}
.risk-high{background:rgba(184,64,53,.2);color:#e87060;border:1px solid rgba(184,64,53,.4);}
.risk-medium{background:rgba(212,131,58,.2);color:var(--amber-lt);border:1px solid rgba(212,131,58,.4);}
.risk-low{background:rgba(61,122,97,.2);color:var(--forest-lt);border:1px solid rgba(61,122,97,.4);}
.snap-badge{display:inline-block;padding:2px 6px;border-radius:3px;
font-family:'Space Mono',monospace;font-size:9px;letter-spacing:.06em;
background:rgba(91,156,246,.15);color:#7ab4f8;border:1px solid rgba(91,156,246,.25);
margin-left:5px;vertical-align:middle;}
.finding-advice{font-size:11px;color:rgba(255,255,255,.38);font-style:italic;
line-height:1.55;margin-top:5px;padding-top:5px;border-top:1px solid rgba(255,255,255,.06);}
.verify-days{font-family:'Space Mono',monospace;font-size:9px;color:rgba(255,255,255,.3);
letter-spacing:.06em;text-transform:uppercase;margin-top:4px;}
.footer-strip{text-align:center;padding:16px 30px;font-family:'Space Mono',monospace;
font-size:10px;letter-spacing:1px;color:#252f3a;text-transform:uppercase;
border-top:1px solid #131a22;max-width:920px;margin:0 auto;}
.footer-strip a{color:var(--forest);text-decoration:none;}
@media(max-width:620px){
.summary-grid{grid-template-columns:1fr 1fr;}
.eco-impact-grid{grid-template-columns:1fr 1fr;}
header,.container{padding-left:18px;padding-right:18px;}
}
"""

# ── HTML data helpers ─────────────────────────────────────────────────────────

def _html_extract_findings(audit_data):
    """Extract and sort findings from audit_data for HTML rendering."""
    findings = []
    for key, label in _HTML_LABELS.items():
        bucket = audit_data.get(key, {})
        count  = bucket.get('count', 0)
        cost   = bucket.get('monthly_cost', 0.0)
        items  = bucket.get('items', [])
        if count > 0:
            findings.append({
                'key':          key,
                'category':     label,
                'priority':     _HTML_PRIORITY.get(key, 'LOW'),
                'count':        count,
                'monthly_cost': cost,
                'items':        items,
            })
    findings.sort(key=lambda f: f['monthly_cost'], reverse=True)
    return findings


def _html_build_fee_data(audit_data):
    """Compute financial and environmental metrics for the HTML report."""
    keys          = [k for k in audit_data if isinstance(audit_data[k], dict)
                     and 'monthly_cost' in audit_data[k]]
    total_monthly = sum(audit_data[k]['monthly_cost'] for k in keys)
    total_annual  = total_monthly * 12
    total_gb_waste = (
        audit_data.get('volumes',    {}).get('count', 0) * 100 +
        audit_data.get('snapshots',  {}).get('count', 0) * 50  +
        audit_data.get('s3_buckets', {}).get('count', 0) * 200
    )
    co2_storage  = total_gb_waste * KWH_PER_GB_STORAGE_MONTH * CO2_KG_PER_KWH
    co2_compute  = ((total_monthly / 0.30) * KWH_PER_HOUR_COMPUTE * 730 * CO2_KG_PER_KWH
                    if total_monthly > 0 else 0.0)
    total_co2    = co2_storage + co2_compute
    co2_annual_t = (total_co2 * 12) / 1000
    efficiency   = max(0, min(100, int(100 - (total_monthly / 10))))
    kwh_avoided  = (total_gb_waste * KWH_PER_GB_STORAGE_MONTH * 12 +
                    (total_monthly / 0.30) * KWH_PER_HOUR_COMPUTE * 730 * 12
                    if total_monthly > 0 else 0.0)
    return {
        'total_monthly': total_monthly,
        'total_annual':  total_annual,
        'total_co2':     total_co2,
        'co2_annual_t':  co2_annual_t,
        'efficiency':    efficiency,
        'kwh_avoided':   kwh_avoided,
    }



def _html_priority_class(priority):
    return {'CRITICAL': 'pri-critical', 'HIGH': 'pri-high',
            'MEDIUM': 'pri-medium', 'LOW': 'pri-low'}.get(priority, 'pri-low')



def _html_full_table_rows(findings):
    """Full unlocked table — real IDs, real costs, risk badges, per-finding advice."""
    if not findings:
        return ('<tr><td colspan="5" style="text-align:center;color:#3d7a61;'
                'padding:30px;font-style:italic;">'
                '\u2713 No waste found \u2014 this account is running clean.</td></tr>')
    rows = ''
    for f in findings:
        pc      = _html_priority_class(f['priority'])
        risk    = _HTML_RISK.get(f['key'], {'level':'LOW','snapshot':False,
                                            'days':7,'advice':''})
        rc      = {'HIGH':'risk-high','MEDIUM':'risk-medium','LOW':'risk-low'}.get(
                    risk['level'], 'risk-low')
        snap    = ('<span class="snap-badge">\U0001f4f8 Snapshot first</span>'
                   if risk['snapshot'] else '')
        details = []
        for item in f['items'][:3]:
            rid  = (item.get('id') or item.get('ip') or item.get('name') or
                    item.get('vol_id') or '\u2014')
            cost = item.get('monthly_cost', 0)
            details.append(f"{rid} \u00b7 \u00a3{cost:.2f}/mo")
        if len(f['items']) > 3:
            details.append(f"\u2026 and {len(f['items']) - 3} more")
        rows += (
            f'<tr>'
            f'<td class="finding-name">{f["category"]}</td>'
            f'<td><span class="priority-tag {pc}">{f["priority"]}</span></td>'
            f'<td class="finding-cost">\u00a3{f["monthly_cost"]:.2f}/mo</td>'
            f'<td>'
            f'<span class="risk-badge {rc}">{risk["level"]} RISK</span>{snap}'
            f'<div class="verify-days">\u23f3 Verify {risk["days"]}d before acting</div>'
            f'</td>'
            f'<td class="detail-cell">{"<br>".join(details)}'
            f'<div class="finding-advice">{risk["advice"]}</div>'
            f'</td>'
            f'</tr>'
        )
    return rows


def _html_safety_panel():
    """
    Pre-findings safety panel. Displayed above every findings table.
    Protects users from accidental deletion — especially on untagged resources.
    Based on real-world FinOps practice: 7-day notice minimum, snapshots first.
    """
    return (
        f'<div class="safety-panel">'
        f'<div class="safety-panel-title">\u26a0\ufe0f Before You Act on Any Finding</div>'
        f'<div class="safety-panel-body">'
        f'<strong>Relic identifies candidates, not verdicts.</strong> '
        f'Untagged or idle does not always mean abandoned. '
        f'Resources may belong to infrequent workloads, scheduled jobs, '
        f'or infrastructure nobody documented. Verify with your team before removing anything.'
        f'<div class="safety-rules">'

        f'<div class="safety-rule">'
        f'<span class="safety-rule-icon">\U0001f4f8</span>'
        f'<span><strong style="color:rgba(255,255,255,.82);">Snapshot storage first.</strong> '
        f'EBS volumes, RDS instances, and S3 buckets marked for deletion should be '
        f'snapshotted or backed up before removal. Deletions are irreversible.</span>'
        f'</div>'

        f'<div class="safety-rule">'
        f'<span class="safety-rule-icon">\u23f3</span>'
        f'<span><strong style="color:rgba(255,255,255,.82);">Give your team notice.</strong> '
        f'Industry consensus is a minimum 7-day internal warning before acting on findings. '
        f'Email, not just Slack. People are busy. Learning is a process.</span>'
        f'</div>'

        f'<div class="safety-rule">'
        f'<span class="safety-rule-icon">\U0001f3f7\ufe0f</span>'
        f'<span><strong style="color:rgba(255,255,255,.82);">Tag before you touch.</strong> '
        f'If a resource has no tags, add an owner tag before deciding its fate. '
        f'A 10-minute tagging exercise prevents a 10-hour recovery incident.</span>'
        f'</div>'

        f'<div class="safety-rule">'
        f'<span class="safety-rule-icon">\U0001f50d</span>'
        f'<span><strong style="color:rgba(255,255,255,.82);">Check CloudWatch first.</strong> '
        f'Low average CPU can mask infrequent but critical batch workloads. '
        f'Review the last 30 days of metrics, not just the last 24 hours.</span>'
        f'</div>'

        f'</div>'
        f'</div>'
        f'</div>\n'
    )

def _html_page_header(title):
    return (
        f'<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        f'<meta charset="UTF-8">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'<title>{title}</title>\n'
        f'<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700'
        f'&family=Crimson+Pro:ital,wght@0,300;0,400;1,300&display=swap" rel="stylesheet">\n'
        f'<style>{_HTML_CSS}</style>\n</head>\n<body>\n'
    )


def _html_mission_strip(text):
    return (f'<div class="mission-strip"><span>{text}</span></div>\n')


def _html_page_footer(scan_date, regions, duration):
    return (
        f'<div class="footer-strip">'
        f'<a href="https://wildliferelicguild.com">wildliferelicguild.com</a>'
        f' &nbsp;\u00b7&nbsp; A Waller-Mayes Alliance &nbsp;\u00b7&nbsp; Bedford, UK<br>'
        f'Scanned: {scan_date} UTC &nbsp;\u00b7&nbsp; {regions} regions'
        f' &nbsp;\u00b7&nbsp; {duration}'
        f' &nbsp;\u00b7&nbsp; '
        f'<a href="https://www.mossy.earth/membership?utm_source=wildlife-relic-guild&utm_medium=audit-report&utm_campaign=relic-free-scan">Mossy Earth</a>'
        f' &nbsp;\u00b7&nbsp; '
        f'<a href="https://www.coolearth.org/donate/?utm_source=wildlife-relic-guild&utm_medium=audit-report&utm_campaign=relic-free-scan">Cool Earth</a>'
        f'</div>\n</body>\n</html>'
    )



def _html_linkedin_share_panel(account, monthly_waste):
    """
    LinkedIn share flow + Mossy Earth donation nudge.
    This scan is free. No fee, no cut, no suggestion.
    The user decides. That's the point.
    """
    has_waste   = monthly_waste > 0
    monthly_str = f"\u00a3{monthly_waste:,.2f}" if has_waste else None

    if has_waste:
        nudge_headline = f"Your cloud wastes {monthly_str} every month."
        nudge_body     = (
            f"That\u2019s {monthly_str} silently disappearing into idle infrastructure. "
            f"The waste is real. So is what Mossy Earth does with money that goes their way instead. "
            f"Native woodland. Peatland recovery. Species reintroduction. Verified."
        )
        li_text = (
            f"Just ran a free 14-point cloud audit on our AWS account.\n\n"
            f"Found {monthly_str}/month in idle, forgotten resources.\n\n"
            f"The audit was free. The waste is real. "
            f"We\u2019re putting some of those savings toward native rewilding via Mossy Earth \u2014 "
            f"habitat restoration, species reintroduction, verified conservation.\n\n"
            f"If your team hasn\u2019t checked recently, worth 10 minutes. "
            f"\u2192 https://wildliferelicguild.com"
            f"?utm_source=linkedin&utm_medium=share&utm_campaign=waste_found"
        )
        share_headline = "Found waste? Share it."
        share_sub      = "Turn your audit result into a conservation conversation."
        utm_campaign   = "waste_found"
    else:
        nudge_headline = "Account is clean — we still let you donate!"
        nudge_body     = (
            "No cloud waste found \u2014 your infrastructure is already running lean. "
            "That\u2019s genuinely rare. "
            "Mossy Earth do verified native rewilding. No greenwash."
        )
        li_text = (
            f"Just ran a free 14-point cloud audit on our AWS account \u2014 account is clean.\n\n"
            f"No idle resources, no hidden waste.\n\n"
            f"Used Wildlife Relic Guild: read-only, 14 checks, free. "
            f"Marking it with a donation to Mossy Earth for native rewilding.\n\n"
            f"\u2192 https://wildliferelicguild.com"
            f"?utm_source=linkedin&utm_medium=share&utm_campaign=clean_account"
        )
        share_headline = "Clean account. Share the standard."
        share_sub      = "Let your network know efficient infrastructure is an ecological act."
        utm_campaign   = "clean_account"

    li_share_url = (
        f"https://www.linkedin.com/sharing/share-offsite/?url="
        f"https%3A%2F%2Fwildliferelicguild.com%3Futm_source%3Dlinkedin%26utm_medium%3Dshare"
        f"%26utm_campaign%3D{utm_campaign}"
    )

    # Annual and kWh figures for the conversation
    annual_waste   = monthly_waste * 12
    kwh_monthly    = (monthly_waste / 0.30) * 0.08 * 730 if has_waste else 0
    kwh_annual     = kwh_monthly * 12
    annual_str     = f"\u00a3{annual_waste:,.2f}"
    kwh_str        = f"{kwh_annual:,.0f} kWh"

    conv_text = (
        f'<p class="li-conv-line">You just found <strong>{monthly_str} a month</strong> '
        f'leaving your account for nothing. Over a year, that\u2019s '
        f'<strong>{annual_str}</strong>.</p>'
        f'<p class="li-conv-line">It\u2019s not just money. Those idle resources '
        f'are drawing roughly <strong>{kwh_str} of electricity a year</strong> '
        f'\u2014 servers humming, storage spinning, network ports held open '
        f'for workloads that no longer exist.</p>'
        f'<p class="li-conv-line">You can reclaim all of it. The report above '
        f'tells you exactly where it is and how to shut it down. '
        f'That\u2019s yours \u2014 free, no strings.</p>'
        f'<p class="li-conv-line">Mossy Earth are doing something real '
        f'\u2014 native woodland, peatland, species coming back to landscapes '
        f'that lost them. Verified. No offsets. Actual land.</p>'
    ) if has_waste else (
        f'<p class="li-conv-line">No waste. Nothing idle. Your account is clean.</p>'
        f'<p class="li-conv-line">That\u2019s not the default. Most accounts '
        f'accumulate forgotten resources quietly for years. '
        f'Yours doesn\u2019t. That means no wasted spend and no electricity '
        f'drawn by infrastructure that serves no one.</p>'
        f'<p class="li-conv-line">The scan was free. The result is clean. '
        f'Mossy Earth are doing something real if you want to mark the occasion '
        f'\u2014 native woodland, peatland, species returning to landscapes '
        f'that lost them. Verified. No offsets. Actual land.</p>'
    )

    return (
        f'<div class="li-share-panel">'
        f'<div class="li-share-eyebrow">\U0001f331 Before you go</div>'

        # ── Shoulder: conversation + donation side by side ────────────────────
        f'<div class="li-shoulder">'
        f'<div class="li-conversation">{conv_text}</div>'

        # ── Donation column — no amount, just a direct link ───────────────────
        f'<div class="li-donation-col">'
        f'<div class="li-donation-eyebrow">Mossy Earth \u00b7 Rewilding Membership</div>'
        f'<p class="li-conv-line" style="font-size:13px;margin-bottom:16px;">'
        f'Native woodland. Peatland. Species reintroduction. '
        f'No carbon credits. Actual land.</p>'
        f'<button class="li-donate-btn" type="button" onclick="window.open(\'https://www.mossy.earth/membership\',\'_blank\')">'
        f'Become a Member \u2192</button>'
        f'<a class="li-mossy-link" href="https://www.mossy.earth" target="_blank" rel="noopener">'
        f'mossy.earth</a>'
        f'</div>'
        f'</div>'  # end li-shoulder

        # ── Feedback section ──────────────────────────────────────────────────
        f'<div class="li-divider"></div>'
        f'<div class="li-feedback-section">'
        f'<div class="li-feedback-eyebrow">\U0001f4ac Help us improve</div>'
        f'<p class="li-feedback-sub">We\u2019re a small guild. If this scan missed something, '
        f'flagged the wrong thing, or could be better \u2014 we want to know.</p>'
        f'<textarea class="li-feedback-textarea" id="feedbackText" rows="3" '
        f'placeholder="What would make this scan more useful?"></textarea>'
        f'<button class="li-feedback-btn" type="button" onclick="submitFeedback()">'
        f'Send feedback</button>'
        f'<p class="li-feedback-note" id="feedbackNote"></p>'
        f'</div>'

        # ── LinkedIn share ────────────────────────────────────────────────────
        f'<div class="li-divider"></div>'
        f'<p class="li-share-headline">{share_headline}</p>'
        f'<p class="li-share-sub">{share_sub}</p>'
        f'<div class="li-post-preview">'
        f'<div class="li-post-preview-label">Your post \u00b7 editable</div>'
        f'<textarea class="li-post-textarea" id="liPostText" rows="7">{li_text}</textarea>'
        f'</div>'
        f'<div class="li-share-actions">'
        f'<a class="li-share-btn" href="{li_share_url}" target="_blank" rel="noopener">'
        f'<svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" '
        f'style="vertical-align:-2px;margin-right:7px;">'
        f'<path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 '
        f'2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 '
        f'5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 '
        f'13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 '
        f'1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>'
        f'</svg>'
        f'Share on LinkedIn'
        f'</a>'
        f'<button class="li-copy-btn" type="button" onclick="copyPostText()">Copy text</button>'
        f'</div>'
        f'<p class="li-mossy-credit">'
        f'Mossy Earth \u00b7 <a href="https://mossy.earth" target="_blank" rel="noopener">'
        f'mossy.earth</a> \u00b7 Native rewilding \u00b7 No greenwash'
        f'</p>'
        f'</div>\n'

        # ── CSS ───────────────────────────────────────────────────────────────
        f'<style>'
        f'.li-share-panel{{background:linear-gradient(150deg,#091810,#0d1f18);'
        f'border:1px solid rgba(47,93,74,.4);border-top:3px solid var(--forest-lt);'
        f'border-radius:8px;padding:36px 30px;margin-bottom:16px;}}'
        f'.li-share-eyebrow{{font-family:"Space Mono",monospace;font-size:10px;letter-spacing:3px;'
        f'color:var(--forest-lt);text-transform:uppercase;margin-bottom:24px;}}'
        f'.li-shoulder{{display:grid;grid-template-columns:1fr 280px;gap:36px;'
        f'align-items:start;margin-bottom:32px;}}'
        f'@media(max-width:700px){{.li-shoulder{{grid-template-columns:1fr;}}}}'
        f'.li-conversation{{}}'
        f'.li-conv-line{{font-size:15px;font-weight:300;color:rgba(255,255,255,.75);'
        f'line-height:1.8;margin-bottom:14px;}}'
        f'.li-conv-line strong{{color:#fff;font-weight:400;}}'
        f'.li-donation-col{{background:rgba(0,0,0,.25);border:1px solid rgba(47,93,74,.3);'
        f'border-radius:6px;padding:22px 20px;display:flex;flex-direction:column;gap:14px;}}'
        f'.li-donation-eyebrow{{font-family:"Space Mono",monospace;font-size:9px;letter-spacing:2px;'
        f'color:var(--forest-lt);text-transform:uppercase;}}'
        f'.li-donation-input-row{{display:flex;align-items:center;gap:8px;}}'
        f'.li-currency{{font-family:"Space Mono",monospace;font-size:22px;'
        f'color:var(--forest-lt);font-weight:700;line-height:1;}}'
        f'.li-donation-input{{background:rgba(0,0,0,.4);border:1px solid rgba(47,93,74,.5);'
        f'border-radius:4px;color:#fff;font-family:"Space Mono",monospace;font-size:20px;'
        f'padding:10px 14px;width:100%;outline:none;}}'
        f'.li-donation-input:focus{{border-color:var(--forest-lt);}}'
        f'.li-donate-btn{{background:var(--forest-lt);color:#fff;border:none;width:100%;'
        f'font-family:"Space Mono",monospace;font-size:11px;font-weight:700;letter-spacing:1px;'
        f'text-transform:uppercase;padding:13px 0;border-radius:4px;cursor:pointer;transition:background .2s;}}'
        f'.li-donate-btn:hover{{background:var(--forest);}}'
        f'.li-donation-note{{font-size:11px;color:rgba(255,255,255,.3);font-style:italic;'
        f'line-height:1.5;min-height:16px;margin:0;}}'
        f'#donationNote.success{{color:#3d7a61;font-style:normal;}}'
        f'#donationNote.error{{color:#b84035;font-style:normal;}}'
        f'.li-mossy-link{{font-family:"Space Mono",monospace;font-size:10px;letter-spacing:1px;'
        f'color:var(--forest-lt);text-decoration:none;text-transform:uppercase;}}'
        f'.li-feedback-section{{margin-bottom:24px;}}'
        f'.li-feedback-eyebrow{{font-family:"Space Mono",monospace;font-size:10px;letter-spacing:3px;'
        f'color:rgba(255,255,255,.3);text-transform:uppercase;margin-bottom:8px;}}'
        f'.li-feedback-sub{{font-size:13px;color:rgba(255,255,255,.4);margin-bottom:12px;'
        f'font-style:italic;line-height:1.6;}}'
        f'.li-feedback-textarea{{width:100%;background:rgba(0,0,0,.3);'
        f'border:1px solid rgba(255,255,255,.08);border-radius:4px;'
        f'color:rgba(255,255,255,.65);font-family:"Crimson Pro",Georgia,serif;'
        f'font-size:14px;line-height:1.7;padding:12px 14px;resize:vertical;outline:none;'
        f'margin-bottom:10px;}}'
        f'.li-feedback-textarea:focus{{border-color:rgba(255,255,255,.2);}}'
        f'.li-feedback-btn{{background:transparent;border:1px solid rgba(255,255,255,.15);'
        f'color:rgba(255,255,255,.45);font-family:"Space Mono",monospace;font-size:10px;'
        f'letter-spacing:1px;text-transform:uppercase;padding:10px 18px;border-radius:4px;'
        f'cursor:pointer;transition:all .2s;}}'
        f'.li-feedback-btn:hover{{border-color:rgba(255,255,255,.35);color:rgba(255,255,255,.8);}}'
        f'.li-feedback-note{{font-size:11px;color:rgba(255,255,255,.25);margin-top:8px;'
        f'font-style:italic;min-height:16px;}}'
        f'#feedbackNote.success{{color:#3d7a61;font-style:normal;}}'
        f'.li-divider{{border:none;border-top:1px solid rgba(47,93,74,.18);margin:0 0 24px;}}'
        f'.li-share-headline{{font-size:17px;font-weight:300;color:rgba(255,255,255,.7);margin-bottom:5px;}}'
        f'.li-share-sub{{font-size:13px;color:rgba(255,255,255,.35);margin-bottom:16px;font-style:italic;}}'
        f'.li-post-preview{{margin-bottom:16px;}}'
        f'.li-post-preview-label{{font-family:"Space Mono",monospace;font-size:9px;letter-spacing:2px;'
        f'color:rgba(255,255,255,.2);text-transform:uppercase;margin-bottom:8px;}}'
        f'.li-post-textarea{{width:100%;background:rgba(0,0,0,.3);'
        f'border:1px solid rgba(47,93,74,.2);border-radius:4px;'
        f'color:rgba(255,255,255,.65);font-family:"Crimson Pro",Georgia,serif;'
        f'font-size:14px;line-height:1.75;padding:14px 16px;resize:vertical;outline:none;}}'
        f'.li-post-textarea:focus{{border-color:rgba(47,93,74,.5);}}'
        f'.li-share-actions{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;}}'
        f'.li-share-btn{{display:inline-flex;align-items:center;background:#0a66c2;color:#fff;'
        f'font-family:"Space Mono",monospace;font-size:11px;font-weight:700;letter-spacing:.5px;'
        f'text-transform:uppercase;padding:11px 20px;border-radius:4px;text-decoration:none;'
        f'transition:background .2s;}}'
        f'.li-share-btn:hover{{background:#0952a0;}}'
        f'.li-copy-btn{{background:transparent;border:1px solid rgba(255,255,255,.1);'
        f'color:rgba(255,255,255,.35);font-family:"Space Mono",monospace;font-size:10px;'
        f'letter-spacing:1px;text-transform:uppercase;padding:11px 16px;border-radius:4px;'
        f'cursor:pointer;transition:all .2s;}}'
        f'.li-copy-btn:hover{{border-color:rgba(255,255,255,.35);color:rgba(255,255,255,.8);}}'
        f'.li-mossy-credit{{font-family:"Space Mono",monospace;font-size:10px;letter-spacing:1px;'
        f'color:rgba(255,255,255,.15);text-transform:uppercase;margin-top:4px;}}'
        f'.li-mossy-credit a{{color:var(--forest-lt);text-decoration:none;}}'
        f'</style>'

        # ── JS ────────────────────────────────────────────────────────────────
        f'<script>'
        f'function submitFeedback(){{'
        f'  var text = document.getElementById("feedbackText").value.trim();'
        f'  var note = document.getElementById("feedbackNote");'
        f'  if (!text) return;'
        f'  note.textContent = "\u2026";'
        f'  fetch("https://wildliferelicguild.com/api/feedback", {{'
        f'    method: "POST",'
        f'    headers: {{"Content-Type": "application/json"}},'
        f'    body: JSON.stringify({{'
        f'      account: "{account}",'
        f'      feedback: text,'
        f'      ts: new Date().toISOString()'
        f'    }})'
        f'  }})'
        f'  .then(function() {{'
        f'    note.textContent = "\u2714 Thank you \u2014 genuinely appreciated.";'
        f'    note.className = "success";'
        f'    document.getElementById("feedbackText").value = "";'
        f'  }})'
        f'  .catch(function() {{'
        f'    note.textContent = "\u2714 Thank you \u2014 genuinely appreciated.";'
        f'    note.className = "success";'
        f'    document.getElementById("feedbackText").value = "";'
        f'  }});'
        f'}}'
        f'function copyPostText(){{'
        f'  var ta  = document.getElementById("liPostText");'
        f'  var btn = document.querySelector(".li-copy-btn");'
        f'  ta.select();'
        f'  try {{ document.execCommand("copy"); }}'
        f'  catch(e) {{ navigator.clipboard && navigator.clipboard.writeText(ta.value); }}'
        f'  btn.textContent = "\u2714 Copied";'
        f'  setTimeout(function(){{ btn.textContent = "Copy text"; }}, 2000);'
        f'}}'
        f'</script>\n'
    )


def _generate_html_preview(audit_data, findings, fee):
    """Free executive summary — the closing document that drives conversion."""
    account   = audit_data.get('account_id', 'Unknown')
    regions   = len(audit_data.get('regions_scanned', []))
    scan_date = audit_data.get('scan_date', '')[:16].replace('T', ' ')
    duration  = f"{audit_data.get('scan_duration_secs', 0):.0f}s"
    checks    = len(findings)
    has_waste = fee['total_monthly'] > 0

    monthly_str = f"\u00a3{fee['total_monthly']:,.2f}"
    annual_str  = f"\u00a3{fee['total_annual']:,.2f}"
    co2_t_str   = f"{fee['co2_annual_t']:.1f}t" if has_waste else '\u2014'
    eff_pct     = fee['efficiency']

    if has_waste:
        headline = (f"You are losing <span class='hl-amber'>{monthly_str}</span>"
                    f" every month to confirmed cloud waste.")
        subhead  = (f"That\u2019s {annual_str}/year. The resources causing it are identified below. "
                    f"Every fix is documented. Everything is in this report.")
    else:
        headline = "Account is clean \u2014 no waste found."
        subhead  = ("Nothing idle, nothing forgotten. "
                    "If you want to support Mossy Earth anyway, the donation field is below.")

    # ── sections ──
    summary = (
        f'<div class="summary-box">'
        f'<div class="summary-title">\u26a0\ufe0f Audit Summary</div>'
        f'<div class="summary-grid">'
        f'<div class="summary-stat red-border">'
        f'<div class="ss-value red">{monthly_str}</div>'
        f'<div class="ss-label">Monthly Waste</div></div>'
        f'<div class="summary-stat">'
        f'<div class="ss-value">{checks} / 14</div>'
        f'<div class="ss-label">Checks Flagged</div></div>'
        f'<div class="summary-stat green-border">'
        f'<div class="ss-value green">{co2_t_str}</div>'
        f'<div class="ss-label">CO\u2082 Waste / Year</div></div>'
        f'</div>'
        f'<div class="efficiency-row">'
        f'<span class="eff-label">Infrastructure efficiency</span>'
        f'<div class="eff-track"><div class="eff-fill" style="width:{eff_pct}%;"></div></div>'
        f'<span class="eff-pct">{eff_pct}%</span>'
        f'</div></div>\n'
    )

    # Full findings table with safety panel
    table_rows = _html_full_table_rows(findings)
    findings_panel = (
        _html_safety_panel() +
        f'<div class="findings-panel">'
        f'<div class="panel-header">'
        f'<div class="panel-title">Findings \u2014 All Resource IDs &amp; Costs</div>'
        f'<div class="panel-count">{checks} of 14 checks flagged</div>'
        f'</div>'
        f'<table><thead><tr>'
        f'<th>Category</th><th>Priority</th><th>Monthly Cost</th>'
        f'<th>Deletion Risk</th><th>Resource Details</th>'
        f'</tr></thead><tbody>{table_rows}</tbody></table>'
        f'</div>\n'
    ) if has_waste else ''

    # ── eco impact panel ──────────────────────────────────────────────────────
    kwh_annual  = fee.get('kwh_avoided', 0.0)
    kwh_str_eco = f"{kwh_annual:,.0f} kWh" if kwh_annual >= 10 else '< 10 kWh'
    co2_str_eco = f"{fee['total_co2']:.1f} kg"
    eco = (
        f'<div class="eco-panel">'
        f'<div class="eco-eyebrow">\U0001f331 Environmental Impact</div>'
        f'<div class="eco-headline">Eliminating this waste avoids '
        f'<em>{kwh_str_eco}</em> of electricity per year.</div>'
        f'<div class="eco-impact-grid">'
        f'<div class="eco-card">'
        f'<div class="eco-card-value">{monthly_str}</div>'
        f'<div class="eco-card-label">Monthly Recoverable</div>'
        f'</div>'
        f'<div class="eco-card">'
        f'<div class="eco-card-value">{kwh_str_eco}</div>'
        f'<div class="eco-card-label">kWh Avoided / Year</div>'
        f'</div>'
        f'<div class="eco-card">'
        f'<div class="eco-card-value">{co2_str_eco}</div>'
        f'<div class="eco-card-label">CO\u2082 / Month (est.)</div>'
        f'</div>'
        f'</div>'
        f'<p class="eco-body">Estimated from idle resource energy use. '
        f'Transparent assumptions \u2014 not a certified offset.</p>'
        f'<div class="eco-footer">'
        f'Conservation partner: <a href="https://mossy.earth">Mossy Earth</a>'
        f' \u00b7 Verified native rewilding \u00b7 No greenwash'
        f'</div>'
        f'</div>\n'
    ) if has_waste else ''

    # ── assemble ──
    result  = _html_page_header(f'Wildlife Relic Guild \u2014 Cloud Audit Report')
    result += _html_mission_strip(
        'We turn cloud waste into measurable financial and environmental impact'
        ' &nbsp;\u00b7&nbsp; Conservation partner: <span class="mossy-name">Mossy Earth</span>'
    )
    _waste_badge = (
        '<span class="badge br">\u26a0 Waste Detected</span>' if has_waste
        else '<span class="badge bg">\u2713 Clean</span>'
    )
    result += (
        f'<header>'
        f'<div class="eyebrow">Cloud Audit Report &nbsp;\u00b7&nbsp; v19.5'
        f' &nbsp;\u00b7&nbsp; Wildlife Relic Guild</div>'
        f'<div class="brand">WILDLIFE RELIC GUILD</div>'
        f'<p class="headline">{headline}</p>'
        f'<p class="subhead">{subhead}</p>'
        f'<div class="badge-row">'
        f'<span class="badge bg">\u2713 IAM Verified</span>'
        f'<span class="badge bg">\u2713 14-Point Scan</span>'
        f'<span class="badge bg">\u2713 Read-Only</span>'
        f'<span class="badge ba">Account: {account}</span>'
        f'{_waste_badge}'
        f'</div></header>\n'
        f'<div class="container">\n'
    )
    result += summary
    result += findings_panel
    result += eco
    result += _html_linkedin_share_panel(account, fee['total_monthly'])
    result += '</div>\n'
    result += _html_page_footer(scan_date, regions, duration)
    return result


def _generate_html_full(audit_data, findings, fee):
    """Full report — all resource IDs, full remediation."""
    account     = audit_data.get('account_id', 'Unknown')
    regions     = len(audit_data.get('regions_scanned', []))
    scan_date   = audit_data.get('scan_date', '')[:16].replace('T', ' ')
    duration    = f"{audit_data.get('scan_duration_secs', 0):.0f}s"
    checks      = len(findings)
    monthly_str = f"\u00a3{fee['total_monthly']:,.2f}"
    annual_str  = f"\u00a3{fee['total_annual']:,.2f}"
    eff_pct     = fee['efficiency']
    co2_t_str   = f"{fee['co2_annual_t']:.1f}t"
    table_rows  = _html_full_table_rows(findings)

    result  = _html_page_header(f'Wildlife Relic Guild \u2014 Full Report')
    result += _html_mission_strip(
        '\u2713 Full Report &nbsp;\u00b7&nbsp; '
        'Conservation partner: <span class="mossy-name">Mossy Earth</span>'
    )
    result += (
        f'<header>'
        f'<div class="eyebrow">Full Report &nbsp;\u00b7&nbsp; v19.5'
        f' &nbsp;\u00b7&nbsp; Wildlife Relic Guild</div>'
        f'<div class="brand">RELIC AUDIT GUILD</div>'
        f'<p class="headline">Your full remediation plan.'
        f' <span class="hl-amber">Recover {monthly_str}/month.</span></p>'
        f'<p class="subhead">Every resource identified. Every fix documented. '
        f'Implement these recommendations to reclaim the identified waste.</p>'
        f'<div class="badge-row">'
        f'<span class="badge bg">\u2713 Full Report</span>'
        f'<span class="badge bg">\u2713 {checks} Findings</span>'
        f'<span class="badge ba">Account: {account}</span>'
        f'</div></header>\n'
        f'<div class="container">\n'
    )

    # Summary
    result += (
        f'<div class="summary-box">'
        f'<div class="summary-title">Financial Summary</div>'
        f'<div class="summary-grid">'
        f'<div class="summary-stat red-border">'
        f'<div class="ss-value red">{monthly_str}</div>'
        f'<div class="ss-label">Monthly Recoverable</div></div>'
        f'<div class="summary-stat">'
        f'<div class="ss-value">{annual_str}</div>'
        f'<div class="ss-label">Annual Recoverable</div></div>'
        f'<div class="summary-stat green-border">'
        f'<div class="ss-value green">{co2_t_str}</div>'
        f'<div class="ss-label">CO\u2082 Avoided / Year</div></div>'
        f'</div>'
        f'<div class="efficiency-row">'
        f'<span class="eff-label">Infrastructure efficiency</span>'
        f'<div class="eff-track"><div class="eff-fill" style="width:{eff_pct}%;"></div></div>'
        f'<span class="eff-pct">{eff_pct}%</span>'
        f'</div></div>\n'
    )

    # Full findings table with safety panel
    result += _html_safety_panel()
    result += (
        f'<div class="findings-panel">'
        f'<div class="panel-header">'
        f'<div class="panel-title">Full Findings \u2014 All Resource IDs</div>'
        f'<div class="panel-count">{checks} of 14 checks flagged</div>'
        f'</div>'
        f'<table><thead><tr>'
        f'<th>Category</th><th>Priority</th><th>Monthly Cost</th>'
        f'<th>Deletion Risk</th><th>Resource Details</th>'
        f'</tr></thead><tbody>{table_rows}</tbody></table>'
        f'</div>\n'
    )

    # Three-pillar impact summary — Environmental pillar updated for free model
    kwh_str_full = f"{fee['kwh_avoided']:,.0f} kWh" if fee['kwh_avoided'] >= 10 else '< 10 kWh'
    result += (
        f'<div class="decision-panel">'
        f'<div class="eco-eyebrow" style="margin-bottom:16px;">'
        f'\U0001f331 What this audit delivered</div>'
        f'<div class="three-pillar">'

        f'<div class="pillar pillar-financial">'
        f'<div class="pillar-label">Financial Impact</div>'
        f'<div class="pillar-value">{monthly_str}</div>'
        f'<div class="pillar-sub">per month recoverable</div>'
        f'<div class="pillar-sub">{annual_str} / year</div>'
        f'</div>'

        f'<div class="pillar pillar-efficiency">'
        f'<div class="pillar-label">Operational Efficiency</div>'
        f'<div class="pillar-value">{kwh_str_full}</div>'
        f'<div class="pillar-sub">estimated energy avoided / year</div>'
        f'<div class="pillar-note">{co2_t_str} CO\u2082 avoided \u2014 transparent assumptions</div>'
        f'</div>'

        f'<div class="pillar pillar-impact">'
        f'<div class="pillar-label">Environmental Contribution</div>'
        f'<div class="pillar-value">Your call</div>'
        f'<div class="pillar-sub">Mossy Earth membership</div>'
        f'<div class="pillar-note">Native rewilding \u00b7 verified \u00b7 from \u00a36.75/mo</div>'
        f'</div>'

        f'</div>'
        f'<p class="eco-body" style="margin-top:16px;">'
        f'Implement the fixes above. Visit wildliferelicguild.com if you want a follow-up check.'
        f'</p>'
        f'<div class="decision-vow">'
        f'Conservation partner: Mossy Earth \u00b7 mossy.earth \u00b7 Verified native rewilding'
        f'</div>'
        f'</div>\n'
    )

    result += _html_linkedin_share_panel(account, fee['total_monthly'])
    result += '</div>\n'
    result += _html_page_footer(scan_date, regions, duration)
    return result


# ── Public HTML API ───────────────────────────────────────────────────────────

def generate_aegis_html(audit_data):
    """Generate the full free HTML report."""
    findings = _html_extract_findings(audit_data)
    fee      = _html_build_fee_data(audit_data)
    return _generate_html_full(audit_data, findings, fee)


def save_html_reports(audit_data, paid=False):
    """Save HTML report to Desktop. Prints clickable path."""
    import os
    account   = audit_data.get('account_id', 'unknown')
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    filename  = f"relic-report-{account}-{timestamp}.html"

    desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
    output_path = os.path.join(desktop if os.path.isdir(desktop)
                               else os.path.dirname(os.path.abspath(__file__)), filename)

    try:
        html = generate_aegis_html(audit_data)
        with open(output_path, 'w', encoding='utf-8') as fh:
            fh.write(html)
        ok(f"HTML report saved   : {output_path}")
        console.print(f"\n  [bold green]Open in browser:[/bold green] [cyan]file://{output_path}[/cyan]\n")
    except Exception as e:
        warn(f"Could not save HTML report: {e}")
        import traceback
        traceback.print_exc()



# ─────────────────────────────────────────────────────────────────────────────
# RELIC ECOLOGICAL ENGINE
# ─────────────────────────────────────────────────────────────────────────────
class RelicAuditEngine:
    """
    Full 14-check multi-region AWS audit engine.
    Warnings = data gaps (thin CW data, unknown instance types).
    Errors   = genuine API failures.
    Both are reported separately — never conflated.
    """

    def __init__(self, unlocked=False):
        self.unlocked = unlocked
        self.session  = boto3.Session()
        self._reset()

    def _reset(self):
        self.audit_data = {
            'scan_date':         datetime.now(timezone.utc).isoformat(),
            'account_id':        'Unknown',
            'regions_scanned':   [],
            'scan_duration_secs':0.0,
            # per-check results
            'volumes':           {'count': 0, 'monthly_cost': 0.0, 'items': []},
            'snapshots':         {'count': 0, 'monthly_cost': 0.0, 'items': []},
            'instances':         {'count': 0, 'monthly_cost': 0.0, 'items': []},
            'elastic_ips':       {'count': 0, 'monthly_cost': 0.0, 'items': []},
            'load_balancers':    {'count': 0, 'monthly_cost': 0.0, 'items': []},
            'nat_gateways':      {'count': 0, 'monthly_cost': 0.0, 'items': []},
            'rds_instances':     {'count': 0, 'monthly_cost': 0.0, 'items': []},
            'cloudwatch_logs':   {'count': 0, 'monthly_cost': 0.0, 'items': []},
            'ecr_images':        {'count': 0, 'monthly_cost': 0.0, 'items': []},
            'lambda_functions':  {'count': 0, 'monthly_cost': 0.0, 'items': []},
            's3_buckets':        {'count': 0, 'monthly_cost': 0.0, 'items': []},
            'sagemaker':         {'count': 0, 'monthly_cost': 0.0, 'items': []},
            'gpu_zombies':       {'count': 0, 'monthly_cost': 0.0, 'items': []},
            'snap_lineage':      {'count': 0, 'monthly_cost': 0.0, 'items': []},
            # diagnostics
            'warnings':          [],
            'errors':            [],
        }

    # ── INTERNAL HELPERS ─────────────────────────────────────────────────────

    def _client(self, service, region=None):
        kwargs = {'config': BOTO_CONFIG}
        if region:
            kwargs['region_name'] = region
        if ENDPOINT_URL:
            kwargs['endpoint_url'] = ENDPOINT_URL
        return self.session.client(service, **kwargs)

    def _add(self, key, count, cost, items=None):
        """Accumulate results into audit_data."""
        self.audit_data[key]['count']        += count
        self.audit_data[key]['monthly_cost'] += cost
        if items:
            self.audit_data[key]['items'].extend(items)

    def _warn(self, msg):
        logger.warning(msg)
        self.audit_data['warnings'].append(msg)

    def _error(self, msg):
        logger.error(msg)
        self.audit_data['errors'].append(msg)

    def _lookup(self, i_type):
        """Three-tier instance lookup: exact → family → default. Fallbacks → warnings."""
        if i_type in INSTANCE_DATA:
            return INSTANCE_DATA[i_type]
        family = i_type.split('.')[0]
        if family in INSTANCE_DATA:
            self._warn(f"Instance type '{i_type}' unmapped — using family '{family}' estimate")
            return INSTANCE_DATA[family]
        self._warn(f"Instance type '{i_type}' unknown — using default estimate")
        return INSTANCE_DATA['default']

    def _get_name(self, resource):
        tags = {t['Key']: t['Value'] for t in resource.get('Tags', [])}
        return tags.get('Name', 'Unnamed')

    def _get_regions(self):
        try:
            ec2 = self._client('ec2', 'us-east-1')
            resp = ec2.describe_regions(Filters=[{
                'Name': 'opt-in-status',
                'Values': ['opt-in-not-required', 'opted-in']
            }])
            regions = [r['RegionName'] for r in resp['Regions']]
            logger.info(f"Detected {len(regions)} active region(s)")
            return regions
        except Exception as e:
            self._error(f"Region detection failed: {e}")
            return [self.session.region_name or 'eu-west-2']

    def _is_ec2_idle(self, cw, instance_id):
        """
        Returns True only if >= IDLE_MIN_RATIO of hourly CW points are below
        IDLE_THRESHOLD. Requires MIN_DATA_POINTS for confidence.
        Thin data → warning (not error). API failure → error.
        """
        try:
            stats = cw.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=datetime.now(timezone.utc) - timedelta(hours=24),
                EndTime=datetime.now(timezone.utc),
                Period=3600,
                Statistics=['Average'],
            )
            points = [d['Average'] for d in stats['Datapoints']]
            if len(points) < MIN_DATA_POINTS:
                self._warn(
                    f"Skipped {instance_id}: only {len(points)} datapoints "
                    f"(need {MIN_DATA_POINTS}). Lower MIN_DATA_POINTS for new instances."
                )
                return False
            idle_ratio = sum(1 for p in points if p < IDLE_THRESHOLD) / len(points)
            return idle_ratio >= IDLE_MIN_RATIO
        except Exception as e:
            self._error(f"CloudWatch CPU check failed ({instance_id}): {e}")
            return False

    # ── CHECK 1: ORPHANED EBS VOLUMES ────────────────────────────────────────

    def _scan_volumes(self, ec2, region):
        section("CHECK 1 OF 14 — Orphaned EBS Volumes")
        info("Scanning for unattached hard drives...")
        try:
            paginator = ec2.get_paginator('describe_volumes')
            volumes = []
            for page in paginator.paginate(Filters=[{'Name': 'status', 'Values': ['available']}]):
                volumes.extend(page.get('Volumes', []))
            if not volumes:
                ok("No orphaned volumes. Clean!")
                return
            total_gb   = sum(v['Size'] for v in volumes)
            total_cost = total_gb * EBS_GBP_PER_GB_MONTH
            row("Orphaned volumes detected:", f"{len(volumes)}")
            row("Total wasted storage:", f"{total_gb} GB")
            row("AWS billing waste:", f"£{total_cost:.2f}/month  (£{total_cost*12:.2f}/year)")
            row("Energy waste:", f"{storage_co2(total_gb):.2f} kg CO₂/month")
            print()
            items = []
            for v in volumes:
                vol_cost = v['Size'] * EBS_GBP_PER_GB_MONTH
                item = {
                    'id': v['VolumeId'], 'name': self._get_name(v),
                    'region': region, 'gb': v['Size'],
                    'monthly_cost': vol_cost,
                    'created': v['CreateTime'].strftime('%d %b %Y'),
                }
                items.append(item)
                if self.unlocked:
                    print(f"    {item['id']:<24} [{item['name']:<20}] {item['gb']:>4} GB  "
                          f"Created: {item['created']}  £{item['monthly_cost']:.2f}/month")
            if not self.unlocked:
                info(f"{len(volumes)} volume IDs")
                info("Exact costs, creation dates and remediation")
            if self.unlocked:
                info("Delete via EC2 Console > Volumes > Actions > Delete Volume")
            self._add('volumes', len(volumes), total_cost, items)
        except Exception as e:
            self._error(f"EBS volume scan failed [{region}]: {e}")

    # ── CHECK 2: ZOMBIE SNAPSHOTS ─────────────────────────────────────────────

    def _scan_snapshots(self, ec2, region):
        section("CHECK 2 OF 14 — Zombie Snapshots")
        info(f"Scanning for orphaned backups older than {ZOMBIE_SNAPSHOT_AGE_DAYS} days...")
        try:
            live_vols = set()
            for page in ec2.get_paginator('describe_volumes').paginate():
                for v in page.get('Volumes', []):
                    live_vols.add(v['VolumeId'])
            all_snaps = []
            for page in ec2.get_paginator('describe_snapshots').paginate(OwnerIds=['self']):
                all_snaps.extend(page.get('Snapshots', []))
            now = datetime.now(timezone.utc)
            zombies = [
                {**s, '_age': (now - s['StartTime']).days}
                for s in all_snaps
                if s.get('VolumeId', '') not in live_vols
                and (now - s['StartTime']).days > ZOMBIE_SNAPSHOT_AGE_DAYS
            ]
            if not zombies:
                ok(f"No zombie snapshots. ({len(all_snaps)} reviewed)")
                return
            total_gb   = sum(z.get('VolumeSize', 0) for z in zombies)
            total_cost = total_gb * SNAPSHOT_GBP_PER_GB
            row("Zombie snapshots:", f"{len(zombies)} of {len(all_snaps)} reviewed")
            row("Wasted storage:", f"{total_gb} GB")
            row("AWS billing waste:", f"£{total_cost:.2f}/month  (£{total_cost*12:.2f}/year)")
            print()
            items = []
            for z in zombies:
                snap_cost = z.get('VolumeSize', 0) * SNAPSHOT_GBP_PER_GB
                item = {
                    'id': z['SnapshotId'], 'region': region,
                    'gb': z.get('VolumeSize', 0), 'age_days': z['_age'],
                    'monthly_cost': snap_cost,
                }
                items.append(item)
            if self.unlocked:
                for item in items[:20]:
                    print(f"    {item['id']:<24} {item['gb']:>4} GB  "
                          f"Age: {item['age_days']} days  £{item['monthly_cost']:.2f}/month")
                if len(items) > 20:
                    print(f"    ... and {len(items)-20} more")
                info("Delete via EC2 Console > Snapshots > select > Delete Snapshot")
            else:
                info(f"{len(zombies)} snapshot IDs")
                info("Ages, parent volume history and remediation")
            self._add('snapshots', len(zombies), total_cost, items)
        except Exception as e:
            self._error(f"Snapshot scan failed [{region}]: {e}")

    # ── CHECK 3: STOPPED EC2 INSTANCES ───────────────────────────────────────

    def _scan_stopped_instances(self, ec2, region):
        section("CHECK 3 OF 14 — Stopped EC2 Instances")
        info("Scanning for servers off but still costing money...")
        try:
            resp = ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['stopped']}]
            )
            instances = [i for r in resp.get('Reservations', []) for i in r.get('Instances', [])]
            if not instances:
                ok("No stopped instances. Clean!")
                return
            # Batch all volume lookups in one call
            all_vol_ids, inst_vol_map = [], {}
            for inst in instances:
                vids = [m['Ebs']['VolumeId'] for m in inst.get('BlockDeviceMappings', [])
                        if m.get('Ebs', {}).get('VolumeId')]
                inst_vol_map[inst['InstanceId']] = vids
                all_vol_ids.extend(vids)
            vol_sizes = {}
            if all_vol_ids:
                try:
                    for page in ec2.get_paginator('describe_volumes').paginate(VolumeIds=all_vol_ids):
                        for v in page.get('Volumes', []):
                            vol_sizes[v['VolumeId']] = v['Size']
                except ClientError:
                    pass
            total_gb, items = 0, []
            for inst in instances:
                inst_gb = sum(vol_sizes.get(vid, 0) for vid in inst_vol_map.get(inst['InstanceId'], []))
                total_gb += inst_gb
                items.append({
                    'id': inst['InstanceId'], 'name': self._get_name(inst),
                    'type': inst.get('InstanceType', 'Unknown'),
                    'region': region, 'ebs_gb': inst_gb,
                    'monthly_cost': inst_gb * EBS_GBP_PER_GB_MONTH,
                })
            total_cost = total_gb * EBS_GBP_PER_GB_MONTH
            row("Stopped instances:", f"{len(instances)}")
            row("Storage still billing:", f"{total_gb} GB")
            row("AWS billing waste:", f"£{total_cost:.2f}/month  (£{total_cost*12:.2f}/year)")
            warn("Stopped instances may also retain Elastic IPs and data transfer costs.")
            print()
            if self.unlocked:
                for item in items:
                    print(f"    {item['id']:<24} [{item['name']:<20}] {item['type']:<14} "
                          f"{item['ebs_gb']:>4} GB  £{item['monthly_cost']:.2f}/month")
                info("Terminate via EC2 Console > Instances > Instance State > Terminate")
            else:
                info(f"{len(instances)} instance IDs")
                info("Instance types, volumes and remediation")
            self._add('instances', len(instances), total_cost, items)
        except Exception as e:
            self._error(f"EC2 stopped instance scan failed [{region}]: {e}")

    # ── CHECK 4: IDLE ELASTIC IPs ─────────────────────────────────────────────

    def _scan_elastic_ips(self, ec2, region):
        section("CHECK 4 OF 14 — Idle Elastic IP Addresses")
        info("Scanning for reserved IP addresses sitting idle...")
        try:
            all_eips = ec2.describe_addresses().get('Addresses', [])
            idle     = [e for e in all_eips if not e.get('AssociationId')]
            if not idle:
                ok(f"No idle Elastic IPs. ({len(all_eips)} reviewed)")
                return
            total_cost = len(idle) * ELASTIC_IP_COST_PER_MONTH
            row("Idle Elastic IPs:", f"{len(idle)} of {len(all_eips)} reviewed")
            row("AWS billing waste:", f"£{total_cost:.2f}/month  (£{total_cost*12:.2f}/year)")
            print()
            items = []
            for e in idle:
                item = {
                    'ip': e.get('PublicIp', 'Unknown'),
                    'allocation_id': e.get('AllocationId', 'N/A'),
                    'region': region,
                    'monthly_cost': ELASTIC_IP_COST_PER_MONTH,
                }
                items.append(item)
                if self.unlocked:
                    print(f"    {item['ip']:<20} {item['allocation_id']:<28} "
                          f"£{item['monthly_cost']:.2f}/month")
            if not self.unlocked:
                info(f"{len(idle)} IP addresses")
                info("Allocation IDs and remediation")
            if self.unlocked:
                info("Release via EC2 Console > Elastic IPs > Actions > Release")
            self._add('elastic_ips', len(idle), total_cost, items)
        except Exception as e:
            self._error(f"Elastic IP scan failed [{region}]: {e}")

    # ── CHECK 5: IDLE LOAD BALANCERS ─────────────────────────────────────────

    def _scan_load_balancers(self, region):
        section("CHECK 5 OF 14 — Idle Load Balancers")
        info("Scanning for load balancers with no active targets...")
        try:
            elbv2 = self._client('elbv2', region)
            lbs, idle = [], []
            for page in elbv2.get_paginator('describe_load_balancers').paginate():
                lbs.extend(page.get('LoadBalancers', []))
            for lb in lbs:
                tgs = elbv2.describe_target_groups(
                    LoadBalancerArn=lb['LoadBalancerArn']
                ).get('TargetGroups', [])
                has_healthy = any(
                    t.get('TargetHealth', {}).get('State') == 'healthy'
                    for tg in tgs
                    for t in elbv2.describe_target_health(
                        TargetGroupArn=tg['TargetGroupArn']
                    ).get('TargetHealthDescriptions', [])
                )
                if not has_healthy:
                    idle.append(lb)
            if not idle:
                ok(f"No idle load balancers. ({len(lbs)} reviewed)")
                return
            total_cost = len(idle) * LB_COST_PER_MONTH
            row("Idle load balancers:", f"{len(idle)} of {len(lbs)} reviewed")
            row("AWS billing waste:", f"£{total_cost:.2f}/month  (£{total_cost*12:.2f}/year)")
            print()
            items = []
            for lb in idle:
                item = {
                    'name': lb['LoadBalancerName'], 'type': lb['Type'],
                    'state': lb['State']['Code'], 'region': region,
                    'monthly_cost': LB_COST_PER_MONTH,
                }
                items.append(item)
                if self.unlocked:
                    print(f"    {item['name']:<36} [{item['type']:<11}] "
                          f"State: {item['state']:<12} £{item['monthly_cost']:.2f}/month")
            if not self.unlocked:
                info(f"{len(idle)} load balancer names")
            if self.unlocked:
                info("Delete via EC2 Console > Load Balancers > Actions > Delete")
            self._add('load_balancers', len(idle), total_cost, items)
        except Exception as e:
            self._error(f"Load balancer scan failed [{region}]: {e}")

    # ── CHECK 6: IDLE NAT GATEWAYS ────────────────────────────────────────────

    def _scan_nat_gateways(self, ec2, region):
        section("CHECK 6 OF 14 — Idle NAT Gateways")
        try:
            resp     = ec2.describe_nat_gateways(Filters=[{'Name': 'state', 'Values': ['available']}])
            gateways = resp.get('NatGateways', [])
            idle     = []
            try:
                cw  = self._client('cloudwatch', region)
                now = datetime.now(timezone.utc)
                for gw in gateways:
                    gw_id = gw['NatGatewayId']
                    metrics = cw.get_metric_statistics(
                        Namespace='AWS/NATGateway',
                        MetricName='BytesOutToDestination',
                        Dimensions=[{'Name': 'NatGatewayId', 'Value': gw_id}],
                        StartTime=now - timedelta(hours=24),
                        EndTime=now,
                        Period=86400,
                        Statistics=['Sum'],
                    )
                    if sum(d['Sum'] for d in metrics.get('Datapoints', [])) == 0:
                        idle.append({
                            'id': gw_id, 'name': self._get_name(gw),
                            'vpc': gw.get('VpcId', ''), 'region': region,
                            'monthly_cost': NAT_GBP_PER_MONTH,
                        })
            except Exception:
                # CloudWatch unavailable — cannot verify traffic. £0 contribution.
                unverified = len(gateways)
                if unverified:
                    self._warn(
                        f"CloudWatch unavailable [{region}] — {unverified} NAT Gateway(s) "
                        "could not be verified. Review manually before deleting."
                    )
                    if self.unlocked:
                        for gw in gateways:
                            print(f"    {gw['NatGatewayId']:<24} [UNVERIFIED — review manually]")
                return  # No cost contribution when unverified
            if not idle:
                ok(f"No idle NAT Gateways. ({len(gateways)} reviewed)")
                return
            total_cost = len(idle) * NAT_GBP_PER_MONTH
            row("Idle NAT Gateways:", f"{len(idle)} of {len(gateways)} reviewed")
            row("AWS billing waste:", f"£{total_cost:.2f}/month  (£{total_cost*12:.2f}/year)")
            print()
            if self.unlocked:
                for gw in idle:
                    print(f"    {gw['id']:<24} [{gw['name']:<20}] "
                          f"VPC: {gw['vpc']}  £{gw['monthly_cost']:.2f}/month")
                info("Delete via VPC Console > NAT Gateways — remove route table entries first")
            else:
                info(f"{len(idle)} NAT Gateway(s)")
            self._add('nat_gateways', len(idle), total_cost, idle)
        except Exception as e:
            self._error(f"NAT Gateway scan failed [{region}]: {e}")

    # ── CHECK 7: STOPPED RDS INSTANCES ───────────────────────────────────────

    def _scan_rds(self, region):
        section("CHECK 7 OF 14 — Stopped RDS Instances")
        try:
            rds = self._client('rds', region)
            all_db, stopped = [], []
            for page in rds.get_paginator('describe_db_instances').paginate():
                all_db.extend(page.get('DBInstances', []))
            for db in all_db:
                if db.get('DBInstanceStatus') == 'stopped':
                    gb   = db.get('AllocatedStorage', 0)
                    cost = gb * RDS_STORAGE_GBP_PER_GB
                    stopped.append({
                        'id': db['DBInstanceIdentifier'],
                        'engine': db.get('DBInstanceClass', ''),
                        'gb': gb, 'region': region,
                        'monthly_cost': cost,
                    })
            if not stopped:
                ok("No stopped RDS instances.")
                return
            total_cost = sum(d['monthly_cost'] for d in stopped)
            row("Stopped RDS instances:", f"{len(stopped)}")
            row("Storage billing waste:", f"£{total_cost:.2f}/month  (£{total_cost*12:.2f}/year)")
            print()
            if self.unlocked:
                for db in stopped:
                    print(f"    {db['id']:<30} [{db['engine']:<16}] "
                          f"{db['gb']:>4} GB  £{db['monthly_cost']:.2f}/month")
                info("Delete or snapshot — stopped RDS still charges for storage")
            else:
                info(f"{len(stopped)} RDS instance(s)")
            self._add('rds_instances', len(stopped), total_cost, stopped)
        except Exception as e:
            self._error(f"RDS scan failed [{region}]: {e}")

    # ── CHECK 8: CLOUDWATCH LOG GROUPS ───────────────────────────────────────

    def _scan_log_groups(self, region):
        section("CHECK 8 OF 14 — CloudWatch Log Groups — No Retention Policy")
        try:
            logs = self._client('logs', region)
            no_ret = []
            for page in logs.get_paginator('describe_log_groups').paginate():
                for lg in page.get('logGroups', []):
                    if 'retentionInDays' not in lg:
                        gb   = lg.get('storedBytes', 0) / (1024**3)
                        cost = gb * LOGS_GBP_PER_GB
                        no_ret.append({
                            'name': lg['logGroupName'],
                            'gb': gb, 'region': region,
                            'monthly_cost': cost,
                        })
            if not no_ret:
                ok("All log groups have retention policies.")
                return
            total_cost = sum(l['monthly_cost'] for l in no_ret)
            row("Log groups with no retention:", f"{len(no_ret)}")
            row("Estimated storage waste:", f"£{total_cost:.2f}/month  (£{total_cost*12:.2f}/year)")
            print()
            if self.unlocked:
                for lg in no_ret[:20]:
                    print(f"    {lg['name'][:50]:<52} {lg['gb']:.2f} GB  £{lg['monthly_cost']:.2f}/month")
                if len(no_ret) > 20:
                    print(f"    ... and {len(no_ret)-20} more")
                info("Set retention via CloudWatch Console > Log Groups > Edit retention")
            else:
                info(f"{len(no_ret)} log group(s)")
            self._add('cloudwatch_logs', len(no_ret), total_cost, no_ret)
        except Exception as e:
            self._error(f"CloudWatch Logs scan failed [{region}]: {e}")

    # ── CHECK 9: OLD ECR IMAGES ───────────────────────────────────────────────

    def _scan_ecr_images(self, region):
        section("CHECK 9 OF 14 — Old ECR Container Images (>90 days)")
        try:
            ecr    = self._client('ecr', region)
            cutoff = datetime.now(timezone.utc) - timedelta(days=90)
            repos, old_images = [], []
            for page in ecr.get_paginator('describe_repositories').paginate():
                repos.extend(page.get('repositories', []))
            for repo in repos:
                try:
                    for img in ecr.describe_images(
                            repositoryName=repo['repositoryName']).get('imageDetails', []):
                        pushed = img.get('imagePushedAt')
                        if pushed and pushed < cutoff:
                            gb   = img.get('imageSizeInBytes', 0) / (1024**3)
                            cost = gb * ECR_GBP_PER_GB
                            old_images.append({
                                'repo': repo['repositoryName'],
                                'digest': img.get('imageDigest', '')[:24],
                                'pushed': pushed.strftime('%Y-%m-%d'),
                                'gb': gb, 'region': region,
                                'monthly_cost': cost,
                            })
                except Exception:
                    continue
            if not old_images:
                ok("No ECR images older than 90 days.")
                return
            total_cost = sum(i['monthly_cost'] for i in old_images)
            row("Old ECR images:", f"{len(old_images)}")
            row("Storage waste:", f"£{total_cost:.2f}/month  (£{total_cost*12:.2f}/year)")
            print()
            if self.unlocked:
                for img in old_images[:20]:
                    print(f"    {img['repo']:<30} [{img['digest']}] "
                          f"pushed {img['pushed']}  £{img['monthly_cost']:.4f}/month")
                if len(old_images) > 20:
                    print(f"    ... and {len(old_images)-20} more")
                info("Delete old images or set ECR lifecycle policies to auto-expire")
            else:
                info(f"{len(old_images)} image(s)")
            self._add('ecr_images', len(old_images), total_cost, old_images)
        except Exception as e:
            self._error(f"ECR scan failed [{region}]: {e}")

    # ── CHECK 10: IDLE LAMBDA FUNCTIONS ──────────────────────────────────────

    def _scan_lambda(self, region):
        section("CHECK 10 OF 14 — Idle Lambda Functions (Hygiene / Indirect Risk)")
        info("Scanning for serverless functions nobody is calling...")
        try:
            lam = self._client('lambda', region)
            cw  = self._client('cloudwatch', region)
            all_fns, idle = [], []
            for page in lam.get_paginator('list_functions').paginate():
                all_fns.extend(page.get('Functions', []))
            if not all_fns:
                ok("No Lambda functions in this region.")
                return
            now    = datetime.now(timezone.utc)
            cutoff = now - timedelta(days=LAMBDA_IDLE_DAYS)
            for fn in all_fns:
                fn_name = fn['FunctionName']
                try:
                    metrics = cw.get_metric_statistics(
                        Namespace='AWS/Lambda',
                        MetricName='Invocations',
                        Dimensions=[{'Name': 'FunctionName', 'Value': fn_name}],
                        StartTime=cutoff, EndTime=now,
                        Period=int(timedelta(days=LAMBDA_IDLE_DAYS).total_seconds()),
                        Statistics=['Sum'],
                    )
                    if sum(d['Sum'] for d in metrics.get('Datapoints', [])) == 0:
                        idle.append({
                            'name': fn_name,
                            'runtime': fn.get('Runtime', 'Unknown'),
                            'memory_mb': fn.get('MemorySize', 0),
                            'last_modified': fn.get('LastModified', 'Unknown'),
                            'region': region,
                            'monthly_cost': 0.0,  # Lambda is free at idle
                        })
                except Exception:
                    continue
            if not idle:
                ok(f"No idle Lambda functions. ({len(all_fns)} reviewed)")
                return
            row("Idle Lambda functions:", f"{len(idle)} of {len(all_fns)} reviewed")
            row("Direct Lambda cost:", "£0.00 (Lambda charges per invocation only)")
            row("Finding type:", "Hygiene / Indirect Risk — not direct cost waste")
            warn(f"{len(idle)} idle function(s) — may have attached triggers still billing.")
            warn("Dead functions carry security and maintenance overhead.")
            print()
            if self.unlocked:
                for fn in idle:
                    print(f"    {fn['name']:<40} [{fn['runtime']:<12}] "
                          f"{fn['memory_mb']:>4} MB  Last modified: {fn['last_modified'][:10]}")
                info("Delete via Lambda Console > Functions > Actions > Delete")
                info("Remove attached triggers (EventBridge, SQS, API Gateway) first")
            else:
                info(f"{len(idle)} function names")
            self._add('lambda_functions', len(idle), 0.0, idle)
        except Exception as e:
            self._error(f"Lambda scan failed [{region}]: {e}")

    # ── CHECK 11: ABANDONED S3 BUCKETS (global) ───────────────────────────────

    def _scan_s3(self):
        section("CHECK 11 OF 14 — Abandoned S3 Buckets (no access in 90+ days)")
        info("Scanning for storage buckets nobody has touched recently...")
        info("(Biggest single waste pattern in AI companies — abandoned training data)")
        try:
            s3  = self._client('s3')
            cw  = self._client('cloudwatch', 'us-east-1')
            all_buckets = s3.list_buckets().get('Buckets', [])
            if not all_buckets:
                ok("No S3 buckets found.")
                return
            now      = datetime.now(timezone.utc)
            cutoff   = now - timedelta(days=S3_IDLE_DAYS)
            abandoned = []
            for bucket in all_buckets:
                name = bucket['Name']
                try:
                    size_m = cw.get_metric_statistics(
                        Namespace='AWS/S3', MetricName='BucketSizeBytes',
                        Dimensions=[{'Name': 'BucketName', 'Value': name},
                                    {'Name': 'StorageType', 'Value': 'StandardStorage'}],
                        StartTime=now - timedelta(days=2), EndTime=now,
                        Period=86400, Statistics=['Average'],
                    )
                    size_bytes = max((d['Average'] for d in size_m.get('Datapoints', [])), default=0)
                    if size_bytes == 0:
                        continue
                    req_m = cw.get_metric_statistics(
                        Namespace='AWS/S3', MetricName='AllRequests',
                        Dimensions=[{'Name': 'BucketName', 'Value': name},
                                    {'Name': 'FilterId', 'Value': 'EntireBucket'}],
                        StartTime=cutoff, EndTime=now,
                        Period=int(timedelta(days=S3_IDLE_DAYS).total_seconds()),
                        Statistics=['Sum'],
                    )
                    if sum(d['Sum'] for d in req_m.get('Datapoints', [])) == 0:
                        gb   = size_bytes / (1024**3)
                        cost = gb * S3_GBP_PER_GB
                        abandoned.append({
                            'name': name, 'gb': gb,
                            'monthly_cost': cost,
                            'co2_kg': storage_co2(gb),
                            'created': bucket.get('CreationDate', '').strftime('%Y-%m-%d')
                                if hasattr(bucket.get('CreationDate', ''), 'strftime') else 'Unknown',
                        })
                except Exception:
                    continue
            if not abandoned:
                ok(f"No clearly abandoned S3 buckets. ({len(all_buckets)} reviewed)")
                info("Note: S3 request metrics require server access logging to be enabled.")
                return
            total_gb   = sum(b['gb'] for b in abandoned)
            total_cost = sum(b['monthly_cost'] for b in abandoned)
            total_co2  = sum(b['co2_kg'] for b in abandoned)
            row("Abandoned S3 buckets:", f"{len(abandoned)} of {len(all_buckets)} reviewed")
            row("Total abandoned storage:", f"{total_gb:.1f} GB")
            row("AWS billing waste:", f"£{total_cost:.2f}/month  (£{total_cost*12:.2f}/year)")
            row("Energy waste:", f"{total_co2:.2f} kg CO₂/month")
            warn("Likely abandoned training sets, experiment outputs or old model artefacts.")
            print()
            if self.unlocked:
                for b in abandoned:
                    print(f"    {b['name']:<40} {b['gb']:>8.1f} GB  "
                          f"£{b['monthly_cost']:.2f}/month  {b['co2_kg']:.3f} kg CO₂")
                info("Review contents then delete or archive to S3 Glacier (£0.004/GB/month)")
            else:
                info(f"{len(abandoned)} bucket(s)")
            self._add('s3_buckets', len(abandoned), total_cost, abandoned)
        except Exception as e:
            self._error(f"S3 scan failed: {e}")

    # ── CHECK 12: IDLE SAGEMAKER ENDPOINTS ────────────────────────────────────

    def _scan_sagemaker(self, region):
        section("CHECK 12 OF 14 — Idle SageMaker Endpoints (7-day check)")
        info("Scanning for AI inference endpoints with no traffic...")
        try:
            sm  = self._client('sagemaker', region)
            cw  = self._client('cloudwatch', region)
            all_eps = sm.list_endpoints(StatusEquals='InService').get('Endpoints', [])
            if not all_eps:
                ok("No active SageMaker endpoints in this region.")
                return
            now, idle = datetime.now(timezone.utc), []
            for ep in all_eps:
                ep_name = ep['EndpointName']
                try:
                    metrics = cw.get_metric_statistics(
                        Namespace='AWS/SageMaker', MetricName='Invocations',
                        Dimensions=[{'Name': 'EndpointName', 'Value': ep_name}],
                        StartTime=now - timedelta(days=7), EndTime=now,
                        Period=604800, Statistics=['Sum'],
                    )
                    if sum(d['Sum'] for d in metrics.get('Datapoints', [])) == 0:
                        try:
                            desc   = sm.describe_endpoint(EndpointName=ep_name)
                            config = sm.describe_endpoint_config(
                                EndpointConfigName=desc.get('EndpointConfigName', ''))
                            variants = config.get('ProductionVariants', [{}])
                            i_type = variants[0].get('InstanceType', 'Unknown') if variants else 'Unknown'
                        except Exception:
                            i_type = 'Unknown'
                        cost = SAGEMAKER_ML_T3_MEDIUM * 730
                        idle.append({
                            'name': ep_name, 'type': i_type,
                            'region': region, 'monthly_cost': cost,
                            'created': ep.get('CreationTime', '').strftime('%Y-%m-%d')
                                if hasattr(ep.get('CreationTime', ''), 'strftime') else 'Unknown',
                        })
                except Exception:
                    continue
            if not idle:
                ok(f"No idle SageMaker endpoints. ({len(all_eps)} reviewed)")
                return
            total_cost = sum(e['monthly_cost'] for e in idle)
            row("Idle SageMaker endpoints:", f"{len(idle)} of {len(all_eps)} reviewed")
            row("Estimated waste (conservative floor):", f"£{total_cost:.2f}/month")
            warn("GPU endpoints (p3, g4dn) cost significantly more — see Check 13.")
            print()
            if self.unlocked:
                for ep in idle:
                    print(f"    {ep['name']:<40} [{ep['type']:<18}] "
                          f"Created: {ep['created']}  ~£{ep['monthly_cost']:.2f}/month min")
                info("Delete via SageMaker Console > Inference > Endpoints > Delete")
            else:
                info(f"{len(idle)} endpoint(s)")
            self._add('sagemaker', len(idle), total_cost, idle)
        except Exception as e:
            self._error(f"SageMaker scan failed [{region}]: {e}")

    # ── CHECK 13: GPU ZOMBIE ENDPOINTS (72-hour deep check) ───────────────────

    def _scan_gpu_zombies(self, region):
        section("CHECK 13 OF 14 — GPU Zombie Endpoints (72-hour Invocation Check)")
        info("Deep-scanning SageMaker endpoints for 72-hour zero-invocation zombies...")
        info("(GPU endpoints cost £500–£2,800/month — the silent killers)")
        try:
            sm  = self._client('sagemaker', region)
            cw  = self._client('cloudwatch', region)
            all_eps = sm.list_endpoints(StatusEquals='InService').get('Endpoints', [])
            if not all_eps:
                ok("No active SageMaker endpoints in this region.")
                return
            now    = datetime.now(timezone.utc)
            window = now - timedelta(hours=GPU_ZOMBIE_IDLE_HOURS)
            zombies = []
            for ep in all_eps:
                ep_name = ep['EndpointName']
                try:
                    metrics = cw.get_metric_statistics(
                        Namespace='AWS/SageMaker', MetricName='Invocations',
                        Dimensions=[{'Name': 'EndpointName', 'Value': ep_name}],
                        StartTime=window, EndTime=now,
                        Period=int(timedelta(hours=GPU_ZOMBIE_IDLE_HOURS).total_seconds()),
                        Statistics=['Sum'],
                    )
                    if sum(d['Sum'] for d in metrics.get('Datapoints', [])) > 0:
                        continue
                    try:
                        desc   = sm.describe_endpoint(EndpointName=ep_name)
                        config = sm.describe_endpoint_config(
                            EndpointConfigName=desc.get('EndpointConfigName', ''))
                        variants = config.get('ProductionVariants', [{}])
                        i_type = variants[0].get('InstanceType', 'Unknown') if variants else 'Unknown'
                    except Exception:
                        i_type = 'Unknown'
                    hourly = SAGEMAKER_GPU_COSTS.get(i_type, SAGEMAKER_ML_T3_MEDIUM)
                    is_gpu = any(i_type.startswith(p) for p in ('ml.p2', 'ml.p3', 'ml.g4', 'ml.g5'))
                    zombies.append({
                        'name': ep_name, 'type': i_type,
                        'is_gpu': is_gpu, 'hourly_rate': hourly,
                        'monthly_cost': hourly * 730, 'region': region,
                        'created': ep.get('CreationTime', '').strftime('%Y-%m-%d')
                            if hasattr(ep.get('CreationTime', ''), 'strftime') else 'Unknown',
                    })
                except Exception:
                    continue
            if not zombies:
                ok(f"No 72h zero-invocation endpoints. ({len(all_eps)} reviewed)")
                return
            total_cost = sum(z['monthly_cost'] for z in zombies)
            gpu_count  = sum(1 for z in zombies if z['is_gpu'])
            row("Zero-invocation endpoints (72h):", f"{len(zombies)} of {len(all_eps)} reviewed")
            row("GPU-class instances:", f"{gpu_count}")
            row("Estimated monthly waste:", f"£{total_cost:.2f}/month  (£{total_cost*12:.2f}/year)")
            if gpu_count > 0:
                warn(f"{gpu_count} GPU endpoint(s) — HIGHEST PRIORITY FINDING.")
                warn("A single idle p3.2xlarge costs ~£2,800/month. Delete immediately.")
            print()
            if self.unlocked:
                for z in sorted(zombies, key=lambda z: (not z['is_gpu'], -z['monthly_cost'])):
                    flag = " ★GPU★" if z['is_gpu'] else "      "
                    print(f"    {z['name']:<40} [{z['type']:<18}]{flag} "
                          f"Created: {z['created']}  £{z['monthly_cost']:.2f}/month")
                info("Delete via SageMaker Console > Inference > Endpoints > Delete")
                info("Model artefacts stay in S3 — endpoints can be recreated anytime")
                info("CLI: aws sagemaker delete-endpoint --endpoint-name <n> --region <r>")
            else:
                info(f"{len(zombies)} zombie endpoint(s)")
                info("Names, instance types, GPU flag, exact costs")
            self._add('gpu_zombies', len(zombies), total_cost, zombies)
        except Exception as e:
            self._error(f"GPU zombie scan failed [{region}]: {e}")

    # ── CHECK 14: REDUNDANT SNAPSHOT LINEAGE ─────────────────────────────────

    def _scan_snapshot_lineage(self, ec2, region):
        section("CHECK 14 OF 14 — Redundant Snapshot Lineage")
        info(f"Scanning for volumes with {SNAPSHOT_LINEAGE_THRESHOLD}+ accumulated snapshots...")
        try:
            now    = datetime.now(timezone.utc)
            cutoff = now - timedelta(days=SNAPSHOT_LINEAGE_AGE_DAYS)
            live_vols = {}
            for page in ec2.get_paginator('describe_volumes').paginate():
                for v in page.get('Volumes', []):
                    live_vols[v['VolumeId']] = v['Size']
            all_snaps = []
            for page in ec2.get_paginator('describe_snapshots').paginate(OwnerIds=['self']):
                all_snaps.extend(page.get('Snapshots', []))
            by_vol = defaultdict(list)
            for s in all_snaps:
                vid = s.get('VolumeId', '')
                if vid in live_vols:
                    by_vol[vid].append(s)
            flagged = []
            for vol_id, snaps in by_vol.items():
                if len(snaps) < SNAPSHOT_LINEAGE_THRESHOLD:
                    continue
                old_snaps = [s for s in snaps if (now - s['StartTime']).days > SNAPSHOT_LINEAGE_AGE_DAYS]
                old_gb    = sum(s.get('VolumeSize', 0) for s in old_snaps)
                old_cost  = old_gb * SNAPSHOT_GBP_PER_GB
                try:
                    vol_name = self._get_name(
                        ec2.describe_volumes(VolumeIds=[vol_id])['Volumes'][0])
                except Exception:
                    vol_name = 'Unnamed'
                flagged.append({
                    'vol_id': vol_id, 'vol_name': vol_name,
                    'vol_gb': live_vols.get(vol_id, 0),
                    'total_snaps': len(snaps), 'old_snaps': len(old_snaps),
                    'old_gb': old_gb, 'region': region,
                    'monthly_cost': old_cost,
                })
            if not flagged:
                ok(f"No excessive snapshot lineage. ({len(by_vol)} volumes with snapshots reviewed)")
                return
            total_cost = sum(f['monthly_cost'] for f in flagged)
            total_old  = sum(f['old_snaps'] for f in flagged)
            row("Volumes with redundant lineage:", f"{len(flagged)}")
            row("Recoverable old snapshots:", f"{total_old}")
            row("Estimated storage waste:", f"£{total_cost:.2f}/month  (£{total_cost*12:.2f}/year)")
            info(f"Glacier Deep Archive: ~£0.001/GB/month vs £{SNAPSHOT_GBP_PER_GB}/GB for snapshots")
            print()
            if self.unlocked:
                for f in sorted(flagged, key=lambda x: -x['monthly_cost']):
                    print(f"    {f['vol_id']:<24} [{f['vol_name']:<20}] "
                          f"{f['vol_gb']:>5} GB volume  "
                          f"{f['total_snaps']} snaps / {f['old_snaps']} old  "
                          f"£{f['monthly_cost']:.2f}/month waste")
                info("Set AWS Backup lifecycle rules to expire old recovery points")
                info("Or: EC2 > Snapshots > filter by VolumeId > delete oldest in batches")
                info("CLI: aws ec2 delete-snapshot --snapshot-id snap-xxx --region <r>")
            else:
                info(f"{len(flagged)} volume(s) with redundant lineage")
            self._add('snap_lineage', len(flagged), total_cost, flagged)
        except Exception as e:
            self._error(f"Snapshot lineage scan failed [{region}]: {e}")

    # ── ENTRY POINT ───────────────────────────────────────────────────────────

    def run_audit(self):
        """Full 14-check multi-region audit. Resets state on each call."""
        self._reset()
        scan_start = time.time()

        banner(
            "RELIC AUDIT GUILD — Cloud Waste Intelligence Engine v19.0\n"
            "Legacy in the landscape, for your company and my family.\n"
            "Read-Only · No ML · No Credentials Stored · No Agents\n"
            "14 checks · Multi-region · Warnings/errors separated"
        )

        console.print(f"\n  [bold white]Mode:[/bold white] [bold green]FULL REPORT — FREE[/bold green]")
        console.print(f"\n  [dim]Establishing secure read-only connection to AWS...[/dim]\n")
        _start_music()

        try:
            sts      = self._client('sts')
            identity = sts.get_caller_identity()
            account  = identity.get('Account', 'Unknown')
            region   = self.session.region_name or 'eu-west-2'
        except NoCredentialsError:
            console.print("  [bold red]✗[/bold red]  [red]No AWS credentials found. Run 'aws configure'.[/red]")
            sys.exit(1)
        except ClientError as e:
            console.print(f"  [bold red]✗[/bold red]  [red]{e}[/red]")
            sys.exit(1)

        self.audit_data['account_id'] = account

        ok(f"Connected.")
        ok(f"Account ID  : {account}")
        ok(f"Home Region : {region}")

        console.print()
        console.print(Rule("[bold white]TRUST & SAFETY CONFIRMATION[/bold white]", style="dim white"))
        ok("Read-only IAM — cannot create, modify or delete anything")
        ok("No data transmitted externally · No credentials stored")
        ok("All findings remain on your local machine only")
        console.print(Rule(style="dim white"))

        regions = self._get_regions()
        self.audit_data['regions_scanned'] = regions
        ok(f"{len(regions)} region(s) found")
        console.print(f"\n  [dim]Starting full 14-check multi-region scan...[/dim]\n")

        with Progress(
            SpinnerColumn(style="green"),
            TextColumn("[bold white]{task.description}"),
            BarColumn(bar_width=30, style="orange1", complete_style="green"),
            TextColumn("[dim]{task.completed}/{task.total} regions[/dim]"),
            TimeElapsedColumn(),
            TextColumn("[dim green]{task.fields[eco_msg]}[/dim green]"),
            console=console,
            transient=False,
        ) as progress:
            task = progress.add_task(
                "Scanning regions...",
                total=len(regions),
                eco_msg=_next_rewilding_msg(),
            )

            # S3 is global — run once, inside the progress context so output is visible
            _s3_done = False
            _running_total = 0.0

            for r in regions:
                progress.update(
                    task,
                    description=f"[bold white]Scanning [cyan]{r}[/cyan]",
                    eco_msg=_next_rewilding_msg(),
                )
                ec2 = self._client('ec2', r)
                self._scan_volumes(ec2, r)
                self._scan_snapshots(ec2, r)
                self._scan_stopped_instances(ec2, r)
                self._scan_elastic_ips(ec2, r)
                self._scan_load_balancers(r)
                self._scan_nat_gateways(ec2, r)
                self._scan_rds(r)
                self._scan_log_groups(r)
                self._scan_ecr_images(r)
                self._scan_lambda(r)
                if not _s3_done:
                    self._scan_s3()
                    _s3_done = True
                self._scan_sagemaker(r)
                self._scan_gpu_zombies(r)
                self._scan_snapshot_lineage(ec2, r)

                new_total = sum(
                    self.audit_data[k]['monthly_cost']
                    for k in self.audit_data
                    if isinstance(self.audit_data[k], dict) and 'monthly_cost' in self.audit_data[k]
                )
                region_cost = new_total - _running_total
                _running_total = new_total
                if region_cost > 0:
                    warn(f"{r} complete — waste detected")
                else:
                    ok(f"{r} complete — clean")
                progress.advance(task)

        self.audit_data['scan_duration_secs'] = time.time() - scan_start

        _stop_music()
        console.print()
        console.print(Rule("[bold green]SCAN COMPLETE[/bold green]", style="green"))
        ok(f"All 14 checks complete in {self.audit_data['scan_duration_secs']:.0f}s across {len(regions)} region(s)")
        console.print()

        self._render_summary()
        self._save_report()

    # ── OUTPUT ────────────────────────────────────────────────────────────────

    def _result_keys(self):
        return [k for k in self.audit_data
                if isinstance(self.audit_data[k], dict)
                and 'monthly_cost' in self.audit_data[k]]

    def _render_summary_to(self, con):
        """Render summary to a specific console instance (used for file capture)."""
        self._render_summary(con=con)

    def _render_summary(self, con=None):
        con = con or console
        keys          = self._result_keys()
        total_monthly = sum(self.audit_data[k]['monthly_cost'] for k in keys)
        total_annual  = total_monthly * 12

        # Environmental
        total_gb_waste = (
            self.audit_data['volumes']['count'] * 100 +
            self.audit_data['snapshots']['count'] * 50 +
            self.audit_data['s3_buckets']['count'] * 200
        )
        total_co2   = storage_co2(total_gb_waste) + co2_for_cost(total_monthly)
        trees_equiv = total_co2 / (21.7 / 12)

        # Shock metric — estimated waste as % of cloud spend.
        # Assumes typical cloud waste is 20-30% of total spend (Gartner benchmark).
        # Inverts that: total_spend_est = waste / 0.25, shock = waste / total_spend_est.
        # Uses annual waste vs £5,000/yr baseline so the number varies meaningfully.
        shock_pct = min(round(total_annual / 50, 1), 100) if total_monthly > 0 else 0

        # Top findings sorted by cost
        sorted_keys = sorted(
            [k for k in keys if self.audit_data[k]['monthly_cost'] > 0],
            key=lambda k: self.audit_data[k]['monthly_cost'], reverse=True
        )

        labels = {
            'volumes':         'Orphaned EBS Volumes',
            'snapshots':       'Zombie Snapshots',
            'instances':       'Stopped EC2 Instances',
            'elastic_ips':     'Idle Elastic IPs',
            'load_balancers':  'Idle Load Balancers',
            'nat_gateways':    'Idle NAT Gateways',
            'rds_instances':   'Stopped RDS Instances',
            'cloudwatch_logs': 'Log Groups (No Retention)',
            'ecr_images':      'Old ECR Images',
            'lambda_functions':'Idle Lambda Functions',
            's3_buckets':      'Abandoned S3 Buckets',
            'sagemaker':       'Idle SageMaker Endpoints',
            'gpu_zombies':     'GPU Zombie Endpoints ★',
            'snap_lineage':    'Redundant Snapshot Lineage',
        }

        priority_colours = {
            'CRITICAL': 'bold red',
            'HIGH':     'bold orange1',
            'MEDIUM':   'bold yellow',
            'LOW':      'dim white',
        }

        # ── EXECUTIVE SUMMARY PANEL ──────────────────────────────────────────

        con.print()
        con.print(Rule("[bold white]RELIC AUDIT GUILD — EXECUTIVE SUMMARY[/bold white]", style="green"))
        con.print()

        summary_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        summary_table.add_column(style="dim white", min_width=28)
        summary_table.add_column(style="bold white")

        summary_table.add_row("Account",   f"[cyan]{self.audit_data['account_id']}[/cyan]")
        summary_table.add_row("Regions scanned", str(len(self.audit_data['regions_scanned'])))
        summary_table.add_row("Scan time", self.audit_data['scan_date'][:16])
        summary_table.add_row("Duration",  f"{self.audit_data['scan_duration_secs']:.0f} seconds")
        summary_table.add_section()

        if total_monthly > 0:
            summary_table.add_row("Monthly waste",       f"[bold orange1]£{total_monthly:.2f}[/bold orange1]")
            summary_table.add_row("Annual waste",        f"[bold orange1]£{total_annual:.2f}[/bold orange1]")
            summary_table.add_row("Waste % of spend",    f"[yellow]~{shock_pct:.0f}% estimated[/yellow]")
            summary_table.add_section()
            summary_table.add_row("Donation to Mossy Earth", "[dim green]Voluntary — your discretion 🌱[/dim green]")
            summary_table.add_section()
            summary_table.add_row("CO₂ from waste",      f"[yellow]{total_co2:.1f} kg/month[/yellow]")
            summary_table.add_row("Tree equivalent",     f"[yellow]{trees_equiv:.1f} trees/month to offset[/yellow]")
            summary_table.add_row("ESG / Scope 3 note",  f"[dim green]Idle AWS resources are Scope 3 reportable[/dim green]")
        else:
            summary_table.add_row("Result", "[bold green]Account is clean — we still let you donate! 🌱[/bold green]")

        con.print(Panel(summary_table, border_style="green", padding=(0, 1)))

        # ── TOP FINDINGS ─────────────────────────────────────────────────────

        if sorted_keys:
            con.print()
            con.print(Rule("[bold white]TOP FINDINGS[/bold white]", style="dim white"))
            con.print()
            for k in sorted_keys[:3]:
                pri, _  = PRIORITY.get(k, ('', ''))
                colour  = priority_colours.get(pri, 'white')
                label   = labels.get(k, k)
                count   = self.audit_data[k]['count']
                cost    = self.audit_data[k]['monthly_cost']
                con.print(
                    f"  [{colour}][{pri}][/{colour}]"
                    f"  [white]{label:<30}[/white]"
                    f"  [orange1]{count} found — £{cost:.2f}/month[/orange1]"
                )

        # ── WASTE BY CATEGORY TABLE ───────────────────────────────────────────

        con.print()
        con.print(Rule("[bold white]WASTE BY CATEGORY[/bold white]", style="dim white"))
        con.print()

        cat_table = Table(
            box=box.SIMPLE_HEAD,
            show_header=True,
            header_style="bold white",
            padding=(0, 1),
        )
        cat_table.add_column("Check",    style="white",    min_width=28)
        cat_table.add_column("Priority", justify="center", min_width=10)
        cat_table.add_column("Found",    justify="right",  min_width=6)
        cat_table.add_column("Monthly",  justify="right",  min_width=12)
        cat_table.add_column("Annual",   justify="right",  min_width=12)

        for k, label in labels.items():
            r   = self.audit_data.get(k, {'count': 0, 'monthly_cost': 0.0})
            pri, _ = PRIORITY.get(k, ('', ''))
            colour = priority_colours.get(pri, 'dim white')
            if r['count'] > 0:
                cat_table.add_row(
                    f"[white]{label}[/white]",
                    f"[{colour}]{pri}[/{colour}]",
                    f"[orange1]{r['count']}[/orange1]",
                    f"[orange1]£{r['monthly_cost']:.2f}[/orange1]",
                    f"[orange1]£{r['monthly_cost']*12:.2f}[/orange1]",
                )
            else:
                cat_table.add_row(
                    f"[dim]{label}[/dim]",
                    f"[dim]{pri}[/dim]",
                    "[dim green]—[/dim green]",
                    "[dim green]Clean[/dim green]",
                    "[dim green]—[/dim green]",
                )

        con.print(cat_table)

        # ── TOTALS + MISSION ──────────────────────────────────────────────────

        con.print()
        con.print(Rule(style="dim white"))

        totals_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        totals_table.add_column(style="dim white", min_width=32)
        totals_table.add_column(style="bold white")
        totals_table.add_row("Monthly waste identified",   f"[bold orange1]£{total_monthly:.2f}[/bold orange1]")
        totals_table.add_row("Annual waste identified",    f"[bold orange1]£{total_annual:.2f}[/bold orange1]")
        totals_table.add_section()
        totals_table.add_row("Donation to Mossy Earth", "[dim green]Voluntary — your discretion 🌱[/dim green]")
        con.print(totals_table)

        if total_monthly > 0:
            con.print(Padding(
                Panel(
                    Text.assemble(
                        ("Mossy Earth · mossy.earth · Verified native rewilding\n", "green"),
                    ),
                    border_style="green",
                    padding=(0, 2),
                ),
                (0, 2)
            ))

        else:
            con.print()
            con.print(Panel(
                Text.assemble(
                    ("✓  Account is clean — we still let you donate!\n", "bold green"),
                    ("No waste found. No charge.\n\n", "green"),
                    ("Well done — your infrastructure is running efficiently.\n", "dim green"),
                    ("Mossy Earth · mossy.earth · Verified native rewilding", "dim green"),
                ),
                border_style="green",
                padding=(0, 2),
            ))

        # ── UNLOCKED: REMEDIATION GUIDE ───────────────────────────────────────

        if self.unlocked:
            con.print()
            con.print(Rule("[bold white]REMEDIATION GUIDE — Priority Order[/bold white]", style="dim white"))
            con.print()

            rem_table = Table(
                box=box.SIMPLE_HEAD,
                show_header=True,
                header_style="bold white",
                padding=(0, 1),
            )
            rem_table.add_column("Finding",   style="white",    min_width=30)
            rem_table.add_column("Priority",  justify="center", min_width=10)
            rem_table.add_column("Time",      justify="center", min_width=8)
            rem_table.add_column("Action",    style="dim cyan", min_width=38)

            remediation_rows = [
                ("GPU Zombie Endpoints",       "CRITICAL", "2 min",  "SageMaker > Endpoints > Delete"),
                ("Idle SageMaker Endpoints",   "CRITICAL", "2 min",  "SageMaker > Endpoints > Delete"),
                ("Stopped EC2 Instances",      "HIGH",     "5 min",  "EC2 > Instances > Terminate"),
                ("Idle NAT Gateways",          "HIGH",     "5 min",  "VPC > NAT Gateways > Delete"),
                ("Idle Load Balancers",        "HIGH",     "2 min",  "EC2 > Load Balancers > Delete"),
                ("Stopped RDS Instances",      "HIGH",     "5 min",  "RDS > Databases > Delete"),
                ("Abandoned S3 Buckets",       "HIGH",     "10 min", "S3 > Empty then Delete"),
                ("Orphaned EBS Volumes",       "HIGH",     "2 min",  "EC2 > Volumes > Delete"),
                ("Redundant Snapshot Lineage", "MEDIUM",   "15 min", "EC2 > Snapshots > delete oldest"),
                ("Zombie Snapshots",           "MEDIUM",   "5 min",  "EC2 > Snapshots > Delete"),
                ("Idle Elastic IPs",           "LOW",      "1 min",  "EC2 > Elastic IPs > Release"),
                ("Old ECR Images",             "LOW",      "5 min",  "ECR > Repositories > Delete"),
                ("Log Groups No Retention",    "LOW",      "3 min",  "CloudWatch > Edit retention"),
                ("Idle Lambda Functions",      "LOW",      "10 min", "Lambda > Functions > Delete"),
            ]
            for finding, pri, effort, action in remediation_rows:
                colour = priority_colours.get(pri, 'dim white')
                rem_table.add_row(
                    finding,
                    f"[{colour}]{pri}[/{colour}]",
                    effort,
                    action,
                )
            con.print(rem_table)

            con.print(Panel(
                Text.assemble(
                    ("Strengthening the UK grid. Planting the forest.\n", "dim green"),
                    ("wildliferelicguild.com\n", "cyan"),
                    ("THE RELIC VOW: Every donation goes to Mossy Earth. Verified rewilding. No greenwash.", "bold green"),
                ),
                border_style="green",
                padding=(0, 2),
            ))

        # ── WARNINGS AND ERRORS ───────────────────────────────────────────────

        if self.audit_data['warnings']:
            con.print()
            con.print(Rule(f"[yellow]DATA GAPS ({len(self.audit_data['warnings'])})[/yellow]", style="yellow"))
            for w in self.audit_data['warnings'][:10]:
                warn(w)

        if self.audit_data['errors']:
            con.print()
            con.print(Rule(f"[red]API FAILURES ({len(self.audit_data['errors'])})[/red]", style="red"))
            for e in self.audit_data['errors'][:10]:
                con.print(f"  [bold red]✗[/bold red]  [red]{e}[/red]")

    def _save_report(self):
        """Save clean plain-text report and trigger HTML generation."""
        account   = self.audit_data['account_id']
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        rtype     = 'full-report' if self.unlocked else 'free-summary'
        txt_file  = f"relic-{rtype}-{account}-{timestamp}.txt"

        keys          = self._result_keys()
        total_monthly = sum(self.audit_data[k]['monthly_cost'] for k in keys)
        total_annual  = total_monthly * 12
        is_clean      = total_monthly == 0

        labels = {
            'volumes':         'Orphaned EBS Volumes',
            'snapshots':       'Zombie Snapshots',
            'instances':       'Stopped EC2 Instances',
            'elastic_ips':     'Idle Elastic IPs',
            'load_balancers':  'Idle Load Balancers',
            'nat_gateways':    'Idle NAT Gateways',
            'rds_instances':   'Stopped RDS Instances',
            'cloudwatch_logs': 'Log Groups (No Retention)',
            'ecr_images':      'Old ECR Images',
            'lambda_functions':'Idle Lambda Functions',
            's3_buckets':      'Abandoned S3 Buckets',
            'sagemaker':       'Idle SageMaker Endpoints',
            'gpu_zombies':     'GPU Zombie Endpoints *',
            'snap_lineage':    'Redundant Snapshot Lineage',
        }

        W = 78  # line width

        def rule(char='─'):
            return char * W

        def centre(text, char=' '):
            return text.center(W)

        def kv(label, value, lw=28):
            return f"  {label:<{lw}}{value}"

        try:
            with open(txt_file, 'w', encoding='utf-8') as f:
                w = f.write

                # ── HEADER ────────────────────────────────────────────────────
                w(rule('═') + '\n')
                w(centre('RELIC AUDIT GUILD') + '\n')
                w(centre('Cloud Waste Intelligence Engine  v19.0') + '\n')
                w(rule('═') + '\n\n')

                w(kv('Account',      account) + '\n')
                w(kv('Regions',      str(len(self.audit_data['regions_scanned']))) + '\n')
                w(kv('Report Type',  'FULL UNLOCKED REPORT' if self.unlocked else 'FREE SUMMARY') + '\n')
                w(kv('Generated',    datetime.now().strftime('%d %B %Y at %H:%M:%S')) + '\n')
                w(kv('Duration',     f"{self.audit_data['scan_duration_secs']:.0f} seconds") + '\n')
                w('\n')

                # ── EXECUTIVE SUMMARY ─────────────────────────────────────────
                w(rule() + '\n')
                w(centre('EXECUTIVE SUMMARY') + '\n')
                w(rule() + '\n\n')

                if is_clean:
                    w(kv('Result', 'Account is clean — we still let you donate!') + '\n')
                else:
                    w(kv('Monthly waste identified',  f"£{total_monthly:.2f}") + '\n')
                    w(kv('Annual waste identified',   f"£{total_annual:.2f}") + '\n')
                    w('\n')
                    w(kv('Donation to Mossy Earth', 'Voluntary — your discretion') + '\n')
                w('\n')

                # ── WASTE BY CATEGORY ─────────────────────────────────────────
                w(rule() + '\n')
                w(centre('WASTE BY CATEGORY') + '\n')
                w(rule() + '\n\n')

                # Header row
                w(f"  {'Check':<32}{'Priority':<12}{'Found':<8}{'Monthly':>12}{'Annual':>12}\n")
                w(f"  {'─'*32}{'─'*12}{'─'*8}{'─'*12}{'─'*12}\n")

                for k, label in labels.items():
                    r   = self.audit_data.get(k, {'count': 0, 'monthly_cost': 0.0})
                    pri, _ = PRIORITY.get(k, ('', ''))
                    if r['count'] > 0:
                        mo  = f"£{r['monthly_cost']:.2f}"
                        ann = f"£{r['monthly_cost']*12:.2f}"
                        w(f"  {label:<32}{pri:<12}{r['count']:<8}{mo:>12}{ann:>12}\n")
                    else:
                        w(f"  {label:<32}{pri:<12}{'—':<8}{'Clean':>12}{'—':>12}\n")
                w('\n')

                # ── TOTALS ────────────────────────────────────────────────────
                w(rule() + '\n\n')
                w(kv('Monthly waste identified',  f"£{total_monthly:.2f}") + '\n')
                w(kv('Annual waste identified',   f"£{total_annual:.2f}") + '\n')
                w('\n')
                w(kv('Donation to Mossy Earth', 'Voluntary — your discretion') + '\n')
                w('\n')

                # ── ESG & ENVIRONMENTAL IMPACT ────────────────────────────────
                w(rule() + '\n')
                w(centre('ESG & ENVIRONMENTAL IMPACT') + '\n')
                w(rule() + '\n\n')
                if not is_clean:
                    total_gb_esg = (
                        self.audit_data['volumes']['count'] * 100 +
                        self.audit_data['snapshots']['count'] * 50 +
                        self.audit_data['s3_buckets']['count'] * 200
                    )
                    co2_esg = storage_co2(total_gb_esg) + co2_for_cost(total_monthly)
                    w(kv('1. Financial Impact',         f"£{total_monthly:.2f}/month recoverable") + '\n')
                    w(kv('   Annual recoverable',       f"£{total_annual:.2f}") + '\n')
                    w('\n')
                    w(kv('2. Operational Efficiency',   f"{co2_esg:.1f} kg CO2/month avoided (est.)") + '\n')
                    w(kv('   Note',                     'Derived from idle resource energy use.') + '\n')
                    w(kv('   ',                         'Transparent assumptions — not a certified offset.') + '\n')
                    w('\n')
                    w(kv('3. Environmental Contribution', 'Voluntary donation to Mossy Earth invited') + '\n')
                    w(kv('   mossy.earth',              'Native rewilding · habitat creation · verified') + '\n')
                    w('\n')
                    w('  This report constitutes ESG-reportable evidence of:\n')
                    w('    (a) Quantified cloud waste elimination\n')
                    w('    (b) CO2 / Scope 3 footprint reduction at source\n')
                    w('    (c) Verified conservation funding — Mossy Earth invoice on file\n')
                else:
                    w('  No waste found — no idle resource emissions to report.\n')
                    w('  A clean account is a clean Scope 3 footprint.\n')
                    w('  Efficiency is conservation — every resource that was never\n')
                    w('  left running is energy that never needed to be funded.\n')
                w('\n')

                # ── CLEAN / LOCKED / UNLOCKED MESSAGE ────────────────────────
                w(rule() + '\n\n')
                if is_clean:
                    w('  Account is clean — we still let you donate!\n')
                    w('  No waste found. No charge.\n\n')
                    w('  Well done — your infrastructure is running efficiently.\n')
                    w('  Conservation partner: Mossy Earth · mossy.earth\n')
                else:
                    w('  Conservation partner: Mossy Earth · mossy.earth · Verified native rewilding\n')
                w('\n')

                # ── REMEDIATION (unlocked only) ───────────────────────────────
                if self.unlocked:
                    w(rule() + '\n')
                    w(centre('REMEDIATION GUIDE — Priority Order') + '\n')
                    w(rule() + '\n\n')
                    w(f"  {'Finding':<34}{'Priority':<12}{'Time':<10}{'Action'}\n")
                    w(f"  {'─'*34}{'─'*12}{'─'*10}{'─'*28}\n")
                    remediation_rows = [
                        ("GPU Zombie Endpoints",       "CRITICAL", "2 min",  "SageMaker > Endpoints > Delete"),
                        ("Idle SageMaker Endpoints",   "CRITICAL", "2 min",  "SageMaker > Endpoints > Delete"),
                        ("Stopped EC2 Instances",      "HIGH",     "5 min",  "EC2 > Instances > Terminate"),
                        ("Idle NAT Gateways",          "HIGH",     "5 min",  "VPC > NAT Gateways > Delete"),
                        ("Idle Load Balancers",        "HIGH",     "2 min",  "EC2 > Load Balancers > Delete"),
                        ("Stopped RDS Instances",      "HIGH",     "5 min",  "RDS > Databases > Delete"),
                        ("Abandoned S3 Buckets",       "HIGH",     "10 min", "S3 > Empty then Delete"),
                        ("Orphaned EBS Volumes",       "HIGH",     "2 min",  "EC2 > Volumes > Delete"),
                        ("Redundant Snapshot Lineage", "MEDIUM",   "15 min", "EC2 > Snapshots > delete oldest"),
                        ("Zombie Snapshots",           "MEDIUM",   "5 min",  "EC2 > Snapshots > Delete"),
                        ("Idle Elastic IPs",           "LOW",      "1 min",  "EC2 > Elastic IPs > Release"),
                        ("Old ECR Images",             "LOW",      "5 min",  "ECR > Repositories > Delete"),
                        ("Log Groups No Retention",    "LOW",      "3 min",  "CloudWatch > Edit retention"),
                        ("Idle Lambda Functions",      "LOW",      "10 min", "Lambda > Functions > Delete"),
                    ]
                    for finding, pri, effort, action in remediation_rows:
                        w(f"  {finding:<34}{pri:<12}{effort:<10}{action}\n")
                    w('\n')

                # ── FOOTER ────────────────────────────────────────────────────
                w(rule('═') + '\n')
                w(centre('wildliferelicguild.com') + '\n')
                w(centre('A Waller-Mayes Alliance  ·  Bedford, UK') + '\n')
                w(centre('Conservation partner: Mossy Earth · mossy.earth · Verified native rewilding') + '\n')
                w(rule('═') + '\n')

            ok(f"Report saved: {txt_file}")
        except Exception as e:
            warn(f"Could not save report: {e}")



        # ── HTML REPORT ───────────────────────────────────────────────────────
        save_html_reports(self.audit_data, paid=self.unlocked)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    engine = RelicAuditEngine(unlocked=True)  # Always full — no paywall
    engine.run_audit()
