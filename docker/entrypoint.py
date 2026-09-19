"""Honor optional runtime UID/GID; otherwise keep Docker's selected user."""
import os
import sys


def main():
    try:
        if "UID" in os.environ or "GID" in os.environ:
            ids = [os.environ.get(name, "1000") for name in ("UID", "GID")]
            if any(not value.isascii() or not value.isdecimal() for value in ids):
                raise ValueError("UID and GID must be non-negative integers")
            uid, gid = map(int, ids)
            if max(uid, gid) >= 2**32 - 1:
                raise ValueError("UID and GID must be less than 4294967295")
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
