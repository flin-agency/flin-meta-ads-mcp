# flin-meta-ads-mcp Design (v0.1.0)

**Status:** Approved
**Date:** 2026-03-20
**Owner:** flin

## 1. Ziel

Ein öffentlich nutzbarer MCP-Server (`flin-meta-ads-mcp`) für Meta Ads, der in `v0.1.0` strikt read-only ist, aber die wichtigsten Core-Ads-Reads vollständig und zuverlässig abdeckt. Das Paket soll von Dritten ohne großen Aufwand via `uvx` in Claude eingebunden und getestet werden können.

## 2. Scope

### In Scope (v0.1.0)

- Deployment/Install über `uvx` aus PyPI
- Auth via `META_ACCESS_TOKEN` (env)
- `META_AD_ACCOUNT_ID` als Default, pro Tool optionaler `ad_account_id` Override
- Typed Core-Read-Tools:
  - `list_ad_accounts`
  - `get_ad_account`
  - `list_campaigns`
  - `get_campaign`
  - `list_adsets`
  - `get_adset`
  - `list_ads`
  - `get_ad`
  - `list_ad_creatives`
  - `get_ad_creative`
  - `get_ad_preview`
  - `get_insights`
- Pagination (`limit`, `after`) und konsistente Output-Struktur
- Rate-Limit-Handling, einheitliche Fehlerklassifikation
- Reproduzierbare Tests (Mock + optional Live)

### Out of Scope (v0.1.0)

- Jegliche Write-Operations auf Business-Objekte (create/update/delete/pause/resume)
- OAuth-Flow, Token-Refresh, Token-Exchange
- npx-Distribution
- Generischer Graph-Proxy-Tool-Ansatz

## 3. Architektur

Vier Schichten:

1. MCP Runtime (`server.py`)
- Tool-Registrierung mit festen JSON Schemas
- Dispatching auf Tool-Handler
- Vereinheitlichte Antworten

2. Tool-Schicht (`tools/*.py`)
- Domänenspezifische Read-Use-Cases
- Input-Normalisierung (z. B. `ad_account_id` Fallback)
- Keine direkte HTTP-Logik

3. Meta API Adapter (`meta_client.py`)
- Versionierte Graph API Calls (`META_GRAPH_API_VERSION`, Default `v21.0`)
- Pagination-Helfer
- Retry/Backoff bei 429/temporären Fehlern
- Request-Trace-Metadaten

4. Guards + Error Mapping (`guards.py`, `errors.py`)
- Hard Read-Only Guard (keine Business-Writes in Tool-Layer)
- Einheitliche Fehlercodes:
  - `auth_error`
  - `permission_error`
  - `rate_limit_error`
  - `validation_error`
  - `meta_api_error`

## 4. Konfigurationsmodell

Pflicht:
- `META_ACCESS_TOKEN`

Optional:
- `META_AD_ACCOUNT_ID`
- `META_GRAPH_API_VERSION` (Default `v21.0`)
- `META_TIMEOUT_SECONDS` (Default `30`)
- `META_MAX_RETRIES` (Default `3`)

Regel:
- Falls ein Tool `ad_account_id` nicht übergeben bekommt, wird `META_AD_ACCOUNT_ID` verwendet.
- Ist beides leer, liefert das Tool `validation_error` mit klarer Hilfsnachricht.

## 5. Tool-Design

## Einheitlicher Input-Standard (wo sinnvoll)

- `ad_account_id: string` (optional)
- `limit: int` (Default `50`, max `200`)
- `after: string` (optional Cursor)
- `fields: list[str]` (optional, endpointabhängig)

## Einheitlicher Output-Standard

```json
{
  "ok": true,
  "data": [],
  "paging": {
    "next_after": null,
    "has_next": false
  },
  "meta": {
    "api_version": "v21.0",
    "request_id": "..."
  }
}
```

## Highlights je Tool

- `list_*` Tools: Filter + Pagination + minimale Default-Felder
- `get_*` Tools: ID-basierter Read, klarer `not_found`/`permission` Fehler
- `get_ad_preview`: Preview über Meta Preview Endpoint (read-only)
- `get_insights`:
  - `level`: `account|campaign|adset|ad`
  - `date_preset` oder `time_range`
  - `fields` (mit sinnvollen Defaults)
  - `breakdowns`, `action_breakdowns`
  - `time_increment`
  - optional `entity_ids`

## 6. Sicherheit und Datenschutz

- Keine Speicherung von Tokens auf Disk
- Kein Logging sensibler Header/Token
- Fehlermeldungen redacted (keine Secrets)
- Dokumentation mit klarer Warnung: nur eigene/erlaubte Ad Accounts nutzen

## 7. Public Usability

README muss enthalten:

- Installation:
  - `uvx flin-meta-ads-mcp`
- Claude MCP Config (copy/paste)
- 2-Minuten-Smoke-Test:
  1. `list_ad_accounts`
  2. `list_campaigns`
  3. `get_insights` (`last_7d`, `level=campaign`)
- Troubleshooting-Tabelle (Permission, Token, Account-ID, Rate-Limit)

## 8. Teststrategie

Automatisierte Tests:

- Unit/Contract-Tests für Input-Validation und Output-Schema
- Mocked HTTP-Tests gegen Meta-Endpunkte
- Error-Mapping-Tests (401/403/429/5xx)
- Pagination-Tests (with/without next cursor)

Optional Live:

- `RUN_LIVE_META_TESTS=1` aktiviert echte API-Tests
- Bei fehlenden Env-Werten werden Live-Tests sauber geskippt

## 9. Release & Distribution

- Paketname: `flin-meta-ads-mcp`
- Distribution: PyPI
- Ausführung: `uvx flin-meta-ads-mcp`
- CI:
  - lint
  - tests
  - build
- Release bei Git Tag

## 10. Akzeptanzkriterien (v0.1.0)

- Alle 12 read-only Tools funktionieren mit konsistentem Schema
- Kein Tool ermöglicht Business-Writes
- Dritte können mit README in <10 Minuten starten
- Test-Suite läuft lokal ohne Live-Token (Mock-Basis)
- Optionaler Live-Testlauf ist dokumentiert und reproduzierbar

## 11. Post-v0.1.0 Roadmap

- Read-only Zusatzbereiche (audiences/pixels/catalogs) als `v0.2.x`
- Optionaler sicherer Auth-Erweiterungsmodus als `v0.3.x`
- Erst danach Diskussion über Write-Tools mit expliziten Safeguards
