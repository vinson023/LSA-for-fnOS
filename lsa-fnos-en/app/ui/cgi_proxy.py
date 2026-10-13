#!/usr/bin/env python3
"""LSA CGI proxy for fnOS - serves the LSA web UI through the desktop iframe.

The fnOS desktop WebView loads this CGI as the application entry point and
fnOS does not allow third-party apps to add routes to its own nginx. LSA is
a GWT application that navigates with origin-absolute URLs such as
/ui/core/index.html and /LSI/Storage/MR/API/..., which do not exist on the
fnOS origin. Every HTML page served through this proxy therefore receives a
<base href> pointing back into the CGI plus a small interceptor that keeps
anchors, XHR/fetch requests and script-driven location navigation on the
proxied paths.
"""
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

CGI_ENTRY_MARKER = '/index.cgi'
CGI_BASE = '/cgi/ThirdParty/lsaen/index.cgi/'
DEFAULT_WEB_PORT = 2463
DEFAULT_SERVICE_PORT = 9000
PORT_FILE = '/opt/lsi/LSIStorageAuthority/conf/fnos_ports.conf'


def configured_ports():
    """Read the ports persisted by the fnOS lifecycle scripts."""
    ports = {'web': DEFAULT_WEB_PORT, 'service': DEFAULT_SERVICE_PORT}
    try:
        with open(PORT_FILE, 'r', encoding='utf-8') as stream:
            for line in stream:
                key, sep, value = line.strip().partition('=')
                if sep and key in ports:
                    parsed = int(value)
                    if 1 <= parsed <= 65535:
                        ports[key] = parsed
    except (OSError, ValueError):
        pass
    return ports


def normalize_path():
    """Resolve the target path from CGI environment variables."""
    request_uri = os.environ.get('REQUEST_URI', '')
    if request_uri:
        raw = request_uri.split('?', 1)[0]
        if CGI_ENTRY_MARKER in raw:
            suffix = raw.split(CGI_ENTRY_MARKER, 1)[1]
            if suffix:
                return suffix if suffix.startswith('/') else '/' + suffix
            return '/'

    path_info = os.environ.get('PATH_INFO', '')
    if path_info and path_info != '/':
        return path_info if path_info.startswith('/') else '/' + path_info

    return '/'


def proxy_base_for(target_path):
    """CGI base href matching the directory of the proxied document.

    GWT pages reference their assets relatively (core/core.nocache.js,
    ../css/gwt.css), so the injected base must mirror the directory of the
    original document, not a fixed one.
    """
    directory = target_path.rsplit('/', 1)[0] + '/'
    return CGI_BASE + directory.lstrip('/')


INTERCEPTOR_TEMPLATE = '''
<script>
(function() {
  var cgiBase = '__CGI_BASE__';
  // LSA performs its module hand-offs (the "Sign in" button, server
  // selection, ...) with root-relative locations such as
  // '/ui/core/index.html?locale=en&serverID=...'. Those URLs assume the app
  // is served from the origin root, so they must be pulled back into the CGI
  // prefix or the browser lands on an fnOS 404 page.
  var navigationPrefixes = ['/ui/'];

  /* Normalise a URL to a root-relative path. Returns null when the target
     cannot be parsed or points at another origin (those are left alone). */
  function normalizeToPath(url) {
    if (typeof url !== 'string' || url.length === 0) { return null; }
    if (url.charAt(0) === '/' && url.charAt(1) !== '/') { return url; }
    if (url.indexOf('://') < 0 && url.indexOf('//') !== 0) { return url; }
    try {
      var absolute = new URL(url, window.location.href);
      if (absolute.host !== window.location.host) { return null; }
      return absolute.pathname + absolute.search + absolute.hash;
    } catch (e) { return null; }
  }

  function rewriteUrl(url) {
    var path = normalizeToPath(url);
    if (path === null) { return url; }
    if (path.charAt(0) !== '/') { return url; }
    if (path.indexOf(cgiBase) === 0) { return path; }
    return cgiBase + path.substring(1);
  }

  /* location.href is an own, non-configurable property of the Location
     instance (WebIDL [LegacyUnforgeable]), so it cannot be patched. The
     Navigation API is therefore the only hook that can catch script-driven
     navigations. */
  function installNavigationGuard() {
    var navigation = window.navigation;
    if (!navigation || typeof navigation.addEventListener !== 'function') { return; }
    navigation.addEventListener('navigate', function(event) {
      var destination = event.destination;
      if (!destination || destination.sameDocument) { return; }
      var path = normalizeToPath(destination.url);
      if (path === null || path.charAt(0) !== '/') { return; }
      if (path.indexOf(cgiBase) === 0) { return; }
      var matched = false;
      for (var i = 0; i < navigationPrefixes.length; i++) {
        if (path.indexOf(navigationPrefixes[i]) === 0) { matched = true; break; }
      }
      if (!matched) { return; }
      var target = cgiBase + path.substring(1);
      try {
        event.intercept({
          handler: function() { return navigation.navigate(target, { history: 'replace' }); }
        });
      } catch (e) {
        try { window.location.replace(target); } catch (e2) {}
      }
    });
  }
  installNavigationGuard();
  function rewriteAnchor(link) {
    if (!link || link.nodeType !== 1 || link.tagName !== 'A') { return; }
    var href = link.getAttribute('href');
    if (href === null) { return; }
    var rewritten = rewriteUrl(href);
    if (rewritten !== href) { link.setAttribute('href', rewritten); }
  }
  function rewriteAnchors(root) {
    if (!root || root.nodeType !== 1) { return; }
    rewriteAnchor(root);
    if (root.querySelectorAll) {
      var links = root.querySelectorAll('a[href]');
      for (var i = 0; i < links.length; i++) { rewriteAnchor(links[i]); }
    }
  }
  function scanDocument() { rewriteAnchors(document.documentElement); }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', scanDocument, false);
  } else {
    scanDocument();
  }
  document.addEventListener('click', function(event) {
    var node = event.target;
    while (node && node.nodeType === 1) {
      if (node.tagName === 'A') { rewriteAnchor(node); return; }
      node = node.parentNode;
    }
  }, true);
  if (window.MutationObserver) {
    new MutationObserver(function(records) {
      for (var i = 0; i < records.length; i++) {
        var record = records[i];
        if (record.type === 'attributes') {
          rewriteAnchors(record.target);
          continue;
        }
        for (var j = 0; j < record.addedNodes.length; j++) {
          rewriteAnchors(record.addedNodes[j]);
        }
      }
    }).observe(document.documentElement, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['href']
    });
  }
  var origOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url) {
    try { arguments[1] = rewriteUrl(url); } catch (e) {}
    return origOpen.apply(this, arguments);
  };
  if (window.fetch) {
    var origFetch = window.fetch;
    window.fetch = function(input, options) {
      try {
        if (typeof input === 'string') {
          input = rewriteUrl(input);
        } else if (input && input.url) {
          var rewritten = rewriteUrl(input.url);
          if (rewritten !== input.url) { input = new Request(rewritten, input); }
        }
      } catch (e) {}
      return origFetch.call(this, input, options);
    };
  }
  /* location.href / location.assign / location.replace: href is an own,
     non-configurable property ([LegacyUnforgeable]) so it cannot be patched,
     but assign/replace live on Location.prototype and LSA uses them too. */
  try {
    var locationProto = Object.getPrototypeOf(window.location);
    var origAssign = locationProto.assign;
    locationProto.assign = function(url) { return origAssign.call(this, rewriteUrl(url)); };
    var origReplace = locationProto.replace;
    locationProto.replace = function(url) { return origReplace.call(this, rewriteUrl(url)); };
  } catch (e) {}
  var origWindowOpen = window.open;
  window.open = function(url) {
    try { arguments[0] = rewriteUrl(url); } catch (e) {}
    return origWindowOpen.apply(this, arguments);
  };
})();
</script>
'''


def inject_proxy_support(body, target_path):
    """Inject <base href> and the URL interceptor into an HTML document."""
    if not body:
        return body
    if b'<base ' in body[:8192].lower():
        return body
    marker = b'<head>'
    idx = body.lower().find(marker)
    if idx < 0:
        return body
    insert_at = idx + len(marker)
    base_tag = '\n<base href="%s">' % proxy_base_for(target_path)
    interceptor = INTERCEPTOR_TEMPLATE.replace('__CGI_BASE__', CGI_BASE)
    injection = (base_tag + interceptor).encode('utf-8')
    return body[:insert_at] + injection + body[insert_at:]


def write_response(response, target_path):
    """Write a CGI response, injecting proxy support into HTML pages."""
    content_type = str(response.headers.get('Content-Type', ''))
    is_html = 'text/html' in content_type.lower()
    body = response.read()

    if is_html:
        body = inject_proxy_support(body, target_path)

    status = getattr(response, 'status', getattr(response, 'code', 502))
    reason = getattr(response, 'reason', 'OK')

    sys.stdout.write('Status: %d %s\r\n' % (status, reason))

    for key, value in response.headers.items():
        lower = key.lower()
        if lower in ('connection', 'transfer-encoding', 'server'):
            continue
        if lower in ('x-frame-options', 'content-security-policy'):
            continue
        if is_html and lower == 'content-length':
            continue
        sys.stdout.write('%s: %s\r\n' % (key, value))

    if is_html:
        sys.stdout.write('Content-Length: %d\r\n' % len(body))

    sys.stdout.write('\r\n')
    sys.stdout.flush()
    sys.stdout.buffer.write(body)
    sys.stdout.buffer.flush()


def proxy_request(target_path, query=''):
    """Proxy a request to the LSA nginx."""
    target_url = 'http://127.0.0.1:%d%s' % (configured_ports()['web'], target_path)
    if query:
        target_url += '?' + query

    content_length = int(os.environ.get('CONTENT_LENGTH', '0') or '0')
    body = sys.stdin.buffer.read(content_length) if content_length > 0 else None

    headers = {}
    for env_name, http_name in [
        ('CONTENT_TYPE', 'Content-Type'),
        ('HTTP_ACCEPT', 'Accept'),
        ('HTTP_HOST', 'X-Forwarded-Host'),
        ('REMOTE_ADDR', 'X-Forwarded-For'),
        ('HTTP_COOKIE', 'Cookie'),
    ]:
        value = os.environ.get(env_name, '')
        if value:
            headers[http_name] = value

    headers['Host'] = '127.0.0.1:%d' % configured_ports()['web']

    method = os.environ.get('REQUEST_METHOD', 'GET')

    try:
        req = urllib.request.Request(target_url, data=body, headers=headers, method=method)
        response = urllib.request.urlopen(req, timeout=120)
        return response
    except urllib.error.HTTPError as exc:
        return exc
    except Exception:
        return None


def main():
    target_path = normalize_path()
    query = os.environ.get('QUERY_STRING', '')

    # The desktop iframe must stay on the fnOS origin: the standalone LSA
    # port is not reachable from the in-app WebView (it resolves localhost
    # on the client side). Serve the discovery page through the CGI and let
    # the injected interceptor keep every later navigation proxied.
    if target_path in ('/', ''):
        target_path = '/ui/remoteserver/index.html'

    response = proxy_request(target_path, query)
    if response:
        write_response(response, target_path)
    else:
        sys.stdout.write('Status: 502 Bad Gateway\r\nContent-Type: text/plain\r\n\r\n')
        sys.stdout.write('LSA proxy error: cannot connect to LSA service on port %d' % configured_ports()['web'])


if __name__ == '__main__':
    main()
