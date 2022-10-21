# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import csv
import subprocess
import re
import logging

logger = logging.getLogger("script")

# Expects a csv file in the format: issue_number,title
# Can be generated with gh issue list and some manual editing

with open("issues.txt", "r") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

issues = {row["issue"]: row["title"] for row in rows}

new_titles = {
    issue: re.sub(r"^\[[^\]]*\][ :]*", "", title) for issue, title in issues.items()
}

for issue, title in issues.items():
    logger.info("{}->{}".format(title, new_titles[issue]))


for issue, title in new_titles.items():
    subprocess.run(["gh", "issue", "edit", issue, "--title", title])
