import os, sys, time, json, threading, urllib.parse, random
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
from cloakbrowser import launch

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

PHONE = os.getenv("RAILWAY_PHONE")
PASSWORD = os.getenv("RAILWAY_PASSWORD")

HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>Railway Booker</title>
<style>
*{box-sizing:border-box;font-family:system-ui,sans-serif}
body{background:#f0f2f5;display:flex;justify-content:center;padding:40px;margin:0}
.card{background:#fff;border-radius:12px;padding:32px;max-width:520px;width:100%;box-shadow:0 2px 12px rgba(0,0,0,.08)}
h2{margin:0 0 24px;color:#1a1a2e;font-size:22px}
.row{display:flex;gap:12px}
.row .field{flex:1}
.field{margin-bottom:16px}
label{display:block;font-size:13px;font-weight:600;color:#444;margin-bottom:4px}
input{width:100%;padding:10px 12px;border:1px solid #ccc;border-radius:8px;font-size:14px}
input:focus{outline:2px solid #4a6cf7;border-color:transparent}
.btn{width:100%;padding:12px;background:#4a6cf7;color:#fff;border:none;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;margin-top:8px}
.btn:hover{background:#3b5de7}
.btn-danger{background:#dc3545}
.btn-danger:hover{background:#c82333}
.btn:disabled{opacity:.6;cursor:not-allowed}
.note{font-size:12px;color:#888;margin-top:12px;text-align:center}
.hidden{display:none}
#log{background:#1a1a2e;color:#0f0;padding:12px;border-radius:8px;font-family:monospace;font-size:12px;max-height:200px;overflow-y:auto;white-space:pre-wrap;margin-top:12px}
#countdown{text-align:center;font-size:28px;font-weight:700;color:#4a6cf7;padding:12px;display:none}
</style></head>
<body>
<div class="card">
<h2>Bangladesh Railway Booking</h2>
<form id="f" method="POST">
<div class="row">
<div class="field"><label>From</label><input name="from" value="Panchagarh"></div>
<div class="field"><label>To</label><input name="to" value="Dhaka"></div>
</div>
<div class="row">
<div class="field"><label>Class</label><input name="cls" value="SNIGDHA"></div>
                <div class="field"><label>Travel Date (YYYY-MM-DD or DD-MM-YYYY)</label><input name="travel_date" type="date" value="2026-06-03"></div>
</div>
<div class="row">
<div class="field"><label>Train Name</label><input name="train" value="PANCHAGARH EXPRESS (794)"></div>
<div class="field"><label>Seats</label><input name="num_seats" type="number" value="3" min="1" max="4"></div>
</div>
<hr style="margin:18px 0;border:none;border-top:1px solid #eee">
<p style="margin:0 0 12px;font-size:13px;color:#666">Click BOOK NOW at:</p>
<div class="row">
<div class="field"><label>Date</label><input name="click_date" type="date" value="2026-05-23"></div>
<div class="field"><label>Time</label><input name="click_time" type="time" value="08:00:01" step="1"></div>
</div>
                <div class="field"><label>Seat Numbers (e.g. 75,76 or GHA-75,GHA-76)</label><input name="seats" value="75,76"></div>
<button class="btn" type="submit" id="startBtn">Start Booking</button>
</form>
<div id="countdown"></div>
<div id="log" class="hidden"></div>
</div>
<script>
var polling, countdownTimer;
document.getElementById('f').onsubmit = function(e){
  e.preventDefault();
  var f = this;
  document.getElementById('log').classList.remove('hidden');
  document.getElementById('log').textContent = '';
  f.querySelector('#startBtn').disabled = true;
  f.querySelector('#startBtn').textContent = 'Running...';
  var data = new URLSearchParams(new FormData(f));
  fetch('/', {method:'POST', body:data}).then(function(r){return r.text()}).then(function(t){
    document.getElementById('log').textContent += t + '\\n';
    countdownTimer = setInterval(function(){
      fetch('/target').then(function(r){return r.text()}).then(function(ts){
        var target = parseInt(ts);
        if(!target) return;
        var diff = Math.max(0, Math.floor((target - Date.now())/1000));
        var h = Math.floor(diff/3600);
        var m = Math.floor((diff%3600)/60);
        var s = diff%60;
        var cd = document.getElementById('countdown');
        cd.style.display = 'block';
        cd.textContent = (h>0?h+'h ':'') + (m>0?m+'m ':'') + s+'s';
        if(diff<=0){ cd.style.color = '#dc3545'; cd.textContent = 'BOOKING NOW!'; }
        else { cd.style.color = '#4a6cf7'; }
      });
    }, 500);
    polling = setInterval(function(){
      fetch('/status').then(function(r){return r.text()}).then(function(s){
        document.getElementById('log').textContent += s;
        document.getElementById('log').scrollTop = document.getElementById('log').scrollHeight;
      });
    }, 1000);
    setTimeout(function(){
      var btn = document.createElement('button');
      btn.className = 'btn btn-danger';
      btn.textContent = 'Stop';
      btn.onclick = function(){
        fetch('/stop');
        btn.disabled = true;
        btn.textContent = 'Stopping...';
      };
      document.getElementById('log').after(btn);
    }, 2000);
  });
};
</script>
</body>
</html>"""

config = {}
target_ts = 0
cancelled = False
config_ready = threading.Event()
log_lines = []

def log(msg):
    with log_lines_lock:
        log_lines.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    print(msg, flush=True)

log_lines_lock = threading.Lock()

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            with log_lines_lock:
                self.wfile.write("".join(log_lines[-30:]).encode())
            return
        if self.path == "/target":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(str(target_ts).encode())
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode())

    def do_POST(self):
        global config, cancelled, target_ts
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/stop":
            cancelled = True
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Stopped")
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        data = {k: v for k, v in urllib.parse.parse_qs(body).items()}
        config = {k: v[0] if isinstance(v, list) else v for k, v in data.items()}
        click_dt = config.get("click_date", "2026-05-23")
        click_tm = config.get("click_time", "08:00:01")
        ymd = click_dt.split("-")
        hmss = click_tm.split(":")
        tgt = datetime(int(ymd[0]), int(ymd[1]), int(ymd[2]), int(hmss[0]), int(hmss[1]), int(hmss[2]))
        target_ts = int(tgt.timestamp() * 1000)
        log("Config received. Starting booking...")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Config received. Starting booking...")
        config_ready.set()

    def log_message(self, fmt, *args):
        pass

class CancelledError(Exception):
    pass

def check_cancel():
    if cancelled:
        raise CancelledError()

for port in range(8923, 8950):
    try:
        server = HTTPServer(("127.0.0.1", port), Handler)
        break
    except OSError:
        continue
else:
    print("No free port found on 8923-8949", flush=True)
    sys.exit(1)

log(f"Open http://127.0.0.1:{port}/ in your browser, fill the form, and click Start.")
server_thread = threading.Thread(target=server.serve_forever, daemon=True)
server_thread.start()

config_ready.wait()
log("Config received, starting booking sequence...")
check_cancel()

try:
    FROM = config.get("from", "Panchagarh")
    TO = config.get("to", "Dhaka")
    CLASS = config.get("cls", "SNIGDHA")
    raw_date = config.get("travel_date", "2026-06-03")
    raw_date = raw_date.split("T")[0].strip()
    try:
        d = datetime.strptime(raw_date, "%Y-%m-%d")
    except ValueError:
        d = datetime.strptime(raw_date, "%d-%m-%Y")
    TARGET_DATE = d.strftime("%d-%b-%Y")
    target_train = config.get("train", "PANCHAGARH EXPRESS (794)")
    num_seats = int(config.get("num_seats", "3"))
    click_dt = config.get("click_date", "2026-05-23")
    click_tm = config.get("click_time", "08:00:01")
    ymd = click_dt.split("-")
    hmss = click_tm.split(":")
    CLICK_TIME = datetime(int(ymd[0]), int(ymd[1]), int(ymd[2]), int(hmss[0]), int(hmss[1]), int(hmss[2]))
    seats_raw = config.get("seats", "75,76")
    SEATS_INPUT = [s.strip() for s in seats_raw.split(",")] if seats_raw else []

    # Early check: warn if CLICK_TIME is already past
    if datetime.now() >= CLICK_TIME:
        log("  NOTE: Click time is already past. To test with a timer, set a future time.")
    else:
        log(f"  Will wait at [2] until {CLICK_TIME}.")

    log("[1] Launching browser...")
    browser = launch(headless=False, humanize=False)
    log("  Browser launched.")
    page = browser.new_page()
    page.set_viewport_size({"width": 1920, "height": 1080})

    log("  Navigating to search page...")
    page.goto(f"https://eticket.railway.gov.bd/booking/train/search"
              f"?fromcity={FROM}&tocity={TO}&doj={TARGET_DATE}&class={CLASS}",
              timeout=60000)
    log("  Page loaded.")
    for _ in range(30):
        check_cancel()
        if page.query_selector("#select-bogie, .book-now-btn, #mobile_number"):
            break
        page.wait_for_timeout(500)
    check_cancel()

    log(f"  Page URL: {page.url}")
    log(f"  Page title: {page.title()}")
    login_found = page.query_selector("#mobile_number")
    log(f"  Login form (#mobile_number) found: {login_found is not None}")
    if login_found:
        log("  Login form detected — filling credentials...")
        page.fill("#mobile_number", PHONE)
        page.fill("#password", PASSWORD)
        log("  Please solve the Cloudflare captcha and click login manually.")
        log("  Waiting for login to complete...")
        for _ in range(120):
            check_cancel()
            if page.query_selector("#select-bogie, .book-now-btn"):
                log("  Login successful!")
                break
            page.wait_for_timeout(500)
        else:
            log("  Login not detected after 60s. Proceeding anyway...")
    check_cancel()

    token = page.evaluate("localStorage.getItem('access_token') || ''")
    if not token:
        log("Warning: No JWT found")

    now = datetime.now()
    diff = (CLICK_TIME - now).total_seconds()
    log(f"  Now={now}  Target={CLICK_TIME}  Diff={diff:.0f}s")

    # Phase A: Wait until 5s before click time, then pre-locate the Book Now button
    if diff > 5:
        wait_before = diff - 5
        log(f"\n[2] Waiting {wait_before:.0f}s, then pre-locating Book Now button...")
        while (CLICK_TIME - datetime.now()).total_seconds() > 5 and not cancelled:
            time.sleep(0.5)
    check_cancel()

    # Pre-locate the target train's "Book Now" button and save click JS
    log(f"  Pre-locating Book Now button ({(CLICK_TIME-datetime.now()).total_seconds():.1f}s before target)...")
    book_now_found = None
    for _ in range(15):
        check_cancel()
        book_now_found = page.evaluate(f"""() => {{
            const all = document.querySelectorAll('[class*="trip"], [class*="train"], [class*="result"]');
            for (const el of all) {{
                if (el.innerText.includes('{target_train}')) {{
                    const buttons = el.querySelectorAll('.book-now-btn');
                    for (const btn of buttons) {{
                        const parent = btn.closest('[class*="coach"], [class*="class"], [class*="trip"]');
                        if (parent && parent.innerText.includes('{CLASS}')) {{
                            return {{
                                found: true,
                                parentText: parent.innerText.substring(0, 50)
                            }};
                        }}
                    }}
                    if (buttons.length > 0) {{
                        return {{ found: true, parentText: '' }};
                    }}
                }}
            }}
            return {{ found: false }};
        }}""")
        if book_now_found and book_now_found.get("found"):
            log(f"  Book Now button confirmed for {target_train} / {CLASS}")
            break
        page.wait_for_timeout(500)

    # Use JavaScript setTimeout for sub-ms precision click at target time
    target_ms = int(CLICK_TIME.timestamp() * 1000)
    t_click_start = time.time()
    page.evaluate(f"""() => {{
        const target = {target_ms};
        const delay = Math.max(0, target - Date.now());
        setTimeout(() => {{
            const all = document.querySelectorAll('[class*="trip"], [class*="train"], [class*="result"]');
            for (const el of all) {{
                if (el.innerText.includes('{target_train}')) {{
                    const buttons = el.querySelectorAll('.book-now-btn');
                    for (const btn of buttons) {{
                        const parent = btn.closest('[class*="coach"], [class*="class"], [class*="trip"]');
                        if (parent && parent.innerText.includes('{CLASS}')) {{
                            btn.click();
                            window.__bookNowClicked = true;
                            return;
                        }}
                    }}
                    if (buttons.length > 0) {{
                        buttons[0].click();
                        window.__bookNowClicked = true;
                        return;
                    }}
                }}
            }}
        }}, delay);
    }}""")
    # Wait for the JS timer to fire + small buffer
    remaining = (CLICK_TIME - datetime.now()).total_seconds()
    if remaining > 0:
        time.sleep(remaining + 0.1)
    else:
        time.sleep(0.1)
    t_click_actual = time.time()
    log(f"\n[3] Book Now fired (JS timer target: {CLICK_TIME.strftime('%H:%M:%S.%f')[:-3]}, page confirmed: {page.evaluate('window.__bookNowClicked || false')})")

    # Fallback: if JS timer didn't work, click manually
    if not page.evaluate("window.__bookNowClicked || false"):
        log("  JS timer did not fire, clicking manually...")
        for _ in range(30):
            check_cancel()
            cards = page.evaluate(f"""() => {{
                const all = document.querySelectorAll('[class*="trip"], [class*="train"], [class*="result"]');
                for (const el of all) {{
                    if (el.innerText.includes('{target_train}')) {{
                        const buttons = el.querySelectorAll('.book-now-btn');
                        for (const btn of buttons) {{
                            const parent = btn.closest('[class*="coach"], [class*="class"], [class*="trip"]');
                            if (parent && parent.innerText.includes('{CLASS}')) {{
                                btn.click();
                                return true;
                            }}
                        }}
                        buttons[0].click();
                        return true;
                    }}
                }}
                return false;
            }}""")
            if cards:
                break
            page.wait_for_timeout(500)

    log(f"\n[4] Waiting for seat layout ({(datetime.now()-CLICK_TIME).total_seconds()*1000:.0f}ms after target)...")
    for _ in range(30):
        check_cancel()
        sel = page.query_selector("#select-bogie")
        if sel and sel.is_visible():
            log(f"  Seat layout loaded ({(datetime.now()-CLICK_TIME).total_seconds()*1000:.0f}ms after target)")
            break
        page.wait_for_timeout(500)
    else:
        log("  Coach dropdown didn't appear!")
        page.screenshot(path="debug_no_coach.png")

    options = page.evaluate("""() => {
        const sel = document.getElementById('select-bogie');
        if (!sel) return [];
        return Array.from(sel.options).map(o => ({v: o.value, t: o.text}));
    }""")
    log(f"  Coaches: {options}")

    gha_val = None
    for o in options:
        if "GHA" in o["t"].upper():
            gha_val = o["v"]
            break
    if gha_val is None:
        for o in reversed(options):
            if "0 seat" not in o["t"].lower():
                gha_val = o["v"]
                break

    page.select_option("#select-bogie", value=gha_val or "1")

    selected_coach_text = None
    for o in options:
        if o["v"] == (gha_val or "1"):
            selected_coach_text = o["t"]
            break
    coach_prefix = selected_coach_text.split(" - ")[0].strip() if selected_coach_text else "GHA"

    PREFERRED_SEATS = []
    for s in SEATS_INPUT:
        if s.isdigit():
            PREFERRED_SEATS.append(f"{coach_prefix}-{s}")
        else:
            PREFERRED_SEATS.append(s)
    if not PREFERRED_SEATS:
        PREFERRED_SEATS = [f"{coach_prefix}-75", f"{coach_prefix}-76"]

    for _ in range(30):
        check_cancel()
        count = page.evaluate("document.querySelectorAll('.modal-body button.btn-seat').length")
        if count > 0:
            log(f"  Seat buttons rendered: {count} seats ({(datetime.now()-CLICK_TIME).total_seconds()*1000:.0f}ms after target)")
            break
        page.wait_for_timeout(500)

    available = page.evaluate("""() => {
        const btns = document.querySelectorAll('.modal-body button.btn-seat.seat-available');
        return Array.from(btns).map(b => {
            const w = b.closest('[ticketid]');
            return {seat: b.title || b.innerText.trim(), ticket_id: w ? w.getAttribute('ticketid') : ''};
        });
    }""")
    log(f"  Seats available: {len(available)} seats ({(datetime.now()-CLICK_TIME).total_seconds()*1000:.0f}ms after target)")
    check_cancel()

    if not available:
        log("  No available seats. Browser stays open.")

    targets = []
    for pref in PREFERRED_SEATS:
        for s in available:
            if s["seat"] == pref:
                targets.append(s)
                break
    while len(targets) < num_seats and len(targets) < len(available):
        for s in available:
            if s not in targets:
                targets.append(s)
                break
    targets = targets[:num_seats]

    log(f"  Targets: {[t['seat'] for t in targets]}")
    check_cancel()

    results = []
    def on_resp(r):
        if "reserve-seat" in r.url:
            try:
                data = r.json()
                results.append(data)
            except Exception as e:
                log(f"  WARN: response json() failed for {r.url}: {e}")
    page.on("response", on_resp)

    t0 = time.time()
    clicked = set()
    targets_tried = False

    while len([r for r in results if r.get("data", {}).get("ack") == 1]) < num_seats:
        check_cancel()

        if not targets_tried and targets:
            targets_tried = True
            seats_to_try = [s for s in targets if s["ticket_id"] not in clicked]
            log(f"  Trying {len(seats_to_try)} preferred targets: {[s['seat'] for s in seats_to_try]}")
        else:
            available = page.evaluate("""() => {
                const btns = document.querySelectorAll('.modal-body button.btn-seat.seat-available');
                return Array.from(btns).map(b => {
                    const w = b.closest('[ticketid]');
                    return {seat: b.title || b.innerText.trim(), ticket_id: w ? w.getAttribute('ticketid') : ''};
                });
            }""")
            seats_to_try = [s for s in available if s["ticket_id"] not in clicked]
            if not seats_to_try:
                log("  No more available seats to try.")
                break
            seats_to_try.sort(key=lambda s: 0 if s["seat"] in PREFERRED_SEATS else 1)
            seats_to_try = seats_to_try[:num_seats]
            log(f"  Trying {len(seats_to_try)} more seats: {[s['seat'] for s in seats_to_try]}")

        if not seats_to_try:
            log("  No more available seats to try.")
            break

        for seat in seats_to_try:
            clicked.add(seat["ticket_id"])
            t_click = time.time()
            page.evaluate(f"""() => {{
                const name = '{seat["seat"]}';
                const btns = document.querySelectorAll('.modal-body button.btn-seat.seat-available');
                for (const b of btns) {{
                    if ((b.title || b.innerText.trim()) === name && !b.disabled) {{
                        b.click();
                        break;
                    }}
                }}
}}""")
            log(f"    Clicked {seat['seat']} ({(t_click-t0)*1000:.0f}ms, +{(time.time()-t_click)*1000:.0f}ms eval)")
            page.wait_for_timeout(random.randint(200, 250))

        for _ in range(40):
            check_cancel()
            confirmed = len([r for r in results if r.get("data", {}).get("ack") == 1])
            if confirmed >= num_seats:
                break
            page.wait_for_timeout(250)

    total = time.time() - t0
    confirmed = [r for r in results if r.get("data", {}).get("ack") == 1]

    log(f"\n[5] Results ({total:.2f}s total):")
    log(f"  Total responses captured: {len(results)}")
    for i, r in enumerate(confirmed):
        d = r.get("data", {})
        log(f"  Seat {i+1}: ack={d.get('ack')} msg={d.get('message')} data={d}")
    for i, r in enumerate(results):
        if r not in confirmed:
            d = r.get("data", {})
            log(f"  Failed {i+1}: ack={d.get('ack')} msg={d.get('message')} data={d}")
    if len(confirmed) < num_seats:
        log(f"  Only {len(confirmed)}/{num_seats} seats confirmed.")

    page.screenshot(path="booking_result.png")
    log("\nBrowser stays open for manual payment.")

except CancelledError:
    log("Cancelled by user. Browser stays open.")
except Exception as e:
    log(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    log(traceback.format_exc())

log("Done. Close the terminal to exit.")
while True:
    time.sleep(1)
