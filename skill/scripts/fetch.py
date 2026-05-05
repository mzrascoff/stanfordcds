"""Download every PDF listed in manifest.py into raw_pdfs/.

Handles:
  - HTTP(S) URLs - direct download with a user-agent header.
  - Google Drive file IDs - follows the virus-scan-warning interstitial.
  - Local paths - copies the file into raw_pdfs/ for uniformity.
"""
import os, re, shutil, sys, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(__file__))
from manifest import CDS_MANIFEST

OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "raw_pdfs"))
os.makedirs(OUT, exist_ok=True)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def looks_like_drive_id(s):
    return re.fullmatch(r"[A-Za-z0-9_-]{20,80}", s) is not None

def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=60).read()

def fetch_drive(file_id):
    """Download a Google Drive file, handling the virus-scan interstitial."""
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    data = http_get(url)
    if data[:4] != b"%PDF":
        html = data.decode("utf-8", errors="ignore")
        m = re.search(r'action="(https://drive\.usercontent\.google\.com/download[^"]*)"', html)
        if m:
            action = m.group(1).replace("&amp;", "&")
            inputs = dict(re.findall(r'name="([^"]+)"\s+value="([^"]*)"', html))
            url2 = f"{action}&{urllib.parse.urlencode(inputs)}"
            data = http_get(url2)
        elif 'confirm=' in html:
            m2 = re.search(r'confirm=([0-9A-Za-z_-]+)', html)
            if m2:
                data = http_get(f"https://drive.google.com/uc?export=download&confirm={m2.group(1)}&id={file_id}")
    if data[:4] != b"%PDF":
        raise RuntimeError(f"did not get a PDF from Drive id {file_id}")
    return data

def download(year_label, source):
    out_path = os.path.join(OUT, f"cds-{year_label}.pdf")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 50_000:
        print(f"  [skip] {year_label}: already have {os.path.getsize(out_path):,} bytes")
        return True

    try:
        if source.startswith(("http://", "https://")):
            data = http_get(source)
            if data[:4] != b"%PDF":
                # Some sites redirect to an HTML wrapper; try Drive flow if it looks Drive-ish.
                if "drive.google.com" in source:
                    m = re.search(r"/d/([A-Za-z0-9_-]+)", source)
                    if m: data = fetch_drive(m.group(1))
                if data[:4] != b"%PDF":
                    raise RuntimeError("response is not a PDF")
        elif looks_like_drive_id(source):
            data = fetch_drive(source)
        elif os.path.isabs(source) and os.path.exists(source):
            shutil.copyfile(source, out_path)
            print(f"  [cp]   {year_label}: copied {os.path.getsize(out_path):,} bytes")
            return True
        else:
            raise RuntimeError(f"unrecognized source format: {source!r}")
    except Exception as e:
        print(f"  [err]  {year_label}: {e}")
        return False

    with open(out_path, "wb") as f:
        f.write(data)
    print(f"  [ok]   {year_label}: {len(data):,} bytes")
    return True

def main():
    if not CDS_MANIFEST:
        print("ERROR: scripts/manifest.py is empty. Add (year, source) entries first.")
        sys.exit(1)
    ok = sum(download(y, s) for y, s in CDS_MANIFEST)
    print(f"\nDownloaded {ok}/{len(CDS_MANIFEST)} PDFs to {OUT}")

if __name__ == "__main__":
    main()
