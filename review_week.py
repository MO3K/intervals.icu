"""
CLI: fill Post-Week Review for a given week, or generate external coach block.

  python review_week.py 21                 # fill 2026/week_21_plan.md Post-Week Review
  python review_week.py 2026 20            # explicit year
  python review_week.py --block 20 21      # external review for W20-W21
  python review_week.py --block 2026 18 2026 21
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import argparse
from datetime import datetime

from coach.review import review_block, review_week


def main():
    parser = argparse.ArgumentParser(description="Post-Week Review autofill or external coach block")
    parser.add_argument("args", nargs="*", help="Week number, or year+week, or block range")
    parser.add_argument("--block", action="store_true", help="Generate external coach review block")
    p = parser.parse_args()

    if p.block:
        if len(p.args) == 2:
            year = datetime.now().year
            start_w, end_w = int(p.args[0]), int(p.args[1])
            start_y = end_y = year
        elif len(p.args) == 4:
            start_y, start_w, end_y, end_w = (int(x) for x in p.args)
        else:
            print("Usage: --block <start_week> <end_week>  OR  --block <sy> <sw> <ey> <ew>")
            sys.exit(1)
        path = review_block(start_y, start_w, end_y, end_w)
        print(f"  ✓ External review saved → {path}")
        return

    if len(p.args) == 1:
        year = datetime.now().year
        week = int(p.args[0])
    elif len(p.args) == 2:
        year, week = int(p.args[0]), int(p.args[1])
    else:
        print("Usage: review_week.py <week>  OR  review_week.py <year> <week>")
        sys.exit(1)

    print(review_week(year, week))


if __name__ == "__main__":
    main()
