#!/home/resi/opt/virtualenvs/scripts/bin/python
import argparse
import os
import sys
import datetime
import re
import requests
import dateutil.parser
from ago import human

api_token = "qBYJn9DryFxyJf263P_e"
base_url = "http://gitlab.flinkwork.com/api/v3"

s = requests.Session()
s.headers["PRIVATE-TOKEN"] = api_token

try:
    import termstyle
except ImportError:
    class termstyle(object):
        @staticmethod
        def default(s):
            return s
        green = default
        red = default
        yellow = default
        magenta = default

def status_color(s):
    _colors = {
        "success":termstyle.green,
        "failed" :termstyle.red,
        "skipped":termstyle.yellow,
        "running":termstyle.magenta,
    }
    return _colors.get(s.strip(), termstyle.default)(s)

def maybe_load_dt(x):
    if not hasattr(x, "lower"):
        return x
    if not re.match("....-..-..T", x):
        # only parse iso8601 strings, not version numbers ;)
        return x
    try:
        return dateutil.parser.parse(x).replace(tzinfo=None)
    except ValueError:
        return x

def load_dt(d):
    d = {k:maybe_load_dt(v) for k, v in d.items()}
    return d

def get(path, limit=None, **kw):
    page = None
    data = []
    while True:
        params = kw.copy()
        params["page"] = page
        params["per_page"] = limit
        r = s.get(base_url + path, params=params)
        if not r.ok:
            break
        rdata = r.json()
        if not isinstance(rdata, list):
            return load_dt(rdata)
        data.extend(rdata)
        if limit is not None and len(data) >= limit:
            break
        page = r.headers.get("X-Next-Page", None)
        if not page:
            break

    return [load_dt(d) for d in data]

_pipelines = {}
def project_pipelines(project_id, limit=3):
    if project_id not in _pipelines:
        _pipelines[project_id] = get("/projects/{}/pipelines".format(project_id), limit=limit)
    return _pipelines[project_id]

def main(args):
    dt_delta = datetime.timedelta(days=args.days)
    max_pipelines = args.pipelines

    projects = get("/projects/")
    if args.project:
        projects = [p for p in projects if args.project in p["path_with_namespace"]]

    now = datetime.datetime.now()

    for project in sorted(projects, key=lambda p: p["last_activity_at"], reverse=True):
        mrs = get("/projects/{}/merge_requests".format(project["id"]), reverse=True, state="opened")
        pipelines = [p for p in project_pipelines(project["id"], 2*max_pipelines) if (now - p["created_at"] < dt_delta)][:max_pipelines]
        if not (pipelines or mrs):
            continue

        print(project["path_with_namespace"], project["web_url"])
        for mr in mrs:
            build_status = ""
            pipeline_by_sha = {p["sha"]:p for p in project_pipelines(mr["source_project_id"])}
            for commit in get("/projects/{}/merge_requests/{}/commits".format(project["id"], mr["id"])):
                try:
                    build_status = pipeline_by_sha[commit["id"]]["status"]
                    break
                except KeyError:
                    pass
            try:
                assignee = mr["assignee"]["name"]
                assignee_color = termstyle.magenta
            except (TypeError, KeyError):
                assignee = "nobody :-("
                assignee_color = termstyle.red
            print("{:>10}".format(mr["id"]),
                status_color("{:>10}".format(build_status)),
                "{:>20}".format(human(mr["created_at"], 1)),
                assignee_color("{:>20}".format(assignee)),
                mr["title"])
        for p in pipelines:
            print("{:>10}".format(p["id"]),
                status_color("{:>10}".format(p["status"])),
                "{:>20}".format(human(p["created_at"], 1)),
                "{:>20}".format(""),
                p["ref"])

if __name__ == "__main__":
    progname = os.path.basename(sys.argv[0])
    parser = argparse.ArgumentParser(prog=progname,
                                     description="gitlab status reporter",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("-d", "--days", type=int, default=5, help="number of days to look back")
    parser.add_argument("-p", "--pipelines", type=int, default=3, help="number of pipelines to show")
    parser.add_argument("project", nargs="?", help="project name filter (substring of namespace/path)")
    args = parser.parse_args()
    main(args)
