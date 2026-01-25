import qrcode
import sys

# Ensure user passed URL
if len(sys.argv) > 1:
    url = sys.argv[1]
    img = qrcode.make(url)
    img.save("mobile_qr.png")
    print(f"QR code generated for {url}")
else:
    print("No URL provided")
