# HAR Metrics Analyzer

A Python script for extracting and analyzing network performance metrics from HAR (HTTP Archive) files.

## Overview

This tool processes HAR files exported from browser developer tools and generates comprehensive network performance metrics including timing data, resource analysis, and statistical summaries.

## Requirements

- Python 3.6+
- No external dependencies (uses only standard library)

## Usage

### Basic Syntax

```bash
python har_metrics.py <har_directory> [options]
```

#### Options
```bash
--csv <filename> # Export detailed metrics to CSV file
--mime-csv <filename>  # Export MIME type distribution to CSV file
--summary-csv <filename> # Export statistical summary (mean/stddev) to CSV file
```

## Project Directory
```bash
project/
├── README.md
├── har_metrics.py
├── har_files/           # Create this directory yourself
│   ├── easy/
│   │   ├── example.com1.har # Include these files from your own tests
│   │   ├── example.com2.har
│   │   └── ...
│   ├── medium/
│   │   ├── github.com1.har
│   │   ├── github.com2.har
│   │   └── ...
│   └── hard/
│       ├── www.youtube.com1.har
│       ├── www.youtube.com2.har
│       └── ...
└── output_metrics/             # Auto-created by script
    ├── easy.csv
    ├── easy_mime.csv
    ├── easy_summary.csv
    └── ...
```

## How It Works
1. Load HAR Files: Reads all .har files from the specified directory
2. Extract Metrics: Parses JSON structure to extract timing and resource data
3. Calculate Statistics: Computes averages, totals, and distributions
4. Generate Reports: Outputs to console and/or CSV files

## Notes
- HAR files use -1 to indicate unavailable timing data; these values are excluded from calculations
- Only successful resource loads with bodySize > 0 are counted in transfer totals
- Throughput is calculated as: (total_bytes × 8) / (page_load_time / 1000)
- Standard deviation uses n divisor when n > 1, otherwise uses 1
- The script automatically creates the output_metrics directory if it doesn't exist

## Exporting HAR Files from Browsers
### Chrome/Edge
1. Open Developer Tools (F12)
2. Go to Network tab
3. Load the page
4. Right-click in the network log → Save all as HAR

### Firefox
1. Open Developer Tools (F12)
2. Go to Network tab
3. Load the page
4. Click the gear icon → Save All As HAR

### Safari
1. Enable Develop menu (Preferences → Advanced)
2. Develop → Show Web Inspector
3. Go to Network tab
4. Load the page
5. Click Export button
