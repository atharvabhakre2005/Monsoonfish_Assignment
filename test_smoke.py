"""Quick smoke test: create a test image, POST to /process, verify all 3 outputs."""

import sys
import json
import urllib.request
import urllib.error
from pathlib import Path

# Add project root so we can reuse the image processor directly too
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import cv2


def create_test_image() -> bytes:
    """Create a simple 200x200 PNG with a white circle on transparent background."""
    img = np.zeros((200, 200, 4), dtype=np.uint8)
    # Draw a white filled circle
    cv2.circle(img, (100, 100), 60, (255, 255, 255, 255), -1)
    # Draw a smaller black circle inside (donut shape)
    cv2.circle(img, (100, 100), 30, (0, 0, 0, 0), -1)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def test_invalid_extension():
    """Test that .txt files are rejected."""
    boundary = b"----TestBoundary"
    body = (
        b"------TestBoundary\r\n"
        b'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
        b"Content-Type: text/plain\r\n\r\n"
        b"not an image\r\n"
        b"------TestBoundary--\r\n"
    )
    req = urllib.request.Request(
        "http://127.0.0.1:8000/process",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary=----TestBoundary"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req)
        print("FAIL: expected 415 for .txt upload")
        return False
    except urllib.error.HTTPError as e:
        if e.code == 415:
            print("PASS: .txt upload correctly rejected with 415")
            return True
        print(f"FAIL: expected 415 but got {e.code}")
        return False


def test_process_image():
    """Test the full processing pipeline."""
    img_bytes = create_test_image()

    boundary = b"----TestBoundary123"
    body = (
        b"------TestBoundary123\r\n"
        b'Content-Disposition: form-data; name="file"; filename="test_logo.png"\r\n'
        b"Content-Type: image/png\r\n\r\n"
        + img_bytes
        + b"\r\n------TestBoundary123--\r\n"
    )
    req = urllib.request.Request(
        "http://127.0.0.1:8000/process",
        data=body,
        headers={"Content-Type": "multipart/form-data; boundary=----TestBoundary123"},
        method="POST",
    )

    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        print(f"PASS: Processing succeeded — response: {json.dumps(data, indent=2)}")

        # Verify all 3 outputs are marked as generated
        assert data["silhouette"] == "generated", "silhouette not generated"
        assert data["border"] == "generated", "border not generated"
        assert data["grayscale"] == "generated", "grayscale not generated"
        print("PASS: All 3 outputs generated")

        # Verify download URLs work
        for name, url in data["downloads"].items():
            dl_resp = urllib.request.urlopen(f"http://127.0.0.1:8000{url}")
            size = len(dl_resp.read())
            print(f"  PASS: {name} downloadable ({size} bytes)")

        return True

    except urllib.error.HTTPError as e:
        print(f"FAIL: got HTTP {e.code}: {e.read().decode()}")
        return False
    except Exception as e:
        print(f"FAIL: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Logo Processing Service — Smoke Tests")
    print("=" * 60)

    results = []
    results.append(("Invalid extension rejection", test_invalid_extension()))
    results.append(("Full processing pipeline", test_process_image()))

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    print(f"Results: {passed}/{len(results)} passed")
    for name, ok in results:
        print(f"  {'✓' if ok else '✗'} {name}")
