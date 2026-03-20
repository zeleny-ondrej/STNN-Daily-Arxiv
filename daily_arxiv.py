import datetime
import requests
import json
import arxiv
import os

# Official Papers With Code API — stable host, no SSL issues
PWC_API_URL = "https://paperswithcode.com/api/v1/papers/"


def get_authors(authors, first_author=False):
    output = str()
    if first_author == False:
        output = ", ".join(str(author) for author in authors)
    else:
        output = authors[0]
    return output


def sort_papers(papers):
    output = dict()
    keys = list(papers.keys())
    keys.sort(reverse=True)
    for key in keys:
        output[key] = papers[key]
    return output


def get_code_url(paper_id):
    """
    Fetch the official repo URL for a paper from the Papers With Code API.
    paper_id: arxiv short id without version, e.g. '2603.19235'
    Returns repo URL string or None.
    """
    try:
        url = f"{PWC_API_URL}{paper_id}/"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        repos = data.get("repositories", [])
        # Prefer official repo; fall back to first available
        for repo in repos:
            if repo.get("is_official", False):
                return repo.get("url")
        if repos:
            return repos[0].get("url")
    except Exception:
        pass
    return None


def get_daily_papers(topic, query="STNN", max_results=2):
    """
    @param topic: str
    @param query: str
    @return paper_with_code: dict
    """

    content = dict()
    content_to_web = dict()

    client = arxiv.Client()
    search_engine = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    cnt = 0

    for result in client.results(search_engine):

        paper_id           = result.get_short_id()
        paper_title        = result.title
        paper_url          = result.entry_id
        paper_abstract     = result.summary.replace("\n", " ")
        paper_authors      = get_authors(result.authors)
        paper_first_author = get_authors(result.authors, first_author=True)
        primary_category   = result.primary_category
        publish_time       = result.published.date()
        update_time        = result.updated.date()
        comments           = result.comment

        if update_time < datetime.date(2023, 1, 1):
            continue

        print(f"Time = {update_time} , title = {paper_title}, author = {paper_first_author}".encode('ascii', 'ignore').decode('ascii'))

        # e.g. 2108.09112v1 -> 2108.09112
        ver_pos = paper_id.find('v')
        paper_key = paper_id[:ver_pos] if ver_pos != -1 else paper_id

        repo_url = get_code_url(paper_key)

        if repo_url:
            cnt += 1
            content[paper_key] = f"|**{update_time}**|**{paper_title}**|{paper_first_author} et.al.|[{paper_id}]({paper_url})|**[link]({repo_url})**|\n"
            content_to_web[paper_key] = f"- {update_time}, **{paper_title}**, {paper_first_author} et.al., Paper: [{paper_url}]({paper_url}), Code: **[{repo_url}]({repo_url})**"
        else:
            content[paper_key] = f"|**{update_time}**|**{paper_title}**|{paper_first_author} et.al.|[{paper_id}]({paper_url})|null|\n"
            content_to_web[paper_key] = f"- {update_time}, **{paper_title}**, {paper_first_author} et.al., Paper: [{paper_url}]({paper_url})"

        comments = None
        if comments is not None:
            content_to_web[paper_key] += f", {comments}\n"
        else:
            content_to_web[paper_key] += f"\n"

    data = {topic: content}
    data_web = {topic: content_to_web}
    return data, data_web


def update_json_file(filename, data_all):
    with open(filename, "r", encoding='utf-8') as f:
        content = f.read()
        if not content:
            m = {}
        else:
            m = json.loads(content)

    json_data = m.copy()

    for data in data_all:
        for keyword in data.keys():
            papers = data[keyword]
            if keyword in json_data.keys():
                json_data[keyword].update(papers)
            else:
                json_data[keyword] = papers

    with open(filename, "w", encoding='utf-8') as f:
        json.dump(json_data, f)


def json_to_md(filename, md_filename,
               to_web=False,
               use_title=True,
               use_tc=True,
               show_badge=False):
    """
    @param filename: str
    @param md_filename: str
    @return None
    """

    DateNow = datetime.date.today()
    DateNow = str(DateNow)
    DateNow = DateNow.replace('-', '.')

    with open(filename, "r", encoding='utf-8') as f:
        content = f.read()
        if not content:
            data = {}
        else:
            data = json.loads(content)

    with open(md_filename, "w+", encoding='utf-8') as f:
        pass

    with open(md_filename, "a+", encoding='utf-8') as f:

        if (use_title == True) and (to_web == True):
            f.write("---\n" + "layout: default\n" + "---\n\n")

        if show_badge == True:
            f.write(f"[![Contributors][contributors-shield]][contributors-url]\n")
            f.write(f"[![Forks][forks-shield]][forks-url]\n")
            f.write(f"[![Stargazers][stars-shield]][stars-url]\n")
            f.write(f"[![Issues][issues-shield]][issues-url]\n\n")

        if use_title == True:
            f.write("## Updated on " + DateNow + "\n\n")
        else:
            f.write("> Updated on " + DateNow + "\n\n")

        if use_tc == True:
            f.write("<details>\n")
            f.write("  <summary>Table of Contents</summary>\n")
            f.write("  <ol>\n")
            for keyword in data.keys():
                day_content = data[keyword]
                if not day_content:
                    continue
                kw = keyword.replace(' ', '-')
                f.write(f"    <li><a href=#{kw}>{keyword}</a></li>\n")
            f.write("  </ol>\n")
            f.write("</details>\n\n")

        for keyword in data.keys():
            day_content = data[keyword]
            if not day_content:
                continue
            f.write(f"## {keyword}\n\n")

            if use_title == True:
                if to_web == False:
                    f.write("|Publish Date|Title|Authors|PDF|Code|\n" + "|---|---|---|---|---|\n")
                else:
                    f.write("| Publish Date | Title | Authors | PDF | Code |\n")
                    f.write("|:---------|:-----------------------|:---------|:------|:------|\n")

            day_content = sort_papers(day_content)

            for _, v in day_content.items():
                if v is not None:
                    f.write(v)

            f.write(f"\n")

            top_info = f"#Updated on {DateNow}"
            top_info = top_info.replace(' ', '-').replace('.', '')
            f.write(f"<p align=right>(<a href={top_info}>back to top</a>)</p>\n\n")

        if show_badge == True:
            f.write(f"[contributors-shield]: https://img.shields.io/github/contributors/SpikingChen/snn-arxiv-daily.svg?style=for-the-badge\n")
            f.write(f"[contributors-url]: https://github.com/SpikingChen/snn-arxiv-daily/graphs/contributors\n")
            f.write(f"[forks-shield]: https://img.shields.io/github/forks/SpikingChen/snn-arxiv-daily.svg?style=for-the-badge\n")
            f.write(f"[forks-url]: https://github.com/SpikingChen/snn-arxiv-daily/network/members\n")
            f.write(f"[stars-shield]: https://img.shields.io/github/stars/SpikingChen/snn-arxiv-daily.svg?style=for-the-badge\n")
            f.write(f"[stars-url]: https://github.com/SpikingChen/snn-arxiv-daily/stargazers\n")
            f.write(f"[issues-shield]: https://img.shields.io/github/issues/SpikingChen/snn-arxiv-daily.svg?style=for-the-badge\n")
            f.write(f"[issues-url]: https://github.com/SpikingChen/snn-arxiv-daily/issues\n\n")

    print("finished")


if __name__ == "__main__":

    data_collector = []
    data_collector_web = []

    keywords = dict()
    keywords["Spatio-Temporal Neural Network"] = ("Spatial Temporal Neural Network")

    for topic, keyword in keywords.items():
        print("Keyword: " + topic)

        data, data_web = get_daily_papers(topic, query=keyword, max_results=100)
        data_collector.append(data)
        data_collector_web.append(data_web)

        print("\n")

    json_file = "stnn-arxiv-daily.json"
    md_file = "README.md"
    update_json_file(json_file, data_collector)
    json_to_md(json_file, md_file)