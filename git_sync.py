import datetime
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run():
    if not os.path.isdir(os.path.join(BASE_DIR, ".git")):
        print("git_sync: not a git repository, skipping.")
        return

    git = ["git", "-C", BASE_DIR]

    subprocess.run(git + ["add", "reports", "docs", "channel_ids.json"], check=False)

    staged = subprocess.run(git + ["diff", "--cached", "--quiet"])
    if staged.returncode == 0:
        print("git_sync: nothing new to commit.")
        return

    date = datetime.datetime.now().strftime("%Y-%m-%d")
    commit = subprocess.run(git + ["commit", "-m", f"New videos {date}"])
    if commit.returncode != 0:
        print("git_sync: commit failed.")
        return

    push = subprocess.run(git + ["push"])
    if push.returncode != 0:
        print("git_sync: push failed (network/auth?). Report is committed locally.")
        sys.exit(1)

    print("git_sync: pushed weekly report.")


if __name__ == "__main__":
    run()
