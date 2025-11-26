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
    "field_quality_centre": "28.6149,77.2100",
    "defense_sourcing": "28.6150,77.2101",
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
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>Department Locator</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(to right, #f0f4fa, #e6f0fc); margin: 0; padding: 0; }
            .header { display: flex; justify-content: space-between; align-items: center; background: #003366; color: #fff; padding: 1rem 2rem; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
            .header-title { font-size: 2rem; font-weight: bold; letter-spacing: 2px; }
            .logo { height: 70px; width: auto; background: #fff; border-radius: 8px; padding: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
            .container { max-width: 800px; margin: 2.5rem auto; background: #fff; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); padding: 2.5rem 3rem; }
            .tag-label { display: inline-block; font-size: 1.2rem; background: #d9ecff; color: #003366; padding: 0.5rem 1.5rem; border-radius: 30px; margin-bottom: 1.5rem; font-weight: bold; letter-spacing: 1px; box-shadow: inset 0 -1px 3px rgba(0,0,0,0.05); }
            ul { list-style-type: none; padding: 0; }
            li { margin-bottom: 1rem; }
            a.dept-link { display: inline-block; padding: 0.8rem 2rem; background: #0074D9; color: #fff; border-radius: 6px; text-decoration: none; font-size: 1.1rem; font-weight: 500; box-shadow: 0 2px 6px rgba(0,0,0,0.1); transition: all 0.3s ease; }
            a.dept-link:hover { background: #005fa3; transform: translateY(-2px); box-shadow: 0 4px 10px rgba(0,0,0,0.15); }
            .qr-link { margin-left:10px; font-size:0.9rem; }
            input[type="text"] { width: 100%; padding: 10px; margin: 20px 0; font-size: 1rem; border-radius: 6px; border: 1px solid #ccc; }
            footer { text-align: center; padding: 1rem; font-size: 0.9rem; color: #666; background: #f0f4fa; margin-top: 3rem; }
            @media (max-width: 600px) { .container { padding: 1.5rem; } .header-title { font-size: 1.5rem; } .logo { height: 50px; } }
        </style>
        <script>
        function filterDepts() {
            let input = document.getElementById('search').value.toLowerCase();
            document.querySelectorAll('.dept-link').forEach(link => {
                link.parentElement.style.display = link.textContent.toLowerCase().includes(input) ? '' : 'none';
            });
        }
        </script>
    </head>
    <body>
        <div class="header">
            <div class="header-title">Department Locator</div>
            <img src="/static/Ashok-Leyland-Logo.png" alt="Ashok Leyland Logo" class="logo">
        </div>
        <div class="container">
            <input type="text" id="search" placeholder="Search Department..." onkeyup="filterDepts()">
            <div class="tag-label">EAST LAND</div>
            <ul>
    '''
    # EAST LAND list – tokens generated per page load
    for code, name in EAST_LAND_DISPLAY.items():
        token = serializer.dumps({"dept": code})
        dept_url = url_for('open_app', dept=code, token=token)
        qr_url = url_for('generate_qr_for_session', dept=code, token=token)
        html += (
            f'<li><a class="dept-link" href="{dept_url}">{name}</a>'
            f'<a class="qr-link" href="{qr_url}">[QR]</a></li>'
        )

    # MAIN LAND list – tokens generated per page load
    html += '''</ul><div class="tag-label">MAIN LAND</div><ul>'''
    for code, name in MAIN_LAND_DISPLAY.items():
        token = serializer.dumps({"dept": code})
        dept_url = url_for('open_app', dept=code, token=token)
        qr_url = url_for('generate_qr_for_session', dept=code, token=token)
        html += (
            f'<li><a class="dept-link" href="{dept_url}">{name}</a>'
            f'<a class="qr-link" href="{qr_url}">[QR]</a></li>'
        )

    html += '''
            </ul>
            <p style="margin-top: 2rem;">
                <a href="/generate_home_qr" class="dept-link" style="background:#28a745;">
                    📍 QR for Landing Page
                </a>
            </p>
            <p style="margin-top: 1rem; font-size: 0.85rem; color:#555;">
                Note: Navigation links and QR codes are valid for 30 minutes from creation for security.
            </p>
        </div>
        <footer>&copy; 2025 Ashok Leyland. All rights reserved.</footer>
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
