#!/home/resi/opt/virtualenvs/gitlab/bin/python

import os
import yaml
import json
import requests
import argparse
from urllib.parse import quote_plus
from termstyle import inverted, red, green, blue, auto as termstyle_auto
termstyle_auto()

CONFIG_FILE="~/.gitlab.yml"
CONFIG = yaml.load(open(os.path.expanduser(CONFIG_FILE)))

CONFIG["url"] = CONFIG["url"] + "/api/v3"

def set_project(project):
    CONFIG["url"] = CONFIG["url"] + "/projects/" + quote_plus(project)

if "project" in CONFIG:
    set_project(CONFIG["project"])

def mk_url(path):
    url = CONFIG["url"]
    if path:
        url = url + "/" + path
    return url

def mk_request_params(path, headers=None, **kw):
    headers = headers or {}
    headers["PRIVATE-TOKEN"] = CONFIG["token"]
    url = mk_url(path)
    params = dict([(k, v) for k, v in kw.items() if k and v])
    kw = {"headers" : headers,
          "params" : params}
    return url, kw

def get_request(*a, **kw):
    url, kw = mk_request_params(*a, **kw)
    return requests.get(url, **kw)

def get_json(*a, **kw):
    r = get_request(*a, **kw)
    try:
        return r.json()
    except:
        print("ERROR loading json from: {}".format(r.url))
        raise

def get_issues(issues=None, labels=None, state="opened"):
    issues = set(issues or [])
    data = get_json("issues", labels=",".join(labels or []), state=state)
    if not issues:
        return data
    return [i for i in data if i["iid"] in issues]

def print_issues(issues, labels):
    issues = set(issues or [])
    for issue in get_issues(issues, labels):
        iid = issue["iid"] # the project local issue number
        if issues and iid not in issues:
            continue
        ann = "({}, {})".format(issue["id"], blue(",".join(issue["labels"])))
        print(green("#{: 4}".format(iid)), issue["title"], ann)

def set_labels(detail, issues, labels):
    if detail not in ("+", "-", "="):
        raise Exception("label requires a flag: label[+-=]")

    for issue in get_issues(issues):
        url, kw = mk_request_params("issues/{}".format(issue["id"]))

        if detail == "+":
            new_labels = issue["labels"] + labels
        elif detail == "-":
            labels = set(labels)
            new_labels = [l for l in issue["labels"] if l not in labels]
        else:
            new_labels = labels
        r = requests.put(url, data={"labels":",".join(new_labels)}, **kw)
        if r.status_code != 200:
            raise Exception(r.status_code, r.text)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-p", "--project", help="project name")
    parser.add_argument("-l", "--labels", nargs="*", help="set labels to given issues (requires -i)")
    parser.add_argument("-i", "--issues", nargs="*", type=int, help="issue numbers")
    parser.add_argument("--all", action="store_true", help="label all issues")
    parser.add_argument("action", nargs="?", help="action")
    args = parser.parse_args()
    if args.project:
        set_project(args.project)

    if args.action:
        if args.action.startswith("label"):
            if not args.issues and args.all:
                args.issues = [issue["iid"] for issue in get_issues()]

            if args.labels and args.issues:
                detail = args.action.replace("label", "")
                set_labels(detail, args.issues, args.labels)
                args.labels = []

            print_issues(args.issues, args.labels)

        elif args.action == "new":
            issues = [issue["iid"] for issue in get_issues() if not issue["labels"]]
            if issues:
                labels = args.labels or ["new"]
                set_labels("+", issues, labels)
                print_issues(issues, labels)

    else:
        print_issues(args.issues, args.labels)
