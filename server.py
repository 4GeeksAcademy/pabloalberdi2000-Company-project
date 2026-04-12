try:
    # try to import flask, or return error if has not been installed
    from flask import Flask
    from flask import send_from_directory
except ImportError:
    print("You don't have Flask installed, run `$ pip3 install flask` and try again")
    exit(1)

import os, subprocess

static_file_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), './')
app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 #disable cache


def resolve_entrypoint():
    """Return the best available entrypoint for the current project layout."""
    if os.path.exists("index.html"):
        return "index.html"
    if os.path.exists("apps/index.html"):
        return "apps/index.html"
    return None


def resolve_application_page():
    if os.path.exists("apps/application.html"):
        return "apps/application.html"
    if os.path.exists("application.html"):
        return "application.html"
    return None

# Serving the index file
@app.route('/', methods=['GET'])
def serve_dir_directory_index():
    if os.path.exists("app.py"):
        # if app.py exists we use the render function
        out = subprocess.Popen(['python3','app.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout,stderr = out.communicate()
        return stdout if out.returncode == 0 else f"<pre style='color: red;'>{stdout.decode('utf-8')}</pre>"
    entrypoint = resolve_entrypoint()
    if entrypoint:
        return send_from_directory(static_file_dir, entrypoint)
    else:
        return "<h1 align='center'>404</h1><h2 align='center'>Missing index.html file</h2><p align='center'><img src='https://github.com/4GeeksAcademy/html-hello/blob/main/.vscode/rigo-baby.jpeg?raw=true' /></p>"


@app.route('/application.html', methods=['GET'])
def serve_application_alias():
    application_page = resolve_application_page()
    if application_page:
        return send_from_directory(static_file_dir, application_page)
    return "<h1 align='center'>404</h1><h2 align='center'>Missing application.html file</h2>"


@app.route('/apps/index.html', methods=['GET'])
def serve_legacy_apps_index_alias():
    entrypoint = resolve_entrypoint()
    if entrypoint:
        return send_from_directory(static_file_dir, entrypoint)
    return "<h1 align='center'>404</h1><h2 align='center'>Missing index.html file</h2>"

# Serving any other image
@app.route('/<path:path>', methods=['GET'])
def serve_any_other_file(path):
    if not os.path.isfile(os.path.join(static_file_dir, path)):
        path = os.path.join(path, 'index.html')
    response = send_from_directory(static_file_dir, path)
    response.cache_control.max_age = 0 # avoid cache memory
    return response

port = int(os.getenv('PORT', '5000'))
app.run(host='0.0.0.0', port=port, debug=True, extra_files=['./'])