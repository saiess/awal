"""One-time vendor of official Swagger UI assets for offline API documentation."""
import hashlib
import json
import urllib.request
import urllib.error
import base64
import io
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "local-narration-setup"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main():
    receipt = ROOT / "docs/swagger-ui-assets.json"
    previous = json.loads(receipt.read_text()) if receipt.exists() else None
    revision = previous["revision"] if previous else json.loads(get("https://api.github.com/repos/swagger-api/swagger-ui/commits/v5.17.14"))["sha"]
    destination = ROOT / "app/static/vendor/swagger"
    destination.mkdir(parents=True, exist_ok=True)
    files, missing = [], []
    npm_notice = None
    for source, name in [("dist/swagger-ui-bundle.js", "swagger-ui-bundle.js"), ("dist/swagger-ui.css", "swagger-ui.css"),
                         ("LICENSE", "LICENSE"), ("dist/swagger-ui-bundle.js.LICENSE.txt", "swagger-ui-bundle.js.LICENSE.txt"),
                         ("NOTICE", "NOTICE")]:
        url = f"https://raw.githubusercontent.com/swagger-api/swagger-ui/{revision}/{source}"
        try:
            data = get(url)
        except urllib.error.HTTPError as e:
            if e.code == 404 and name == "swagger-ui-bundle.js.LICENSE.txt":
                metadata = json.loads(get("https://registry.npmjs.org/swagger-ui-dist/5.17.14"))
                dist = metadata["dist"]
                package = get(dist["tarball"])
                algorithm, digest = dist["integrity"].split("-", 1)
                assert algorithm == "sha512" and base64.b64encode(hashlib.sha512(package).digest()).decode() == digest
                with tarfile.open(fileobj=io.BytesIO(package), mode="r:gz") as archive:
                    names = archive.getnames()
                    candidate = next((n for n in names if n == "package/swagger-ui-bundle.js.LICENSE.txt"), None)
                    if candidate is None:
                        missing.append(source)
                        npm_notice = {"registry": "https://registry.npmjs.org/swagger-ui-dist/5.17.14",
                                      "tarball": dist["tarball"], "integrity": dist["integrity"],
                                      "note": "Referenced webpack license sidecar absent from official Git tree and npm release. Original aggregate LICENSE and NOTICE retained; no substitute sidecar fabricated."}
                        continue
                    data = archive.extractfile(candidate).read()
                npm_notice = {"registry": "https://registry.npmjs.org/swagger-ui-dist/5.17.14",
                              "tarball": dist["tarball"], "integrity": dist["integrity"], "member": candidate}
                url = dist["tarball"] + "#" + candidate
            elif e.code == 404 and name == "NOTICE":
                missing.append(source)
                continue
            else:
                raise
        checksum = hashlib.sha256(data).hexdigest()
        expected = next((f["sha256"] for f in previous["files"] if f["file"] == name), None) if previous else None
        if expected:
            assert checksum == expected
        (destination / name).write_bytes(data)
        files.append({"file": name, "url": url, "sha256": checksum, "bytes": len(data)})
    receipt.write_text(json.dumps({"version": "5.17.14", "revision": revision, "files": files, "missing_upstream": missing,
                                   "published_notice_source": npm_notice}, indent=2), encoding="utf-8")
    print(f"Vendored {len(files)} official Swagger UI assets at {revision}")


if __name__ == "__main__":
    main()
