from flask import Flask, url_for, request, abort, redirect, send_file
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from urllib.parse import quote
import qrcode
from io import BytesIO
import os

app = Flask(__name__)

# For Render deployment. If this causes issues locally, comment SERVER_NAME when testing on localhost.
app.config['SERVER_NAME'] = "chirayu-navigation.onrender.com"
app.config['PREFERRED_URL_SCHEME'] = 'https'

SECRET_KEY = "your-very-secret-key"
serializer = URLSafeTimedSerializer(SECRET_KEY)

ANDROID_PACKAGE = "com.mmi.maps"
PLAY_STORE_URL = f"https://play.google.com/store/apps/details?id={ANDROID_PACKAGE}&hl=en_IN"
IOS_APPSTORE_URL = "https://apps.apple.com/in/app/mappls-mapmyindia/id723492531"

# ---------------------------
# Department coordinates
# ---------------------------
EAST_LAND_DEPARTMENTS = {
    "project_planning": "13.2057989,80.3209443",
    "shop_vii": "13.2062904,80.3207080",
    "shop_vi": "13.2099126,80.3209142",
    "shop_v": "13.2086706,80.3205279",
    "shop_iv": "13.2070161,80.3203764",
    "ev_shop": "13.2075096,80.3191446",
    "hrd_centre": "13.2068653,80.3192841",
    "canteen": "13.2066567,80.3192250",
    "central_quality_office": "13.2064706,80.3196311",
    "field_quality_centre": "13.206572069601032, 80.31957997029414",
    "defense_sourcing": "13.2057989,80.3209443",
}

EAST_LAND_DISPLAY = {
    "project_planning": "Project Planning",
    "shop_vii": "Shop VII",
    "shop_vi": "Shop VI",
    "shop_v": "Shop V",
    "shop_iv": "Shop IV",
    "ev_shop": "EV Shop",
    "hrd_centre": "HRD Centre",
    "canteen": "Canteen",
    "central_quality_office": "Central Quality Office",
    "field_quality_centre": "Field Quality Centre",
    "defense_sourcing": "Defense Sourcing",
}

MAIN_LAND_DEPARTMENTS = {
    "chassis_shop": "13.209549919810451,80.31742205591088",
    "gearbox_6s": "13.209837363670559,80.31813483425225",
    "gearbox_9s": "13.209837363670559,80.31813483425225",
    "heat_treatment": "13.207957473496801,80.31784613241723",
    "admin_finance": "13.209693574424433,80.3166161104447",
    "canteen_main": "13.209821525072439,80.31702112397613",
    "shop_2_office": "13.208204685252353,80.31658514318255",
    "vts_shop": "13.208029794646409,80.31705504743034",
}

MAIN_LAND_DISPLAY = {
    "chassis_shop": "Chassis Shop",
    "gearbox_6s": "Gearbox Assembly 6S",
    "gearbox_9s": "Gearbox Assembly 9S",
    "heat_treatment": "Heat Treatment",
    "admin_finance": "Admin Office - Finance",
    "canteen_main": "Canteen",
    "shop_2_office": "Shop 2 Office",
    "vts_shop": "VTS Shop",
}

TOKEN_MAX_AGE = 1800  # 30 minutes in seconds

# ---------------------------
# Landing page (static URL)
# ---------------------------
@app.route('/')
def landing_page():
    # home_qr_url is no longer used in UI, but backend /generate_home_qr still exists
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Ashok Leyland - Department Locator</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">

        <style>
            * { box-sizing: border-box; }
            body {
                margin: 0;
                font-family: "Segoe UI", Arial, sans-serif;
                background: #f4f7fb;
                color: #111827;
            }

            /* Top header with centered big logo */
            .app-header {
                background: #003366;
                color: #ffffff;
                padding: 22px 16px 18px;
                display: flex;
                justify-content: center;
                align-items: center;
                box-shadow: 0 4px 12px rgba(0,0,0,0.25);
            }
            .header-center {
                text-align: center;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 8px;
            }
            .logo-circle {
                width: 120px;
                height: 120px;
                border-radius: 999px;
                background: #ffffff;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 6px 18px rgba(0,0,0,0.35);
                overflow: hidden;
            }
            .logo-circle img {
                width: 100px;
                height: auto;
            }
            .header-title-main {
                font-size: 1.6rem;
                font-weight: 700;
                letter-spacing: 2px;
            }
            .header-title-sub {
                font-size: 0.9rem;
                opacity: 0.9;
            }

            .page-wrapper {
                max-width: 1200px;
                margin: 22px auto 32px;
                padding: 0 16px;
            }

            .page-title {
                font-size: 1.5rem;
                font-weight: 600;
                margin-bottom: 6px;
                color: #111827;
                text-align: center;
            }
            .page-subtitle {
                font-size: 0.95rem;
                color: #4b5563;
                margin-bottom: 18px;
                text-align: center;
            }

            /* Zone selector view */
            #zone-selector {
                text-align: center;
            }
            .zone-buttons {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 16px;
                margin-top: 18px;
            }
            .zone-btn {
                min-width: 220px;
                padding: 12px 18px;
                border-radius: 999px;
                border: none;
                background: #0074D9;
                color: #ffffff;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                box-shadow: 0 6px 16px rgba(0,116,217,0.4);
                text-transform: uppercase;
                letter-spacing: 0.08em;
            }
            .zone-btn:hover {
                background: #005fa3;
                transform: translateY(-1px);
            }

            /* Zone view (after clicking East/Main) */
            #zone-view {
                display: none;
            }
            .zone-header {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 14px;
            }
            .back-btn {
                border: none;
                background: transparent;
                font-size: 1.4rem;
                cursor: pointer;
                color: #003366;
                padding: 4px 8px 4px 0;
            }
            .zone-title-block {
                display: flex;
                flex-direction: column;
            }
            .zone-title {
                font-size: 1.3rem;
                font-weight: 600;
                color: #111827;
            }
            .zone-subtitle {
                font-size: 0.9rem;
                color: #4b5563;
            }

            .search-box {
                position: relative;
                margin-bottom: 18px;
            }
            .search-input {
                width: 100%;
                padding: 11px 40px 11px 14px;
                border-radius: 999px;
                border: 1px solid #d1d5db;
                font-size: 0.98rem;
                outline: none;
                box-shadow: 0 2px 8px rgba(15,23,42,0.06);
                background: #ffffff;
            }
            .search-input:focus {
                border-color: #0074D9;
                box-shadow: 0 0 0 1px rgba(0,116,217,0.3);
            }
            .search-icon {
                position: absolute;
                right: 14px;
                top: 50%;
                transform: translateY(-50%);
                font-size: 1.1rem;
                color: #9ca3af;
            }

            .layout-grid {
                display: block; /* single column now */
            }

            .card {
                background: rgba(255,255,255,0.95);
                border-radius: 16px;
                padding: 16px 16px 18px;
                box-shadow: 0 10px 25px rgba(15,23,42,0.12);
                border: 1px solid rgba(148,163,184,0.25);
                margin-bottom: 16px;
            }

            .dept-list {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .dept-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 6px;
            }

            /* Department button (keep same blue as original) */
            .dept-link {
                flex: 1;
                display: inline-block;
                padding: 9px 11px;
                background: #0074D9;
                border-radius: 999px;
                text-decoration: none;
                color: #ffffff;
                font-size: 0.95rem;
                font-weight: 500;
                border: 1px solid transparent;
                transition: all 0.18s ease;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .dept-link:hover {
                background: #005fa3;
                border-color: #003366;
                transform: translateY(-1px);
                box-shadow: 0 3px 6px rgba(0,0,0,0.25);
            }

            .footer-actions {
                margin-top: 24px;
                display: flex;
                flex-direction: column;
                gap: 10px;
                align-items: flex-start;
            }

            .note-text {
                font-size: 0.8rem;
                color: #003366;
                margin-top: 4px;
            }

            footer {
                text-align: center;
                font-size: 0.8rem;
                color: #6b7280;
                padding: 12px 0 20px;
            }

            @media (max-width: 640px) {
                .app-header {
                    padding: 18px 10px;
                }
                .logo-circle {
                    width: 100px;
                    height: 100px;
                }
                .logo-circle img {
                    width: 80px;
                }
                .page-wrapper {
                    margin-top: 18px;
                }
                .card {
                    padding: 14px 12px 16px;
                }
            }
        </style>

        <script>
            function openZone(zone) {
                document.getElementById('zone-selector').style.display = 'none';
                document.getElementById('zone-view').style.display = 'block';

                const eastZone = document.getElementById('east-zone');
                const mainZone = document.getElementById('main-zone');
                const title = document.getElementById('zone-title');
                const subtitle = document.getElementById('zone-subtitle');

                if (zone === 'east') {
                    eastZone.style.display = 'block';
                    mainZone.style.display = 'none';
                    title.textContent = 'East Land Departments';
                    subtitle.textContent = 'Select a department in East Land to start navigation.';
                } else {
                    eastZone.style.display = 'none';
                    mainZone.style.display = 'block';
                    title.textContent = 'Main Land Departments';
                    subtitle.textContent = 'Select a department in Main Land to start navigation.';
                }

                const search = document.getElementById('search');
                if (search) {
                    search.value = '';
                    filterDepts();
                }
            }

            function goBack() {
                document.getElementById('zone-view').style.display = 'none';
                document.getElementById('zone-selector').style.display = 'block';
            }

            function filterDepts() {
                const input = document.getElementById('search');
                if (!input) return;
                const term = input.value.toLowerCase();
                document.querySelectorAll('.dept-link').forEach(link => {
                    const row = link.parentElement;
                    const match = link.textContent.toLowerCase().includes(term);
                    row.style.display = match ? '' : 'none';
                });
            }
        </script>
    </head>
    <body>
        <header class="app-header">
            <div class="header-center">
                <div class="logo-circle">
                    <img src="/static/Ashok-Leyland-Logo.png" alt="Ashok Leyland Logo">
                </div>
                <div class="header-title-main">ASHOK LEYLAND</div>
                <div class="header-title-sub">Department Locator</div>
            </div>
        </header>

        <main class="page-wrapper">
            <!-- First view: Logo + two options -->
            <section id="zone-selector">
                <div class="page-title">Department Locator</div>
                <div class="page-subtitle">
                    Choose your zone inside the plant to view departments and open navigation.
                </div>
                <div class="zone-buttons">
                    <button class="zone-btn" onclick="openZone('east')">East Land Departments</button>
                    <button class="zone-btn" onclick="openZone('main')">Main Land Departments</button>
                </div>
            </section>

            <!-- Second view: zone-specific list with back arrow -->
            <section id="zone-view">
                <div class="zone-header">
                    <button class="back-btn" onclick="goBack()">&#8592;</button>
                    <div class="zone-title-block">
                        <div class="zone-title" id="zone-title">East Land Departments</div>
                        <div class="zone-subtitle" id="zone-subtitle">
                            Select a department in East Land to start navigation.
                        </div>
                    </div>
                </div>

                <div class="search-box">
                    <input id="search" class="search-input" type="text"
                           placeholder="Search department in this zone…"
                           onkeyup="filterDepts()">
                    <span class="search-icon">&#128269;</span>
                </div>

                <div class="layout-grid">
                    <section class="card" id="east-zone">
                        <div class="dept-list">
    '''
    # EAST LAND list – tokens generated per page load
    for code, name in EAST_LAND_DISPLAY.items():
        token = serializer.dumps({"dept": code})
        dept_url = url_for('open_app', dept=code, token=token)
        html += (
            f'<div class="dept-row">'
            f'<a class="dept-link" href="{dept_url}">{name}</a>'
            f'</div>'
        )

    html += '''
                        </div>
                    </section>

                    <section class="card" id="main-zone" style="display:none;">
                        <div class="dept-list">
    '''

    # MAIN LAND list – tokens generated per page load
    for code, name in MAIN_LAND_DISPLAY.items():
        token = serializer.dumps({"dept": code})
        dept_url = url_for('open_app', dept=code, token=token)
        html += (
            f'<div class="dept-row">'
            f'<a class="dept-link" href="{dept_url}">{name}</a>'
            f'</div>'
        )

    html += '''
                        </div>
                    </section>
                </div>

                <div class="footer-actions">
                    <p class="note-text">
                        Note: Navigation links and QR codes are valid for 30 minutes from creation for security.
                    </p>
                </div>
            </section>
        </main>

        <footer>
            &copy; 2025 Ashok Leyland. All rights reserved.
        </footer>
    </body>
    </html>
    '''
    return html

# ---------------------------
# Open app / redirect to Mappls (token required, 30 min)
# ---------------------------
@app.route('/open_app/<dept>')
def open_app(dept):
    token = request.args.get('token')
    if not token:
        return "<h2>Invalid or missing token.</h2>", 403

    try:
        data = serializer.loads(token, max_age=TOKEN_MAX_AGE)
        if data.get("dept") != dept:
            raise BadSignature("Department mismatch")
    except (BadSignature, SignatureExpired) as e:
        app.logger.warning(f"Token error for {dept}: {e}")
        return "<h2>This navigation link has expired or is invalid. Please request a fresh link inside the plant.</h2>", 403

    # Look up department
    dept_name = EAST_LAND_DISPLAY.get(dept) or MAIN_LAND_DISPLAY.get(dept)
    dept_coords = EAST_LAND_DEPARTMENTS.get(dept) or MAIN_LAND_DEPARTMENTS.get(dept)
    if not dept_name or not dept_coords:
        return "<h2>Invalid department selected.</h2>", 404

    # Clean lat/lon
    lat, lon = [x.strip() for x in dept_coords.split(',')]
    encoded_name = quote(dept_name)

    # Mappls universal navigation link
    mappls_url = (
        f"https://mappls.com/navigation"
        f"?places={lat},{lon},{encoded_name}"
        f"&isNav=true&mode=driving"
    )

    return redirect(mappls_url, code=302)

# ---------------------------
# Session QR for a specific navigation link (expires in 30 min)
# This is meant for showing on screen / kiosk, NOT for permanent printing.
# ---------------------------
@app.route('/generate_qr_for_session/<dept>')
def generate_qr_for_session(dept):
    token = request.args.get('token')
    if not token:
        abort(403, "Missing token")

    try:
        data = serializer.loads(token, max_age=TOKEN_MAX_AGE)
        if data.get("dept") != dept:
            abort(403, "Token mismatch")
    except (BadSignature, SignatureExpired):
        abort(403, "Invalid or expired token")

    qr_url = url_for('open_app', dept=dept, token=token, _external=True)
    img = qrcode.make(qr_url)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png")

# ---------------------------
# Permanent QR for landing page (to print and use forever)
# ---------------------------
@app.route('/generate_home_qr')
def generate_home_qr():
    home_url = url_for('landing_page', _external=True)
    img = qrcode.make(home_url)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png")

# ---------------------------
# Main
# ---------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
