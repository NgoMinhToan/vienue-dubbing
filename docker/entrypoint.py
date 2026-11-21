"""Honor optional runtime UID/GID; otherwise keep Docker's selected user."""
import os
from pathlib import Path
import sys


def prepare_output(uid=None, gid=None):
    """Create APP_OUTPUT_DIR and hand it to the runtime user before dropping privileges."""
    directory = Path(os.environ.get("APP_OUTPUT_DIR", "/app/output"))
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"Cannot create output directory {directory}: {exc}", file=sys.stderr)
        return
    if uid is not None and os.geteuid() == 0:
        try:
            os.chown(directory, uid, gid)
        except OSError as exc:
            print(f"Cannot set owner of {directory}: {exc}", file=sys.stderr)


def main():
    try:
        uid = gid = None
        if "UID" in os.environ or "GID" in os.environ:
            ids = [os.environ.get(name, "1000") for name in ("UID", "GID")]
            if any(not value.isascii() or not value.isdecimal() for value in ids):
                raise ValueError("UID and GID must be non-negative integers")
            uid, gid = map(int, ids)
            if max(uid, gid) >= 2**32 - 1:
                raise ValueError("UID and GID must be less than 4294967295")
        prepare_output(uid, gid)
        if uid is not None:
            if os.geteuid() == 0:
                os.setgroups([])
                os.setgid(gid)
                os.setuid(uid)
            elif (os.geteuid(), os.getegid()) != (uid, gid):
                raise ValueError("UID/GID conflict with Docker --user; use one configuration")
        command = sys.argv[1:]
        if not command:
            raise ValueError("No command supplied; remove command: [] from Compose")
        os.execvp(command[0], command)
    except (OSError, ValueError) as exc:
        print(f"Container startup failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
