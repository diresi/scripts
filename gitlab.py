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
        rdata = r.json()
        if not isinstance(rdata, list):
            return load_dt(rdata)
        data.extend(rdata)
        page = r.headers.get("X-Next-Page", None)
        if not page:
            break

    data.sort(key=lambda x:x["id"], reverse=reverse)
    return [load_dt(d) for d in data]

projects = {_project["path_with_namespace"]:_project for _project in get("/projects/")}

_pipelines = {}
def project_pipelines(project_id):
    if project_id not in _pipelines:
        _pipelines[project_id] = get("/projects/{}/pipelines".format(project_id), reverse=True)
    return _pipelines[project_id]

now = datetime.datetime.now()
for project in sorted(projects.values(), key=lambda p: p["last_activity_at"], reverse=True):
    mrs = get("/projects/{}/merge_requests".format(project["id"]), reverse=True, state="opened")
    pipelines = [p for p in project_pipelines(project["id"]) if (now - p["created_at"] < datetime.timedelta(days=5))][:3]
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
        except (TypeError, KeyError):
            assignee = "nobody :-("
        print("{:>10}".format(mr["id"]),
              "{:>10}".format(build_status),
              "{:>20}".format(human(mr["created_at"], 1)),
              "{:>20}".format(assignee),
              mr["title"])
    for p in pipelines:
        print("{:>10}".format(p["id"]),
              "{:>10}".format(p["status"]),
              "{:>20}".format(human(p["created_at"], 1)),
              "{:>20}".format(""),
              p["ref"])
