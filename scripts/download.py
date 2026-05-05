"""Download every Stanford CDS PDF from Google Drive."""
import os, sys, urllib.request, urllib.parse, re
sys.path.insert(0, os.path.dirname(__file__))
from manifest import CDS_MANIFEST

OUT = "/sessions/compassionate-sleepy-fermat/mnt/outputs/stanford-cds-open/raw_pdfs"
os.makedirs(OUT, exist_ok=True)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=60)

def download(year, file_id):
    out_path = os.path.join(OUT, f"stanford-cds-{year}.pdf")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 50_000:
        print(f"  [skip] {year}: already have {os.path.getsize(out_path):,} bytes")
        return True
    # Drive public file - try direct download
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        r = fetch(url)
        data = r.read()
    except Exception as e:
        print(f"  [err] {year}: {e}")
        return False
    # If we got an HTML page (virus warning), need to follow the form
    if data[:4] != b"%PDF":
        # Look for the confirm token in the HTML
        html = data.decode("utf-8", errors="ignore")
        # New-style: form with action="https://drive.usercontent.google.com/download"
        m = re.search(r'action="(https://drive\.usercontent\.google\.com/download[^"]*)"', html)
        if m:
            action = m.group(1).replace("&amp;", "&")
            # Collect hidden inputs
            inputs = dict(re.findall(r'name="([^"]+)"\s+value="([^"]*)"', html))
            params = urllib.parse.urlencode(inputs)
            url2 = f"{action}&{params}"
            try:
                data = fetch(url2).read()
            except Exception as e:
                print(f"  [err] {year}: {e}")
                return False
        # Old-style confirm token
        elif 'confirm=' in html:
            m2 = re.search(r'confirm=([0-9A-Za-z_-]+)', html)
            if m2:
                url2 = f"https://drive.google.com/uc?export=download&confirm={m2.group(1)}&id={file_id}"
                try:
                    data = fetch(url2).read()
                except Exception as e:
                    print(f"  [err] {year}: {e}")
                    return False
    if data[:4] != b"%PDF":
        print(f"  [err] {year}: did not get a PDF (first bytes: {data[:50]!r})")
        return False
    with open(out_path, "wb") as f:
        f.write(data)
    print(f"  [ok]   {year}: {len(data):,} bytes")
    return True

ok = 0
for year, fid in CDS_MANIFEST:
    if download(year, fid):
        ok += 1
print(f"\nDownloaded {ok}/{len(CDS_MANIFEST)} PDFs")
