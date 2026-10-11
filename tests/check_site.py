"""Validate local asset links and committed generated features without a server."""
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote,urlsplit

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.research.core import build_features,load_snapshot


class Links(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]; self.ids=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        self.links.extend(attrs[key] for key in ("href","src") if key in attrs)
        if "id" in attrs: self.ids.append(attrs["id"])


def main():
    for file in (ROOT/"docs").glob("*.html"):
        parser=Links();parser.feed(file.read_text(encoding="utf-8"))
        assert len(parser.ids)==len(set(parser.ids)),f"Duplicate HTML ID in {file}"
        for link in parser.links:
            url=urlsplit(link)
            if url.scheme or url.netloc or not url.path: continue
            target=(file.parent/unquote(url.path)).resolve()
            assert target.exists(),f"Missing asset/link: {file.name}: {link}"
    rows,coverage=build_features(load_snapshot(ROOT/"docs/data"))
    payload=json.loads((ROOT/"docs/data/research.json").read_text(encoding="utf-8"))
    assert coverage==payload["coverage"],"Regenerate stale research coverage"
    assert [[row[key] for key in payload["columns"]] for row in rows]==payload["rows"],"Regenerate stale research feature rows"
    print("PASS: HTML IDs, local navigation/assets, and generated research snapshot are current.")


if __name__=="__main__": main()
