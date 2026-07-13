import argparse
import concurrent.futures
import urllib.error
import urllib.request


def call(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def send_many(base_url, path, count, workers):
    url = f"{base_url.rstrip('/')}{path}"
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        statuses = list(pool.map(call, [url] * count))
    print(f"{path}: sent={count}, statuses={dict((s, statuses.count(s)) for s in sorted(set(statuses)))}")


def main():
    parser = argparse.ArgumentParser(description="Generate demo-service baseline and fault traffic")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--normal", type=int, default=40)
    parser.add_argument("--slow", type=int, default=12)
    parser.add_argument("--errors", type=int, default=20)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    send_many(args.base_url, "/", args.normal, args.workers)
    send_many(args.base_url, "/slow", args.slow, args.workers)
    send_many(args.base_url, "/error", args.errors, args.workers)


if __name__ == "__main__":
    main()
