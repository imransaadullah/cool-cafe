# Distribution Guide

Ship **one graphical installer** to customers. They choose their role during setup.

> **See also:** [README](../README.md) for architecture overview and [Local testing](../docs/LOCAL_TESTING.md) for dev setup.

## Build the installer (on your dev machine)

Requirements:
- Python 3.11+
- Node.js 18+ (for dashboard embedded in local server)
- PyQt6 (installed automatically by the build script)
- PostgreSQL **not** required on build machine

```bat
scripts\build_installer.bat
```

Output:

```
deploy\installer\installer_output\CyberCafe Setup.exe
```

Share **only this file**. It is a self-contained PyQt wizard that bundles all three roles.

## What the installer offers

The graphical wizard walks through:

1. **Welcome** — overview of the three roles
2. **Installation type** — Local Server, Global Server, or Client PC
3. **Location & options** — install folder, desktop shortcut, autostart, client watchdog
4. **Installing** — copies files with a live progress log
5. **Finish** — optional launch into the role’s first-run setup wizard

| Type | Default folder | What it does |
|------|----------------|--------------|
| **Local Server** | `C:\Program Files\CyberCafe Local Server` | Branch server + dashboard + setup wizard |
| **Global Server** | `C:\Program Files\CyberCafe Global Server` | Multi-site owner API + sync hub |
| **Client** | `C:\Program Files\CyberCafe Client` | PC kiosk client + optional watchdog |

Each installed app runs its own **first-run setup wizard** (database, admin account, network, etc.) when launched.

## Typical deployment

```
Owner laptop/cloud          Café counter PC              Gaming PCs
─────────────────          ─────────────────            ───────────
CyberCafe Setup.exe        CyberCafe Setup.exe          CyberCafe Setup.exe
  → Global Server            → Local Server               → Client
  → PostgreSQL               → PostgreSQL                 → points to local server IP
```

1. Install **Global Server** at HQ (optional, multi-site only)
2. Install **Local Server** at each café branch
3. Install **Client** on every customer PC
4. During local setup, set `GLOBAL_SERVER_URL` if using multi-site sync

## Develop / preview the installer UI

After staging payloads (run at least steps 3–4 of the build, or the full build):

```bat
scripts\start_installer.bat
```

## Portable builds (without the setup exe)

After `build_installer.bat`, portable folders also exist at:

- `local_server\dist\CyberCafe Server\`
- `global_server\dist\CyberCafe Global Server\`
- `client\dist\CyberCafe Client\`

Zip and distribute if you skip bundling into `CyberCafe Setup.exe`.

## Legacy Inno Setup (optional)

`deploy\installer\cybercafe_setup.iss` remains for teams that prefer Inno Setup. The primary distributable is now the PyQt graphical installer.

## Re-run setup on an installed machine

```bat
"C:\Program Files\CyberCafe Local Server\CyberCafe Server.exe" --setup
"C:\Program Files\CyberCafe Global Server\CyberCafe Global Server.exe" --setup
```

Client: delete `config.json` in the install folder to trigger the client setup wizard.
