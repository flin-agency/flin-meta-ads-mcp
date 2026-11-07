# Privacy

The server runs locally and sends requested API reads to `graph.facebook.com`.
Browser login uses Facebook/Meta and a local callback on `127.0.0.1`; token exchange
sends the App Secret to Meta. Ad API reads use a token and, if configured, an HMAC
proof rather than the raw App Secret. Requested images come from Meta HTTPS CDN
hosts without the Graph token. The server does not retain ad/image files.

Tool results go to the MCP client (for example Claude) and are subject to that
client's account/workspace data policies. Previews may load Facebook content in
the client. There is no project-operated data collection or analytics endpoint.
Update checks contact PyPI; installation downloads packages and possibly a Python
runtime from uv's official managed runtime source. Meta credentials are excluded
from update subprocesses.

Claude manages sensitive extension settings. Browser login stores an **unencrypted**
token and App Secret in `~/.config/flin-meta-ads-mcp/credentials.json`, or the path
set by `META_AUTH_FILE`. macOS/Linux file permissions restrict it to its owner.
An explicitly configured token takes priority over a saved browser login.

To remove access, revoke the app/business integration or token in Meta. Removing
a password-manager share or deleting a local file alone does not revoke an issued
token. Close the extension, remove its settings, and delete the credentials file
if no other installation needs it. Remove
`~/Library/Application Support/flin-meta-ads-mcp/desktop/` to delete downloaded
servers and runtimes. Uninstalling the extension does not remove these shared files.

[Security](SECURITY.md) · [Support](SUPPORT.md)
