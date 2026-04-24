# Product Requirements Document (PRD)
## In-House Web-Based Graphics System for Live Stream Production

**Version:** 1.1  
**Date:** February 27, 2025  
**Status:** Draft (stakeholder decisions incorporated)  
**Reference Products:** CasparCG, Bridge (SVT). Amagi Cloudport referenced for context only, not as a parity target.

---

## Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [Target State & Strategic Direction](#3-target-state--strategic-direction)
4. [Product Vision & Goals](#4-product-vision--goals)
5. [User Personas](#5-user-personas)
6. [Feature Requirements](#6-feature-requirements)
7. [Technical Architecture](#7-technical-architecture)
8. [UI/UX Requirements & Bridge Modification Scope](#8-uiux-requirements--bridge-modification-scope)
9. [Extension & Refinement Strategy](#9-extension--refinement-strategy)
10. [Success Metrics](#10-success-metrics)
11. [Phased Roadmap](#11-phased-roadmap)
12. [Appendix](#12-appendix)

---

## 1. Executive Summary

### 1.1 Purpose
This PRD defines requirements for **extending and refining** the in-house web-based graphics system for live stream production. The system builds on open-source **CasparCG Server** and **Bridge**, enhancing Bridge's UI and capabilities to better control and orchestrate CasparCG playout—providing a web-based master control experience.

### 1.2 Key Decisions
- **Extend, don't replace:** CasparCG Server remains the playout engine; Bridge is the control layer. Focus on extending and refining how CasparCG is used via Bridge.
- **Modify existing Bridge:** Enhance the current Bridge UI (plugins, rundown, network tab) rather than building a greenfield app.
- **Graphics:** HTML templates via CasparCG's CEF-based HTML consumer; no After Effects integration.
- **Priorities:** Reliability and simplicity over low latency.
- **Deployment:** Cloud-only.

### 1.3 Scope
- **In scope:** Live stream ingest, compositing, graphics overlay, multi-output delivery, scheduling, rundown, and web-based master control.
- **Out of scope (this draft):** Legacy SDI/DeckLink output, native Adobe After Effects integration, full 24/7 managed service offering.

---

## 2. Current State Analysis

### 2.1 Server Project (`/work/server`)

| Attribute | Details |
|-----------|---------|
| **Base** | CasparCG Server (C++, GPL-3.0) |
| **Control** | AMCP over TCP (port 5250) |
| **Build** | CMake, FFmpeg, TBB, SFML, CEF (for HTML) |
| **Customizations** | `CasparMedia/` templates (timer.html, lowerthird.html), SRT-focused docs |

**Strengths:**
- Mature broadcast playout
- 24/7 production use since 2006
- HTML templates via CEF, FFmpeg producers/consumers
- SRT input/output support

**Weaknesses:**
- C++ codebase; hard to extend for cloud-native workflows
- Tied to AMCP; not HTTP/ REST-first
- GPU/OpenGL dependency; less suited for headless cloud
- License (GPL) may constrain commercial use

### 2.2 Bridge Project (`/work/bridge`)

| Attribute | Details |
|-----------|---------|
| **Base** | svt/bridge (Node.js, React, MIT) |
| **Runtime** | Node.js + Electron (optional) |
| **Customizations** | caspar-network plugin (SRT I/O, HLS/WebRTC preview) |

**Key Features Implemented:**
- **Rundown tab:** Live switch, library, rundown, thumbnail, inspector
- **Time tab:** Clock, latency widgets
- **Network tab:** Inputs, outputs, preview (caspar-network)

**Strengths:**
- Extensible plugin model, shared state via WebSocket
- React + react-grid-layout for flexible UI
- SRT stream management, live preview (HLS/WebRTC)

**Weaknesses:**
- Tightly coupled to CasparCG/AMCP
- Layout and UX designed for TV production, not generic “cloudport”
- No native scheduling, automation, or cloud deployment focus
- Electron path adds deployment complexity

### 2.3 Gaps to Address (Bridge-Focused)

| Capability | Current | Target |
|------------|---------|--------|
| Audit logs | None | User actions, system events |
| Preview stability | HLS/WebRTC in caspar-network | Improved fallbacks, error handling |
| Rundown UX | Basic | Refined item management |
| Deployment | On-prem / dev | Cloud-only |
| Connection feedback | Basic | Refined error handling |

---

## 3. Target State & Strategic Direction

### 3.1 Target Architecture (Conceptual)

```
┌─────────────────────────────────────────────────────────────────┐
│                    WEB-BASED CONTROL UI (Bridge)                 │
│  Modified Bridge: Rundown | Live Switch | Network | Graphics      │
│  + Audit logs | Refined UX | Scheduling (future)                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │ AMCP (TCP) + WebSocket (state)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CASPARCG SERVER                               │
│  - SRT/FFmpeg ingest → HTML templates (CEF) → SRT/FFmpeg output  │
│  - Layer-based compositing, playout, consumers                   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Why Extend CasparCG via Bridge?

1. **Leverage mature playout:** CasparCG is battle-tested for 24/7 broadcast; no need to rebuild playout logic.
2. **Improve control experience:** Bridge's UI can be refined and extended for better operator workflows.
3. **Build on existing investment:** caspar-network plugin, templates, SRT configs already in place.
4. **Focused scope:** One engineer, 6 months—extending Bridge is more achievable than replacing the entire stack.

---

## 4. Product Vision & Goals

### 4.1 Vision
A web-based graphics and playout system that enables live stream production from any browser, with broadcast-grade quality. By extending Bridge and refining its use of CasparCG, the system provides a modern master control experience for live streams.

### 4.2 Goals
1. **Operational simplicity:** Single operator can manage multiple channels and live sources from one UI.
2. **Low latency:** Sub-5s glass-to-glass where applicable; configurable latency tradeoffs.
3. **Graphics parity:** Lower thirds, timers, scoreboards, L-bands, and templated HTML graphics.
4. **Scalability:** Add channels and sources without redesigning the system.
5. **Extensibility:** API-first for MAM, EPG, ad servers, and automation.

---

## 5. User Personas

| Persona | Role | Needs |
|---------|------|-------|
| **Director** | Live event control | Switch sources, trigger graphics, manage breaks |
| **Graphics Operator** | Graphics design & playout | Create templates, schedule graphics, trigger overlays |
| **Stream Engineer** | Technical setup | Configure ingest/output, codecs, bitrates |
| **Scheduler** | Content planning | Build rundowns, set break rules, automation |
| **Viewer (internal)** | Monitoring | Preview feeds, check quality, latency |

---

## 6. Feature Requirements

### 6.1 Ingest & Sources

| ID | Requirement | Priority | Notes |
|----|--------------|----------|-------|
| I1 | SRT input (caller/listener) | P0 | Primary live source protocol |
| I2 | RTMP input | P0 | Common streaming source |
| I3 | HLS input (VOD/restart) | P1 | Fallback/backup feeds |
| I4 | Local file playback (MP4, MOV, MXF) | P1 | Bumpers, fill, ads |
| I5 | Multi-source (30+ sources, 8+ cameras) | P2 | Amagi parity |
| I6 | WebRTC/WHIP input | P2 | Ultra-low latency ingest |

### 6.2 Graphics & Overlays

| ID | Requirement | Priority | Notes |
|----|--------------|----------|-------|
| G1 | HTML/CSS/JS templates | P0 | Lower thirds, timers, scoreboards |
| G2 | Variable injection (name, score, time) | P0 | Data-driven graphics |
| G3 | Animated transitions (DVE) | P1 | Wipes, fades, slides |
| G4 | Automated graphics scheduling | P1 | Rule-based insertion |
| G5 | L-bands, credit squeezes | P2 | Amagi-style presentation |
| G6 | After Effects export (optional) | P3 | Pre-rendered or templated |

### 6.3 Playout & Switching

| ID | Requirement | Priority | Notes |
|----|--------------|----------|-------|
| P1 | Live source switching | P0 | Cut, mix, keys |
| P2 | Layer-based compositing | P0 | Background, fill, keyer layers |
| P3 | Break management | P0 | Ad breaks, fill, return to live |
| P4 | Intent-capture system | P1 | Predefined intents for breaks, graphics |
| P5 | Frame-accurate switching | P2 | Deterministic timing |

### 6.4 Output & Delivery

| ID | Requirement | Priority | Notes |
|----|--------------|----------|-------|
| O1 | HLS output | P0 | Primary OTT delivery |
| O2 | RTMP output | P0 | CDN push |
| O3 | SRT output | P1 | Low-latency delivery |
| O4 | UDP/HD-SDI (optional) | P2 | Broadcast integration |
| O5 | Multi-profile (bitrate ladder) | P1 | ABR HLS |
| O6 | 4K UHD support | P2 | Future-ready |

### 6.5 Scheduling & Automation

| ID | Requirement | Priority | Notes |
|----|--------------|----------|-------|
| S1 | Rundown/playlist management | P0 | Ordered content + graphics |
| S2 | Time-based scheduling | P1 | Start/stop at specific times |
| S3 | Rule-based graphics | P1 | E.g., “show lower third during segment X” |
| S4 | Event templates | P2 | Reusable event configs |
| S5 | Integration with EPG/MAM | P2 | External data sources |

### 6.6 Master Control UI

| ID | Requirement | Priority | Notes |
|----|--------------|----------|-------|
| M1 | Live preview (program, preview) | P0 | Low-latency program/preview |
| M2 | Source selector / switcher UI | P0 | Visual source selection |
| M3 | Graphics trigger panel | P0 | Take, release, cue |
| M4 | Break control (start, duration, return) | P0 | Ad break management |
| M5 | Multi-channel view | P1 | Single operator, multiple channels |
| M6 | Remote operation (web-only) | P0 | No desktop app required |

### 6.7 Monitoring & Operations

| ID | Requirement | Priority | Notes |
|----|--------------|----------|-------|
| MO1 | Stream health (bitrate, frame rate) | P0 | Input/output metrics |
| MO2 | Latency monitoring | P1 | Glass-to-glass |
| MO3 | Error alerts | P0 | Source loss, encode failure |
| MO4 | Activity logs / audit trail | P0 | User actions, system events; must be added to Bridge |
| MO5 | Role-based access control | P1 | Per-channel, per-feature |

---

## 7. Technical Architecture

### 7.1 Core Components

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| **Web UI (Bridge)** | React, Node.js | Master control, rundown, live switch, graphics, caspar-network (SRT I/O, preview) |
| **Playout Engine** | CasparCG Server (C++) | FFmpeg producers/consumers, HTML templates via CEF, SRT I/O, layer compositing |
| **Control Protocol** | AMCP (TCP 5250) | Bridge caspar plugin sends AMCP commands to CasparCG |
| **State Sync** | WebSocket (Bridge) | Shared state across clients, plugin data |

### 7.2 CasparCG Playout Pipeline

```
[SRT/FFmpeg Input] → CasparCG decode → [layers + HTML template overlay] → encode → [SRT/FFmpeg Output]
                                       ↑
                               HTML templates (CEF render)
                               Lower thirds, timers, etc.
```

### 7.3 Graphics (HTML-Only)

- **CasparCG HTML consumer:** CEF-based rendering of HTML/CSS/JS templates.
- **Variable injection:** Bridge inspector/variables plugin drives template data.
- **Templates:** Existing CasparMedia (timer.html, lowerthird.html); extend as needed.

### 7.4 Deployment

- **Cloud-only:** CasparCG + Bridge deployed in cloud (Docker/K8s or similar). CasparCG requires GPU for CEF; cloud instances with GPU or software rendering where supported.

---

## 8. UI/UX Requirements & Bridge Modification Scope

### 8.1 Approach: Modify Existing Bridge

**Decision:** Modify existing Bridge (not greenfield).
- Reuse plugin architecture, shared state, grid layout.
- Keep CasparCG plugin; extend and refine it.
- Add audit logs; refine rundown, network tab, live switch UX.
- Keep AMCP as control protocol to CasparCG.


### 8.2 Required UI Modifications (Bridge)

| Area | Current State | Target State |
|------|---------------|--------------|
| **Connection model** | AMCP to CasparCG (via caspar plugin) | Keep; refine connection handling, error feedback |
| **Rundown** | CasparCG library, playout | Refine UX; improve rundown item management |
| **Live switch** | CasparCG layers | Refine source/layer switching UX |
| **Network tab** | SRT I/O via caspar-network + AMCP | Extend; improve inputs/outputs/preview UX |
| **Preview** | HLS/WebRTC from caspar-network | Keep; improve stability and fallbacks |
| **New: Audit logs** | None | Add audit log feature—user actions, system events |
| **Graphics panel** | Inspector + variables | Refine; dedicated graphics trigger if needed |

### 8.3 Screen Layout (Proposed)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  [Channels ▼]  Live Master Control                    [User] [Settings]   │
├─────────────┬──────────────────────────────────────┬─────────────────────┤
│ RUNDOWN     │  PREVIEW (Program)                   │  INSPECTOR          │
│             │  ┌─────────────────────────────┐    │  - Source info      │
│ □ Item 1    │  │                             │    │  - Graphics vars    │
│ ■ Item 2 ←  │  │    [Live/Program Output]    │    │  - Output status    │
│ □ Item 3    │  │                             │    │                     │
│ □ Break     │  └─────────────────────────────┘    │  [Graphics Panel]   │
│             │  PREVIEW (Preview)                   │  [Take] [Release]   │
│ [Add] [↑↓]  │  ┌─────────────────────────────┐    │                     │
│             │  │    [Next Source]            │    │  [Break Control]    │
│             │  └─────────────────────────────┘    │  [Start] [Return]   │
├─────────────┴──────────────────────────────────────┴─────────────────────┤
│  SOURCE GRID (1..N)  [SRT-1] [SRT-2] [RTMP-1] [VOD] [FILL]               │
│  [Network] Tab: Inputs | Outputs | Preview                               │
│  [Time] Tab: Clock | Latency                                            │
│  [Scheduling] Tab: Rules | Events                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.4 Key UX Principles

1. **Single-pane control:** Director sees rundown, preview, and triggers without context switching.
2. **Source-first:** Visual source selection (click to preview, take to air).
3. **Graphics as first-class:** Dedicated panel for take/release and variable editing.
4. **Break awareness:** Clear break state (live vs. break) and one-click return.
5. **Mobile-friendly monitoring:** Optional simplified view for tablets/phones.

---

## 9. Extension & Refinement Strategy

There is **no migration away from CasparCG**. The goal is to **extend and refine** how CasparCG is used via Bridge.

### 9.1 Extend CasparCG Usage
- Continue using CasparCG Server as the playout engine.
- Refine SRT input/output workflows; improve configs and templates.
- Add or extend HTML templates (timer, lower third) in CasparMedia.

### 9.2 Extend Bridge Capabilities
- Refine existing plugins (rundown, live switch, caspar-network, inspector).
- Add audit logs for user actions and system events.
- Improve UX: connection handling, error feedback, preview stability.

### 9.3 Cloud Deployment
- Deploy CasparCG + Bridge in cloud (target: cloud-only).
- Document build and deploy for production (see [PRODUCTION_BUILD.md](PRODUCTION_BUILD.md), [DEV_SETUP.md](DEV_SETUP.md) in this folder).

---

## 10. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Glass-to-glass latency | < 5 s (configurable) | End-to-end timing |
| Operator efficiency | 1 operator : 4 channels | Operational data |
| Uptime | 99.9% | Monitoring |
| Graphics take latency | < 500 ms | UI to air |
| Time to add new channel | < 30 min | Setup time |

---

## 11. Phased Roadmap

**Constraint:** 1 engineer, 6 months.

### Phase 1: Audit Logs & Stability (Months 1–2)
- Add audit log feature to Bridge (user actions, system events).
- Improve caspar-network preview stability (HLS/WebRTC fallbacks).
- Refine connection handling and error feedback in Bridge.

### Phase 2: UX Refinements (Months 2–4)
- Refine rundown UX (item management, drag-drop).
- Improve live switch and inspector workflows.
- Extend network tab (inputs/outputs) UX.

### Phase 3: Cloud Deployment & Templates (Months 4–6)
- Cloud deployment for CasparCG + Bridge.
- Extend CasparMedia templates as needed.
- Documentation and runbooks.

---

## 12. Appendix

### A. Glossary

| Term | Definition |
|------|------------|
| AMCP | Ambercorn Master Control Protocol (CasparCG) |
| DVE | Digital Video Effects |
| DBI | Dynamic Brand Insertion |
| EPG | Electronic Program Guide |
| MAM | Media Asset Management |
| RBAC | Role-Based Access Control |
| SRT | Secure Reliable Transport |

### B. References

- **CasparCG Server:** https://github.com/CasparCG/server  
- **Bridge:** https://github.com/svt/bridge  
- **Amagi Cloudport:** https://www.amagi.com/products/cloudport-cloud-playout  
- **Amagi Live Master Control:** https://www.amagi.com/products/cloudport-cloud-playout/live-master-control  

### C. Stakeholder Decisions

| Decision | Choice |
|----------|--------|
| Deployment | Cloud-only |
| Priority | Reliability and simplicity (over low latency) |
| Graphics | HTML-only (no After Effects integration) |
| UI approach | Modify existing Bridge (not greenfield) |
| Timeline | 6 months, 1 engineer initially |
| Amagi comparison | Not a target—reference was for existing plugin context only |
| Integrations (MAM, EPG, ad servers) | None as of now |
| Audit / compliance | Audit logs must be added to Bridge code |

### D. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-02-27 | — | First draft |
| 1.1 | 2025-02-27 | — | Stakeholder decisions; extend CasparCG (no migration); audit logs; 6mo/1 eng roadmap |
