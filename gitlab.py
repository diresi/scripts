#!/home/resi/opt/virtualenvs/scripts/bin/python
import datetime
import requests
import dateutil.parser
from ago import human

api_token = "qBYJn9DryFxyJf263P_e"
base_url = "http://gitlab.flinkwork.com/api/v3"

s = requests.Session()
s.headers["PRIVATE-TOKEN"] = api_token

def maybe_load_dt(x):
    if not hasattr(x, "lower"):
        return x
    try:
        return dateutil.parser.parse(x).replace(tzinfo=None)
    except ValueError:
        return x

def load_dt(d):
    d = {k:maybe_load_dt(v) for k, v in d.items()}
    return d

def get(path, reverse=False, **kw):
    page = None
    data = []
    while True:
        params = kw.copy()
        params["page"] = page
        r = s.get(base_url + path, params=params)
        if not r.ok:
            break
        data.extend(r.json())
        page = r.headers.get("X-Next-Page", None)
        if not page:
            break

    data.sort(key=lambda x:x["id"], reverse=reverse)
    return [load_dt(d) for d in data]

projects = {_project["path_with_namespace"]:_project for _project in get("/projects/")}

now = datetime.datetime.now()
for project in sorted(projects.values(), key=lambda p: p["last_activity_at"], reverse=True):
    mrs = get("/projects/{}/merge_requests".format(project["id"]), reverse=True, state="opened")

    pipelines = get("/projects/{}/pipelines".format(project["id"]), reverse=True)[:3]
    pipelines = [p for p in pipelines if (now - p["created_at"] < datetime.timedelta(days=5))]
    if not (pipelines or mrs):
        continue

    print(project["path_with_namespace"], project["web_url"])
    for mr in mrs:
        try:
            assignee = mr["assignee"]["name"]
        except KeyError:
            assignee = "nobody :-("
        print("{:>10}".format(mr["id"]), "{:>10}".format(""), "{:>20}".format(human(mr["created_at"], 1)), "{:>10}".format(assignee), "  ", mr["title"])
    for p in pipelines:
        print("{:>10}".format(p["id"]), "{:>10}".format(p["status"]), "{:>20}".format(human(p["created_at"], 1)), "  ", p["ref"])
