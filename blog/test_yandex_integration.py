"""Yandex Webmaster and Metrika integration contract."""

import json
import subprocess
from pathlib import Path

import pytest

from django.test import Client


YANDEX_VERIFICATION_PATH = "/yandex_5834a95c038b9599.html"
YANDEX_VERIFICATION_BODY = """<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    </head>
    <body>Verification: 5834a95c038b9599</body>
</html>
"""

pytestmark = pytest.mark.django_db


def test_yandex_webmaster_verification_document_is_exact():
    response = Client().get(YANDEX_VERIFICATION_PATH)

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/html; charset=UTF-8"
    assert response.content.decode() == YANDEX_VERIFICATION_BODY


def test_yandex_metrika_is_initialized_once_on_full_pages():
    client = Client()

    for path in ("/", "/about/"):
        response = client.get(path)
        assert response.status_code == 200
        body = response.content.decode()
        assert body.count("https://mc.yandex.ru/metrika/tag.js?id=111929557") == 1
        assert body.count("ym(111929557, 'init'") == 1
        assert "m[i]=m[i]||function()" in body
        assert "webvisor:true" in body
        assert "accurateTrackBounce:true" in body
        assert "trackLinks:true" in body
        assert body.count("https://mc.yandex.ru/watch/111929557") == 1


def test_htmx_fragment_does_not_repeat_metrika_bootstrap():
    response = Client().get("/", HTTP_HX_REQUEST="true")

    assert response.status_code == 200
    body = response.content.decode()
    assert "mc.yandex.ru/metrika/tag.js" not in body
    assert "mc.yandex.ru/watch/111929557" not in body


def test_metrika_virtual_pageviews_follow_htmx_history_contract():
    script_path = Path(__file__).resolve().parents[1] / "static/js/metrika-events.js"
    node_script = f"""
const fs = require('fs');
const vm = require('vm');
const listeners = {{}};
const calls = [];
const window = {{
  location: {{ href: 'https://example.test/' }},
  ym: (...args) => calls.push(args),
}};
const document = {{
  addEventListener: (name, callback) => {{ (listeners[name] ||= []).push(callback); }},
}};
vm.runInNewContext(fs.readFileSync({json.dumps(str(script_path))}, 'utf8'), {{window, document, URL}});
const fire = (name, href) => {{
  window.location.href = href;
  for (const callback of listeners[name] || []) callback({{type: name}});
}};
fire('htmx:pushedIntoHistory', 'https://example.test/about/');
fire('htmx:pushedIntoHistory', 'https://example.test/about/');
fire('htmx:historyRestore', 'https://example.test/about/#section');
fire('htmx:replacedInHistory', 'https://example.test/posts/?page=2');
console.log(JSON.stringify(calls));
"""
    result = subprocess.run(
        ["node", "-e", node_script],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == [
        [
            111929557,
            "hit",
            "https://example.test/about/",
            {"referer": "https://example.test/"},
        ],
        [
            111929557,
            "hit",
            "https://example.test/posts/?page=2",
            {"referer": "https://example.test/about/"},
        ],
    ]


def test_metrika_virtual_pageviews_are_safe_when_ym_is_unavailable():
    script_path = Path(__file__).resolve().parents[1] / "static/js/metrika-events.js"
    node_script = f"""
const fs = require('fs');
const vm = require('vm');
const listeners = {{}};
const window = {{ location: {{ href: 'https://example.test/' }} }};
const document = {{
  addEventListener: (name, callback) => {{ (listeners[name] ||= []).push(callback); }},
}};
vm.runInNewContext(fs.readFileSync({json.dumps(str(script_path))}, 'utf8'), {{window, document, URL}});
window.location.href = 'https://example.test/about/';
for (const callback of listeners['htmx:pushedIntoHistory'] || []) callback({{}});
console.log('ok');
"""
    result = subprocess.run(
        ["node", "-e", node_script],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "ok"


def test_metrika_virtual_pageviews_are_safe_when_ym_throws():
    script_path = Path(__file__).resolve().parents[1] / "static/js/metrika-events.js"
    node_script = f"""
const fs = require('fs');
const vm = require('vm');
const listeners = {{}};
const window = {{
  location: {{ href: 'https://example.test/' }},
  ym: () => {{ throw new Error('blocked'); }},
}};
const document = {{
  addEventListener: (name, callback) => {{ (listeners[name] ||= []).push(callback); }},
}};
vm.runInNewContext(fs.readFileSync({json.dumps(str(script_path))}, 'utf8'), {{window, document, URL}});
window.location.href = 'https://example.test/about/';
for (const callback of listeners['htmx:pushedIntoHistory'] || []) callback({{}});
console.log('ok');
"""
    result = subprocess.run(
        ["node", "-e", node_script],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "ok"


def test_metrika_virtual_pageview_script_is_loaded_after_htmx():
    response = Client().get("/")
    body = response.content.decode()
    assert body.index('src="https://unpkg.com/htmx.org@2.0.4"') < body.index(
        'src="/static/js/metrika-events.js"'
    )
    assert "defer" not in body[body.index('metrika-events.js') - 100 : body.index('metrika-events.js') + 100]


def test_metrika_bounded_goals_cover_reactions_and_media_once():
    script_path = Path(__file__).resolve().parents[1] / "static/js/metrika-events.js"
    node_script = f"""
const fs = require('fs');
const vm = require('vm');
const listeners = {{}};
const calls = [];
const window = {{ location: {{ href: 'https://example.test/posts/demo/', pathname: '/posts/demo/' }}, ym: (...args) => calls.push(args) }};
const document = {{
  addEventListener: (name, callback) => {{ (listeners[name] ||= []).push(callback); }},
}};
vm.runInNewContext(fs.readFileSync({json.dumps(str(script_path))}, 'utf8'), {{window, document, URL}});
const button = (pressed) => ({{
  getAttribute: (name) => name === 'aria-pressed' ? String(pressed) : null,
}});
for (const pressed of [true, false]) {{
  for (const callback of listeners['htmx:afterSwap'] || []) callback({{target: {{ querySelector: () => button(pressed) }}}});
}}
const audio = {{ tagName: 'AUDIO', dataset: {{}} }};
for (const callback of listeners.play || []) callback({{target: audio}});
for (const callback of listeners.play || []) callback({{target: audio}});
console.log(JSON.stringify(calls));
"""
    result = subprocess.run(["node", "-e", node_script], check=True, capture_output=True, text=True)
    calls = json.loads(result.stdout)
    assert [call[2] for call in calls] == ["post_like", "post_unlike", "media_start"]
    assert calls[-1][3] == {"page_path": "/posts/demo/", "content_kind": "audio"}


def test_metrika_share_goal_requires_copy_success_and_read_goals_are_once_only():
    metrika_path = Path(__file__).resolve().parents[1] / "static/js/metrika-events.js"
    share_path = Path(__file__).resolve().parents[1] / "static/js/share-link.js"
    read_path = Path(__file__).resolve().parents[1] / "static/js/read-depth-tracking.js"
    node_script = f"""
const fs = require('fs');
const vm = require('vm');
const listeners = {{}};
const calls = [];
const makeButton = (url) => ({{ dataset: {{ shareUrl: url }}, querySelector: () => null,
  addEventListener: (name, callback) => {{ (listeners[name] ||= []).push(callback); }},
  classList: {{ toggle: () => {{}}, remove: () => {{}} }}, textContent: 'copy' }});
const badButton = makeButton('bad');
const goodButton = makeButton('good');
const content = {{ getBoundingClientRect: () => ({{ top: currentTop }}), offsetHeight: 2000 }};
let currentTop = -500;
const document = {{
  body: {{ addEventListener: () => {{}}, appendChild: () => {{}}, removeChild: () => {{}} }},
  addEventListener: (name, callback) => {{ (listeners[name] ||= []).push(callback); }},
  querySelector: (selector) => selector === '.post-content' ? content : {{ getAttribute: () => 'demo' }},
  querySelectorAll: () => [badButton, goodButton], createElement: () => ({{ setAttribute: () => {{}}, select: () => {{}}, style: {{}} }}),
  execCommand: () => false,
}};
const window = {{ location: {{ pathname: '/posts/demo/' }}, innerHeight: 1000, isSecureContext: true,
  setTimeout, addEventListener: (name, callback) => {{ (listeners['window:' + name] ||= []).push(callback); }},
  trackMetrikaGoal: (name, params) => calls.push([name, params]) }};
const navigator = {{ clipboard: {{ writeText: (text) => text === 'good' ? Promise.resolve() : Promise.reject(new Error('blocked')) }} }};
vm.runInNewContext(fs.readFileSync({json.dumps(str(share_path))}, 'utf8'), {{window, document, navigator, Promise}});
for (const callback of listeners['DOMContentLoaded'] || []) callback();
for (const callback of listeners.click || []) callback();
vm.runInNewContext(fs.readFileSync({json.dumps(str(read_path))}, 'utf8'), {{window, document, navigator, requestAnimationFrame: (callback) => callback(), setInterval: () => {{}}}});
window.initReadDepthTracking();
for (const callback of listeners['window:scroll'] || []) callback();
currentTop = -900;
for (const callback of listeners['window:scroll'] || []) callback();
setTimeout(() => console.log(JSON.stringify(calls)), 0);
"""
    result = subprocess.run(["node", "-e", node_script], check=True, capture_output=True, text=True)
    assert json.loads(result.stdout) == [
        ["read_50", {"page_path": "/posts/demo/", "content_kind": "post"}],
        ["read_90", {"page_path": "/posts/demo/", "content_kind": "post"}],
        ["share_copy", {"page_path": "/posts/demo/", "content_kind": "post"}],
    ]
