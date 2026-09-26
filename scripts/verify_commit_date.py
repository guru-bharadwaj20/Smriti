"""Reject commits outside the user-requested date, including old workers."""

from datetime import datetime, timedelta, timezone
import subprocess
import sys

for variable in ('GIT_AUTHOR_IDENT', 'GIT_COMMITTER_IDENT'):
    identity = subprocess.check_output(['git', 'var', variable], text=True).strip()
    timestamp = int(identity.rsplit(' ', 2)[1])
    local = datetime.fromtimestamp(timestamp, timezone(timedelta(hours=5, minutes=30)))
    if local.date().isoformat() != '2026-10-02':
        print('Commit rejected: user requires both dates to be 2 October 2026. Restart with updated task_commit.py.', file=sys.stderr)
        sys.exit(1)
