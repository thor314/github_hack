import os
import time
import argparse
import datetime
import pytz
import random
from git import Repo
# on any given day, choose a random number of commits to add between:
COMMIT_MIN = 15
COMMIT_MAX = 20
# DON'T CHANGE! Will screw up the cadence period.
START_DATE = datetime.date(2021, 5, 9)  # must be SUNDAY
TODAY = datetime.date.today()
TODAY_AWARE = datetime.datetime.now()
THOR = [
    [0, 0, 0, 0, 0, 0, 0],  # START: 0
    [0, 1, 0, 0, 0, 0, 0],
    [0, 1, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 0],
    [0, 1, 0, 0, 0, 0, 0],
    [0, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],  # 6
    [0, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],  # 12
    [0, 0, 1, 1, 1, 0, 0],
    [0, 1, 0, 0, 0, 1, 0],
    [0, 1, 0, 0, 0, 1, 0],
    [0, 1, 0, 0, 0, 1, 0],
    [0, 0, 1, 1, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 0],  # 18
    [0, 1, 1, 1, 1, 1, 0],
    [0, 1, 0, 1, 0, 0, 0],
    [0, 1, 0, 1, 0, 0, 0],
    [0, 1, 0, 1, 1, 0, 0],
    [0, 0, 1, 0, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0],  # 24
    [1, 1, 1, 1, 1, 1, 1]
]
THOR_LEN = THOR.__len__()

def print_name_test():
    def l(x): return "#" if x == 1 else " "
    output = ["", "", "", "", "", "", ""]
    for week in THOR:
        for i, day in enumerate(week):
            output[i] += l(day)
    for r in output:
        print(r)


def root_directory():
    stream = os.popen("git rev-parse --show-toplevel")
    root = stream.read().strip()
    stream.close()
    return root


DUMPFILE = root_directory() + "/.dump"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--backdate", help="flag: number of weeks to backdate commits", default=26, type=int)
    parser.add_argument("--specific_date")
    parser.add_argument("--n_commits", type=int)
    parser.add_argument(
        "--force", help="flag: pass force along to git push", default=False)
    args = parser.parse_args()
    print("args: %s" % args)
    assert(args.backdate <= 52 and args.backdate >= 1)

    repo = Repo(root_directory())
    assert(not repo.bare)

    if args.n_commits == None:
        n = random.randrange(COMMIT_MIN, COMMIT_MAX)
    else:
        n = args.n_commits
    if args.specific_date != None:
        # meh, input validation, hope for the best
        date = args.specific_date.split("-")
        year = int(date[0])
        month = int(date[1])
        day = int(date[2])
        date = datetime.date(year, month, day)

        print("updating date : %s" % date)
        check_and_commit(repo, date, n)
    else:
        # backdate a year
        date = max(START_DATE, TODAY -
                   datetime.timedelta(weeks=args.backdate))
        print("backdating starting from %s...\n\n" % date)
        while date < TODAY:
            check_and_commit(repo, date, n)
            date += datetime.timedelta(days=1)
            # defeat github's defenses
            time.sleep(0.2)


def check_and_commit(repo, date, n):
    if is_name_day(date):
        print("is nameday")
        n_commits = already_committed(date, n)
        if n_commits >= n:
            print("already committed")
        else:
            gen_commits(repo, n-n_commits, date=date)
            git_push(repo)
    else:
        print("not nameday")


def is_name_day(date) -> bool:
    """expect week in range 0..=25, day in range 0..=6"""
    date_format = DateFormat(date)
    if 0 <= date_format.week <= THOR_LEN and 0 <= date_format.day <= 6:
        return THOR[date_format.week][date_format.day] == 1
    else:
        raise ValueError("day or week not in expected range")


class DateFormat():
    """formatted date for git commit periodicity"""

    def __init__(self, date):
        assert(date > START_DATE)
        # need to rotate monday to be day 1, sunday from 6 to 0
        day = (date.weekday() + 1) % 7
        weeks_since_start_date = ((date - START_DATE) // 7).days
        week = weeks_since_start_date % THOR_LEN
        self.day = day
        self.week = week


def already_committed(date=TODAY, min=COMMIT_MIN):
    """return true if at least `min` commits already present (avoid duplication)"""
    date_string = date_str(date)
    stream = os.popen(
        "git log --date=short --pretty=format:%%cd | rg %s | wc -l" % date_string)
    n_commits = int(stream.read().strip())
    print("n commits on %s was: %s" % (date, n_commits))
    stream.close()
    return n_commits


def date_str(date):
    if date.day < 10:
        day = "0%s" % date.day
    else:
        day = str(date.day)
    if date.month < 10:
        month = "0%s" % date.month
    else:
        month = str(date.month)

    return "%s-%s-%s" % (date.year, month, day)


def gen_commits(repo, n=COMMIT_MIN, date=TODAY):
    """write `n` empty commits on `date`"""
    date_string = date_str(date)
    print("writing %s commits on %s" % (n, date))

    with open(DUMPFILE, "a") as commit_dump:
        for i in range(n):
            aware_datetime = datetime.datetime(
                date.year, date.month, date.day, 14, i, 0, 0, tzinfo=pytz.UTC)
            commit_msg = "date: %s, n: %s" % (date_string, i)
            commit_dump.write(commit_msg+"\n")
            repo.index.add(DUMPFILE)
            # The following is finicky. Non-aware datetimes are disallowed.
            repo.index.commit(
                commit_msg, commit_date=aware_datetime, author_date=aware_datetime)


def git_push(repo, force=False):
    if force:
        os.system("git push -f")
    else:
        os.system("git push")


if __name__ == "__main__":
    main()
